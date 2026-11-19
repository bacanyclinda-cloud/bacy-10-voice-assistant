"""BACY-10 v3.6: cloud-backed editable owner preferences and connector library.

These are owner preferences and setup links, not a way to rewrite provider rules.
"""
from pathlib import Path

OWNER_DART = r'''
import 'package:flutter/material.dart';
import '../support/bacy10_memory.dart';

class BacyOwnerInstructionsScreen extends StatefulWidget {
  const BacyOwnerInstructionsScreen({super.key});
  @override
  State<BacyOwnerInstructionsScreen> createState() => _OwnerInstructionsState();
}

class _OwnerInstructionsState extends State<BacyOwnerInstructionsScreen> {
  final editor = TextEditingController();
  bool busy = true;
  String status = '';

  @override
  void initState() {super.initState();_load();}
  Future<void> _load() async {
    try {
      final facts=await BacyMemory.readAll();
      if(mounted)setState(() {
        editor.text=facts['owner_behavior_preferences'] ?? '';
        busy=false;
      });
    } catch (_) {if(mounted)setState(() {busy=false;status='Unable to read memories.';});}
  }

  Future<void> _save() async {
    final v=editor.text.trim();
    if(v.isEmpty || v.length>1200){
      setState(()=>status='Enter 1 to 1200 characters.');return;
    }
    setState(() {busy=true;status='Saving to private memory…';});
    try {
      final response=await BacyMemory.remember('owner_behavior_preferences',v);
      if(mounted)setState(()=>status='$response Reconnect voice to apply.');
    } catch (_){if(mounted)setState(()=>status='Save failed. Please try again.');}
    finally {if(mounted)setState(()=>busy=false);}
  }

  Future<void> _remove() async {
    setState(()=>busy=true);
    try {
      final result=await BacyMemory.forget('owner_behavior_preferences');
      if(mounted)setState(() {editor.clear();status=result;});
    } catch(_){if(mounted)setState(()=>status='Removal failed.');}
    finally {if(mounted)setState(()=>busy=false);}
  }
  @override
  void dispose(){editor.dispose();super.dispose();}
  @override
  Widget build(BuildContext context)=>Scaffold(
    backgroundColor:const Color(0xFF090F18),
    appBar:AppBar(title:const Text('Owner instructions'),backgroundColor:const Color(0xFF17212D)),
    body:SafeArea(child:ListView(padding:const EdgeInsets.all(18),children:[
      const Text('Teach BACY-10 your preferences',
        style:TextStyle(fontSize:20,color:Colors.white,fontWeight:FontWeight.w600)),
      const SizedBox(height:10),
      const Text('Edit your speaking style, coding preferences and phone-tool behaviour. Saves to your existing private cloud memory when online. These preferences do not override Android permissions or provider limits.',
        style:TextStyle(color:Color(0xFFAEC2D0),height:1.4)),
      const SizedBox(height:16),
      TextField(controller:editor,maxLines:9,maxLength:1200,enabled:!busy,
        style:const TextStyle(color:Colors.white),
        decoration:const InputDecoration(
          border:OutlineInputBorder(),
          labelText:'My instructions',
          hintText:'Speak casually and give full JavaScript code. Use my Android phone tools when I ask to open apps, draft messages or make a call.',
          alignLabelWithHint:true)),
      const SizedBox(height:12),
      FilledButton.icon(onPressed:busy?null:_save,
        icon:const Icon(Icons.cloud_upload_outlined),
        label:Text(busy?'Please wait':'SAVE PRIVATE INSTRUCTIONS')),
      OutlinedButton(onPressed:busy?null:_remove,child:const Text('Remove this preference')),
      if(status.isNotEmpty)Padding(padding:const EdgeInsets.only(top:12),
        child:Text(status,style:const TextStyle(color:Color(0xFFC9E2F0)))),
    ])),
  );
}
'''

CATALOG_DART = r'''
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class _Entry {
  final String name,method,details,url;
  const _Entry(this.name,this.method,this.details,this.url);
}

const entries = <_Entry>[
  _Entry('Google Gemini','API key','Add your own key in AI Providers, Test Gemini, save, then reconnect voice.','https://aistudio.google.com/apikey'),
  _Entry('ElevenLabs','API key','Save and test your key. Separate audio integration is required to replace Gemini Live speech.','https://elevenlabs.io/docs'),
  _Entry('LiveKit Cloud','Cloud project + token bridge','Deploy the agent and token bridge, then enter only the authorized HTTPS token endpoint.','https://docs.livekit.io/agents/'),
  _Entry('Gmail','Google OAuth via MCP','Connect a Gmail-capable HTTPS MCP server and grant mail scopes through Google sign-in.','https://developers.google.com/gmail/api/auth/about-auth'),
  _Entry('Google Calendar','Google OAuth via MCP','Authorize a Calendar-capable MCP service with Google sign-in.','https://developers.google.com/workspace/calendar/api/auth'),
  _Entry('Google Drive','Google OAuth via MCP','Authorize a Drive connector with the minimum file scope.','https://developers.google.com/drive/api/guides/about-auth'),
  _Entry('Google Docs','Google OAuth via MCP','Connect a Google Workspace Docs tool through OAuth.','https://developers.google.com/docs/api/auth'),
  _Entry('Google Sheets','Google OAuth via MCP','Connect a Sheets tool server with only necessary spreadsheet scopes.','https://developers.google.com/sheets/api/scopes'),
  _Entry('Google Contacts','Google OAuth via MCP','Enable the People API and authorize a connector.','https://developers.google.com/people'),
  _Entry('Google Photos','Google OAuth via MCP','Check supported Photos API permissions and connect through OAuth.','https://developers.google.com/photos'),
  _Entry('YouTube','Google OAuth or API','Enable YouTube Data API and authorize supported account features.','https://developers.google.com/youtube/v3'),
  _Entry('Google Maps','API or Android intents','Native directions work without a private Maps API key.','https://developers.google.com/maps/documentation'),
  _Entry('Outlook Mail','Microsoft OAuth via MCP','Register an Entra app and grant selected Graph mail scopes.','https://learn.microsoft.com/en-us/graph/auth/'),
  _Entry('Microsoft Calendar','Microsoft OAuth via MCP','Use Graph Calendars permissions through an authorized MCP server.','https://learn.microsoft.com/en-us/graph/api/resources/calendar'),
  _Entry('OneDrive','Microsoft OAuth via MCP','Connect Microsoft Graph Files endpoints.','https://learn.microsoft.com/en-us/graph/onedrive-concept-overview'),
  _Entry('Microsoft Teams','Microsoft OAuth via MCP','Requires approved Teams scopes and sometimes tenant administrator consent.','https://learn.microsoft.com/en-us/graph/teams-concept-overview'),
  _Entry('GitHub','OAuth or fine-grained token','Connect GitHub MCP through a server you trust.','https://github.com/github/github-mcp-server'),
  _Entry('GitLab','OAuth or access token','Use a limited project token and GitLab-compatible MCP server.','https://docs.gitlab.com/api/'),
  _Entry('Notion','OAuth or integration token','Create an integration and share selected pages.','https://developers.notion.com/'),
  _Entry('Slack','OAuth','Install an approved Slack app and connect its MCP server.','https://api.slack.com/authentication/oauth-v2'),
  _Entry('Discord','Bot token','Create a Discord bot and connect a controlled server.','https://discord.com/developers/docs/quick-start/overview-of-apps'),
  _Entry('Telegram','Bot token','Create a bot with BotFather and use Telegram Bot API tools.','https://core.telegram.org/bots/api'),
  _Entry('WhatsApp personal','Android app','Open WhatsApp and compose drafts on your phone, without exposing chat credentials.','https://faq.whatsapp.com/'),
  _Entry('WhatsApp Business API','Meta OAuth','Requires Meta business app, API permissions and approved sender.','https://developers.facebook.com/docs/whatsapp/cloud-api/'),
  _Entry('Facebook Pages','Meta OAuth','Use approved Pages API permissions for pages you control.','https://developers.facebook.com/docs/graph-api/'),
  _Entry('Instagram Professional','Meta OAuth','Requires an eligible professional account.','https://developers.facebook.com/docs/instagram-platform/'),
  _Entry('LinkedIn','Approved OAuth','Use only approved LinkedIn APIs and scopes.','https://learn.microsoft.com/en-us/linkedin/'),
  _Entry('Reddit','OAuth','Register an approved Reddit app and connect the API.','https://www.reddit.com/dev/api/'),
  _Entry('Dropbox','OAuth','Authorize a Dropbox developer app with selected file scopes.','https://www.dropbox.com/developers/documentation'),
  _Entry('Box','OAuth','Use a Box developer app and an authorized MCP gateway.','https://developer.box.com/'),
  _Entry('Trello','API token','Configure a scoped Trello connector.','https://developer.atlassian.com/cloud/trello/'),
  _Entry('Jira','Atlassian OAuth','Connect Jira Cloud through an authorized tool server.','https://developer.atlassian.com/cloud/jira/platform/'),
  _Entry('Confluence','Atlassian OAuth','Authorize selected Confluence spaces.','https://developer.atlassian.com/cloud/confluence/'),
  _Entry('Asana','OAuth or token','Grant access to the intended project or workspace.','https://developers.asana.com/docs'),
  _Entry('ClickUp','OAuth or token','Authorize a ClickUp API tool for selected spaces.','https://developer.clickup.com/'),
  _Entry('Airtable','Personal token','Generate a base-scoped Airtable token.','https://airtable.com/developers/web/api/introduction'),
  _Entry('Linear','OAuth or API token','Authorize access to intended Linear projects.','https://linear.app/developers'),
  _Entry('Figma','OAuth or token','Connect Figma files through its approved API.','https://www.figma.com/developers/api'),
  _Entry('Canva','OAuth','Use supported Canva Connect API permissions.','https://www.canva.dev/docs/connect/'),
  _Entry('Shopify','Custom app OAuth','Use minimum Shopify Admin scopes for your store.','https://shopify.dev/docs/api/admin-graphql'),
  _Entry('WooCommerce','REST API token','Use read-only WooCommerce REST keys first.','https://woocommerce.github.io/woocommerce-rest-api-docs/'),
  _Entry('Supabase','API via server','Keep service-role secrets on backend, not in the APK.','https://supabase.com/docs/guides/api'),
  _Entry('Cloudflare','Scoped API token','Connect account resources with limited-permission token.','https://developers.cloudflare.com/fundamentals/api/'),
  _Entry('Vercel','API token','Connect only specific team or project resources.','https://vercel.com/docs/rest-api'),
  _Entry('AWS','Short-lived IAM credentials','Use a backend with least-privilege temporary IAM permissions.','https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html'),
];

class BacyConnectionsCatalogScreen extends StatelessWidget {
 const BacyConnectionsCatalogScreen({super.key});
 @override
 Widget build(BuildContext context)=>Scaffold(
  backgroundColor:const Color(0xFF090F18),
  appBar:AppBar(title:const Text('Connections library'),backgroundColor:const Color(0xFF17212D)),
  body:ListView(children:[
   const Padding(padding:EdgeInsets.all(17),child:Text(
     'Choose a service and follow the official setup instructions. A guide entry is NOT an active connection. You need its authorized OAuth login or API key and a compatible MCP server before the agent can use it.',
     style:TextStyle(color:Color(0xFFB8CCD9),height:1.45))),
   ...entries.map((e)=>ExpansionTile(
    title:Text(e.name,style:const TextStyle(color:Colors.white)),
    subtitle:Text(e.method,style:const TextStyle(color:Color(0xFFA5BECA))),
    iconColor:const Color(0xFFB6DCEB),
    children:[Padding(padding:const EdgeInsets.fromLTRB(16,4,16,12),
     child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Text(e.details,style:const TextStyle(color:Color(0xFFCBDCE6),height:1.4)),
      TextButton(onPressed:()async{
       final uri=Uri.tryParse(e.url);
       if(uri!=null)await launchUrl(uri,mode:LaunchMode.externalApplication);
      },child:const Text('Open official setup guide')),
     ]))
    ],
   ))
  ]),
 );
}
'''

def once(file, old, new):
 s=file.read_text(encoding='utf-8')
 if s.count(old)!=1:raise RuntimeError(f'v36 UI anchor missing: {file} {old[:72]!r}, count={s.count(old)}')
 file.write_text(s.replace(old,new,1),encoding='utf-8')

def apply(root:Path):
 mobile=root/'mobile'
 (mobile/'lib/screens/bacy10_owner_instructions_screen.dart').write_text(OWNER_DART,encoding='utf-8')
 (mobile/'lib/screens/bacy10_connections_catalog_screen.dart').write_text(CATALOG_DART,encoding='utf-8')
 settings=mobile/'lib/screens/bacy10_provider_settings_screen.dart'
 once(settings,"import '../support/bacy10_token_client.dart';",
     "import '../support/bacy10_token_client.dart';\nimport 'bacy10_owner_instructions_screen.dart';\nimport 'bacy10_connections_catalog_screen.dart';")
 once(settings,"      _panel('Google Gemini',[",
     """      Card(color:const Color(0xFF17212D),child:Column(children:[
        ListTile(
          leading:const Icon(Icons.psychology_outlined,color:Color(0xFFBEE7FC)),
          title:const Text('Owner instructions',style:TextStyle(color:Colors.white)),
          subtitle:const Text('Edit and back up how BACY-10 behaves',style:TextStyle(color:Color(0xFFABBFCC))),
          onTap:()=>Navigator.push(context,MaterialPageRoute(
            builder:(_)=>const BacyOwnerInstructionsScreen())),
        ),
        ListTile(
          leading:const Icon(Icons.hub_outlined,color:Color(0xFFBEE7FC)),
          title:const Text('Connections library',style:TextStyle(color:Colors.white)),
          subtitle:const Text('App APIs, OAuth and MCP setup guides',style:TextStyle(color:Color(0xFFABBFCC))),
          onTap:()=>Navigator.push(context,MaterialPageRoute(
            builder:(_)=>const BacyConnectionsCatalogScreen())),
        ),
      ])),
      const SizedBox(height:14),
      _panel('Google Gemini',[""")
 (root/'agent/tests/test_owner_v36_ui.py').write_text("""from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_editable_owner_instruction_screen():
 s=(R/'mobile/lib/screens/bacy10_owner_instructions_screen.dart').read_text()
 assert "owner_behavior_preferences" in s
 assert "BacyMemory.remember" in s
 assert "BacyMemory.forget" in s
def test_connection_catalog_is_honest():
 s=(R/'mobile/lib/screens/bacy10_connections_catalog_screen.dart').read_text()
 assert "NOT an active connection" in s
 assert s.count("_Entry(")>35
 assert "launchUrl" in s
def test_provider_settings_navigation():
 s=(R/'mobile/lib/screens/bacy10_provider_settings_screen.dart').read_text()
 assert "BacyOwnerInstructionsScreen()" in s
 assert "BacyConnectionsCatalogScreen()" in s
""",encoding='utf-8')
 once(mobile/'pubspec.yaml','version: 3.5.0+40','version: 3.6.0+41')
 for file,old in [
     (root/'agent/tests/test_built_in_owner_directive.py',"assert 'version: 3.5.0+40' in pubspec"),
     (root/'agent/tests/test_behavior_restore.py',"assert 'version: 3.5.0+40' in (ROOT/'mobile/pubspec.yaml').read_text()"),
     (root/'agent/tests/test_owner_provider_settings.py',"assert 'version: 3.5.0+40' in (ROOT/'mobile/pubspec.yaml').read_text()"),
 ]:
  once(file,old,old.replace('3.5.0+40','3.6.0+41'))
