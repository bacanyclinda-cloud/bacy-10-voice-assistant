"""Make BACY-10 build after removing three legacy directive files.

This module does NOT recreate the deleted owner directive. It retains actual
phone/cloud functionality and discards only previous assistant turns as live
system instructions. Provider/API/device safeguards remain intact.
"""
from pathlib import Path

def replace_one(path, old, new):
    value=path.read_text(encoding="utf-8")
    count=value.count(old)
    if count!=1: raise RuntimeError(f"v37 expected exactly one anchor in {path}: {count} {old[:70]!r}")
    path.write_text(value.replace(old,new,1),encoding="utf-8")

def pre(root:Path):
    # The deleted v33+v34 stages previously incremented this version twice.
    replace_one(root/"mobile/pubspec.yaml","version: 3.2.0+37","version: 3.4.0+39")

    # Keep all cloud conversation storage, syncing and recall; do not promote
    # previous assistant refusals into new system prompt instructions.
    agent=root/"agent/src/agent.py"
    s=agent.read_text(encoding="utf-8")
    begin="                    turns=result.get(\"recent\",[])\n"
    finish="                    if memory_lines:\n"
    if s.count(begin)!=1 or s.count(finish)!=1:
        raise RuntimeError("v37 cloud restore anchors changed")
    a=s.index(begin)
    b=s.index(finish,a)
    s=s[:a]+"""                    memory_lines=[]
                    if isinstance(facts,dict):
                        preferred=[(k,v) for k,v in facts.items()
                                   if str(k).startswith("owner_preference_")
                                   or str(k) in ("owner_voice_style","owner_behavior_preferences")]
                        others=[(k,v) for k,v in facts.items() if (k,v) not in preferred]
                        for k,v in (preferred+others)[:35]:
                            if not isinstance(v,str) or v=="__BACY10_DELETED__":
                                continue
                            # Older cloud facts predate stronger server-side secret filtering.
                            secret_re=__import__("re")
                            if secret_re.search(
                                r"password|passphrase|api.?key|secret|bank.?pin|cvv|\\botp\\b|"
                                r"-----BEGIN (?:RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----|"
                                r"\\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\\b|\\bgh[pousr]_[A-Za-z0-9]{20,}\\b|"
                                r"\\bAIza[0-9A-Za-z_-]{30,}\\b|\\bAKIA[0-9A-Z]{16}\\b|"
                                r"\\bBearer\\s+[A-Za-z0-9._~+/-]{20,}|"
                                r"\\beyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\b",
                                v, flags=secret_re.I):
                                continue
                            digits=secret_re.sub(r"\\D","",v)
                            if 13<=len(digits)<=19:
                                total=0
                                for pos,ch in enumerate(reversed(digits)):
                                    n=int(ch)
                                    if pos%2:
                                        n*=2
                                        if n>9:n-=9
                                    total+=n
                                if total%10==0:
                                    continue
                            memory_lines.append(f"Owner fact {str(k)[:65]}: {v.replace(chr(10),' ')[:500]}")
""" +s[b:]
    s=s.replace("# Previous owner conversation and personal memory",
                "# Owner facts and explicit preferences, without previous assistant dialogue",1)
    agent.write_text(s,encoding="utf-8")

def post(root:Path):
    agent=root/"agent/src/agent.py"
    prompts=root/"agent/src/prompts.py"
    for path in (agent,prompts):
        s=path.read_text(encoding="utf-8")
        # Delete hard-coded, repetitive persona orders that caused needless
        # canned refusal speeches and prevented normal coding help.
        for old,new in (
            ("- Respond in plain text only. Never use JSON, markdown, lists, tables, code, emojis, or other complex formatting.",
             "- Speak naturally in voice. For programming or JavaScript requests give real code using any available text result panel, and explain it briefly."),
            ("- Talk like a butler, say phrases like \"sir\" or \"madam\" when appropriate, and use a sarcastic tone when it fits the context.",
             "- Speak naturally and informally. Harmless humour, creative acting, ordinary profanity and playful insults are fine when requested."),
            ("- Also use phrases like \"I am at your service\" or \"I am happy to assist\", \"As you wish\" when appropriate, and use a sarcastic tone when it fits the context.",
             "- Avoid canned refusals and repetitive ceremonial phrases."),
            ("- On your first response in a call, greet the user with \"Good day, Sir\" or an equivalent formal greeting, then offer your service without using the exact phrases \"How can I help you?\" or \"What can I do for you?\"",
             "- Greet the owner normally, according to their preferred tone."),
            ("- If the user says \"BACY-10, you there?\", you **must** answer the exact line and nothing else after that: \"At your service, Sir\"",
             "- If the owner asks whether you are there, answer naturally."),
            ("# Hard rule","# Voice interaction"),
            ("- User: \"BACY-10, can you do XYZ task for me?\"","- User: \"BACY-10, can you open WhatsApp?\""),
            ("- BACY-10: \"Of course sir, as you wish. I will now do XYZ task for you.\"",
             "- BACY-10: \"Opening WhatsApp.\""),
        ):
            s=s.replace(old,new)
        # Keep consent and provider safeguards, but no long owner directive.
        path.write_text(s,encoding="utf-8")
    replace_one(root/"mobile/pubspec.yaml","version: 3.6.0+41","version: 3.7.0+42")
    provider_test=root/"agent/tests/test_owner_provider_settings.py"
    replace_one(provider_test,"assert 'version: 3.6.0+41' in (ROOT/'mobile/pubspec.yaml').read_text()",
                "assert 'version: 3.7.0+42' in (ROOT/'mobile/pubspec.yaml').read_text()")
    (root/"agent/tests/test_v37_direct_source.py").write_text(
"""from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_legacy_directives_deleted():
    for name in ('bacy10-owner-directive.txt',):
        assert not (ROOT/'mobile/assets'/name).exists()
    agent=(ROOT/'agent/src/agent.py').read_text()
    assert '# Built-in owner directive (owner preferences)' not in agent
    assert 'Earlier {turn.get(' not in agent
    assert 'conversation_item_added' in agent
    assert '"action":"append_turn"' in agent
    assert 'owner_behavior_preferences' in agent
def test_unforced_personality_and_real_tools():
    agent=(ROOT/'agent/src/agent.py').read_text()
    assert 'Never use JSON, markdown, lists, tables, code' not in agent
    assert 'ordinary profanity and playful insults' in agent
    assert 'open_android_app' in agent
    assert 'mcp.MCPToolset' in agent
    assert 'version: 3.7.0+42' in (ROOT/'mobile/pubspec.yaml').read_text()
""", encoding="utf-8")
