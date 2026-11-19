"""Remove the redundant hard-coded owner biography and legacy persona text
from the live Gemini instructions; retain phone tools and live voice settings.
"""
from pathlib import Path

def once(path, old, new):
    s=path.read_text(encoding="utf8")
    if s.count(old)!=1: raise RuntimeError(f"Prompt cleanup anchor mismatch: {path}: {old[:65]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf8")

def apply(root:Path):
    agent=root/"agent/src/agent.py"
    source=agent.read_text(encoding="utf8")
    before="                        # Built-in owner context (provided by the owner)\n"
    after="                        # Android phone actions and private memory\n"
    if source.count(before)!=1 or source.count(after)!=1:
        raise RuntimeError("Existing personal biography boundaries changed")
    a=source.index(before)
    b=source.index(after,a)
    replacement="""                        # Private owner preferences (loaded from current cloud memory)
                        - Respond to everyday owner requests directly. Ordinary jokes, fictional acting, strong language, coding and benign practical work do not call for scripted refusals or lectures.
                        - Listen when the owner wants to read aloud. If they say 'I want to read it for you', respond 'Go ahead, I'm listening', then wait.
                        - Be conversational and concise. Do not volunteer unrelated personal biography, school subjects, earlier projects or repetitive formal greetings.
                        - Use phone and web tools when requested. Be truthful about actual tool outcomes and Android permissions.

"""
    source=source[:a]+replacement+source[b:]
    begin="                    memory_lines=[]\n"
    end="                    if memory_lines:\n"
    if source.count(begin)!=1 or source.count(end)!=1:
        raise RuntimeError("Cloud memory loading anchors changed")
    start=source.index(begin)
    stop=source.index(end,start)
    source=source[:start]+"""                    memory_lines=[]
                    if isinstance(facts,dict):
                        for k in ("owner_behavior_preferences","owner_workflow_preferences","owner_voice_style"):
                            v=facts.get(k)
                            if isinstance(v,str) and v.strip() and v!="__BACY10_DELETED__":
                                memory_lines.append(f"Current {k}: {v.strip()[:1250]}")
""" +source[stop:]
    agent.write_text(source,encoding="utf8")

    # Newly built apps must not automatically reintroduce the old profile.
    bundle=root/"config/bacy10-owner-profile.json"
    if bundle.exists(): bundle.unlink()

    mobile=root/"mobile"
    once(mobile/"pubspec.yaml","version: 3.8.0+43","version: 4.0.0+44")
    for name in ("test_owner_provider_settings.py","test_v37_direct_source.py",
                 "test_v38_gemini_runtime.py","test_v39_live_websocket.py"):
        path=root/"agent/tests"/name
        value=path.read_text(encoding="utf8")
        if "3.8.0+43" in value:
            path.write_text(value.replace("3.8.0+43","4.0.0+44"),encoding="utf8")

    (root/"agent/tests/test_v40_prompt_cleanup.py").write_text(
"""from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_no_legacy_personal_profile_in_live_prompt():
    agent=(R/'agent/src/agent.py').read_text()
    assert '# Built-in owner context' not in agent
    assert 'Go ahead, I\\'m listening' in agent
    assert 'owner_behavior_preferences' in agent
    assert 'owner_workflow_preferences' in agent
    assert 'api_version="v1beta"' in agent
    assert 'mcp.MCPToolset' in agent
    assert 'conversation_item_added' in agent
    assert not (R/'config/bacy10-owner-profile.json').exists()
    assert 'version: 4.0.0+44' in (R/'mobile/pubspec.yaml').read_text()
""",encoding="utf8")
