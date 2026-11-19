"""BACY-10 v3.1 independently installable release variant.

Android cannot upgrade across different signing keys. Preserve the installed
BACY-10 package and local data by building this independently installable copy.
This does NOT migrate Android-private data, but the owner can re-pair to restore
previously synchronized cloud facts and conversations.
"""
from pathlib import Path

def once(path: Path, old: str, new: str):
    s=path.read_text(encoding="utf-8")
    n=s.count(old)
    if n != 1:
        raise RuntimeError(f"Side-by-side install anchor changed: {path}, count={n}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

def apply(root: Path) -> None:
    gradle = root / "mobile/android/app/build.gradle"
    once(gradle,
         'applicationId = "za.co.bacy10.personalassistant"',
         'applicationId = "za.co.bacy10.personalassistant.v31safe"')
    manifest = root / "mobile/android/app/src/main/AndroidManifest.xml"
    once(manifest,
         'android:label="BACY-10"',
         'android:label="BACY-10 NEW"')
    pubspec = root / "mobile/pubspec.yaml"
    once(pubspec, "version: 3.1.0+35", "version: 3.1.1+36")
    overlay_test = root / "agent/tests/test_quick_overlay.py"
    once(overlay_test, "assert 'version: 3.1.0+35'", "assert 'version: 3.1.1+36'")
    (root / "agent/tests/test_parallel_install.py").write_text(
        """from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def test_distinct_package_keeps_old_installation():
    gradle=(ROOT/'mobile/android/app/build.gradle').read_text()
    manifest=(ROOT/'mobile/android/app/src/main/AndroidManifest.xml').read_text()
    assert 'applicationId = "za.co.bacy10.personalassistant.v31safe"' in gradle
    assert 'android:label="BACY-10 NEW"' in manifest
    assert 'BacyOverlayLauncherActivity' in manifest
    assert 'version: 3.1.1+36' in (ROOT/'mobile/pubspec.yaml').read_text()
""", encoding="utf-8")
