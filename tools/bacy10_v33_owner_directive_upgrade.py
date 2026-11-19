"""Embed the owner-approved BACY-10 directive in LiveKit and the APK.

Builds on the restored original voice/design and existing Cloudflare memory.
Does not change the original Android UI or floating overlay.
"""
from pathlib import Path

DIRECTIVE_FILE = Path(__file__).resolve().parent.parent / "config" / "bacy10-owner-directive.txt"


def once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"Owner directive anchor changed in {path}: expected 1, got {count}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def apply(root: Path) -> None:
    directive = DIRECTIVE_FILE.read_text(encoding="utf-8").strip()
    if not 500 < len(directive) < 5500:
        raise RuntimeError("Owner directive is missing or unexpectedly large")
    if '"""' in directive or "'''" in directive:
        raise RuntimeError("Owner directive cannot contain triple-quote delimiters")
    if "formal British butler personality" not in directive or "remember this" not in directive:
        raise RuntimeError("Owner voice and memory requirements are missing")

    for path, anchor, spaces in (
        (root / "agent/src/agent.py", "                        # Guardrails", "                        "),
        (root / "agent/src/prompts.py", "    # Guardrails", "    "),
    ):
        block = "\n".join(spaces + line for line in directive.splitlines())
        once(path, anchor,
             spaces + "# Built-in owner directive (owner preferences)\n"
             + block + "\n\n" + anchor)

    mobile = root / "mobile"
    asset = mobile / "assets/bacy10_owner_directive.txt"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text(directive + "\n", encoding="utf-8")

    pubspec = mobile / "pubspec.yaml"
    once(pubspec, "  assets:\n", "  assets:\n    - assets/bacy10_owner_directive.txt\n")
    once(pubspec, "version: 3.2.0+37", "version: 3.3.0+38")

    (root / "agent/tests/test_built_in_owner_directive.py").write_text("""from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_directive_embedded_in_live_agent():
    agent = (ROOT / 'agent/src/agent.py').read_text()
    prompts = (ROOT / 'agent/src/prompts.py').read_text()
    for src in (agent, prompts):
        assert '# Built-in owner directive (owner preferences)' in src
        assert 'formal British butler personality' in src
        assert 'Do not censor harmless swear words' in src
        assert 'do not reflexively respond' in src
        assert 'use the real private memory tool' in src
    assert 'Talk like a butler' in agent


def test_mobile_contains_owner_directive_without_ui_replacement():
    mobile = ROOT / 'mobile'
    asset = (mobile / 'assets/bacy10_owner_directive.txt').read_text()
    assert 'Owner: BW Silinda' in asset
    assert 'remember this' in asset
    pubspec = (mobile / 'pubspec.yaml').read_text()
    assert 'assets/bacy10_owner_directive.txt' in pubspec
    assert 'version: 3.3.0+38' in pubspec
    manifest = (mobile/'android/app/src/main/AndroidManifest.xml').read_text()
    assert 'BacyOverlayLauncherActivity' not in manifest
    assert (mobile/'lib/support/bacy10_cloud_memory.dart').is_file()
""", encoding="utf-8")
