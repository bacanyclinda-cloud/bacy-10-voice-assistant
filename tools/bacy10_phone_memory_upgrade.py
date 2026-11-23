"""BACY-10 phone actions and private editable owner memory.

Applied to the pinned upstream source at package time. No account credentials
or secret values are included in the generated APK or checked-in files.
"""
from pathlib import Path


KOTLIN = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.content.Intent
import android.provider.MediaStore
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

class MainActivity : FlutterActivity() {
    private val channelName = "bacy10/phone"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                try {
                    when (call.method) {
                        "openApp" -> {
                            val requested = call.argument<String>("name")?.trim().orEmpty()
                            if (requested.isBlank() || requested.length > 80) {
                                result.error("BAD_NAME", "Say an installed app name.", null)
                                return@setMethodCallHandler
                            }
                            val knownPackages = mapOf(
                                "whatsapp" to "com.whatsapp",
                                "whatsapp business" to "com.whatsapp.w4b",
                                "youtube" to "com.google.android.youtube",
                                "chrome" to "com.android.chrome",
                                "facebook" to "com.facebook.katana",
                                "messenger" to "com.facebook.orca",
                                "telegram" to "org.telegram.messenger",
                                "spotify" to "com.spotify.music",
                                "maps" to "com.google.android.apps.maps",
                                "gmail" to "com.google.android.gm",
                                "camera" to "com.android.camera",
                                "settings" to "com.android.settings"
                            )
                            val lookup = requested.lowercase(Locale.ROOT)
                            val known = knownPackages[lookup]
                            val packageManager = packageManager
                            var launch = if (known != null) packageManager.getLaunchIntentForPackage(known) else null
                            if (launch == null) {
                                val query = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                                val installed = packageManager.queryIntentActivities(query, 0)
                                val candidate = installed.firstOrNull {
                                    it.loadLabel(packageManager).toString().lowercase(Locale.ROOT) == lookup
                                } ?: installed.firstOrNull {
                                    it.loadLabel(packageManager).toString().lowercase(Locale.ROOT).contains(lookup)
                                }
                                if (candidate != null) {
                                    launch = Intent(Intent.ACTION_MAIN)
                                        .addCategory(Intent.CATEGORY_LAUNCHER)
                                        .setClassName(candidate.activityInfo.packageName, candidate.activityInfo.name)
                                }
                            }
                            if (launch == null) {
                                result.success("That app is not installed or not available.")
                            } else {
                                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                startActivity(launch)
                                result.success("Opened " + requested + ".")
                            }
                        }
                        "openCamera" -> {
                            val selfie = call.argument<Boolean>("selfie") == true
                            val cameraIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                            if (selfie) {
                                cameraIntent.putExtra("android.intent.extras.CAMERA_FACING", 1)
                                cameraIntent.putExtra("android.intent.extra.USE_FRONT_CAMERA", true)
                                cameraIntent.putExtra("android.intent.extras.LENS_FACING_FRONT", 1)
                            }
                            if (cameraIntent.resolveActivity(packageManager) == null) {
                                result.success("No compatible camera app was found.")
                            } else {
                                startActivity(cameraIntent)
                                result.success(
                                    if (selfie) "Selfie camera opened. Tap the shutter to capture your photo."
                                    else "Camera opened. Tap the shutter to take a photo."
                                )
                            }
                        }
                        else -> result.notImplemented()
                    }
                } catch (error: Exception) {
                    result.error("PHONE_ACTION_FAILED", error.message ?: "Phone action failed.", null)
                }
            }
    }
}
'''


MEMORY_DART = r'''
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Owner-controlled private facts, stored in Android encrypted storage.
/// Defaults have no passwords, PINs, contact numbers, addresses, or API keys.
class BacyMemory {
  static const _storage = FlutterSecureStorage();
  static const _key = 'bacy10_private_profile_v1';
  // No personal profile is hard-coded into the APK. Owner facts are loaded
  // from the authenticated cloud memory after the phone is paired.
  static const Map<String, String> _defaults = {};

  static Future<Map<String, String>> readAll() async {
    final stored = await _storage.read(key: _key);
    if (stored == null) return Map<String, String>.of(_defaults);
    try {
      final decoded = jsonDecode(stored);
      if (decoded is Map) {
        return decoded.map((k, v) => MapEntry(k.toString(), v.toString()));
      }
    } catch (_) {}
    return <String, String>{};
  }

  static Future<void> saveAll(Map<String, String> facts) async {
    await _storage.write(key: _key, value: jsonEncode(facts));
  }

  static Future<String> remember(String field, String value) async {
    final key = field.trim().toLowerCase();
    final item = value.trim();
    if (key.isEmpty || item.isEmpty || key.length > 65 || item.length > 1300) {
      return 'Cannot save that detail; use a short field name and value.';
    }
    if (RegExp(r'password|passphrase|secret|api.?key|bank.?pin|otp|cvv', caseSensitive: false)
        .hasMatch(key)) {
      return 'For your privacy, I will not save passwords, PINs, or secret codes.';
    }
    final items = await readAll();
    if (items.length >= 80 && !items.containsKey(key)) {
      return 'The profile is full. Delete a fact first.';
    }
    items[key] = item;
    await saveAll(items);
    return 'Saved the detail about ' + key + ' to your private phone memory.';
  }

  static Future<String> forget(String field) async {
    final key = field.trim().toLowerCase();
    final items = await readAll();
    if (!items.containsKey(key)) return 'No saved detail named ' + key + '.';
    items.remove(key);
    await saveAll(items);
    return 'Forgot your saved detail about ' + key + '.';
  }

  static Future<void> clear() async => saveAll(<String, String>{});
}
'''


MEMORY_SCREEN = r'''
import 'package:flutter/material.dart';
import '../support/bacy10_memory.dart';

/// Lets the owner review, correct and delete all facts spoken to BACY-10.
/// Never uploads the profile to GitHub or a separate database.
class BacyMemoryScreen extends StatefulWidget {
  const BacyMemoryScreen({super.key});

  @override
  State<BacyMemoryScreen> createState() => _BacyMemoryScreenState();
}

class _BacyMemoryScreenState extends State<BacyMemoryScreen> {
  Map<String, String> facts = {};
  bool loading = true;
  bool busy = false;
  final keyController = TextEditingController();
  final valueController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final saved = await BacyMemory.readAll();
    if (mounted) setState(() { facts = saved; loading = false; });
  }

  @override
  void dispose() {
    keyController.dispose();
    valueController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => busy = true);
    final result = await BacyMemory.remember(keyController.text, valueController.text);
    keyController.clear();
    valueController.clear();
    await _load();
    if (mounted) {
      setState(() => busy = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result)));
    }
  }

  Future<void> _clear() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete all personal memory?'),
        content: const Text('This deletes saved facts and conversation history from your phone and private cloud memory. Keep the app installed and connected until cloud deletion is confirmed.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete memory')),
        ],
      ),
    );
    if (confirmed == true) {
      final result = await BacyMemory.clear();
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result)));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFF070B11),
    appBar: AppBar(
      title: const Text('My BACY-10 memory'),
      backgroundColor: const Color(0xFF070B11),
      foregroundColor: Colors.white,
    ),
    body: loading ? const Center(child: CircularProgressIndicator()) :
      ListView(
        padding: const EdgeInsets.all(18),
        children: [
          const Text(
            'Your details are encrypted on this phone. You can also say '
            '"remember my girlfriend is ..." or "forget my address" during a call. '
            'Only add personal details you want your cloud voice assistant to know.',
            style: TextStyle(color: Color(0xFFB5C5D0), height: 1.5),
          ),
          const SizedBox(height: 16),
          for (final entry in facts.entries)
            Card(
              color: const Color(0xFF14202B),
              child: ListTile(
                title: Text(entry.key, style: const TextStyle(color: Color(0xFFA9D7E5))),
                subtitle: Text(entry.value, style: const TextStyle(color: Colors.white)),
                trailing: IconButton(
                  icon: const Icon(Icons.delete_outline, color: Color(0xFFD3A79C)),
                  onPressed: () async {
                    await BacyMemory.forget(entry.key);
                    await _load();
                  },
                ),
                onTap: () {
                  keyController.text = entry.key;
                  valueController.text = entry.value;
                },
              ),
            ),
          const SizedBox(height: 22),
          TextField(
            controller: keyController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'Fact name (girlfriend, home, phone, studies...)',
              labelStyle: TextStyle(color: Color(0xFFB5C5D0)),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: valueController,
            maxLines: 3,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              labelText: 'What should BACY-10 remember?',
              labelStyle: TextStyle(color: Color(0xFFB5C5D0)),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: busy ? null : _save,
            child: const Text('Save to private memory'),
          ),
          const SizedBox(height: 18),
          TextButton(
            onPressed: _clear,
            child: const Text('Delete all saved memory', style: TextStyle(color: Color(0xFFD3A79C))),
          ),
        ],
      ),
  );
}
'''


PHONE_TOOLS = r'''
"""Android phone actions dispatched only to the current user's LiveKit client."""
import json
from livekit.agents import RunContext, function_tool, get_job_context
from livekit.agents.llm import ToolError


class PhoneTools:
    @property
    def tools(self):
        return [
            self.open_android_app,
            self.open_phone_camera,
            self.open_selfie_camera,
            self.read_my_private_memory,
            self.remember_about_me,
            self.forget_about_me,
        ]

    async def _phone(self, method: str, args: dict) -> dict:
        ctx = get_job_context()
        participants = list(ctx.room.remote_participants.values())
        if not participants:
            raise ToolError("Your Android phone is not connected to the voice call.")
        try:
            response = await ctx.room.local_participant.perform_rpc(
                destination_identity=participants[0].identity,
                method=method,
                payload=json.dumps(args),
                response_timeout=20.0,
            )
            value = json.loads(response)
            if not isinstance(value, dict):
                raise ValueError("Invalid phone response.")
            return value
        except Exception as exc:
            raise ToolError("The phone could not complete that action: " + str(exc)) from exc

    @function_tool()
    async def open_android_app(self, context: RunContext, app_name: str) -> str:
        """Open an installed Android phone application by its visible app name.

        Args:
            app_name: Name of app to launch, such as WhatsApp, YouTube, Settings or Chrome.
        """
        return str((await self._phone("bacy10.phone", {"action": "open_app", "name": app_name})).get("message"))

    @function_tool()
    async def open_phone_camera(self, context: RunContext) -> str:
        """Open the Android system camera visibly on the user's phone."""
        return str((await self._phone("bacy10.phone", {"action": "open_camera"})).get("message"))

    @function_tool()
    async def open_selfie_camera(self, context: RunContext) -> str:
        """Open the front camera to take a selfie. User presses shutter to save photo."""
        return str((await self._phone("bacy10.phone", {"action": "selfie"})).get("message"))

    @function_tool()
    async def read_my_private_memory(self, context: RunContext) -> dict:
        """Retrieve the owner's current saved name, studies, girlfriend, preferences, projects, and other voluntary facts.

        Call when asked who the owner is, what you remember, or before answering a personal question.
        """
        return await self._phone("bacy10.memory", {"action": "read"})

    @function_tool()
    async def remember_about_me(self, context: RunContext, fact_name: str, fact_value: str) -> str:
        """Privately remember a durable fact about the owner when they ask you to remember it.

        Args:
            fact_name: Concise type of fact such as studies, girlfriend, home, preferences.
            fact_value: Factual value provided by owner, not an inference.
        """
        return str((await self._phone("bacy10.memory", {"action": "remember", "key": fact_name, "value": fact_value})).get("message"))

    @function_tool()
    async def forget_about_me(self, context: RunContext, fact_name: str) -> str:
        """Delete a previously saved fact from the owner's phone at their request.

        Args:
            fact_name: The fact name the owner wants removed.
        """
        return str((await self._phone("bacy10.memory", {"action": "forget", "key": fact_name})).get("message"))
'''


def apply(root: Path) -> None:
    mobile = root / "mobile"
    main = mobile / "android/app/src/main"
    (main / "kotlin/com/livekit/example/VoiceAssistant/MainActivity.kt").write_text(KOTLIN, encoding="utf-8")
    manifest = main / "AndroidManifest.xml"
    xml = manifest.read_text(encoding="utf-8")
    launcher_query = '''        <intent>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent>
'''
    xml = xml.replace("    <queries>\n", "    <queries>\n" + launcher_query, 1)
    manifest.write_text(xml, encoding="utf-8")

    (mobile / "lib/support/bacy10_memory.dart").write_text(MEMORY_DART, encoding="utf-8")
    (mobile / "lib/screens/bacy10_memory_screen.dart").write_text(MEMORY_SCREEN, encoding="utf-8")

    controller = mobile / "lib/controllers/app_ctrl.dart"
    t = controller.read_text(encoding="utf-8")
    t = t.replace("import 'dart:async';", "import 'dart:async';\nimport 'dart:convert';\nimport 'package:flutter/services.dart';\nimport '../support/bacy10_memory.dart';", 1)
    t = t.replace("    session.addListener(_handleSessionChange);", '''
    // RPC is restricted to the authenticated LiveKit AI participant.
    room.registerRpcMethod('bacy10.phone', (request) async {
      if (room.agentParticipant?.identity != request.callerIdentity) {
        return jsonEncode({'ok': false, 'message': 'Only your BACY-10 agent may control this phone.'});
      }
      try {
        final command = jsonDecode(request.payload) as Map<String, dynamic>;
        final channel = const MethodChannel('bacy10/phone');
        String? message;
        switch (command['action']) {
          case 'open_app':
            message = await channel.invokeMethod<String>('openApp', {'name': command['name']});
            break;
          case 'open_camera':
            message = await channel.invokeMethod<String>('openCamera', {'selfie': false});
            break;
          case 'selfie':
            message = await channel.invokeMethod<String>('openCamera', {'selfie': true});
            break;
          default:
            message = 'Unsupported phone action.';
        }
        return jsonEncode({'ok': true, 'message': message ?? 'No result.'});
      } catch (error) {
        return jsonEncode({'ok': false, 'message': 'Phone action failed: ' + error.toString()});
      }
    });
    room.registerRpcMethod('bacy10.memory', (request) async {
      if (room.agentParticipant?.identity != request.callerIdentity) {
        return jsonEncode({'ok': false, 'message': 'Memory access denied.'});
      }
      try {
        final requestData = jsonDecode(request.payload) as Map<String, dynamic>;
        switch (requestData['action']) {
          case 'read':
            return jsonEncode({'ok': true, 'facts': await BacyMemory.readAll()});
          case 'remember':
            return jsonEncode({'ok': true, 'message': await BacyMemory.remember(
              (requestData['key'] ?? '').toString(), (requestData['value'] ?? '').toString())});
          case 'forget':
            return jsonEncode({'ok': true, 'message': await BacyMemory.forget(
              (requestData['key'] ?? '').toString())});
        }
      } catch (error) {
        return jsonEncode({'ok': false, 'message': 'Could not use private memory.'});
      }
      return jsonEncode({'ok': false, 'message': 'Unknown memory action.'});
    });
    session.addListener(_handleSessionChange);''', 1)
    t = t.replace("    session.removeListener(_handleSessionChange);",
                  "    room.unregisterRpcMethod('bacy10.phone');\n"
                  "    room.unregisterRpcMethod('bacy10.memory');\n"
                  "    session.removeListener(_handleSessionChange);", 1)
    controller.write_text(t, encoding="utf-8")

    welcome = mobile / "lib/screens/welcome_screen.dart"
    t = welcome.read_text(encoding="utf-8")
    t = t.replace("import 'package:flutter/material.dart';",
                  "import 'package:flutter/material.dart';\nimport 'bacy10_memory_screen.dart';", 1)
    needle = "                  const SizedBox(height: 22),\n                  const Text('REAL-TIME AUDIO"
    if needle not in t:
        raise RuntimeError("BACY-10 welcome screen changed unexpectedly.")
    t = t.replace(needle, '''                  const SizedBox(height: 16),
                  TextButton.icon(
                    onPressed: () => Navigator.of(ctx).push(
                      MaterialPageRoute(builder: (_) => const BacyMemoryScreen()),
                    ),
                    icon: const Icon(Icons.person_outline),
                    label: const Text('My private memory'),
                  ),
''' + needle, 1)
    welcome.write_text(t, encoding="utf-8")

    pubspec = mobile / "pubspec.yaml"
    t = pubspec.read_text(encoding="utf-8").replace("version: 1.1.0+15", "version: 1.2.0+16")
    pubspec.write_text(t, encoding="utf-8")

    agent = root / "agent/src"
    (agent / "phone_tools.py").write_text(PHONE_TOOLS, encoding="utf-8")
    entry = agent / "agent.py"
    t = entry.read_text(encoding="utf-8")
    t = t.replace("from tools import BrowserTools", "from tools import BrowserTools\nfrom phone_tools import PhoneTools", 1)
    t = t.replace("        self.browser_tools = BrowserTools(self.browser)",
                  "        self.browser_tools = BrowserTools(self.browser)\n"
                  "        self.phone_tools = PhoneTools()", 1)
    t = t.replace("                *self.browser_tools.tools,",
                  "                *self.browser_tools.tools,\n"
                  "                *self.phone_tools.tools,", 1)
    t = t.replace("                        # Tools\n",
                  """                        # Android phone actions and private memory
                        - You control Android apps only using the open_android_app tool, never browser tools.
                        - Use open_phone_camera or open_selfie_camera for camera requests.
                        - Selfie capture requires the user's visible shutter press. Never say a photo was taken until confirmed.
                        - Call read_my_private_memory when asked about the owner or personal history.
                        - Remember new personal facts only when the owner explicitly requests this.
                        - Do not invent girlfriend names or details absent from owner memory.
                        - Never store passwords, API keys, verification codes, banking PINs, or similar secrets.
                        - Keep existing British voice and concise, warm style.
                        - Browser controls act on the cloud browser, not arbitrary Android applications.
                        - Opening installed apps does not grant ability to click other apps, send messages, or control the whole phone.

                        # Tools
""", 1)
    entry.write_text(t, encoding="utf-8")
