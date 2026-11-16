"""Self-check for plugins/repo-docs/skills/repo-docs/scripts/check_repo_docs.py."""
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_repo_docs", ROOT / "plugins/repo-docs/skills/repo-docs/scripts/check_repo_docs.py")
crd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crd)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".env.example").write_text("# Base URL of the API\nAPI_URL=x\n\nSECRET=\n")
        assert crd.env_keys(repo / ".env.example") == [("API_URL", True), ("SECRET", False)]
        assert not crd.is_client(repo)
        (repo / "pubspec.yaml").write_text("dependencies:\n  flutter:\n    sdk: flutter\n")
        assert crd.is_client(repo)

        problems = crd.audit(repo, client=True, hub=False)
        assert "missing AGENTS.md" in problems
        assert "missing docs/ui-standards.md" in problems
        assert ".env.example: SECRET has no comment above it" in problems

        (repo / "AGENTS.md").write_text("# Agents\n")
        (repo / "CLAUDE.md").write_text("@AGENTS.md\n")
        assert crd.audit(repo, client=False, hub=True) == []
    print("test_repo_docs: ok")


if __name__ == "__main__":
    main()
