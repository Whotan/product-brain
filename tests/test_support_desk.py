"""Self-check for plugins/support-desk/scripts/desk.py, standard library only.

Builds a throw-away hub with a made-up service desk project ("ACS"), then checks the page round trip
(build -> extract), refresh (new tickets, clinic comments, status changes), merge (db resets), plan
(approvals, placeholders, stale moves) and apply against a fake Jira. Nothing touches a real Jira.

Run: python3 tests/test_support_desk.py
"""

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "plugins/support-desk/scripts/desk.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.dont_write_bytecode = True
import desk  # noqa: E402


def check(cond, what):
    if not cond:
        print("FAIL:", what)
        sys.exit(1)
    print("ok  ", what)


CONFIG = {
    "jira_url": "https://jira.example.test/",
    "project": "ACS",
    "apps": [["general", "General"], ["web", "Web app"]],
    "tags": ["bug", "feature"],
    "type_flow": {"Support": "support"},
    "default_flow": "dev",
    "flow": {
        "dev": {"Waiting for support": ["Ready for Develop", "Waiting for customer"],
                "Waiting for customer": ["Waiting for support", "Closed"]},
        "support": {"Waiting for support": ["Resolved", "Canceled"], "Resolved": ["Closed"]},
    },
    "routes": {"dev": {"Closed": ["Waiting for customer", "Closed"]}},
    "allowed_placeholders": ["client"],
}


def ticket(key, **kw):
    t = {"key": key, "app": "web", "alsoApps": [], "pri": "P2", "cls": "Bug", "type": "Bug",
         "jira": "Waiting for support", "created": "1 Nov", "tfa": "x", "ten": "x", "ask": "x", "asken": "x",
         "att": "", "thread": [["customer", "1 Nov", "asked"]], "checks": [["a.php:1", "confirmed", "yes"]],
         "truth": "t", "move": "m", "reply": "hello", "gloss": "g", "noreply": False, "tags": ["bug"],
         "suggest": "Ready for Develop", "suggestWhy": "w", "createdAt": "2026-11-01T10:00:00",
         "updatedAt": "2026-11-02T10:00:00", "lastReplyAt": "2026-11-02T10:00:00"}
    t.update(kw)
    return t


class FakeJira:
    """Answers the calls desk.apply makes, from a status table, and records what was sent."""

    def __init__(self, status, edges):
        self.status, self.edges, self.sent = status, edges, []

    def call(self, method, path, body=None):
        self.sent.append((method, path, body))
        key = path.split("/")[4] if "servicedeskapi" in path else path.split("/")[5]
        if path.endswith("/comment"):
            return (201, {"id": "c-" + key})
        if method == "GET":
            return 200, {"transitions": [{"id": str(i), "to": {"name": n}}
                                         for i, n in enumerate(self.edges.get(self.status[key], []))]}
        target = self.edges[self.status[key]][int(body["transition"]["id"])]
        self.status[key] = target
        return 204, None


def main():
    tmp = Path(tempfile.mkdtemp())
    hub = tmp / "hub"
    (hub / "brand").mkdir(parents=True)
    (hub / "brand/brand.css").write_text(":root{--ds-primary:#123456}", encoding="utf-8")
    (hub / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    (hub / "brain.config.json").write_text(json.dumps(
        {"design": {"logo": {"light": "logo.svg"}}, "support_desk": CONFIG}), encoding="utf-8")
    cfg = desk.load_config(str(hub))
    check(cfg["jira_url"] == "https://jira.example.test", "jira_url loses its trailing slash")
    check(cfg["title"] == "ACS Support Desk", "title defaults from the project key")

    # ---- page round trip
    tickets = [ticket("ACS-1"), ticket("ACS-2", type="Support", suggest="Resolved", reply="see </script> [client]")]
    html = desk.build_page(str(hub), cfg, tickets, "built today")
    check("__" not in html.split("const T")[0][-50:] and "__TICKETS__" not in html, "every slot filled")
    check("--ds-primary:#123456" in html, "hub brand.css inlined")
    check('class="logo-dark"' in html and "data:image/svg+xml;base64," in html, "logo inlined (dark falls back to light)")
    check("</script> [client]" not in html, "ticket text cannot close the script tag")
    back = desk.extract_page(html)
    check(back["tickets"] == tickets and back["built"] == "built today", "extract returns exactly what was built")
    check(desk.validate(cfg, [ticket("ACS-3", app="mobile", suggest="Closed")]) and True, "validate catches bad app/suggest")
    bad = desk.validate(cfg, [ticket("ACS-3", app="mobile", suggest="Closed")])
    check(any("app 'mobile'" in b for b in bad) and any("suggest 'Closed'" in b for b in bad), "validate names both problems")

    # ---- refresh
    data = {"tickets": tickets, "built": "x"}
    fetched = {"issues": [
        {"key": "ACS-1", "type": "Bug", "status": "Waiting for support", "summary": "", "description": "",
         "createdAt": "2026-11-01T10:00:00", "updatedAt": "2026-11-05T09:00:00", "attachments": [],
         "comments": [{"by": "us", "created": "2026-11-02T10:00:00", "body": "old"},
                      {"by": "customer", "created": "2026-11-05T09:00:00", "body": "still broken"}]},
        {"key": "ACS-2", "type": "Support", "status": "Resolved", "summary": "", "description": "",
         "createdAt": "2026-11-01T10:00:00", "updatedAt": "2026-11-04T09:00:00", "attachments": [], "comments": []},
        {"key": "ACS-9", "type": "Bug", "status": "Waiting for support", "summary": "New one", "description": "desc",
         "createdAt": "2026-11-06T08:00:00", "updatedAt": "2026-11-06T08:00:00",
         "attachments": [{"id": "1"}, {"id": "2"}], "comments": []},
    ]}
    data, ch = desk.refresh(cfg, data, fetched)
    check([c["key"] for c in ch["commented"]] == ["ACS-1"] and len(ch["commented"][0]["comments"]) == 1,
          "only the customer's new comment counts")
    check([c["key"] for c in ch["status"]] == ["ACS-2"], "status-only change reported")
    t2 = [t for t in data["tickets"] if t["key"] == "ACS-2"][0]
    check(t2["jira"] == "Resolved" and t2["suggest"] == "", "status updated; suggestion for the old status dropped")
    seed = ch["new"][0]["seed"]
    check(seed["key"] == "ACS-9" and seed["created"] == "6 Nov" and seed["att"] == "2 attachments", "new ticket seeded")

    # ---- merge
    db = tmp / "db"
    (db / "replies").mkdir(parents=True)
    (db / "moves").mkdir()
    (db / "replies/ACS-1.json").write_text(json.dumps({"state": "approved", "reply": "old"}))
    (db / "moves/ACS-1.json").write_text(json.dumps({"state": "approved", "to": "Ready for Develop"}))
    new9 = {**seed, "app": "web", "pri": "P3", "cls": "Question", "ten": "New one", "asken": "desc", "checks": [],
            "truth": "t", "move": "m", "reply": "hi", "gloss": "g", "tags": [], "suggest": "", "suggestWhy": "",
            "thread_add": [["customer", "6 Nov", "asked"]]}
    patch = {"ACS-1": {"reply": "new draft", "suggest": "Waiting for customer",
                       "thread_add": [["customer", "5 Nov", "still broken"]]}, "ACS-9": new9}
    data, ops = desk.merge(cfg, data, patch, str(db))
    t1 = [t for t in data["tickets"] if t["key"] == "ACS-1"][0]
    check(t1["thread"][-1][2] == "still broken" and t1["reply"] == "new draft", "patch applied, thread appended")
    check({(o["op"], o["collection"], o["doc_id"]) for o in ops} ==
          {("set", "replies", "ACS-1"), ("delete", "moves", "ACS-1"), ("set", "replies", "ACS-9")},
          "db resets: reply row reset, stale move deleted, no delete for a missing row")
    check(all(o.get("if_version") == "FILL" for o in ops if o["doc_id"] == "ACS-1")
          and "if_version" not in [o for o in ops if o["doc_id"] == "ACS-9"][0], "existing rows need a version")
    check(desk.validate(cfg, data["tickets"]) == [], "merged data is valid")

    # ---- plan
    for f in (db / "replies").iterdir():
        f.unlink()
    for f in (db / "moves").iterdir():
        f.unlink()
    data = {"tickets": [ticket("ACS-1"), ticket("ACS-2", type="Support", jira="Waiting for support", suggest="Resolved"),
                        ticket("ACS-3"), ticket("ACS-4", jira="Waiting for customer", suggest="Closed"),
                        ticket("ACS-5")]}
    w = lambda c, k, d: (db / c / f"{k}.json").write_text(json.dumps(d))
    w("replies", "ACS-1", {"state": "approved", "reply": "Dear [client], fixed."})
    w("moves", "ACS-1", {"state": "approved", "to": "Ready for Develop", "from": "Waiting for support", "by": "u_1"})
    w("replies", "ACS-2", {"state": "approved", "reply": "on [date]"})
    w("replies", "ACS-3", {"state": "draft", "note": "say it ships Friday"})
    w("moves", "ACS-3", {"state": "approved", "to": "Ready for Develop", "from": "Ready for Develop"})
    w("moves", "ACS-4", {"state": "approved", "to": "Closed", "from": "Waiting for customer"})
    w("replies", "ACS-5", {"state": "posted", "reply": "done", "posted": {"at": "x"}})
    p = {i["key"]: i for i in desk.plan(cfg, data, str(db))["items"]}
    check(p["ACS-1"]["reply"] == "Dear [client], fixed." and p["ACS-1"]["to"] == "Ready for Develop"
          and p["ACS-1"]["by"] == "u_1", "approved reply + move planned; allowed placeholder passes")
    check(p["ACS-2"]["reply"] is None and "placeholder" in p["ACS-2"]["blocked"][0], "a [placeholder] blocks posting")
    check(p["ACS-3"]["to"] is None and "Jira now says" in p["ACS-3"]["blocked"][0] and p["ACS-3"]["note"],
          "move approved from an old status is blocked; the note is surfaced")
    check("ACS-5" not in p, "posted reply is not planned again")

    # ---- apply (fake Jira)
    fj = FakeJira({"ACS-1": "Waiting for support", "ACS-4": "Waiting for customer"},
                  {"Waiting for support": ["Ready for Develop", "Waiting for customer"],
                   "Waiting for customer": ["Waiting for support", "Closed"]})
    the_plan = {"items": [p["ACS-1"], p["ACS-4"], p["ACS-2"]]}
    data2, log, ops = desk.apply(fj, cfg, data, the_plan, str(db))
    L = {x["key"]: x for x in log}
    check(L["ACS-1"]["comment"] == "c-ACS-1" and L["ACS-1"]["steps"] == ["Ready for Develop: ok"], "reply posted, then moved")
    check(fj.status["ACS-4"] == "Closed", "direct transition taken")
    check(not any(path.endswith("ACS-2/comment") for _, path, _ in fj.sent), "blocked reply never sent")
    check({(o["collection"], o["doc_id"]) for o in ops} == {("replies", "ACS-1"), ("moves", "ACS-1"), ("moves", "ACS-4")},
          "db write-backs for what happened")
    check([t for t in data2["tickets"] if t["key"] == "ACS-1"][0]["jira"] == "Ready for Develop", "page data follows Jira")

    # routed move: Waiting for support -> Closed through Waiting for customer
    fj = FakeJira({"ACS-7": "Waiting for support"},
                  {"Waiting for support": ["Waiting for customer"], "Waiting for customer": ["Closed"]})
    data = {"tickets": [ticket("ACS-7")]}
    _, log, _ = desk.apply(fj, cfg, data, {"items": [{"key": "ACS-7", "type": "Bug", "reply": None, "to": "Closed",
                                                      "blocked": []}]}, str(db))
    check(fj.status["ACS-7"] == "Closed" and log[0]["steps"] == ["Waiting for customer: ok", "Closed: ok"],
          "configured route used when there is no direct transition")
    # note answers and the automatic fetch window
    (db / "replies/ACS-7.json").write_text(json.dumps({"state": "draft", "note": "why?"}))
    _, ops = desk.merge(cfg, {"tickets": [ticket("ACS-7")]}, {"ACS-7": {"_claude": "Because."}}, str(db))
    check(ops == [{"op": "update", "collection": "replies", "doc_id": "ACS-7",
                   "data": {"claude": "Because.", "note": ""}, "if_version": "FILL"}],
          "an answer to a note alone updates the row without resetting the draft")
    check(desk.since_auto({"tickets": [ticket("ACS-1", lastReplyAt="2026-11-09T01:00:00")]}) == "2026-11-09T01:00:00",
          "--since auto starts at the newest activity on the page")
    # ---- linked issues
    check("linkedIssue\":null" in html.replace(" ", ""), "no linked_issue config: the page hides the button")
    cfg2 = desk.load_config(str(hub))
    cfg2["linked_issue"] = {"project": "DEV", "types": ["Task", "Bug"], "link_type": "Relates"}
    html2 = desk.build_page(str(hub), cfg2, [ticket("ACS-1", links=[["DEV-1", "Done", "old fix", "relates to"]])], "b")
    check('"linkedIssue":{"project":"DEV","types":["Task","Bug"]}' in html2.replace(" ", ""), "linked_issue reaches the page")
    check(desk.validate(cfg2, [ticket("ACS-1", links=[["DEV-1"]])]) != [], "malformed links rejected")
    (db / "links").mkdir(exist_ok=True)
    (db / "links/ACS-1.json").write_text(json.dumps({"state": "requested", "issueType": "Bug", "brief": " cover filters ", "by": "u_2"}))
    (db / "links/ACS-2.json").write_text(json.dumps({"state": "cancelled", "issueType": "Task"}))
    data = {"tickets": [ticket("ACS-1"), ticket("ACS-2")]}
    for f in list((db / "replies").iterdir()) + list((db / "moves").iterdir()):
        f.unlink()
    p = {i["key"]: i for i in desk.plan(cfg2, data, str(db))["items"]}
    check(p["ACS-1"]["link"] == {"issueType": "Bug", "brief": "cover filters", "by": "u_2", "project": "DEV"}
          and "ACS-2" not in p, "a requested link is planned; a cancelled one is not")
    p = {i["key"]: i for i in desk.plan(cfg, data, str(db))["items"]}
    check(p["ACS-1"]["link"] is None and "linked_issue is not set" in p["ACS-1"]["blocked"][0],
          "a request without linked_issue config is blocked, not guessed")

    class LinkJira:
        def __init__(self):
            self.links, self.sent = set(), []

        def call(self, method, path, body=None):
            self.sent.append((method, path, body))
            if method == "POST":
                self.links.add((body["inwardIssue"]["key"], body["outwardIssue"]["key"]))
                return 201, None
            k = path.split("/")[5].split("?")[0]
            if k == "DEV-404":
                return 404, "nope"
            other = [a if b == k else b for a, b in self.links if k in (a, b)]
            return 200, {"fields": {"summary": "s", "status": {"name": "To Do"}, "issuelinks": [
                {"type": {"inward": "relates to", "outward": "relates to"},
                 "outwardIssue": {"key": o, "fields": {"summary": "x", "status": {"name": "To Do"}}}} for o in other]}}

    lj = LinkJira()
    data2, op, msg = desk.link(lj, cfg2, data, "ACS-1", "DEV-9", str(db))
    check(("DEV-9", "ACS-1") in lj.links and msg == "linked DEV-9 to ACS-1", "issue link created")
    check(data2["tickets"][0]["links"] == [["DEV-9", "To Do", "x", "relates to"]], "page links refreshed from Jira")
    check(op["op"] == "update" and op["data"]["state"] == "created" and op["data"]["issue"] == "DEV-9"
          and op["if_version"] == "FILL", "links row marked created")
    _, _, msg = desk.link(lj, cfg2, data2, "ACS-1", "DEV-9", str(db))
    check(msg.endswith("already linked to ACS-1") and sum(1 for m, *_ in lj.sent if m == "POST") == 1,
          "linking twice does not create a second link")
    try:
        desk.link(lj, cfg2, data2, "ACS-1", "DEV-404", str(db))
        check(False, "missing issue stops")
    except SystemExit as e:
        check("not found" in str(e), "a missing issue is never linked")
    check(desk.link_failed("ACS-1", "cancelled by user", str(db))["data"]["state"] == "failed", "failure recorded")
    print("all support-desk checks passed")


if __name__ == "__main__":
    main()
