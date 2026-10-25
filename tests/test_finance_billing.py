"""Self-check for plugins/finance/skills/monthly-billing/scripts/billing.py (+ xlsx_read.py), standard library only.

Builds a throw-away hub with a made-up project ("Acme") and a small finance workbook, writes worklog records
the way `fetch` would, and checks what `init`, `build`, `audit` and `plan` (dry run) produce. Nothing touches
Jira, Tempo or Google Sheets.

Run: python3 tests/test_billing.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPT = ROOT / "plugins/finance/skills/monthly-billing/scripts/billing.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.dont_write_bytecode = True
import xlsx_read  # noqa: E402


def check(cond, what):
    if not cond:
        print("FAIL:", what)
        sys.exit(1)
    print("ok  ", what)


def col(n):
    return xlsx_read.get_column_letter(n)


def write_xlsx(path, sheets):
    """sheets: {name: {"A1": value or "=formula" or ("=formula", cached), ...}} -> a minimal .xlsx.
    ("shared", master_a1, formula, cached) writes a shared-formula cell, as spreadsheet exports do."""
    def cell(a1, v):
        if isinstance(v, tuple) and v[0] == "shared":
            _, si, f, cached = v
            body = f'<f t="shared" si="{si}"{f" ref=\"{a1}\"" if f else ""}>{escape(f or "")}</f>' if f else \
                f'<f t="shared" si="{si}"/>'
            return f'<c r="{a1}">{body}<v>{cached}</v></c>'
        if isinstance(v, tuple):
            f, cached = v
            return f'<c r="{a1}"><f>{escape(f[1:])}</f><v>{cached}</v></c>'
        if isinstance(v, str):
            return f'<c r="{a1}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
        return f'<c r="{a1}"><v>{v}</v></c>'

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        rels, entries = [], []
        for i, (name, cells) in enumerate(sheets.items(), 1):
            rows = {}
            for a1, v in cells.items():
                c, r = xlsx_read.coordinate_from_string(a1)
                rows.setdefault(r, []).append((xlsx_read.column_index_from_string(c), cell(a1, v)))
            xml = "".join(f'<row r="{r}">' + "".join(x for _, x in sorted(cs)) + "</row>" for r, cs in sorted(rows.items()))
            z.writestr(f"xl/worksheets/sheet{i}.xml",
                       '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       f"<sheetData>{xml}</sheetData></worksheet>")
            rels.append(f'<Relationship Id="rId{i}" Type="worksheet" Target="worksheets/sheet{i}.xml"/>')
            entries.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(rels) + "</Relationships>")
        z.writestr("xl/workbook.xml",
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(entries) + "</sheets></workbook>")


def finance_tab():
    """Acme: Jane has a bare "Planned" header and "BillableJane Doe" without a space; August's C2 leaves out
    Omar's Planned column (I); September holds figures; October has no row yet."""
    t = {"A1": "Name Project", "B1": "Month", "C1": "Total Planned in Jira (h)", "D1": "Total Logged in Jira (h)",
         "E1": "Total Billable in Jira (h)", "F1": "Planned", "G1": "Logged Jane Doe", "H1": "BillableJane Doe",
         "I1": "Planned Omar Ali", "J1": "Logged Omar Ali", "K1": "Billable Omar Ali",
         "A2": "Acme", "B2": "August", "C2": ("=F2", 10), "D2": ("=G2+J2", 12), "E2": ("=H2+K2", 11),
         "F2": 10, "G2": 7, "H2": 6, "I2": 5, "J2": 5, "K2": 5,
         "A3": "Acme", "B3": "September", "C3": ("shared", "0", "SUM(F3,I3)", 0),
         "D3": ("=SUM(G3,J3)", 10), "E3": ("=SUM(H3,K3)", 9), "G3": 10, "H3": 9,
         "A5": "Notes", "B5": "Budget"}
    return t


def worklog(**k):
    base = {"worklog_id": None, "epic_key": None, "epic": "", "summary": "Task", "status": "DONE",
            "project_name": "Acme", "account_key": "", "account_lead": "Lead", "account_customer": "Acme",
            "comment": "Did the thing"}
    base.update(k)
    base.setdefault("project_key", base["issue_key"].split("-")[0])
    return base


def config(**extra):
    cfg = {
        "id": "acme", "name": "Acme", "mode": "project",
        "rules": ["Hours in OPS with component Acme are billed with the project."],
        "jira": {"url": "https://jira.example.test", "projects": ["ACM"], "home_project": "ACM",
                 "extra_scope": [{"project": "OPS", "components": ["Acme"], "include": "bill"},
                                 {"project": "MEET", "components": ["Acme"], "include": "report"}]},
        "billing": {"weekend_days": ["Saturday", "Sunday"]},
        "finance": {"tab": "Acme", "header_rows": 1, "row_label": "Acme"},
        "people": [
            {"name": "Jane Doe", "role": "PM", "finance_columns": {"planned": "Planned", "logged": "Logged Jane Doe",
                                                                 "billable": "BillableJane Doe"}},
            {"name": "Omar Ali", "role": "BE", "finance_columns": {"planned": "Planned Omar Ali",
                                                                 "logged": "Logged Omar Ali",
                                                                 "billable": "Billable Omar Ali"}}],
    }
    cfg.update(extra)
    return cfg


def run(hub, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args, "--hub", str(hub)], capture_output=True, text=True,
                       cwd=hub)
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = Path(tempfile.mkdtemp(prefix="finance-test-"))
    hub = tmp / "hub"
    hub.mkdir()
    (hub / "brain.config.json").write_text(json.dumps({"version": "1.0.0", "hub_name": "acme-brain",
                                                       "finance": config()}, indent=2), encoding="utf-8")
    xlsx = tmp / "finance.xlsx"
    write_xlsx(xlsx, {"Acme": finance_tab(), "Other": {"A1": "x"}})

    # -- xlsx_read ------------------------------------------------------------------------------------------
    wb = xlsx_read.load_workbook(xlsx)
    check(wb.sheetnames == ["Acme", "Other"], "xlsx_read: sheet names in order")
    check(wb["Acme"]["C2"].value == "=F2" and wb["Acme"]["H1"].value == "BillableJane Doe", "xlsx_read: formulas, text")
    check(wb["Acme"]["C3"].value == "=SUM(F3,I3)", "xlsx_read: shared formula master")
    check(xlsx_read.load_workbook(xlsx, data_only=True)["Acme"]["D2"].value == 12, "xlsx_read: cached values")
    check(xlsx_read._shift("SUM(F3,$I3,\"F3\")", 2, 1) == 'SUM(G5,$I5,"F3")', "xlsx_read: shared formula shift")

    # -- records the way `fetch` writes them --------------------------------------------------------------
    oct_dir = hub / ".work" / "finance" / "acme" / "2026-10"
    oct_dir.mkdir(parents=True)
    recs = [
        worklog(issue_key="ACM-1", full_name="Jane Doe", billed_h=6, logged_h=8, started="2026-10-02 09:00",
                summary="Spec for checkout"),
        worklog(issue_key="ACM-2", full_name="Omar Ali", billed_h=5, logged_h=5, started="2026-10-03 10:00"),
        worklog(issue_key="ACM-2", full_name="Omar Ali", billed_h=0, logged_h=1, started="2026-10-04 10:00",
                comment=""),
        worklog(issue_key="OPS-9", full_name="Sam Lee", billed_h=2, logged_h=2, started="2026-10-05 11:00",
                scope="OPS/Acme", project_key="OPS"),
        worklog(issue_key="MEET-3", full_name="Jane Doe", billed_h=0, logged_h=3, started="2026-10-06 11:00",
                scope="MEET/Acme", project_key="MEET"),
    ]
    (oct_dir / "records.json").write_text(json.dumps(recs), encoding="utf-8")

    # -- build October: new month row, new columns for Sam, only empty cells --------------------------------
    code, out = run(hub, "build", "--month", "2026-10", "--finance", str(xlsx))
    check(code == 0, "build October runs" + ("" if code == 0 else f": {out[-400:]}"))
    rows = json.loads((oct_dir / "finance_new_rows.json").read_text())
    check(len(rows) == 1 and rows[0]["row"] == 4 and rows[0]["insert_after_row"] == 3,
          "missing October row is planned under September (row 4)")
    cols = json.loads((oct_dir / "finance_new_columns.json").read_text())
    check([c["person"] for c in cols] == ["Sam Lee"] and cols[0]["columns"] == {"planned": "L", "logged": "M", "billable": "N"},
          "Sam (billed through the shared project, no column) gets L:N")
    check(cols[0]["copy_format_from"] == "I:K", "new columns copy the right-most person's format")
    check(rows[0]["cells"]["D4"] == "=SUM(G4,J4,M4)", "new row's Logged total sums every person, Sam included")
    cells = json.loads((oct_dir / "finance_cells.json").read_text())
    check(cells.get("G4") == 8 and cells.get("H4") == 6, "Jane: Logged 8 (incl. non-billable), Billable 6")
    check(cells.get("J4") == 6 and cells.get("K4") == 5, "Omar: Logged counts the non-billable hour (6), Billable 5")
    check(cells.get("M4") == 2 and cells.get("N4") == 2, "Sam's shared-project hours are billed with the project")
    check(not any(v == 3 for v in cells.values()), "meeting project (report only) is not billed or logged")
    report = (oct_dir / "report.md").read_text(encoding="utf-8")
    check("Changes to apply" in report and "Insert row 4" in report and "Add columns for Sam Lee" in report,
          "report opens with the changes to apply")
    check("Worklogs of Jane Doe not (fully) billed" in report and "https://jira.example.test/browse/ACM-1" in report,
          "logged-but-not-billed lists the worklogs with links")
    check("MEET/Acme" in report, "report-only scope is listed in the report")
    hl = json.loads((oct_dir / "highlights.json").read_text(encoding="utf-8"))
    check(len(hl["picked"]) == 2, "two highlights picked")

    # -- build September: equal cells skipped, a differing value is never overwritten -----------------------
    sep_dir = oct_dir.parent / "2026-09"
    sep_dir.mkdir()
    (sep_dir / "records.json").write_text(json.dumps([
        worklog(issue_key="ACM-1", full_name="Jane Doe", billed_h=8, logged_h=10, started="2026-09-02 09:00")]),
        encoding="utf-8")
    code, out = run(hub, "build", "--month", "2026-09", "--finance", str(xlsx))
    check(code == 0, "build September runs")
    cells = json.loads((sep_dir / "finance_cells.json").read_text())
    held = json.loads((sep_dir / "finance_compare.json").read_text())["not_written"]
    check("G3" not in cells and "H3" not in cells, "existing September values are not written again")
    check(held == [{"cell": "H3", "finance": 9, "jira": 8}], "a differing value is held and flagged, not overwritten")
    fixes = json.loads((sep_dir / "finance_formula_fixes.json").read_text())
    check(fixes == [], "September totals already cover every person: no fix")

    # -- audit flags the incomplete August formula, changes nothing ----------------------------------------
    code, out = run(hub, "audit", "--month", "2026-10", "--finance", str(xlsx), "--months", "2")
    check(code == 0 and "C2 `=F2` leaves out planned column(s) I" in out, "audit flags August's C2")

    # -- adjustments: a note-only entry adds a note and changes no value -----------------------------------
    adj = tmp / "adjust.json"
    adj.write_text(json.dumps([{"person": "Jane Doe", "reason": "Agreed: spec rework not billed"}]))
    run(hub, "build", "--month", "2026-10", "--finance", str(xlsx), "--adjust", str(adj))
    comp = json.loads((oct_dir / "finance_compare.json").read_text())
    check(comp["notes"] == {"H4": "Logged 8, billable 6. Agreed: spec rework not billed"}, "note-only adjustment")

    # -- SLA invoiceable: proposal, the PM's split, and a split that doesn't add up -------------------------
    sla = config(billing={"sla_reserved_hours": 2}, preferences={"sla_reserved_from": ["PM"]})
    for p, c in zip(sla["people"], ("O", "P")):
        p["finance_columns"]["invoiceable"] = f"Invoiceable {p['name']}"
    sla_tab = dict(finance_tab(), O1="Invoiceable Jane Doe", P1="Invoiceable Omar Ali", Q1="Acme Invoiceable")
    sla_xlsx = tmp / "sla.xlsx"
    write_xlsx(sla_xlsx, {"Acme": sla_tab})
    sla_cfg = tmp / "sla.json"
    sla_cfg.write_text(json.dumps(sla), encoding="utf-8")
    code, out = run(hub, "build", "--config", str(sla_cfg), "--month", "2026-10", "--finance", str(sla_xlsx))
    check(code == 0 and "PROPOSAL only" in out and "| Jane Doe | PM | 6.0 | 4.0 | 2.0 |" in out,
          "SLA proposal takes the reserved 2 h from the PM")
    split = tmp / "split.json"
    split.write_text(json.dumps({"_source": "pm", "Jane Doe": 5, "Omar Ali": 4, "Sam Lee": 2}))
    code, out = run(hub, "build", "--config", str(sla_cfg), "--month", "2026-10", "--finance", str(sla_xlsx),
                    "--invoiceable", str(split))
    cells = json.loads((oct_dir / "finance_cells.json").read_text())
    check(cells.get("O4") == 5 and cells.get("P4") == 4, "the PM's split is written to the Invoiceable columns")
    bad = tmp / "bad-split.json"
    bad.write_text(json.dumps({"_source": "pm", "Jane Doe": 6, "Omar Ali": 5, "Sam Lee": 2}))
    code, out = run(hub, "build", "--config", str(sla_cfg), "--month", "2026-10", "--finance", str(sla_xlsx),
                    "--invoiceable", str(bad))
    check("but the invoiceable split sums to 13.0 h" in out, "a split that doesn't add up is reported")

    # -- init reads the tab: bare "Planned", "BillableX", a total column; writes the hub config -------------
    code, out = run(hub, "init", "--config", str(tmp / "new.json"), "--finance", str(sla_xlsx), "--tab", "Acme",
                    "--name", "Acme")
    d = json.loads(out)
    people = {p["name"]: p["finance_columns"] for p in d["draft"]["people"]}
    check(people.get("Jane Doe", {}).get("planned") == "Planned" and people["Jane Doe"]["billable"] == "BillableJane Doe",
          "init: bare Planned and BillableX belong to Jane")
    check("Acme" not in people and any(u["header"] == "Acme Invoiceable" for u in d["unread_headers"]),
          "init: a total column is not taken for a person")
    check(d["draft"]["mode"] == "project" and d["draft"]["finance"]["row_label"] == "Acme",
          "init: project mode and row label read from the tab")
    before = (hub / "brain.config.json").read_text(encoding="utf-8")
    run(hub, "init", "--finance", str(xlsx), "--tab", "Acme")
    check((hub / "brain.config.json").read_text(encoding="utf-8") == before, "init without --write changes nothing")

    # -- plan (dry run): Planned cells in the new row, no Tempo call needed for the cells -------------------
    nov = tmp / "plan.json"
    nov.write_text(json.dumps([{"person": "Jane Doe", "hours": 20}, {"person": "Omar Ali", "hours": 40}]))
    # plan's finance part only (the Tempo part needs Jira): call the function directly
    sys.argv = ["billing.py"]
    import importlib.util
    spec = importlib.util.spec_from_file_location("billing", SCRIPT)
    billing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(billing)
    billing.CFG = config()
    cells, problems, new_rows = billing.plan_finance_cells(json.loads(nov.read_text()), "2026-11", str(xlsx))
    check(new_rows and new_rows[0]["row"] == 4 and cells == {"F4": 20, "I4": 40},
          "plan: a missing November row is planned and the Planned cells go in it")

    # -- outside a hub -------------------------------------------------------------------------------------
    p = subprocess.run([sys.executable, str(SCRIPT), "build", "--month", "2026-10"], capture_output=True, text=True,
                       cwd=tmp)
    check(p.returncode != 0 and "No brain.config.json" in p.stderr, "outside a hub: a clear message")
    check(not list(SCRIPT.parent.glob("__pycache__")), "no __pycache__ left next to the scripts")
    shutil.rmtree(tmp, ignore_errors=True)
    print("all checks passed")


if __name__ == "__main__":
    main()
