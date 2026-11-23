"""BACY-10 v3.8 server-side Gemini Live fix.

Reproduced with exact v3.7 instructions: old Gemini 3.1 Flash Live gave an
unnecessary refusal to a harmless roleplay request, while Gemini 3.8 Live
answered playfully. Upgrade LiveKit's Google plugin for proper support and
initialize future sessions on Gemini 3.8 Live. No Android UI or cloud DB edits.
"""
from pathlib import Path

def replace_one(path:Path,old:str,new:str):
    src=path.read_text(encoding='utf-8')
    if src.count(old)!=1:
        raise RuntimeError(f'v38 SDK upgrade anchor mismatch: {path}: {src.count(old)}')
    path.write_text(src.replace(old,new,1),encoding='utf-8')

def apply(root:Path):
    agent=root/'agent/src/agent.py'
    replace_one(agent,'model="gemini-3.1-flash-live-preview",',
                'model="gemini-3.8-live",\\n                temperature=0.9,\\n                enable_affective_dialog=True,')
    # The earlier livekit-plugins-google 1.6.10 did not support reliable
    # mid-session instruction updates for Gemini 3.1 (needs >=1.8.2).
    project=root/'agent/pyproject.toml'
    replace_one(project,'"livekit-agents[google,images,mcp]>=1.6.9",',
                '"livekit-agents[google,images,mcp]>=1.8.5,<2",')
    replace_one(root/'mobile/pubspec.yaml','version: 3.7.0+42','version: 3.8.0+43')
    test=root/'agent/tests/test_owner_provider_settings.py'
    replace_one(test,
      "assert 'version: 3.7.0+42' in (ROOT/'mobile/pubspec.yaml').read_text()",
      "assert 'version: 3.8.0+43' in (ROOT/'mobile/pubspec.yaml').read_text()")
    v37_test=root/'agent/tests/test_v37_direct_source.py'
    replace_one(v37_test,
      "assert 'version: 3.7.0+42' in (ROOT/'mobile/pubspec.yaml').read_text()",
      "assert 'version: 3.8.0+43' in (ROOT/'mobile/pubspec.yaml').read_text()")
    (root/'agent/tests/test_v38_gemini_runtime.py').write_text(
        """from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_live_model_upgrade_and_voice_consistency():
    agent=(R/'agent/src/agent.py').read_text()
    assert 'model=\"gemini-3.8-live\"' in agent
    assert 'model=\"gemini-3.1-flash-live-preview\"' not in agent
    assert 'voice=\"Enceladus\"' in agent
    assert 'language=\"en-GB\"' in agent
    assert 'repeat a harmless swear word' in agent
    assert 'give a witty, playful roast' in agent
    assert 'mcp.MCPToolset' in agent
def test_new_livekit_plugin_supported():
    project=(R/'agent/pyproject.toml').read_text()
    assert 'livekit-agents[google,images,mcp]>=1.8.5,<2' in project
    assert 'conversation_item_added' in (R/'agent/src/agent.py').read_text()
    assert 'async def restore_cloud_memory()' in (R/'agent/src/agent.py').read_text()
    assert (R/'mobile/lib/support/bacy10_cloud_memory.dart').exists()
    assert 'version: 3.8.0+43' in (R/'mobile/pubspec.yaml').read_text()
""",encoding='utf-8')
