"""BACY-10 v3.9 server-only Gemini Live WebSocket repair.

A real deployment of the older RealtimeModel without an explicit API version
reproduced a Google Live WebSocket HTTP 404. An actual Google-plugin session
opened with api_version="v1beta" using the same Google API key, model,
voice, SDK and tool-scheduling options. This patch pins that verified version.
Do not rewrite memory or Android app data for this server-side defect.
"""
from pathlib import Path

def apply(root:Path):
    agent=root/"agent/src/agent.py"
    src=agent.read_text(encoding="utf-8")
    old='                model="gemini-3.8-live",\n                temperature=0.9,\n                enable_affective_dialog=True,\n                voice="Enceladus",'
    new='                model="gemini-3.8-live",\n                api_version="v1beta",  # real plugin WebSocket verified; avoids HTTP 404\n                input_audio_transcription=genai_types.AudioTranscriptionConfig(),\n                output_audio_transcription=genai_types.AudioTranscriptionConfig(),\n                temperature=0.9,\n                voice="Enceladus",'
    if src.count(old)!=1:
        raise RuntimeError(f"Unexpected Gemini Live constructor: {src.count(old)}")
    agent.write_text(src.replace(old,new,1),encoding="utf-8")
    tests=root/"agent/tests/test_v39_live_websocket.py"
    tests.write_text(
        """from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_live_api_version_is_pinned_to_working_endpoint():
    agent=(ROOT/'agent/src/agent.py').read_text(encoding='utf8')
    assert 'model="gemini-3.8-live",' in agent
    assert 'api_version="v1beta"' in agent
    assert 'input_audio_transcription=genai_types.AudioTranscriptionConfig()' in agent
    assert 'output_audio_transcription=genai_types.AudioTranscriptionConfig()' in agent
    assert agent.count('api_version="v1beta"') == 1
    assert 'voice="Enceladus"' in agent
    assert 'temperature=0.9' in agent
    assert 'enable_affective_dialog' not in agent
    assert 'language="en-GB"' in agent
    assert 'mcp.MCPToolset' in agent
def test_existing_owner_data_untouched():
    assert (ROOT/'mobile/lib/support/bacy10_cloud_memory.dart').is_file()
    assert (ROOT/'mobile/lib/screens/bacy10_provider_settings_screen.dart').is_file()
    assert 'conversation_item_added' in (ROOT/'agent/src/agent.py').read_text()
    assert 'version: 3.8.0+43' in (ROOT/'mobile/pubspec.yaml').read_text()
""",encoding="utf-8")
