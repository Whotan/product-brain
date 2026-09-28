"""Self-check for the hub files pb sync manages: doc folders, .gitignore, README.

Run: python3 tests/test_pb_hub_files.py
"""

import json
import runpy
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    pb = runpy.run_path(str(ROOT / "bin/pb"), run_name="pb_under_test")
    with tempfile.TemporaryDirectory() as tmp:
        hub = Path(tmp)
        subprocess.run(["git", "init", "-q", str(hub)], check=True)
        subprocess.run(["git", "-C", str(hub), "remote", "add", "origin",
                        "ssh://git@git.example.com:2222/team/acme-brain.git"], check=True)
        shutil.copy(ROOT / "templates/brain.config.template.json", hub / "brain.config.json")
        cfg = pb["load_config"](hub)

        for _ in range(2):  # second run must change nothing
            pb["ensure_doc_folders"](hub, cfg, False)
            pb["ensure_exclusions"](hub, hub / "repos", hub / "graph", [], False)
            pb["write_readme"](hub, cfg, hub / "graph", False)

        for dtype in cfg["doc_types"]:
            assert (hub / "docs" / dtype / ".gitkeep").exists(), dtype
        assert (hub / ".gitignore").read_text(encoding="utf-8").count(".claude/settings.local.json") == 1

        readme = (hub / "README.md").read_text(encoding="utf-8")
        assert "{{" not in readme, "unfilled placeholder"
        assert "git clone ssh://git@git.example.com:2222/team/acme-brain.git" in readme
        assert "Open the `acme-brain` folder" in readme
        assert "| `docs/specs/` | What a feature should do and why |" in readme

        # the hub settings template must parse and carry the UTF-8 fix
        settings = json.loads((ROOT / "templates/hub-settings.template.json").read_text(encoding="utf-8"))
        assert settings["env"]["PYTHONUTF8"] == "1"
        for name in ("hub-mcp.template.json", "hub-settings.local.example.json"):
            text = (ROOT / "templates" / name).read_text(encoding="utf-8")
            json.loads(text)
            assert "${" not in text, f"{name}: .mcp.json can't expand ${{VAR}} from settings env"

    # old installs: only reported when pb runs from the plugin cache
    legacy = pb["legacy_installs"]
    with tempfile.TemporaryDirectory() as tmp:
        home, hub = Path(tmp) / "home", Path(tmp) / "hub"
        plugin_root = home / ".claude/plugins/cache/product-brain/product-brain/9.9.9"
        (plugin_root / "bin").mkdir(parents=True)
        (plugin_root / "bin/pb").write_text("")
        old_skill = home / ".claude/skills/brainify"
        old_skill.mkdir(parents=True)
        (old_skill / "SKILL.md").write_text("---\nversion: 0.3.0\n---\n")
        (hub / ".claude").mkdir(parents=True)
        (hub / "brain.config.json").write_text("{}")
        (hub / ".claude/settings.json").write_text('{"enabledPlugins": {"product-brain@product-brain": true}}')

        legacy.__globals__["framework_root"] = lambda: ROOT
        assert legacy(hub, home, "/old/pb") == [], "checkout installs are the old copy by design"

        legacy.__globals__["framework_root"] = lambda: plugin_root
        (hub / ".mcp.json").write_text('{"mcpServers": {"jira": {"command": "uvx", "args": ["mcp-atlassian"]}}}')
        found = legacy(hub, home, "/old/pb")
        assert len(found) == 4, found
        assert "0.3.0" in found[0] and "/old/pb" in found[1] and "git-workflow" in found[2]
        assert "mcp-atlassian" in found[3], "old Jira launch (blocked on Windows) not flagged"

        (home / ".local/bin").mkdir(parents=True)
        (home / ".local/bin/pb").write_text("")  # found even when which() misses it (Windows)
        assert any(".local" in f for f in legacy(hub, home, "")), "old ~/.local/bin/pb missed"
        (home / ".local/bin/pb").unlink()

        shutil.rmtree(old_skill)
        (hub / ".claude/settings.json").write_text(
            '{"enabledPlugins": {"git-workflow@product-brain": true, "guardrails@product-brain": true}}')
        shutil.copy(ROOT / "templates/hub-mcp.template.json", hub / ".mcp.json")
        assert legacy(hub, home, str(plugin_root / "bin/pb")) == [], "template's Jira launch flagged as old"

    # dependency check: warns with an install hint when a program is missing, silent otherwise
    bash = shutil.which("bash")
    if bash:
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "bin"
            bare.mkdir()
            for tool in ("sed", "sort", "uname"):
                (bare / tool).symlink_to(shutil.which(tool))
            hub = Path(tmp) / "hub"
            hub.mkdir()
            (hub / "brain.config.json").write_text("{}")
            (hub / ".mcp.json").write_text('{"mcpServers": {"jira": {"command": "uvx"}}}')
            out = subprocess.run([bash, str(ROOT / "hooks/check-deps.sh")], capture_output=True, text=True,
                                 env={"PATH": str(bare), "CLAUDE_PROJECT_DIR": str(hub)})
            assert out.returncode == 0
            for tool in ("git", "python3", "node", "graphify", "uvx"):
                assert f"- {tool} (" in out.stdout, (tool, out.stdout)
            assert "Install:" in out.stdout
    print("ok")


if __name__ == "__main__":
    main()
