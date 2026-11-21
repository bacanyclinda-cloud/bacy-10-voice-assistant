"""Bundle the owner-approved BACY-10 profile without requiring a setup form."""
import json
import re
from pathlib import Path


def apply(root: Path) -> None:
    source = Path(__file__).resolve().parent.parent / "config/bacy10-owner-profile.json"
    profile = json.loads(source.read_text(encoding="utf-8"))
    groups = ("identity", "education", "work", "skills", "projects",
              "interests", "career", "development_preferences", "voice_preferences",
              "privacy", "preferences", "tools_hardware")
    facts = {}
    for group in groups:
        data = profile.get(group, {})
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    value = v
                elif isinstance(v, list):
                    value = ", ".join(str(item) for item in v)
                else:
                    continue
                if value.strip():
                    facts[k.lower()] = value.strip()[:2200]
        elif isinstance(data, str):
            facts[group] = data
    facts["profile_updated"] = profile["updated"]
    # Hard cap prevents accidentally bundling unusually large or secret documents.
    if not 20 <= len(facts) <= 110:
        raise ValueError("BACY-10 owner profile has unexpected count of confirmed facts")
    flat = "\n".join("    " + json.dumps(k, ensure_ascii=False) + ": " +
                     json.dumps(v, ensure_ascii=False) + ","
                     for k, v in sorted(facts.items()))
    memory = root / "mobile/lib/support/bacy10_memory.dart"
    text = memory.read_text(encoding="utf-8")
    before = re.search(
        r"  static const Map<String, String> _defaults = \{.*?\n  \};",
        text, flags=re.S
    )
    if not before:
        raise RuntimeError("Default owner memory field not found")
    text = text[:before.start()] + "  static final Map<String, String> _defaults = {\n" + \
        flat + "\n  };" + text[before.end():]
    # Existing Android installations may retain an earlier four-field profile.
    # Merge with the updated built-in facts so no manual import is needed.
    text = text.replace(
        "return decoded.map((k, v) => MapEntry(k.toString(), v.toString()));",
        "final oldFacts = decoded.map<String, String>((k, v) => "
        "MapEntry(k.toString(), v.toString()));\n"
        "        return <String, String>{...oldFacts, ..._defaults};",
        1
    )
    memory.write_text(text, encoding="utf-8")

    welcome = root / "mobile/lib/screens/welcome_screen.dart"
    w = welcome.read_text(encoding="utf-8")
    w = w.replace("import 'bacy10_memory_screen.dart';\n", "", 1)
    begin = w.find("                  const SizedBox(height: 16),\n                  TextButton.icon(")
    end = w.find("                  const SizedBox(height: 22),", begin)
    if begin < 0 or end < 0 or "My private memory" not in w[begin:end]:
        raise RuntimeError("Could not remove the unwanted owner memory editing button")
    w = w[:begin] + w[end:]
    welcome.write_text(w, encoding="utf-8")

    agent = root / "agent/src/agent.py"
    source_code = agent.read_text(encoding="utf-8")
    prompt = "\n".join("                        - " + k + ": " + v.replace("\n"," ")
                       for k, v in sorted(facts.items()))
    needle = "                        # Android phone actions and private memory\n"
    if needle not in source_code:
        raise RuntimeError("Cannot embed owner profile in BACY-10 prompt")
    source_code = source_code.replace(
        needle,
        "                        # Built-in owner context (provided by the owner)\n"
        "                        - The following owner details are private profile data. "
        "Use only when relevant to owner's request. Do not volunteer personal "
        "contact or relationship information to unrelated people. Never invent unknown facts.\n"
        + prompt + "\n\n" + needle,
        1
    )
    agent.write_text(source_code, encoding="utf-8")

    bundle = root / "config"
    bundle.mkdir(exist_ok=True)
    (bundle / "bacy10-owner-profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    pubspec = root / "mobile/pubspec.yaml"
    package = pubspec.read_text(encoding="utf-8")
    package = package.replace("version: 1.2.0+16", "version: 1.3.0+17")
    pubspec.write_text(package, encoding="utf-8")
