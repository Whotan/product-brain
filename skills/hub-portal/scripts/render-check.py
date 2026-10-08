#!/usr/bin/env python3
"""Serve the built portal and fail on page errors, horizontal overflow or a dead library.

    python render-check.py [--hub <path>]

Serves <portal.out> over HTTP (the library fetches md/*.json, which a file:// page cannot),
then loads it at 1280 and 390 px wide in light and dark and prints one line per case:

    PASS|WARN|FAIL render <width> <theme> — <detail> — <remedy>

Each case opens the Library tab and the first document in its list, so a broken bundle or a
renderer error shows up here rather than in front of a reader. Screenshots of every case
land in <portal.out>-shots/ for the one look before publishing. Exit 1 on any FAIL.

An unreachable CDN (the Markdown renderer loads from cdnjs) is a WARN, not a FAIL: the page
still renders and shows documents as plain text, but Markdown rendering was not verified.

Needs the Python `playwright` package. If it is not importable, or no browser can be
launched, it prints a WARN that the render was NOT checked and exits 0 - it never reports
a pass it did not measure. Browser resolution: $UX_EXECUTABLE_PATH or
$PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH, else Playwright's own browser, else Edge.
"""

import argparse
import functools
import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path

sys.dont_write_bytecode = True
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WIDTHS = (1280, 390)
THEMES = ("light", "dark")
OVERFLOW_JS = """() => {
  const d = document.documentElement, W = window.innerWidth;
  if (d.scrollWidth <= W) return {sw: d.scrollWidth, w: W, culprits: []};
  const clips = el => { for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX; if (o === 'hidden' || o === 'auto' || o === 'scroll' || o === 'clip') return true; }
    return false; };
  const wide = [...document.body.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > W + 1 && !clips(e));
  const outer = wide.filter(e => !wide.includes(e.parentElement));
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].join('.') : '');
  return {sw: d.scrollWidth, w: W, culprits: outer.slice(0, 4).map(e => name(e) + ' (right ' + Math.round(e.getBoundingClientRect().right) + 'px)')};
}"""


def line(level, name, detail, remedy=""):
    print("%s %s — %s%s" % (level, name, detail, (" — " + remedy) if remedy else ""))


def find_hub(start):
    d = Path(start).resolve()
    for p in [d, *d.parents]:
        if (p / "brain.config.json").is_file():
            return p
    return None


def launch(pw):
    exe = os.environ.get("UX_EXECUTABLE_PATH") or os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
    tries = ([{"executable_path": exe}] if exe else []) + [{}, {"channel": "msedge"}]
    why = []
    for kw in tries:
        try:
            return pw.chromium.launch(**kw), None
        except Exception as exc:
            why.append("%s: %s" % (kw or "default", str(exc).splitlines()[0]))
    return None, "; ".join(why)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hub", default=".")
    args = ap.parse_args()
    hub = find_hub(args.hub)
    if hub is None:
        print("ERROR no brain.config.json at or above %s - pass --hub" % Path(args.hub).resolve())
        return 2
    cfg = json.loads((hub / "brain.config.json").read_text(encoding="utf-8"))
    root = (hub / (cfg.get("portal") or {}).get("out", ".work/hub-portal")).resolve()
    if not (root / "index.html").is_file():
        line("FAIL", "render", "%s has no index.html" % root, "run build.py first")
        return 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        line("WARN", "render", "NOT checked: the Python playwright package is not installed",
             "pip install playwright, or check it by hand at 1280 and 390 px in both themes")
        return 0

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/index.html" % srv.server_address[1]
    shots = root.parent / (root.name + "-shots")
    shots.mkdir(exist_ok=True)
    fails = warns = 0
    try:
        with sync_playwright() as pw:
            browser, why = launch(pw)
            if browser is None:
                line("WARN", "render", "NOT checked: no browser could be launched (%s)" % why,
                     "set UX_EXECUTABLE_PATH to an installed Chromium or headless-shell binary")
                return 0
            for width in WIDTHS:
                for theme in THEMES:
                    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=theme)
                    pg, errs = ctx.new_page(), []
                    pg.on("pageerror", lambda e, errs=errs: errs.append("page error: %s" % e))
                    net = []
                    pg.on("console", lambda m, errs=errs: errs.append("console: %s" % m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
                    pg.on("requestfailed", lambda r, net=net: net.append(r.url.split("/")[2]) if not r.url.startswith(base.rsplit("/", 1)[0]) else None)
                    name = "render %d %s" % (width, theme)
                    try:
                        # The page renders itself from inline data; external fonts and the
                        # Markdown library may still be loading, so wait for the page, not the network.
                        pg.goto(base + "#status", wait_until="commit", timeout=60000)
                        pg.wait_for_selector("#v-status", timeout=30000)
                        pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
                        pg.wait_for_timeout(300)
                        ov = pg.evaluate(OVERFLOW_JS)
                        pg.screenshot(path=str(shots / ("%d-%s-status.png" % (width, theme))))
                        pg.evaluate("() => { location.hash = 'library'; }")
                        pg.wait_for_selector("#l-tree .doclink", timeout=30000)
                        pg.wait_for_function("() => !/loading/.test(document.querySelector('#l-count').textContent)", timeout=60000)
                        count = pg.inner_text("#l-count")
                        pg.click("#l-tree .doclink")
                        pg.wait_for_selector("#r-body .md, #r-body .withheld", timeout=30000)
                        rendered = bool(pg.query_selector("#r-body .md"))
                        if not pg.evaluate("() => !!(window.marked && window.DOMPurify)"):
                            net.append("cdnjs.cloudflare.com (still loading)")
                        pg.screenshot(path=str(shots / ("%d-%s-library.png" % (width, theme))))
                    except Exception as exc:
                        ctx.close()
                        fails += 1
                        line("FAIL", name, "the page did not finish rendering: %s" % str(exc).splitlines()[0],
                             "open the built page in a browser and check its console")
                        continue
                    ctx.close()
                    if errs:
                        fails += 1
                        line("FAIL", name, "; ".join(errs[:3]), "fix the script error")
                    elif ov["sw"] > ov["w"]:
                        fails += 1
                        line("FAIL", name, "horizontal overflow: scrollWidth %d > %d; outermost: %s"
                             % (ov["sw"], ov["w"], ", ".join(ov["culprits"]) or "not isolated"),
                             "let the element wrap or scroll inside itself")
                    elif "could not load" in count or not rendered:
                        fails += 1
                        line("FAIL", name, "the library did not load its documents (%s)" % count,
                             "check that md/*.json sits beside index.html")
                    elif net:
                        warns += 1
                        line("WARN", name, "layout and library checked, but %s could not be reached from this machine, "
                             "so Markdown rendering was NOT verified" % ", ".join(sorted(set(net))),
                             "re-run when the network is back, or check one document by hand")
                    else:
                        line("PASS", name, "no page errors, no overflow, library loaded")
            browser.close()
    finally:
        srv.shutdown()
    print("Screenshots in %s" % shots)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
