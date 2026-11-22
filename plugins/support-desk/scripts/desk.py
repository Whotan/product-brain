#!/usr/bin/env python3
"""Support desk engine: one review page per Jira Service Desk project, rebuilt from Jira, and the
team's approvals applied back to Jira.

The config is the hub's brain.config.json > "support_desk" (the hub is the nearest folder up from the
current one that holds brain.config.json; --hub to override). Work files go to
<hub>/.work/support-desk/<run>/. Standard library only.

Commands (each reads and writes JSON files; nothing here talks to claude.ai, the skill does that):

  extract PAGE                      tickets + build note out of a page HTML  -> data.json
  fetch --since ISO | --open        Jira issues of the project (+ public comments) -> fetched.json
  refresh                           data.json + fetched.json -> data.json (mechanical fields) + changes.json
  merge --patch FILE                apply Claude's triage patch to data.json; emit db-ops.json (resets)
  build --built TEXT                data.json + template + hub brand/logo -> page.html
  plan --db DIR                     data.json + db dump -> plan.json (what /support-desk:apply would do)
  apply [--dry-run]                 plan.json -> Jira comments/transitions; log.json + db-ops-apply.json + data.json
  link --key K --issue I            link a created issue to ticket K (or --failed REASON); db-ops-link.json

The token is read from the environment variable named in support_desk.token_env (default
JIRA_PERSONAL_TOKEN), or from the "env" block of <hub>/.claude/settings.local.json. It is never printed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import base64

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "page", "template.html")

DEFAULTS = {
    "token_env": "JIRA_PERSONAL_TOKEN",
    "closed": ["Closed", "Resolved", "Done", "Canceled"],
    "type_flow": {},
    "default_flow": "default",
    "flow": {},
    "routes": {},
    "resolutions": {"Resolved": "Done", "Canceled": "Won't Do"},
    "allowed_placeholders": [],
    "apps": [["general", "General"]],
    "tags": ["bug", "feature", "question"],
    "team_users": [],
    "customer_label": "Customer",
    "linked_issue": None,
}

# Every ticket on the page carries these fields (reference/data.md describes each one).
REQUIRED = ["key", "app", "alsoApps", "pri", "cls", "type", "jira", "created", "tfa", "ten", "ask",
            "asken", "att", "thread", "checks", "truth", "move", "reply", "gloss", "tags",
            "suggest", "suggestWhy", "createdAt", "updatedAt", "lastReplyAt"]
CLASSES = ["Question", "Bug", "Feature request", "Usage/config", "Known", "Unclear"]
PRIORITIES = ["P1", "P2", "P3", "P4"]
VERDICTS = ["confirmed", "refuted", "cant"]   # the page shows "cant" as "can't tell"
AUTHORS = ["customer", "us"]   # who wrote a thread entry: the requester side, or the team
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------- hub and config

def find_hub(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, "brain.config.json")):
            return d
        up = os.path.dirname(d)
        if up == d:
            sys.exit("No brain.config.json in this folder or above: run this from inside the hub.")
        d = up


def load_config(hub):
    with open(os.path.join(hub, "brain.config.json"), encoding="utf-8") as f:
        full = json.load(f)
    sd = full.get("support_desk")
    if not sd:
        sys.exit("brain.config.json has no support_desk section. See reference/config.md in the plugin.")
    cfg = dict(DEFAULTS)
    cfg.update(sd)
    for k in ("jira_url", "project"):
        if not cfg.get(k):
            sys.exit(f"support_desk.{k} is missing in brain.config.json.")
    cfg["jira_url"] = cfg["jira_url"].rstrip("/")
    cfg.setdefault("title", f"{cfg['project']} Support Desk")
    cfg["_design"] = full.get("design") or {}
    return cfg


def token(hub, cfg):
    name = cfg["token_env"]
    v = os.environ.get(name)
    if not v:
        p = os.path.join(hub, ".claude", "settings.local.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                v = (json.load(f).get("env") or {}).get(name)
    if not v:
        sys.exit(f"No Jira token: set {name} in the environment or in the env block of "
                 ".claude/settings.local.json (the jira skill's setup does this). It is never printed.")
    return v


def rjson(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def wjson(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


# ---------------------------------------------------------------- small helpers

def stamp(iso):
    """Any Jira timestamp ('2026-11-18T16:17:20+0330', '2026-11-18T12:47:20.000+0000') -> UTC
    '2026-11-18T12:47:20', the page's format. The two Jira APIs answer in different zones, so never truncate."""
    if not iso:
        return ""
    s = re.sub(r"\.\d+", "", iso)
    try:
        return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z").astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return iso[:19]


def short_date(iso):
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MON[int(m) - 1]}"


def flow_targets(cfg, t):
    flow = cfg["flow"].get(cfg["type_flow"].get(t.get("type"), cfg["default_flow"]), {})
    return flow.get(t.get("jira"), [])


def strip_allowed(cfg, text):
    for p in cfg["allowed_placeholders"]:
        text = text.replace(f"[{p}]", "")
    return text


def has_placeholder(cfg, text):
    return bool(re.search(r"\[[^\]]+\]", strip_allowed(cfg, text or "")))


def is_closed(cfg, t):
    return t.get("jira") in cfg["closed"]


# ---------------------------------------------------------------- page <-> data

def extract_page(html):
    i = html.find("const T = ")
    if i < 0:
        sys.exit("This page has no 'const T = ' ticket array: is it a support-desk page?")
    i = html.index("[", i)
    tickets, end = json.JSONDecoder().raw_decode(html[i:])
    normalize(tickets)
    m = re.search(r'const BUILT = ("(?:[^"\\]|\\.)*")', html)
    return {"tickets": tickets, "built": json.loads(m.group(1)) if m else ""}


def normalize(tickets):
    """Pages built before this plugin called the requester side "clinic"."""
    for t in tickets:
        t["thread"] = [["customer" if r[0] == "clinic" else r[0]] + list(r[1:]) for r in t.get("thread", [])]
    return tickets


def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()


def build_page(hub, cfg, tickets, built, template=TEMPLATE):
    if not tickets:
        sys.exit("No tickets to build a page from.")
    normalize(tickets)
    problems = validate(cfg, tickets)
    if problems:
        sys.exit("Fix these before building:\n  " + "\n  ".join(problems))
    with open(template, encoding="utf-8") as f:
        h = f.read()
    brand_path = os.path.join(hub, cfg["_design"].get("build", "brand"), "brand.css")
    brand = ""
    if os.path.exists(brand_path):
        with open(brand_path, encoding="utf-8") as f:
            brand = f.read().replace("</", "<\\/")
    logo = cfg["_design"].get("logo") or {}
    if isinstance(logo, str):
        logo = {"light": logo}
    tags = []
    for cls, key in (("logo-light", "light"), ("logo-dark", "dark")):
        p = logo.get(key) or logo.get("light")
        if p and os.path.exists(os.path.join(hub, p)):
            tags.append(f'<img class="{cls}" src="{data_uri(os.path.join(hub, p))}" alt="" aria-hidden="true">')
    page_cfg = {
        "project": cfg["project"],
        "jiraUrl": cfg["jira_url"],
        "apps": cfg["apps"],
        "tags": cfg["tags"],
        "flow": cfg["flow"],
        "typeFlow": cfg["type_flow"],
        "defaultFlow": cfg["default_flow"],
        "closed": cfg["closed"],
        "allowedPlaceholders": cfg["allowed_placeholders"],
        "storePrefix": cfg["project"].lower() + ".",
        "customerLabel": cfg["customer_label"],
        "linkedIssue": ({"project": cfg["linked_issue"]["project"],
                         "types": cfg["linked_issue"].get("types") or ["Task"]} if cfg.get("linked_issue") else None),
    }
    title = cfg["title"].replace("&", "&amp;").replace("<", "&lt;")
    for k, v in (("__TITLE__", title), ("__BRAND__", brand), ("__LOGO__", "".join(tags)),
                 ("__TICKETS__", js(tickets)), ("__BUILT__", js(built)), ("__CONFIG__", js(page_cfg))):
        if h.count(k) != 1:
            sys.exit(f"Template slot {k} found {h.count(k)} times; expected once.")
        h = h.replace(k, v)
    return h


def validate(cfg, tickets):
    out, seen = [], set()
    apps = {a[0] for a in cfg["apps"]}
    tags = set(cfg["tags"])
    for t in tickets:
        k = t.get("key", "?")
        if k in seen:
            out.append(f"{k}: listed twice")
        seen.add(k)
        miss = [f for f in REQUIRED if f not in t]
        if miss:
            out.append(f"{k}: missing {', '.join(miss)}")
            continue
        if t["app"] not in apps:
            out.append(f"{k}: app '{t['app']}' is not one of {sorted(apps)}")
        if any(a not in apps for a in t["alsoApps"]):
            out.append(f"{k}: alsoApps has an unknown app")
        bad = [g for g in t["tags"] if g not in tags]
        if bad:
            out.append(f"{k}: unknown tags {bad} (support_desk.tags)")
        if t["pri"] not in PRIORITIES:
            out.append(f"{k}: pri must be one of {PRIORITIES}")
        if not (isinstance(t["cls"], str) and t["cls"].strip()):
            out.append(f"{k}: cls is empty (use one of {CLASSES})")
        for row in t["checks"]:
            if not (isinstance(row, list) and len(row) == 3 and row[1] in VERDICTS):
                out.append(f"{k}: each check is [evidence, {'|'.join(VERDICTS)}, finding]")
                break
        if not all(isinstance(r, list) and len(r) == 4 for r in t.get("links", [])):
            out.append(f"{k}: each link is [key, status, summary, relation]")
        for row in t["thread"]:
            if not (isinstance(row, list) and len(row) == 3 and row[0] in AUTHORS):
                out.append(f"{k}: each thread entry is [customer|us, date, summary]")
                break
        if t["suggest"] and cfg["flow"] and t["suggest"] not in flow_targets(cfg, t):
            out.append(f"{k}: suggest '{t['suggest']}' is not a move from '{t['jira']}' "
                       f"(allowed: {flow_targets(cfg, t)})")
    return out


# ---------------------------------------------------------------- Jira

class Jira:
    def __init__(self, base, tok):
        self.base = base
        self.h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json",
                  "Accept": "application/json"}

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method, headers=self.h,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")[:400]

    def ok(self, method, path, body=None):
        s, res = self.call(method, path, body)
        if s >= 300:
            sys.exit(f"Jira {method} {path} -> {s}: {res}")
        return res


FIELDS = ["summary", "description", "status", "issuetype", "created", "updated", "reporter", "attachment", "issuelinks"]


def issue_links(f):
    """[[key, status, summary, relation], ...] for every issue linked to this one."""
    out = []
    for l in f.get("issuelinks") or []:
        side, rel = ("outwardIssue", l["type"]["outward"]) if "outwardIssue" in l else ("inwardIssue", l["type"]["inward"])
        o = l.get(side) or {}
        of = o.get("fields") or {}
        out.append([o.get("key"), (of.get("status") or {}).get("name", ""), of.get("summary", ""), rel])
    return out


def fetch(j, cfg, since=None, only_open=False, keys=None):
    clauses = [f'project = "{cfg["project"]}"']
    if keys:
        clauses.append("key in (" + ",".join(keys) + ")")
    if since:
        # A day of slack: Jira reads the date in the token owner's time zone; refresh compares exact stamps.
        d = (dt.datetime.fromisoformat(since[:19]) - dt.timedelta(days=1)).strftime("%Y/%m/%d %H:%M")
        clauses.append(f'updated >= "{d}"')
    if only_open:
        clauses.append("statusCategory != Done")
    jql = " AND ".join(clauses) + " ORDER BY created DESC"
    issues, start = [], 0
    while True:
        res = j.ok("POST", "/rest/api/2/search", {"jql": jql, "fields": FIELDS, "startAt": start, "maxResults": 100})
        issues += res["issues"]
        start += len(res["issues"])
        if not res["issues"] or start >= res["total"]:
            break
    out = []
    for it in issues:
        f = it["fields"]
        k = it["key"]
        reporter = (f.get("reporter") or {}).get("name")
        customer = {reporter} if reporter else set()
        s, parts = j.call("GET", f"/rest/servicedeskapi/request/{k}/participant?limit=100")
        if s < 300 and parts:
            customer |= {p.get("name") for p in parts.get("values", [])}
        comments, cstart = [], 0
        while True:
            s, res = j.call("GET", f"/rest/servicedeskapi/request/{k}/comment?public=true&internal=false"
                                   f"&start={cstart}&limit=100")
            if s >= 300 or not res:
                break
            for c in res.get("values", []):
                who = (c.get("author") or {}).get("name")
                comments.append({
                    "id": c.get("id"),
                    "by": "us" if who in cfg["team_users"] or who not in customer else "customer",
                    "created": stamp((c.get("created") or {}).get("iso8601")),
                    "body": c.get("body") or "",
                })
            if res.get("isLastPage", True):
                break
            cstart += len(res.get("values", []))
        out.append({
            "key": k,
            "type": f["issuetype"]["name"],
            "status": f["status"]["name"],
            "summary": f.get("summary") or "",
            "description": f.get("description") or "",
            "createdAt": stamp(f.get("created")),
            "updatedAt": stamp(f.get("updated")),
            "attachments": [{"id": a.get("id"), "filename": a.get("filename"), "mimeType": a.get("mimeType")}
                            for a in (f.get("attachment") or [])],
            "comments": sorted(comments, key=lambda c: c["created"]),
            "links": issue_links(f),
        })
    return {"jql": jql, "fetchedAt": dt.datetime.now().isoformat(timespec="seconds"), "issues": out}


# ---------------------------------------------------------------- refresh: data + fetched -> changes

def since_auto(data):
    """Everything changed after the last fetch has a newer stamp than anything already on the page."""
    stamps = [s for t in data["tickets"] for s in (t.get("updatedAt"), t.get("lastReplyAt"), t.get("createdAt")) if s]
    if not stamps:
        sys.exit("The page has no timestamps: use --open for a first full fetch.")
    return max(stamps)


def att_text(n):
    return "" if not n else ("1 attachment" if n == 1 else f"{n} attachments")


def refresh(cfg, data, fetched):
    byk = {t["key"]: t for t in data["tickets"]}
    changes = {"new": [], "commented": [], "status": [], "unchanged": []}
    for it in fetched["issues"]:
        k = it["key"]
        last = it["comments"][-1]["created"] if it["comments"] else ""
        t = byk.get(k)
        if t is None:
            changes["new"].append({
                "key": k,
                "seed": {"key": k, "type": it["type"], "jira": it["status"], "created": short_date(it["createdAt"]),
                         "createdAt": it["createdAt"], "updatedAt": it["updatedAt"], "lastReplyAt": last,
                         "tfa": it["summary"], "ask": it["description"], "att": att_text(len(it["attachments"])),
                         "links": it.get("links", [])},
                "comments": it["comments"], "attachments": it["attachments"],
            })
            continue
        seen = max(t.get("lastReplyAt") or "", t.get("updatedAt") or "", t.get("createdAt") or "")
        fresh = [c for c in it["comments"] if c["created"] > seen and c["by"] == "customer"]
        moved = t["jira"] != it["status"]
        entry = {"key": k, "from": t["jira"], "to": it["status"]}
        t["jira"] = it["status"]
        t["updatedAt"] = max(t.get("updatedAt") or "", it["updatedAt"])
        t["lastReplyAt"] = max(t.get("lastReplyAt") or "", last)
        if "links" in it:
            t["links"] = it["links"]
        if fresh:
            changes["commented"].append({**entry, "comments": fresh, "attachments": it["attachments"]})
        elif moved:
            changes["status"].append(entry)
            # A suggestion made for the old status no longer applies.
            if t["suggest"] and t["suggest"] not in flow_targets(cfg, t):
                t["suggest"], t["suggestWhy"] = "", ""
        else:
            changes["unchanged"].append(k)
    return data, changes


# ---------------------------------------------------------------- merge: Claude's triage patch

def merge(cfg, data, patch, db_dir=None):
    """patch = {KEY: {field: value, ..., "thread_add": [[who, date, summary], ...]}}.
    A new key needs a full ticket (seed from changes.json + Claude's fields).
    Returns (data, db_ops): resets for rows whose draft or suggestion Claude replaced."""
    byk = {t["key"]: t for t in data["tickets"]}
    ops = []
    for k, p in patch.items():
        p = dict(p)
        add = p.pop("thread_add", [])
        answer = p.pop("_claude", None)  # Claude's answer to the reviewer's note, shown under the note
        if k in byk:
            t = byk[k]
            t.update(p)
        else:
            t = {"key": k, "alsoApps": [], "thread": [], "noreply": False, **p}
            data["tickets"].append(t)
            byk[k] = t
        t["thread"] = list(t.get("thread") or []) + list(add)
        if "reply" in p or "noreply" in p:
            row = {"key": k, "state": "noreply" if t.get("noreply") else "draft",
                   "note": "", "updatedAt": now_z(), "resetBy": "support-desk"}
            if answer:
                row["claude"] = answer
            ops.append(db_op(db_dir, "replies", k, "set", row))
        elif answer:
            ops.append(db_op(db_dir, "replies", k, "update", {"claude": answer, "note": ""}))
        if "suggest" in p:
            ops.append(db_op(db_dir, "moves", k, "delete", None))
    ops = [o for o in ops if o]
    return data, ops


def now_z():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def db_doc(db_dir, coll, k):
    if not db_dir:
        return None
    p = os.path.join(db_dir, coll, k + ".json")
    return rjson(p) if os.path.exists(p) else None


def db_op(db_dir, coll, k, op, data):
    """One ArtifactData batch entry. Writes to an existing row need its version: the entry carries
    "if_version": "FILL" and the skill fills it from the listing that produced the dump."""
    exists = db_doc(db_dir, coll, k) is not None
    if op == "delete" and not exists:
        return None
    e = {"op": op, "collection": coll, "doc_id": k}
    if data is not None:
        e["data"] = data
    if exists:
        e["if_version"] = "FILL"
    return e


# ---------------------------------------------------------------- plan + apply

def plan(cfg, data, db_dir):
    items = []
    for t in data["tickets"]:
        k = t["key"]
        r = db_doc(db_dir, "replies", k) or {}
        m = db_doc(db_dir, "moves", k) or {}
        state = r.get("state") or ("noreply" if t.get("noreply") else "draft")
        text = r["reply"] if isinstance(r.get("reply"), str) else t["reply"]
        item = {"key": k, "type": t["type"], "status": t["jira"], "reply": None, "to": None,
                "blocked": [], "note": (r.get("note") or "").strip(), "by": r.get("by") or m.get("by"),
                "replyState": state}
        if state == "approved" and not r.get("posted"):
            if not text.strip():
                item["blocked"].append("approved reply is empty")
            elif has_placeholder(cfg, text):
                item["blocked"].append("approved reply still has a [placeholder]")
            else:
                item["reply"] = text
        if m.get("state") == "approved" and not m.get("appliedAt") and m.get("to"):
            if m["to"] == t["jira"]:
                item["blocked"].append(f"already in {m['to']}")
            else:
                item["to"] = m["to"]
                if m.get("from") and m["from"] != t["jira"]:
                    item["blocked"].append(f"approved as a move from {m['from']}, but Jira now says {t['jira']}")
                    item["to"] = None
        lk = db_doc(db_dir, "links", k) or {}
        item["link"] = None
        if lk.get("state") == "requested" and not lk.get("issue"):
            if not cfg.get("linked_issue"):
                item["blocked"].append("a linked issue was requested but support_desk.linked_issue is not set")
            else:
                item["link"] = {"issueType": lk.get("issueType") or "Task", "brief": (lk.get("brief") or "").strip(),
                                "by": lk.get("by"), "project": cfg["linked_issue"]["project"]}
        if item["link"] or item["reply"] or item["to"] or item["blocked"] or (item["note"] and state not in ("posted", "closed")):
            items.append(item)
    return {"items": items}


def route(cfg, t_type, target):
    flow = cfg["type_flow"].get(t_type, cfg["default_flow"])
    return cfg["routes"].get(flow, {}).get(target)


def transition(j, cfg, key, target):
    s, tr = j.call("GET", f"/rest/api/2/issue/{key}/transitions")
    if s >= 300:
        return False, f"transitions {s}"
    cand = [x for x in tr["transitions"] if x["to"]["name"] == target]
    if not cand:
        return None, [x["to"]["name"] for x in tr["transitions"]]
    body = {"transition": {"id": cand[0]["id"]}}
    if target in cfg["resolutions"]:
        body["fields"] = {"resolution": {"name": cfg["resolutions"][target]}}
    s, res = j.call("POST", f"/rest/api/2/issue/{key}/transitions", body)
    return (s < 300), (None if s < 300 else f"{s} {res}")


def apply(j, cfg, data, the_plan, db_dir, dry=False):
    byk = {t["key"]: t for t in data["tickets"]}
    log, ops = [], []
    for it in the_plan["items"]:
        k = it["key"]
        L = {"key": k, "comment": None, "steps": [], "skipped": list(it["blocked"])}
        log.append(L)
        if it["reply"]:
            if dry:
                L["comment"] = "dry-run"
            else:
                s, res = j.call("POST", f"/rest/servicedeskapi/request/{k}/comment",
                                {"body": it["reply"], "public": True})
                if s >= 300:
                    L["comment"] = f"ERROR {s} {res}"
                    continue  # never move a ticket whose reply failed
                L["comment"] = res.get("id")
                r = db_doc(db_dir, "replies", k) or {}
                ops.append(db_op(db_dir, "replies", k, "update" if r else "set",
                                 {"key": k, "state": "posted", "reply": it["reply"],
                                  "posted": {"at": now_z(), "commentId": res.get("id"),
                                             "actions": f"Posted as public comment {res.get('id')}."}}))
        if it["to"]:
            target = it["to"]
            path = [target]
            if dry:
                L["steps"].append(f"dry-run -> {target}")
                continue
            ok, info = transition(j, cfg, k, target)
            if ok is None:
                path = route(cfg, it["type"], target)
                if not path:
                    L["steps"].append(f"no transition to {target}; available: {info}")
                    continue
                ok = True
                for step in path:
                    ok, info = transition(j, cfg, k, step)
                    L["steps"].append(f"{step}: {'ok' if ok else info}")
                    if not ok:
                        break
            else:
                L["steps"].append(f"{target}: {'ok' if ok else info}")
            if ok:
                frm = byk[k]["jira"]
                byk[k]["jira"] = target
                byk[k]["updatedAt"] = dt.datetime.now().isoformat(timespec="seconds")
                ops.append(db_op(db_dir, "moves", k, "update",
                                 {"appliedAt": now_z(), "appliedTo": target, "from": frm}))
    return data, log, [o for o in ops if o]


def link(j, cfg, data, key, issue, db_dir):
    """Link a newly created issue to support ticket `key`. Returns (data, db_op, message)."""
    li = cfg.get("linked_issue") or {}
    t = next((x for x in data["tickets"] if x["key"] == key), None)
    if t is None:
        sys.exit(f"{key} is not on the page.")
    s, iss = j.call("GET", f"/rest/api/2/issue/{issue}?fields=summary,status,issuelinks")
    if s >= 300:
        sys.exit(f"{issue} not found in Jira ({s}); nothing linked.")
    known = [l[0] for l in issue_links(iss["fields"])]
    if key not in known:
        s, res = j.call("POST", "/rest/api/2/issueLink",
                        {"type": {"name": li.get("link_type", "Relates")},
                         "inwardIssue": {"key": issue}, "outwardIssue": {"key": key}})
        if s >= 300:
            sys.exit(f"Linking {issue} to {key} failed: {s} {res}")
        msg = f"linked {issue} to {key}"
    else:
        msg = f"{issue} was already linked to {key}"
    s, mine = j.call("GET", f"/rest/api/2/issue/{key}?fields=issuelinks")  # the page shows links as the ticket sees them
    if s < 300:
        t["links"] = issue_links(mine["fields"])
    op = db_op(db_dir, "links", key, "update" if db_doc(db_dir, "links", key) else "set",
               {"key": key, "state": "created", "issue": issue, "createdAt": now_z()})
    return data, op, msg


def link_failed(key, reason, db_dir):
    return db_op(db_dir, "links", key, "update" if db_doc(db_dir, "links", key) else "set",
                 {"key": key, "state": "failed", "error": reason[:300], "updatedAt": now_z()})


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hub")
    ap.add_argument("--work", help="work folder (default <hub>/.work/support-desk/current)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("extract"); s.add_argument("page")
    s = sub.add_parser("fetch"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--since", help="ISO time, or 'auto': the newest activity on the page")
    g.add_argument("--open", action="store_true"); g.add_argument("--keys")
    sub.add_parser("refresh")
    s = sub.add_parser("merge"); s.add_argument("--patch", required=True); s.add_argument("--db")
    s = sub.add_parser("build"); s.add_argument("--built", required=True); s.add_argument("--out")
    sub.add_parser("check")
    s = sub.add_parser("plan"); s.add_argument("--db", required=True)
    s = sub.add_parser("apply"); s.add_argument("--db", required=True); s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("link"); s.add_argument("--key", required=True); s.add_argument("--db", required=True)
    g = s.add_mutually_exclusive_group(required=True); g.add_argument("--issue"); g.add_argument("--failed")
    a = ap.parse_args(argv)

    hub = find_hub(a.hub)
    cfg = load_config(hub)
    work = a.work or os.path.join(hub, ".work", "support-desk", "current")
    os.makedirs(work, exist_ok=True)
    W = lambda n: os.path.join(work, n)

    if a.cmd == "extract":
        with open(a.page, encoding="utf-8") as f:
            d = extract_page(f.read())
        print(wjson(W("data.json"), d), f"{len(d['tickets'])} tickets, built: {d['built']!r}")
    elif a.cmd == "fetch":
        j = Jira(cfg["jira_url"], token(hub, cfg))
        if a.since == "auto":
            a.since = since_auto(rjson(W("data.json")))
        res = fetch(j, cfg, since=a.since, only_open=a.open, keys=a.keys.split(",") if a.keys else None)
        print(wjson(W("fetched.json"), res), f"{len(res['issues'])} issues ({res['jql']})")
    elif a.cmd == "refresh":
        data, ch = refresh(cfg, rjson(W("data.json")), rjson(W("fetched.json")))
        wjson(W("data.json"), data)
        print(wjson(W("changes.json"), ch))
        print(json.dumps({k: (len(v)) for k, v in ch.items()}),
              "new:", [c["key"] for c in ch["new"]], "commented:", [c["key"] for c in ch["commented"]],
              "status:", [f"{c['key']} {c['from']}->{c['to']}" for c in ch["status"]])
    elif a.cmd == "merge":
        data, ops = merge(cfg, rjson(W("data.json")), rjson(a.patch), a.db)
        wjson(W("data.json"), data)
        print(wjson(W("db-ops.json"), ops), f"{len(ops)} db writes")
        probs = validate(cfg, data["tickets"])
        print("valid" if not probs else "PROBLEMS:\n  " + "\n  ".join(probs))
    elif a.cmd == "check":
        probs = validate(cfg, rjson(W("data.json"))["tickets"])
        print("valid" if not probs else "PROBLEMS:\n  " + "\n  ".join(probs))
        sys.exit(1 if probs else 0)
    elif a.cmd == "build":
        data = rjson(W("data.json"))
        data["built"] = a.built
        wjson(W("data.json"), data)
        out = a.out or W("page.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_page(hub, cfg, data["tickets"], a.built))
        n_open = sum(1 for t in data["tickets"] if not is_closed(cfg, t))
        print(out, f"{len(data['tickets'])} tickets, {n_open} open")
    elif a.cmd == "plan":
        p = plan(cfg, rjson(W("data.json")), a.db)
        print(wjson(W("plan.json"), p))
        for it in p["items"]:
            print(f"{it['key']:>9}  reply:{'yes' if it['reply'] else '-':3}  move:{it['to'] or '-':22}"
                  f"  {('BLOCKED: ' + '; '.join(it['blocked'])) if it['blocked'] else ''}"
                  f"{'  NOTE' if it['note'] else ''}")
    elif a.cmd == "apply":
        j = Jira(cfg["jira_url"], token(hub, cfg))
        data, log, ops = apply(j, cfg, rjson(W("data.json")), rjson(W("plan.json")), a.db, a.dry_run)
        if not a.dry_run:
            wjson(W("data.json"), data)
            wjson(W("db-ops-apply.json"), ops)
        print(wjson(W("log.json"), log))
        for L in log:
            print(L)
    elif a.cmd == "link":
        ops_path = W("db-ops-link.json")
        ops = rjson(ops_path) if os.path.exists(ops_path) else []
        ops = [o for o in ops if o["doc_id"] != a.key]
        if a.failed:
            ops.append(link_failed(a.key, a.failed, a.db))
            print(f"recorded: no issue created for {a.key}")
        else:
            j = Jira(cfg["jira_url"], token(hub, cfg))
            data, op, msg = link(j, cfg, rjson(W("data.json")), a.key, a.issue, a.db)
            wjson(W("data.json"), data)
            ops.append(op)
            print(msg)
        print(wjson(ops_path, ops))


if __name__ == "__main__":
    main()
