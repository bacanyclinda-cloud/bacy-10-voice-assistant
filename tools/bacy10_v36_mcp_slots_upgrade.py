"""BACY-10 v3.6: three encrypted owner-configured MCP server slots.

MCP servers are not automatically authenticated. Each HTTPS endpoint must be
provisioned by the owner, and provider OAuth consent remains a separate step.
"""
from pathlib import Path

def once(file,old,new):
 s=file.read_text(encoding='utf-8')
 n=s.count(old)
 if n!=1:raise RuntimeError(f"v36 MCP anchor mismatch in {file}: {n} {old[:65]!r}")
 file.write_text(s.replace(old,new,1),encoding='utf-8')

def apply(root:Path):
 mobile=root/'mobile'
 settings=mobile/'lib/screens/bacy10_provider_settings_screen.dart'
 once(settings,'  final mcp = TextEditingController();',
      '  final mcp = TextEditingController();\n  final mcp2 = TextEditingController();\n  final mcp3 = TextEditingController();')
 once(settings,'  final mcpBearer = TextEditingController();',
      '  final mcpBearer = TextEditingController();\n  final mcpBearer2 = TextEditingController();\n  final mcpBearer3 = TextEditingController();')
 once(settings,"        BacyProviderSettings.read('mcp_enabled'),",
      """        BacyProviderSettings.read('mcp_enabled'),
        BacyProviderSettings.read('mcp_url_2'),
        BacyProviderSettings.read('mcp_url_3'),
        BacyProviderSettings.read('mcp_bearer_2'),
        BacyProviderSettings.read('mcp_bearer_3'),""")
 once(settings,"        pairingSaved=values[7]=='yes';",
      "        pairingSaved=values[7]=='yes'; mcp2.text=values[8];mcp3.text=values[9];")
 once(settings,"for (final c in [gemini, elevenlabs, livekit, mcp, mcpBearer, pairing])",
      "for (final c in [gemini, elevenlabs, livekit, mcp, mcp2, mcp3, mcpBearer, mcpBearer2, mcpBearer3, pairing])")
 once(settings,"    if (mcp.text.trim().isNotEmpty && !BacyProviderSettings.validHttps(mcp.text)) {",
      """    if ([mcp,mcp2,mcp3].any((c)=>c.text.trim().isNotEmpty &&
        !BacyProviderSettings.validHttps(c.text))) {""")
 once(settings,"      if(mcpBearer.text.trim().isNotEmpty) await BacyProviderSettings.save('mcp_bearer',mcpBearer.text);",
      """      if(mcpBearer.text.trim().isNotEmpty) await BacyProviderSettings.save('mcp_bearer',mcpBearer.text);
      if(mcpBearer2.text.trim().isNotEmpty) await BacyProviderSettings.save('mcp_bearer_2',mcpBearer2.text);
      if(mcpBearer3.text.trim().isNotEmpty) await BacyProviderSettings.save('mcp_bearer_3',mcpBearer3.text);""")
 once(settings,"      await BacyProviderSettings.save('mcp_url',mcp.text);",
      """      await BacyProviderSettings.save('mcp_url',mcp.text);
      await BacyProviderSettings.save('mcp_url_2',mcp2.text);
      await BacyProviderSettings.save('mcp_url_3',mcp3.text);""")
 once(settings,"      gemini.clear();elevenlabs.clear();mcpBearer.clear();pairing.clear();",
      "      gemini.clear();elevenlabs.clear();mcpBearer.clear();mcpBearer2.clear();mcpBearer3.clear();pairing.clear();")
 once(settings,"        _field('MCP bearer token (if needed)',mcpBearer,secret:true,hint:mcpSaved?'Saved (hidden)':''),",
      """        _field('MCP bearer token (if needed)',mcpBearer,secret:true,hint:mcpSaved?'Saved (hidden)':''),
        const Divider(color:Color(0xFF324454)),
        _field('MCP server 2 · HTTPS',mcp2,hint:'https://other-server.example/mcp'),
        _field('Server 2 bearer token',mcpBearer2,secret:true,hint:'Optional'),
        const Divider(color:Color(0xFF324454)),
        _field('MCP server 3 · HTTPS',mcp3,hint:'https://third-server.example/mcp'),
        _field('Server 3 bearer token',mcpBearer3,secret:true,hint:'Optional'),""")

 provider=mobile/'lib/support/bacy10_provider_settings.dart'
 once(provider,"    final mcpUrl = await read('mcp_url');",
      """    final configuredServers = <Map<String,String>>[
      {'url':await read('mcp_url'),'bearer':await read('mcp_bearer')},
      {'url':await read('mcp_url_2'),'bearer':await read('mcp_bearer_2')},
      {'url':await read('mcp_url_3'),'bearer':await read('mcp_bearer_3')},
    ];
    final servers = mcpEnabled
        ? configuredServers.where((s)=>validHttps(s['url']??'')).toList()
        : <Map<String,String>>[];
    final mcpUrl=await read('mcp_url');""")
 once(provider,"      'mcp_bearer': mcpEnabled && validHttps(mcpUrl) ? await read('mcp_bearer') : '',",
      """      'mcp_bearer': mcpEnabled && validHttps(mcpUrl) ? await read('mcp_bearer') : '',
      'mcp_servers':servers,""")

 agent=root/'agent/src/agent.py'
 once(agent,"owner_mcp: dict | None = None","owner_mcp: list | None = None")
 s=agent.read_text(encoding='utf-8')
 a=s.find('        self._owner_mcp_tools = []\n')
 b=s.find('        self.phone_tools = PhoneTools()',a)
 if a<0 or b<0 or b<a:raise RuntimeError('agent MCP setup block missing')
 s=s[:a]+'''        self._owner_mcp_tools = []
        from urllib.parse import urlparse
        from ipaddress import ip_address
        for idx, entry in enumerate((owner_mcp or [])[:3]):
            if not isinstance(entry, dict):
                continue
            url=entry.get('url')
            if not isinstance(url,str) or len(url)>800:
                continue
            parsed=urlparse(url)
            host=parsed.hostname or ''
            try:
                private_address=not ip_address(host).is_global
            except ValueError:
                private_address=False
            if (parsed.scheme!='https' or not host or parsed.username or
                private_address or host in ('localhost','0.0.0.0') or
                host.endswith(('.local','.internal'))):
                continue
            bearer=entry.get('bearer')
            headers={}
            if isinstance(bearer,str) and bearer and len(bearer)<4096:
                headers['Authorization']='Bearer '+bearer
            self._owner_mcp_tools.append(
                mcp.MCPToolset(id='owner-mcp-'+str(idx+1),
                  mcp_server=mcp.MCPServerHTTP(url,headers=headers)))
''' + s[b:]
 agent.write_text(s,encoding='utf-8')
 once(agent,"    owner_mcp={}\n    mcp_url=owner_providers.get('mcp_url')\n    if isinstance(mcp_url,str) and mcp_url.startswith('https://'):\n        owner_mcp={'url':mcp_url,'bearer':str(owner_providers.get('mcp_bearer') or '')}",
      """    owner_mcp=owner_providers.get('mcp_servers')
    if not isinstance(owner_mcp,list):
        owner_mcp=[]
    owner_mcp=owner_mcp[:3]""")

 (root/'agent/tests/test_v36_mcp_slots.py').write_text("""from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_three_encrypted_mcp_slots():
 s=(R/'mobile/lib/screens/bacy10_provider_settings_screen.dart').read_text()
 assert "MCP server 2" in s and "MCP server 3" in s
 assert "mcp_bearer_2" in s and "mcp_bearer_3" in s
 p=(R/'mobile/lib/support/bacy10_provider_settings.dart').read_text()
 assert "'mcp_servers':servers" in p
 assert "mcp_url_3" in p
def test_livekit_three_toolsets():
 a=(R/'agent/src/agent.py').read_text()
 assert "owner-mcp-" in a
 assert "mcp.MCPToolset" in a
 assert "[:3]" in a
""",encoding='utf-8')
