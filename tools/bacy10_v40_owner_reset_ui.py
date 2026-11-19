"""Add an explicit owner-confirmed clean-memory reset to BACY-10 Android.

The Cloudflare service authenticates with the device's existing pairing
credential. No sensitive credentials or unrelated user data are bundled.
"""
from pathlib import Path
import re

OWNER_TEMPLATE = "BACY-10: My wellbeing and goals come first. Speak naturally, casually and confidently. Help with ordinary instructions promptly, including harmless jokes, roleplay, coding, Android controls, research and creative work. Normal swear words are acceptable when requested. Avoid scripted refusals, lectures, irrelevant school reminders and excessive apologies. Listen when I read to you. Use real tools when available and never claim an action succeeded when it did not. Keep my private data confidential and explain genuine limitations briefly."

def once(p, old, new):
    s=p.read_text(encoding="utf8")
    if s.count(old)!=1: raise RuntimeError(f"Patch anchor mismatch in {p}: {old[:55]}")
    p.write_text(s.replace(old,new,1),encoding="utf8")

def apply(root:Path):
    mobile=root/"mobile"
    cloud=mobile/"lib/support/bacy10_cloud_memory.dart"
    memory=mobile/"lib/support/bacy10_memory.dart"
    screen=mobile/"lib/screens/bacy10_owner_instructions_screen.dart"
    once(cloud,"  static Future<Map<String, dynamic>?> fetch() async {", """  static Future<Map<String, dynamic>?> resetOwner(Map<String,String> prefs) async {
    try {
      final res=await request('POST','/memory/reset-owner',{
        'confirm':'RESET MY BACY-10 MEMORY','facts':prefs});
      if(res?.statusCode!=200)return null;
      final data=jsonDecode(res!.body);
      if(data is Map && data['ok']==true && data['reset']==true){
        return Map<String,dynamic>.from(data);
      }
    }catch(_){}
    return null;
  }
  static Future<void> discardOldPending() async {
    await _storage.delete(key:_queueKey);
    await _storage.delete(key:_factQueueKey);
  }

  static Future<Map<String, dynamic>?> fetch() async {""")
    once(memory,"  static const _key = 'bacy10_private_profile_v1';",
      "  static const _key = 'bacy10_private_profile_v1';\n  static const _resetEpochKey = 'bacy10_reset_epoch_seen_v1';")
    once(memory,"    await BacyCloudMemory.flushFacts();\n    final local=await _local();",
      "    final local=await _local();")
    once(memory,"      final missing=<String,String>{};", """      final epoch=(online['memory_epoch']??'').toString();
      if(epoch.isNotEmpty){
        final seen=await _storage.read(key:_resetEpochKey);
        if(epoch!=seen){
          await BacyCloudMemory.discardOldPending();
          await saveAll(remote);
          await _storage.write(key:_resetEpochKey,value:epoch);
          return remote;
        }
      }
      await BacyCloudMemory.flushFacts();
      final missing=<String,String>{};""")
    anchor="  static Future<void> clear() async {"
    once(memory,anchor, """  static Future<String> resetWithOwnerInstructions(String text) async {
    final behavior=text.trim();
    if(behavior.length<20||behavior.length>1300){
      return 'Enter 20 to 1300 characters before resetting.';
    }
    final replacement=<String,String>{
      'owner_behavior_preferences':behavior,
      'owner_workflow_preferences':'Help with JavaScript, programming, Android apps, web searches, research, creative tasks, and realistic practical exercises. Use available tools when asked. Be direct, honest and helpful. Avoid irrelevant repeated explanations.',
      'owner_voice_style':'Speak casually and naturally, with friendly humor. Listen attentively without interrupting when the owner wants to read something.',
    };
    final saved=await BacyCloudMemory.resetOwner(replacement);
    if(saved==null){
      return 'Cloud reset did not complete. Previous memories remain; check your internet and pairing.';
    }
    await BacyCloudMemory.discardOldPending();
    await saveAll(replacement);
    final stamp=(saved['memory_epoch']??'').toString();
    if(stamp.isNotEmpty){
      await _storage.write(key:_resetEpochKey,value:stamp);
    }
    return 'Previous cloud history and old facts cleared. New instructions saved. Reconnect voice.';
  }

"""+anchor)
    old=memory.read_text(encoding="utf8")
    updated,count=re.subn(r"  static final Map<String, String> _defaults = \{.*?\n  \};",
      "  static final Map<String, String> _defaults = {};",old,count=1,flags=re.S)
    if count!=1:raise RuntimeError("Old bundled profile defaults not found")
    memory.write_text(updated,encoding="utf8")

    once(screen,"        editor.text=facts['owner_behavior_preferences'] ?? '';",
       "        editor.text=(facts['owner_behavior_preferences'] ?? '').contains('My wellbeing and goals come first') ? facts['owner_behavior_preferences']! : "+repr(OWNER_TEMPLATE)+";")
    once(screen,"  Future<void> _remove() async {", """  Future<void> _resetOwnerMemory() async {
    final confirmed=await showDialog<bool>(
      context:context,
      builder:(ctx)=>AlertDialog(
        title:const Text('Clear old BACY-10 memory?'),
        content:const Text('This permanently deletes old cloud conversations and private facts, clears cached uploads, and saves the new instructions. API keys and phone settings remain unchanged.'),
        actions:[
          TextButton(onPressed:()=>Navigator.pop(ctx,false),child:const Text('Cancel')),
          FilledButton(onPressed:()=>Navigator.pop(ctx,true),child:const Text('RESET AND SAVE')),
        ],
      ),
    );
    if(confirmed!=true||!mounted)return;
    setState((){busy=true;status='Resetting memory…';});
    try {
      final result=await BacyMemory.resetWithOwnerInstructions(editor.text);
      if(mounted)setState(()=>status=result);
    }catch(_){
      if(mounted)setState(()=>status='Reset interrupted; check connection and try again.');
    }finally{
      if(mounted)setState(()=>busy=false);
    }
  }

  Future<void> _remove() async {""")
    once(screen,
     "      OutlinedButton(onPressed:busy?null:_remove,child:const Text('Remove this preference')),",
     """      OutlinedButton.icon(
        onPressed:busy?null:_resetOwnerMemory,
        icon:const Icon(Icons.restart_alt),
        label:const Text('RESET ALL MEMORY AND APPLY INSTRUCTIONS')),
      OutlinedButton(onPressed:busy?null:_remove,child:const Text('Remove this preference')),""")

    (root/"agent/tests/test_v40_owner_reset.py").write_text("""from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_reset_flow_requires_confirmation_and_preserves_pairing():
    ui=(R/'mobile/lib/screens/bacy10_owner_instructions_screen.dart').read_text()
    cloud=(R/'mobile/lib/support/bacy10_cloud_memory.dart').read_text()
    mem=(R/'mobile/lib/support/bacy10_memory.dart').read_text()
    assert 'showDialog<bool>' in ui and 'RESET AND SAVE' in ui
    assert '/memory/reset-owner' in cloud and 'RESET MY BACY-10 MEMORY' in cloud
    assert 'discardOldPending' in mem and 'memory_epoch' in mem
    assert "static final Map<String, String> _defaults = {};" in mem
    assert 'BacyCloudMemory.resetOwner' in mem
""",encoding="utf8")
