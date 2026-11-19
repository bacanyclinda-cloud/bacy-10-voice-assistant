"""BACY-10 v3.5: encrypted BYOK provider settings, LiveKit endpoint and MCP tools.

No secret is included in the APK or checked into git. Google Gemini BYOK is
provided by the owner phone over the authorized LiveKit room at call start.
Cloudflare pairing and cloud memories remain unchanged.
"""
from pathlib import Path

PROVIDER_DART = r'''
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class BacyProviderSettings {
  static const _storage = FlutterSecureStorage();
  static const _prefix = 'bacy10_owner_provider_v1_';

  static Future<String> read(String key) async =>
      (await _storage.read(key: _prefix + key)) ?? '';

  static Future<void> save(String key, String value) async {
    if (value.length > 4096) throw StateError('Value too long');
    await _storage.write(key: _prefix + key, value: value.trim());
  }

  static Future<void> remove(String key) async =>
      _storage.delete(key: _prefix + key);

  static bool validHttps(String value) {
    final url = Uri.tryParse(value.trim());
    if (url == null || url.scheme != 'https' || url.host.isEmpty ||
        url.userInfo.isNotEmpty || url.hasFragment) return false;
    final host = url.host.toLowerCase();
    return host != 'localhost' && host != '127.0.0.1' &&
        host != '0.0.0.0' && host != '::1' &&
        !host.endsWith('.local') && !host.endsWith('.internal');
  }

  static Future<String?> tokenEndpoint() async {
    final url = await read('livekit_token_endpoint');
    if (url.isEmpty || !validHttps(url)) return null;
    return url;
  }

  static Future<Map<String, dynamic>> agentConfig() async {
    final googleEnabled = (await read('gemini_enabled')) == 'yes';
    final mcpEnabled = (await read('mcp_enabled')) == 'yes';
    final mcpUrl = await read('mcp_url');
    return {
      'gemini_api_key': googleEnabled ? await read('gemini_api_key') : '',
      'mcp_url': mcpEnabled && validHttps(mcpUrl) ? mcpUrl : '',
      'mcp_bearer': mcpEnabled && validHttps(mcpUrl) ? await read('mcp_bearer') : '',
    };
  }

  static Future<String> testGemini(String key) async {
    if (key.trim().isEmpty) return 'Save a Gemini API key first.';
    try {
      final r = await http.get(
        Uri.parse('https://generativelanguage.googleapis.com/v1beta/models'),
        headers: {'x-goog-api-key': key.trim()},
      ).timeout(const Duration(seconds: 12));
      if (r.statusCode == 200) return 'Gemini API key accepted.';
      if (r.statusCode == 401 || r.statusCode == 403) return 'Gemini key was rejected or lacks access.';
      if (r.statusCode == 429) return 'Gemini request limit reached.';
      return 'Gemini returned HTTP '+r.statusCode.toString()+'.';
    } catch (_) { return 'Could not reach Gemini. Check internet.'; }
  }

  static Future<String> testElevenLabs(String key) async {
    if (key.trim().isEmpty) return 'Save an ElevenLabs API key first.';
    try {
      final r = await http.get(Uri.parse('https://api.elevenlabs.io/v1/voices'),
        headers: {'xi-api-key': key.trim()},
      ).timeout(const Duration(seconds: 12));
      if (r.statusCode == 200) return 'ElevenLabs API key accepted.';
      if (r.statusCode == 401 || r.statusCode == 403) return 'ElevenLabs key was rejected.';
      if (r.statusCode == 429) return 'ElevenLabs request limit reached.';
      return 'ElevenLabs returned HTTP '+r.statusCode.toString()+'.';
    } catch (_) { return 'Could not reach ElevenLabs. Check internet.'; }
  }
}
'''

SETTINGS_DART = r'''
import 'package:flutter/material.dart';
import '../support/bacy10_provider_settings.dart';
import '../support/bacy10_token_client.dart';

/// On-device encrypted provider configuration, never added to cloud memories.
class BacyProviderSettingsScreen extends StatefulWidget {
  const BacyProviderSettingsScreen({super.key});
  @override
  State<BacyProviderSettingsScreen> createState() => _BacyProviderSettingsScreenState();
}

class _BacyProviderSettingsScreenState extends State<BacyProviderSettingsScreen> {
  final gemini = TextEditingController();
  final elevenlabs = TextEditingController();
  final livekit = TextEditingController();
  final mcp = TextEditingController();
  final mcpBearer = TextEditingController();
  final pairing = TextEditingController();
  bool busy = false;
  bool geminiSaved = false, elevenSaved = false, mcpSaved = false, pairingSaved = false;
  bool geminiEnabled = false, mcpEnabled = false;
  String result = '';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final values = await Future.wait([
        BacyProviderSettings.read('gemini_api_key'),
        BacyProviderSettings.read('elevenlabs_api_key'),
        BacyProviderSettings.read('livekit_token_endpoint'),
        BacyProviderSettings.read('mcp_url'),
        BacyProviderSettings.read('mcp_bearer'),
        BacyProviderSettings.read('gemini_enabled'),
        BacyProviderSettings.read('mcp_enabled'),
        PairingTokenClient.hasPairingCode().then((v)=> v ? 'yes' : ''),
      ]);
      if (!mounted) return;
      setState(() {
        geminiSaved=values[0].isNotEmpty; elevenSaved=values[1].isNotEmpty;
        livekit.text=values[2]; mcp.text=values[3]; mcpSaved=values[4].isNotEmpty;
        geminiEnabled=values[5]=='yes'; mcpEnabled=values[6]=='yes';
        pairingSaved=values[7]=='yes';
      });
    } catch (_) {
      if (mounted) setState(()=>result='Encrypted storage is unavailable on this phone.');
    }
  }

  @override
  void dispose() {
    for (final c in [gemini, elevenlabs, livekit, mcp, mcpBearer, pairing]) { c.dispose(); }
    super.dispose();
  }

  Future<void> _save() async {
    if (busy) return;
    if (livekit.text.trim().isNotEmpty &&
        !BacyProviderSettings.validHttps(livekit.text)) {
      setState(()=>result='The LiveKit token endpoint must be a public HTTPS URL.');
      return;
    }
    if (mcp.text.trim().isNotEmpty && !BacyProviderSettings.validHttps(mcp.text)) {
      setState(()=>result='The MCP URL must be a public HTTPS URL.');
      return;
    }
    setState(() {busy=true; result='Saving encrypted settings…';});
    try {
      if(gemini.text.trim().isNotEmpty) await BacyProviderSettings.save('gemini_api_key',gemini.text);
      if(elevenlabs.text.trim().isNotEmpty) await BacyProviderSettings.save('elevenlabs_api_key',elevenlabs.text);
      if(mcpBearer.text.trim().isNotEmpty) await BacyProviderSettings.save('mcp_bearer',mcpBearer.text);
      await BacyProviderSettings.save('livekit_token_endpoint',livekit.text);
      await BacyProviderSettings.save('mcp_url',mcp.text);
      await BacyProviderSettings.save('gemini_enabled',geminiEnabled?'yes':'no');
      await BacyProviderSettings.save('mcp_enabled',mcpEnabled?'yes':'no');
      if(pairing.text.trim().isNotEmpty) await PairingTokenClient.saveCode(pairing.text);
      gemini.clear();elevenlabs.clear();mcpBearer.clear();pairing.clear();
      if(mounted) setState(() {result='Saved privately on this phone. Reconnect voice to apply changes.';});
      await _load();
    } catch (_) {
      if(mounted) setState(()=>result='Save failed. No API keys were sent to a cloud backup.');
    } finally {if(mounted)setState(()=>busy=false);}
  }

  Future<void> _check(String provider) async {
    if(busy) return;
    setState(() {busy=true;result='Testing provider…';});
    String outcome='';
    try {
      if(provider=='gemini') {
        final value=gemini.text.trim().isNotEmpty?gemini.text.trim():await BacyProviderSettings.read('gemini_api_key');
        outcome=await BacyProviderSettings.testGemini(value);
      } else if(provider=='elevenlabs') {
        final value=elevenlabs.text.trim().isNotEmpty?elevenlabs.text.trim():await BacyProviderSettings.read('elevenlabs_api_key');
        outcome=await BacyProviderSettings.testElevenLabs(value);
      }
    } catch (_) { outcome='Provider test failed.'; }
    if(mounted)setState(() {busy=false;result=outcome;});
  }

  Future<void> _clear(String key) async {
    await BacyProviderSettings.remove(key);
    await _load();
    if(mounted)setState(()=>result='Removed stored '+key+' from this phone.');
  }

  Widget _field(String title,TextEditingController controller,{bool secret=false,String? hint}){
    return Padding(
      padding:const EdgeInsets.only(bottom:12),
      child:TextField(controller:controller,obscureText:secret,
        enableSuggestions:!secret,autocorrect:!secret,
        keyboardType:secret?TextInputType.visiblePassword:TextInputType.url,
        decoration:InputDecoration(labelText:title,hintText:hint,
          border:const OutlineInputBorder(),isDense:true),
      ),
    );
  }

  Widget _panel(String title,List<Widget> contents){
    return Card(color:const Color(0xFF17212D),margin:const EdgeInsets.only(bottom:16),
      child:Padding(padding:const EdgeInsets.all(14),
        child:Column(crossAxisAlignment:CrossAxisAlignment.stretch,children:[
          Text(title,style:const TextStyle(color:Colors.white,fontSize:17,fontWeight:FontWeight.w600)),
          const SizedBox(height:10),...contents,
        ]),
      ),
    );
  }

  Widget _note(String value)=>Padding(padding:const EdgeInsets.only(bottom:12),
    child:Text(value,style:const TextStyle(fontSize:12,color:Color(0xFFABBFCC),height:1.4)));

  @override
  Widget build(BuildContext context)=>Scaffold(
    backgroundColor:const Color(0xFF0A1019),
    appBar:AppBar(title:const Text('BACY-10 · AI Providers'),backgroundColor:const Color(0xFF121B26)),
    body:SafeArea(child:ListView(padding:const EdgeInsets.all(16),children:[
      _note('Your keys are encrypted on THIS phone, not bundled in the APK or uploaded to cloud memory. Use only accounts and keys that belong to you.'),
      _panel('Google Gemini',[
        _note(geminiSaved?'Gemini key saved securely. Enter a new one to replace it.':'Enter your own Google AI Studio Gemini API key.'),
        _field('Gemini API key',gemini,secret:true),
        SwitchListTile.adaptive(value:geminiEnabled,
          onChanged:(v)=>setState(()=>geminiEnabled=v),title:const Text('Use my key for Gemini Live',style:TextStyle(color:Colors.white)),
          subtitle:const Text('Requires an active LiveKit connection.',style:TextStyle(color:Color(0xFFA9B6C3)))),
        Wrap(spacing:10,children:[
          OutlinedButton(onPressed:busy?null:()=>_check('gemini'),child:const Text('Test Gemini key')),
          TextButton(onPressed:busy?null:()=>_clear('gemini_api_key'),child:const Text('Remove key'))
        ]),
      ]),
      _panel('ElevenLabs',[
        _note('Save and test an ElevenLabs API key. The current Gemini Live voice uses its own audio output; ElevenLabs requires a separately configured speech pipeline before it can become the voice.'),
        _field('ElevenLabs API key',elevenlabs,secret:true,hint:elevenSaved?'Saved (hidden)':''),
        Wrap(spacing:10,children:[
          OutlinedButton(onPressed:busy?null:()=>_check('elevenlabs'),child:const Text('Test ElevenLabs')),
          TextButton(onPressed:busy?null:()=>_clear('elevenlabs_api_key'),child:const Text('Remove key')),
        ]),
      ]),
      _panel('LiveKit connection',[
        _note('Leave empty for your existing Cloudflare token bridge. To use another LiveKit account, deploy BACY-10 and its authorized token bridge on that account, then enter its HTTPS /token endpoint here. API key and secret stay on its server.'),
        _field('Alternative LiveKit token endpoint',livekit,hint:'https://your-worker.workers.dev/token'),
        _field('New phone pairing code (optional)',pairing,secret:true,hint:pairingSaved?'Already paired':'Required on a new phone'),
        TextButton(onPressed:busy?null:()=>setState(()=>livekit.clear()),
          child:const Text('Use default LiveKit endpoint')),
      ]),
      _panel('MCP tools · Gmail, Calendar and more',[
        _note('Connect only to an MCP server you trust and have authorized. Gmail and Calendar access requires Google OAuth on that server; adding this URL alone does NOT grant Google account access. The agent may see tools exposed by the connected server.'),
        _field('HTTPS MCP server URL',mcp,hint:'https://your-mcp-server.com/mcp'),
        _field('MCP bearer token (if needed)',mcpBearer,secret:true,hint:mcpSaved?'Saved (hidden)':''),
        SwitchListTile.adaptive(value:mcpEnabled,
          onChanged:(v)=>setState(()=>mcpEnabled=v),title:const Text('Enable MCP tools',style:TextStyle(color:Colors.white)),
          subtitle:const Text('Only enable after setting up server authorization.',style:TextStyle(color:Color(0xFFA9B6C3)))),
        TextButton(onPressed:busy?null:()=>_clear('mcp_bearer'),
          child:const Text('Remove MCP token')),
      ]),
      if(result.isNotEmpty)Padding(padding:const EdgeInsets.only(bottom:12),
        child:Text(result,style:const TextStyle(color:Color(0xFFC7DDE9)))),
      FilledButton.icon(onPressed:busy?null:_save,
        icon:const Icon(Icons.save_outlined),
        label:Text(busy?'PLEASE WAIT':'SAVE PROVIDERS & CONNECTION')),
      const SizedBox(height:22),
    ])),
  );
}
'''

def once(path:Path,old:str,new:str)->None:
    raw=path.read_text(encoding='utf-8')
    matches=raw.count(old)
    if matches!=1:raise RuntimeError(f'v35 anchor mismatch ({matches}) {path}: {old[:70]!r}')
    path.write_text(raw.replace(old,new,1),encoding='utf-8')

def apply(root:Path)->None:
    mobile=root/'mobile'
    (mobile/'lib/support/bacy10_provider_settings.dart').write_text(PROVIDER_DART,encoding='utf-8')
    (mobile/'lib/screens/bacy10_provider_settings_screen.dart').write_text(SETTINGS_DART,encoding='utf-8')

    token=mobile/'lib/support/bacy10_token_client.dart'
    once(token,"import 'package:http/http.dart' as http;",
         "import 'package:http/http.dart' as http;\nimport 'bacy10_provider_settings.dart';")
    once(token,'    return _delegate.send(request);',"""    final custom = await BacyProviderSettings.tokenEndpoint();
    if (custom != null) {
      // The user manually selected this endpoint. Send the existing pairing
      // token only to this HTTPS server, never to a third-party API provider.
      final bytes = await request.finalize().toBytes();
      final relay = http.Request(request.method, Uri.parse(custom));
      relay.headers.addAll(request.headers);
      relay.bodyBytes = bytes;
      return _delegate.send(relay);
    }
    return _delegate.send(request);""")

    ctrl=mobile/'lib/controllers/app_ctrl.dart'
    once(ctrl,"import '../support/bacy10_cloud_memory.dart';",
         "import '../support/bacy10_cloud_memory.dart';\nimport '../support/bacy10_provider_settings.dart';")
    once(ctrl,"    room.registerRpcMethod('bacy10.memory', (request) async {",
         """    room.registerRpcMethod('bacy10.providers', (request) async {
      // Do not disclose credentials to any participant other than the
      // authenticated agent. No provider key goes into a chat or cloud memory.
      if (room.agentParticipant?.identity != request.callerIdentity) {
        return jsonEncode({'ok':false,'message':'Provider access denied'});
      }
      try {
        final args=jsonDecode(request.payload) as Map<String,dynamic>;
        if (args['action'] != 'session_config') return jsonEncode({'ok':false});
        final cfg=await BacyProviderSettings.agentConfig();
        return jsonEncode({'ok':true, ...cfg});
      } catch (_) { return jsonEncode({'ok':false}); }
    });
    room.registerRpcMethod('bacy10.memory', (request) async {""")
    once(ctrl,"    room.unregisterRpcMethod('bacy10.memory');",
         "    room.unregisterRpcMethod('bacy10.providers');\n    room.unregisterRpcMethod('bacy10.memory');")

    welcome=mobile/'lib/screens/welcome_screen.dart'
    once(welcome,"import 'package:flutter/material.dart';",
         "import 'package:flutter/material.dart';\nimport 'bacy10_provider_settings_screen.dart';")
    once(welcome,"            IconButton(\n              tooltip: 'Hands-free permissions',",
         """            IconButton(
              tooltip: 'AI providers and connections',
              onPressed: () => Navigator.of(ctx).push(MaterialPageRoute(
                builder: (_) => const BacyProviderSettingsScreen())),
              icon: const Icon(Icons.vpn_key_rounded,
                color: Color(0xFFDBEAE0)),
            ),
            IconButton(
              tooltip: 'Hands-free permissions',""")
    # Keep the full-screen app/voice design, add one settings icon to the call.
    screen=mobile/'lib/screens/agent_screen.dart'
    once(screen,"import 'package:flutter/material.dart';",
         "import 'package:flutter/material.dart';\nimport 'bacy10_provider_settings_screen.dart';")
    once(screen,"_buildLayoutSwitcher(ctx, agentLayoutState),",
         """_buildLayoutSwitcher(ctx, agentLayoutState),
              Positioned(top: 8, right: 8, child: SafeArea(
                child: IconButton(
                  tooltip: 'AI providers',
                  onPressed: () => Navigator.of(ctx).push(MaterialPageRoute(
                    builder: (_) => const BacyProviderSettingsScreen())),
                  icon: const Icon(Icons.tune_rounded),
                ),
              )),""")

    agent=root/'agent/src/agent.py'
    once(agent,"from livekit.plugins import ai_coustics, google",
         "from livekit.plugins import ai_coustics, google\nfrom livekit.agents import mcp")
    once(agent,"    def __init__(self, browser: BrowserManager | None = None) -> None:",
         "    def __init__(self, browser: BrowserManager | None = None, *, gemini_api_key: str | None = None, owner_mcp: dict | None = None) -> None:")
    once(agent,"        self.browser_tools = BrowserTools(self.browser)",
         """        self.browser_tools = BrowserTools(self.browser)
        self._owner_mcp_tools = []
        if owner_mcp and owner_mcp.get('url'):
            from urllib.parse import urlparse
            from ipaddress import ip_address
            url = owner_mcp['url']
            parsed = urlparse(url)
            host = parsed.hostname or ''
            try:
                private_address = not ip_address(host).is_global
            except ValueError:
                private_address = False
            if (parsed.scheme == 'https' and host and
                not private_address and host not in ('localhost',) and
                not host.endswith(('.local', '.internal')) and not parsed.username):
                headers = {}
                if owner_mcp.get('bearer'):
                    headers['Authorization'] = 'Bearer ' + owner_mcp['bearer']
                self._owner_mcp_tools.append(
                    mcp.MCPToolset(id='owner-mcp',
                      mcp_server=mcp.MCPServerHTTP(url, headers=headers)))""")
    once(agent,"                tool_response_scheduling=genai_types.FunctionResponseScheduling.WHEN_IDLE,",
         """                tool_response_scheduling=genai_types.FunctionResponseScheduling.WHEN_IDLE,
                **({'api_key': gemini_api_key} if gemini_api_key else {}),""")
    once(agent,"                *self.browser_tools.tools,",
         "                *self.browser_tools.tools,\n                *self._owner_mcp_tools,")

    # Connect before starting the model so it can optionally receive the key
    # from the authenticated owner phone via a private LiveKit RPC.
    once(agent,"    ctx.add_shutdown_callback(browser.close)",
         """    ctx.add_shutdown_callback(browser.close)
    await ctx.connect()

    async def request_owner_providers():
        import json as _json
        import asyncio as _asyncio
        # Wait briefly for the owner phone to appear; provider keys are never
        # printed, written to logs or placed in agent instructions.
        for _ in range(20):
            participants=list(ctx.room.remote_participants.values())
            if participants:
                try:
                    payload=await ctx.room.local_participant.perform_rpc(
                        destination_identity=participants[0].identity,
                        method='bacy10.providers',
                        payload=_json.dumps({'action':'session_config'}),
                        response_timeout=3.0,
                    )
                    config=_json.loads(payload)
                    if isinstance(config,dict) and config.get('ok'):
                        return config
                except Exception:
                    pass
                return {}
            await _asyncio.sleep(.25)
        return {}
    owner_providers=await request_owner_providers()""")
    once(agent,"    assistant = Assistant(browser)",
         """    owner_gemini=owner_providers.get('gemini_api_key')
    if not isinstance(owner_gemini,str) or not (8<len(owner_gemini)<400):
        owner_gemini=None
    owner_mcp={}
    mcp_url=owner_providers.get('mcp_url')
    if isinstance(mcp_url,str) and mcp_url.startswith('https://'):
        owner_mcp={'url':mcp_url,'bearer':str(owner_providers.get('mcp_bearer') or '')}
    assistant = Assistant(browser, gemini_api_key=owner_gemini, owner_mcp=owner_mcp)""")
    once(agent,"    await ctx.connect()\n    asyncio.create_task(restore_cloud_memory())",
         "    asyncio.create_task(restore_cloud_memory())")

    pyproject=root/'agent/pyproject.toml'
    once(pyproject,'"livekit-agents[google,images]>=1.6.9",',
         '"livekit-agents[google,images,mcp]>=1.6.9",')
    once(mobile/'pubspec.yaml',"version: 3.4.0+39","version: 3.5.0+40")

    (root/'agent/tests/test_owner_provider_settings.py').write_text(
        """from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_encrypted_secrets_not_bundled():
    a=(ROOT/'mobile/lib/support/bacy10_provider_settings.dart').read_text()
    assert 'FlutterSecureStorage' in a and 'gemini_api_key' in a
    assert 'testElevenLabs' in a and 'testGemini' in a
    assert 'validHttps' in a
    assert 'bacy10.providers' in (ROOT/'mobile/lib/controllers/app_ctrl.dart').read_text()
    assert 'bacy10.providers' in (ROOT/'agent/src/agent.py').read_text()
    assert 'api_key' in (ROOT/'agent/src/agent.py').read_text()
def test_existing_design_and_cloud_remain():
    assert 'BacyProviderSettingsScreen' in (ROOT/'mobile/lib/screens/welcome_screen.dart').read_text()
    assert 'BacyProviderSettingsScreen' in (ROOT/'mobile/lib/screens/agent_screen.dart').read_text()
    assert (ROOT/'mobile/lib/support/bacy10_cloud_memory.dart').is_file()
    assert 'BacyOverlayLauncherActivity' not in (ROOT/'mobile/android/app/src/main/AndroidManifest.xml').read_text()
    assert 'version: 3.5.0+40' in (ROOT/'mobile/pubspec.yaml').read_text()
def test_optional_real_mcp_toolset():
    a=(ROOT/'agent/src/agent.py').read_text()
    assert 'mcp.MCPToolset' in a and 'mcp.MCPServerHTTP' in a
    assert '[google,images,mcp]' in (ROOT/'agent/pyproject.toml').read_text()
""",encoding='utf-8')
