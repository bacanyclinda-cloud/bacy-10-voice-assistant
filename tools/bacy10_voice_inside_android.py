"""Install three REAL voice choices inside the BACY-10 Android/LiveKit package.

Original Gemini voice remains unchanged. Voice 2 selects a different Gemini
voice. Voice 3 uses text-only Gemini Live with ElevenLabs speech synthesis.
No secrets are embedded; ElevenLabs key is stored in Android secure storage.
"""
from pathlib import Path

VOICE_TOOLS = r'''import json
from livekit.agents import RunContext, function_tool
from livekit.agents.llm import ToolError

class VoiceTools:
    def __init__(self, room):
        self.room = room

    @property
    def tools(self):
        return [self.switch_bacy_voice]

    @function_tool()
    async def switch_bacy_voice(self, context: RunContext, voice: str) -> str:
        """Switch BACY-10's actual Android voice via a verified phone RPC.
        Supports original voice1, alternate voice2, and ElevenLabs female voice3.

        Args:
            voice: One of voice1, voice2, voice3, original, second, third,
                female or elevenlabs, as requested by the owner.
        """
        options = {
            'voice1':'voice1','one':'voice1','original':'voice1',
            'voice2':'voice2','two':'voice2','second':'voice2',
            'voice3':'voice3','three':'voice3','third':'voice3',
            'female':'voice3','girl':'voice3','elevenlabs':'voice3',
        }
        chosen=options.get(str(voice).lower().strip())
        if not chosen:
            raise ToolError('Choose voice one, two or three.')
        others=list(self.room.remote_participants.values())
        if not others:
            raise ToolError('Connect BACY-10 on your Android phone to switch voices.')
        try:
            raw=await self.room.local_participant.perform_rpc(
                destination_identity=others[0].identity,
                method='bacy10.voice',
                payload=json.dumps({'action':'switch','voice':chosen}),
                response_timeout=8.0,
            )
            data=json.loads(raw)
            if not isinstance(data,dict) or not data.get('ok'):
                raise ToolError(str(data.get('message','Phone did not accept voice switch.')))
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError('Could not confirm the voice switch with your Android phone.') from exc
        return 'Voice '+chosen[-1]+' selected. Your phone will briefly reconnect to use it.'
'''

def replace(path: Path, old: str, new: str) -> None:
    text=path.read_text(encoding='utf-8')
    if text.count(old)!=1:
        raise RuntimeError(f'BACY-10 source changed unexpectedly: {path} {old[:45]} matches={text.count(old)}')
    path.write_text(text.replace(old,new,1),encoding='utf-8')

def apply(root: Path) -> None:
    a=root/'agent/src'
    (a/'voice_tools.py').write_text(VOICE_TOOLS,encoding='utf-8')
    f=a/'agent.py'
    replace(f,'from phone_tools import PhoneTools','from phone_tools import PhoneTools\nfrom voice_tools import VoiceTools')
    source = f.read_text(encoding='utf-8')
    lines = [line for line in source.splitlines() if 'def __init__(self, browser: BrowserManager' in line]
    if len(lines) != 1 or not lines[0].rstrip().endswith(') -> None:'):
        raise RuntimeError('Cannot safely locate Assistant constructor for voice upgrade')
    original = lines[0]
    changed = original.replace(') -> None:', ', voice_profile: str = "voice1", room=None) -> None:')
    f.write_text(source.replace(original, changed, 1), encoding='utf-8')
    replace(f,'        self.phone_tools = PhoneTools()',
              '        self.phone_tools = PhoneTools()\n        self.voice_tools = VoiceTools(room)')
    replace(f,'                *self.phone_tools.tools,',
              '                *self.phone_tools.tools,\n                *self.voice_tools.tools,')
    # In the original profile, preserve the unchanged model, voice and instructions.
    replace(f,'                voice="Enceladus",',
              '                voice="Enceladus" if voice_profile != "voice2" else "Puck",\n                **({"modalities":[genai_types.Modality.TEXT]} if voice_profile == "voice3" else {}),')
    # Do not modify the V4.0 system instructions or assistant behaviour.
    # Insert before session setup without assuming whitespace in the owner's config assignment.
    source = f.read_text(encoding='utf-8')
    marker = '    session = AgentSession('
    if source.count(marker) != 1:
        raise RuntimeError('Phone provider configuration is not available before session setup.')
    setup = """    voice_profile=owner_providers.get('voice_profile','voice1')
    if voice_profile not in ('voice1','voice2','voice3'):
        voice_profile='voice1'
    voice3_tts=None
    if voice_profile == 'voice3':
        key=owner_providers.get('elevenlabs_api_key','')
        if not isinstance(key,str) or not key.strip():
            raise RuntimeError('Voice 3 requires an ElevenLabs key in Android AI Providers.')
        from livekit.plugins import elevenlabs
        voice3_tts=elevenlabs.TTS(
            api_key=key,
            voice_id=str(owner_providers.get('elevenlabs_voice_id') or '22N9cF8z0o7y23njdyaY'),
            model='eleven_flash_v2_5',
        )
"""
    source = source.replace(marker, setup + marker, 1)
    f.write_text(source, encoding='utf-8')
    replace(f,'    session = AgentSession(\n','    session = AgentSession(\n        tts=voice3_tts,\n')
    source = f.read_text(encoding='utf-8')
    candidates = [line for line in source.splitlines()
                  if line.lstrip().startswith('assistant = Assistant(')]
    if len(candidates) != 1 or not candidates[0].rstrip().endswith(')'):
        raise RuntimeError('Unable to find the Assistant construction site safely.')
    original = candidates[0]
    changed = original.rstrip()[:-1] + ', voice_profile=voice_profile, room=ctx.room)'
    f.write_text(source.replace(original, changed, 1), encoding='utf-8')
    replace(root/'agent/pyproject.toml',
        '    "livekit-plugins-ai-coustics~=0.2",',
        '    "livekit-plugins-ai-coustics~=0.2",\n    "livekit-plugins-elevenlabs>=1.8.0,<2",')

    provider=root/'mobile/lib/support/bacy10_provider_settings.dart'
    replace(provider,"      'mcp_bearer': mcpEnabled && validHttps(mcpUrl) ? await read('mcp_bearer') : '',",
        """      'mcp_bearer': mcpEnabled && validHttps(mcpUrl) ? await read('mcp_bearer') : '',
      'voice_profile': (await read('voice_profile')).isEmpty ? 'voice1' : await read('voice_profile'),
      'elevenlabs_api_key': (await read('voice_profile')) == 'voice3' ? await read('elevenlabs_api_key') : '',
      'elevenlabs_voice_id': await read('elevenlabs_voice_id'),""")

    ctrl=root/'mobile/lib/controllers/app_ctrl.dart'
    replace(ctrl,'  bool isSessionStarting = false;',"""  bool isSessionStarting = false;
  String selectedVoice = 'voice1';
  bool _changingVoice = false;

  Future<void> switchVoice(String chosen) async {
    if (!['voice1','voice2','voice3'].contains(chosen) || _changingVoice) return;
    if (chosen=='voice3' &&
        (await BacyProviderSettings.read('elevenlabs_api_key')).trim().isEmpty) {
      connectionError = 'To use the female Voice 3, first save ElevenLabs key in AI Providers.';
      notifyListeners();
      return;
    }
    _changingVoice = true;
    try {
      await BacyProviderSettings.save('voice_profile',chosen);
      selectedVoice=chosen;
      notifyListeners();
      if (session.connectionState == sdk.ConnectionState.connected) {
        await disconnect();
        await Future<void>.delayed(const Duration(milliseconds: 450));
        connect();
      }
    } finally {
      _changingVoice=false;
    }
  }
""")
    replace(ctrl,'  AppCtrl() {',"""  AppCtrl() {
    BacyProviderSettings.read('voice_profile').then((v) {
      if (_hasCleanedUp) return;
      selectedVoice=['voice1','voice2','voice3'].contains(v) ? v : 'voice1';
      notifyListeners();
    });""")
    replace(ctrl,"    room.registerRpcMethod('bacy10.providers', (request) async {","""    room.registerRpcMethod('bacy10.voice', (request) async {
      if (room.agentParticipant?.identity != request.callerIdentity) {
        return jsonEncode({'ok':false,'message':'Only BACY-10 may change voice.'});
      }
      try {
        final data=jsonDecode(request.payload) as Map<String,dynamic>;
        final chosen=data['voice']?.toString() ?? '';
        if(data['action']!='switch' ||
            !['voice1','voice2','voice3'].contains(chosen)) {
          return jsonEncode({'ok':false,'message':'Unsupported voice option.'});
        }
        if(chosen=='voice3' &&
            (await BacyProviderSettings.read('elevenlabs_api_key')).trim().isEmpty) {
          return jsonEncode({'ok':false,'message':'Save ElevenLabs key in phone AI Providers first.'});
        }
        Future<void>.delayed(const Duration(milliseconds: 900), () => switchVoice(chosen));
        return jsonEncode({'ok':true,'message':'Switch accepted.'});
      } catch (_) { return jsonEncode({'ok':false,'message':'Voice switching failed.'}); }
    });
    room.registerRpcMethod('bacy10.providers', (request) async {""")
    replace(ctrl,"    room.unregisterRpcMethod('bacy10.providers');",
        "    room.unregisterRpcMethod('bacy10.providers');\n    room.unregisterRpcMethod('bacy10.voice');")

    screen=root/'mobile/lib/screens/agent_screen.dart'
    anchor='              Positioned(top: 8, right: 8, child: SafeArea('
    selector="""              Positioned(top: 8, left: 8, child: SafeArea(
                child: Consumer<AppCtrl>(builder: (context, controller, _) =>
                  PopupMenuButton<String>(
                    tooltip: 'Switch BACY-10 voice',
                    icon: const Icon(Icons.record_voice_over_rounded),
                    initialValue: controller.selectedVoice,
                    onSelected: (v) => controller.switchVoice(v),
                    itemBuilder: (_) => const [
                      PopupMenuItem(value:'voice1', child: Text('Voice 1 · Original (unchanged)')),
                      PopupMenuItem(value:'voice2', child: Text('Voice 2 · Alternate Gemini')),
                      PopupMenuItem(value:'voice3', child: Text('Voice 3 · Florence · Female ElevenLabs')),
                    ],
                  )),
              )),
"""
    replace(screen,anchor,selector+anchor)
    ui=root/'mobile/lib/screens/bacy10_provider_settings_screen.dart'
    content=ui.read_text(encoding='utf-8')
    content=content.replace(
        'Separate audio integration is required to replace Gemini Live speech.',
        'Voice 3 speaks with female ElevenLabs Florence; save and test this key, then switch voice and reconnect. Original voice is unchanged.')
    ui.write_text(content,encoding='utf-8')
