"""BACY-10 mobile assistant reliability and safe native Android capabilities.

Applies to the generated Flutter / LiveKit source at packaging time.
No credentials or backend secrets are embedded in the APK.
"""
from pathlib import Path

READY_SCREEN = r"""
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';
import '../controllers/app_ctrl.dart' as app;
import '../support/bacy10_token_client.dart';
import '../widgets/bacy_live_orb.dart';

/// Fast, animated assistant home. Existing pairing is reused from encrypted
/// Android storage; a fresh device can authorize in Connection settings.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});
  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  bool hasPairing = false;
  bool initializing = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    try {
      hasPairing = await PairingTokenClient.hasPairingCode();
    } catch (_) {
      hasPairing = false;
    }
    if (!mounted) return;
    setState(() => initializing = false);
    if (hasPairing) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.read<app.AppCtrl>().connect();
      });
    }
  }

  Future<void> _connectionSettings() async {
    final input = TextEditingController();
    final code = await PairingTokenClient.readCode();
    input.text = code ?? '';
    if (!mounted) { input.dispose(); return; }
    final changed = await showDialog<String>(
      context: context,
      builder: (dialog) => AlertDialog(
        backgroundColor: const Color(0xFF0F1723),
        title: const Text('Secure voice connection', style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('BACY-10 needs private authorization once per device. An existing paired phone reconnects automatically.',
              style: TextStyle(color: Color(0xFFAFBAC8))),
            const SizedBox(height: 16),
            TextField(
              controller: input,
              obscureText: true,
              enableSuggestions: false,
              autocorrect: false,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Private connection code',
                labelStyle: TextStyle(color: Color(0xFFAFBAC8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialog), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(dialog, input.text.trim()),
            child: const Text('Save privately')),
        ],
      ),
    );
    input.dispose();
    if (changed == null || changed.isEmpty) return;
    await PairingTokenClient.saveCode(changed);
    if (!mounted) return;
    setState(() => hasPairing = true);
    context.read<app.AppCtrl>().connect();
  }

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF05070C),
    child: SafeArea(
      child: Consumer2<app.AppCtrl, sdk.Session>(
        builder: (ctx, controller, session, _) => Stack(
          children: [
            Positioned(
              top: 9, right: 10,
              child: IconButton(
                icon: const Icon(Icons.tune_rounded, color: Color(0xFF8B9EAF)),
                tooltip: 'Connection settings',
                onPressed: _connectionSettings,
              ),
            ),
            Center(child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 500),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Text('BACY—10', style: TextStyle(
                  fontSize: 30, letterSpacing: 6, color: Color(0xFFF5F9FF),
                  fontWeight: FontWeight.w300)),
                const SizedBox(height: 5),
                const Text('PERSONAL INTELLIGENCE', style: TextStyle(
                  letterSpacing: 2, color: Color(0xFF91A4BA), fontSize: 10)),
                const SizedBox(height: 28),
                const SizedBox(
                  width: 300, height: 300,
                  child: BacyLiveOrb(),
                ),
                const SizedBox(height: 13),
                Text(controller.isSessionStarting ? 'Establishing secure voice…' :
                  (hasPairing ? 'Ready to speak' : 'Set up your private voice connection'),
                  style: const TextStyle(color: Color(0xFFBFCEDC), fontSize: 15)),
                if (controller.connectionError != null) Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 10),
                  child: Text(controller.connectionError!, textAlign: TextAlign.center,
                    style: const TextStyle(color: Color(0xFFE6AFAA), fontSize: 13)),
                ),
                const SizedBox(height: 19),
                SizedBox(
                  width: 194, height: 50,
                  child: FilledButton.icon(
                    onPressed: initializing || controller.isSessionStarting
                      ? null : (hasPairing ? controller.connect : _connectionSettings),
                    icon: const Icon(Icons.mic_none_rounded),
                    label: Text(controller.isSessionStarting ? 'CONNECTING' : 'START VOICE'),
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFFBCD7EB),
                      foregroundColor: const Color(0xFF0B1521),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
                    ),
                  ),
                ),
              ]),
            )),
          ],
        ),
      ),
    ),
  );
}
"""

ACCESSIBILITY = r"""
package com.livekit.example.VoiceAssistantFlutter

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/** Explicitly user-enabled Android accessibility actions. No background scraping. */
class BacyAccessibilityService : AccessibilityService() {
    companion object {
        var instance: BacyAccessibilityService? = null
            private set

        fun describeScreen(): String {
            val service = instance ?: return "Enable BACY-10 in Android Accessibility settings first."
            val root = service.rootInActiveWindow ?: return "No active screen is available to inspect."
            val packageName = root.packageName?.toString().orEmpty()
            if (isProtected(packageName)) return "Sensitive app screen is protected from AI inspection."
            val results = mutableListOf<String>()
            fun visit(node: AccessibilityNodeInfo?, depth: Int) {
                if (node == null || depth > 20 || results.size >= 70) return
                if (node.isPassword) return
                val text = node.text?.toString()?.trim().orEmpty()
                val hint = node.contentDescription?.toString()?.trim().orEmpty()
                val label = if (text.isNotBlank()) text else hint
                if (label.isNotBlank()) results.add(label.take(130))
                for (i in 0 until node.childCount) visit(node.getChild(i), depth + 1)
            }
            visit(root, 0)
            return "Visible controls in " + packageName + ": " + results.distinct().joinToString(" | ").take(5000)
        }

        fun clickVisible(label: String): String {
            val service = instance ?: return "Enable BACY-10 in Accessibility settings first."
            if (label.length !in 2..100) return "Give the exact visible control name."
            val risky = setOf("pay", "buy", "send", "delete", "purchase", "confirm", "transfer", "reset")
            if (risky.any { label.lowercase().contains(it) }) {
                return "For safety, tap this sensitive action yourself."
            }
            val root = service.rootInActiveWindow ?: return "The active screen is unavailable."
            if (isProtected(root.packageName?.toString().orEmpty())) {
                return "This sensitive app cannot be controlled by BACY-10."
            }
            fun find(node: AccessibilityNodeInfo?, depth: Int): AccessibilityNodeInfo? {
                if (node == null || depth > 20 || node.isPassword) return null
                val a = node.text?.toString().orEmpty()
                val b = node.contentDescription?.toString().orEmpty()
                if (a.equals(label, true) || b.equals(label, true)) return node
                for (i in 0 until node.childCount) {
                    val found = find(node.getChild(i), depth + 1)
                    if (found != null) return found
                }
                return null
            }
            var node = find(root, 0) ?: return "I cannot find that control on screen."
            for (i in 0..4) {
                if (node.isClickable && node.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return "Tapped the visible control."
                }
                node = node.parent ?: break
            }
            return "The control is visible but Android did not allow a tap."
        }

        fun global(button: String): String {
            val service = instance ?: return "Enable BACY-10 in Accessibility settings first."
            val action = when (button.lowercase()) {
                "back" -> GLOBAL_ACTION_BACK
                "home" -> GLOBAL_ACTION_HOME
                "recents" -> GLOBAL_ACTION_RECENTS
                "notifications" -> GLOBAL_ACTION_NOTIFICATIONS
                "quick_settings" -> GLOBAL_ACTION_QUICK_SETTINGS
                else -> return "Supported navigation: back, home, recents, notifications, quick_settings."
            }
            return if (service.performGlobalAction(action)) "Navigation performed."
                else "Android did not permit that navigation."
        }

        private fun isProtected(name: String): Boolean {
            val value = name.lowercase()
            return listOf("bank", "wallet", "authenticator", "password", "capitec",
                "fnb", "standardbank", "absa", "nedbank", "tyme", "paypal").any { value.contains(it) }
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() {}
    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }
}
"""

ACCESS_CONFIG = r"""<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeWindowStateChanged|typeWindowContentChanged"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:canRetrieveWindowContent="true"
    android:description="@string/accessibility_description"
    android:notificationTimeout="150"
    android:accessibilityFlags="flagReportViewIds"/>
"""

NATIVE_BRANCH = r"""
                                "navigate" -> {
                                    val place = call.argument<String>("place")?.trim().orEmpty()
                                    if (place.isBlank() || place.length > 180) {
                                        "Tell me a place or address to navigate to."
                                    } else {
                                        val uri = android.net.Uri.parse("geo:0,0?q=" + android.net.Uri.encode(place))
                                        val intent = Intent(Intent.ACTION_VIEW, uri)
                                        startActivity(intent)
                                        "Opened maps for " + place + ". Check the route and start navigation."
                                    }
                                }
                                "screen_read" -> BacyAccessibilityService.describeScreen()
                                "screen_tap" -> BacyAccessibilityService.clickVisible(
                                    call.argument<String>("label")?.trim().orEmpty())
                                "system_nav" -> BacyAccessibilityService.global(
                                    call.argument<String>("button")?.trim().orEmpty())
                                "accessibility_settings" -> {
                                    startActivity(Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS))
                                    "Opened Accessibility settings so you can authorize BACY-10 screen controls."
                                }
                                "whatsapp_draft" -> {
                                    val phone = call.argument<String>("phone")?.filter { it.isDigit() }.orEmpty()
                                    val body = call.argument<String>("body")?.take(1800).orEmpty()
                                    if (phone.length !in 8..15 || body.isBlank()) {
                                        "Give a valid WhatsApp phone number and a message."
                                    } else {
                                        val url = "https://wa.me/" + phone + "?text=" + android.net.Uri.encode(body)
                                        startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
                                        "Opened a WhatsApp message draft. Review and tap Send."
                                    }
                                }
                                "calendar_draft" -> {
                                    val title = call.argument<String>("title")?.trim()?.take(120).orEmpty()
                                    if (title.isBlank()) "Give me the calendar event name."
                                    else {
                                        val intent = Intent(Intent.ACTION_INSERT)
                                            .setData(android.provider.CalendarContract.Events.CONTENT_URI)
                                            .putExtra(android.provider.CalendarContract.Events.TITLE, title)
                                        startActivity(intent)
                                        "Opened the calendar event editor for your review."
                                    }
                                }
                                "choose_photo" -> {
                                    val intent = Intent(Intent.ACTION_GET_CONTENT)
                                        .setType("image/*")
                                        .addCategory(Intent.CATEGORY_OPENABLE)
                                    startActivity(Intent.createChooser(intent, "Choose a photo"))
                                    "Opened Android photo selection. You choose which photo to share."
                                }
"""

EXTRA_TOOLS = r'''
    @function_tool()
    async def navigate_on_android(self, context: RunContext, destination: str) -> str:
        """Open Android maps route search for an address, business or nearest category, e.g. nearest airport. Do not use cloud Playwright to navigate on the phone."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "navigate", "place": destination})).get("message"))

    @function_tool()
    async def inspect_current_android_screen(self, context: RunContext) -> str:
        """Read the currently visible Android screen after the owner enables Accessibility and requests help. Sensitive banking and password screens are excluded."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "screen_read"})).get("message"))

    @function_tool()
    async def tap_visible_android_label(self, context: RunContext, label: str) -> str:
        """Tap one exact visible nonsensitive Android control by label, only when the owner has asked for that action."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "screen_tap", "label": label})).get("message"))

    @function_tool()
    async def android_system_navigation(self, context: RunContext, button: str) -> str:
        """Android Back, Home, Recents, Notifications or Quick Settings navigation, when user-enabled Accessibility is available."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "system_nav", "button": button})).get("message"))

    @function_tool()
    async def enable_android_screen_controls(self, context: RunContext) -> str:
        """Open the user-controlled Android Accessibility permission screen."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "accessibility_settings"})).get("message"))

    @function_tool()
    async def draft_whatsapp_on_phone(self, context: RunContext, phone_number: str, message: str) -> str:
        """Open a WhatsApp draft and let the owner review and send it; never claim it was sent."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "whatsapp_draft", "phone": phone_number, "body": message})).get("message"))

    @function_tool()
    async def create_calendar_event_draft(self, context: RunContext, title: str) -> str:
        """Open Android calendar with an event draft for the owner to review and save."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "calendar_draft", "title": title})).get("message"))

    @function_tool()
    async def open_phone_photo_picker(self, context: RunContext) -> str:
        """Open Android's private photo picker; only owner-selected images are accessible."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "choose_photo"})).get("message"))
'''

def change_one(path: Path, needle: str, replacement: str) -> None:
    data = path.read_text(encoding="utf-8")
    if data.count(needle) != 1:
        raise RuntimeError(f"Expected one match in {path}: {needle[:70]}")
    path.write_text(data.replace(needle, replacement, 1), encoding="utf-8")


def apply(root: Path) -> None:
    mobile = root / "mobile"
    agent = root / "agent/src"
    (mobile / "lib/screens/welcome_screen.dart").write_text(READY_SCREEN, encoding="utf-8")
    main = mobile / "android/app/src/main"
    native = main / "kotlin/com/livekit/example/VoiceAssistant"
    (native / "BacyAccessibilityService.kt").write_text(ACCESSIBILITY, encoding="utf-8")
    values = main / "res/values/strings.xml"
    if values.exists():
        xml = values.read_text(encoding="utf-8")
        if "accessibility_description" not in xml:
            xml = xml.replace("</resources>",
              '<string name="accessibility_description">BACY-10 screen control on your request</string>\n</resources>')
            values.write_text(xml, encoding="utf-8")
    else:
        values.parent.mkdir(parents=True, exist_ok=True)
        values.write_text('<resources><string name="accessibility_description">BACY-10 screen control on your request</string></resources>', encoding="utf-8")
    access_xml = main / "res/xml/bacy10_accessibility.xml"
    access_xml.parent.mkdir(parents=True, exist_ok=True)
    access_xml.write_text(ACCESS_CONFIG, encoding="utf-8")

    manifest = main / "AndroidManifest.xml"
    content = manifest.read_text(encoding="utf-8")
    service = """        <service
            android:name=".BacyAccessibilityService"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
            android:exported="true">
            <intent-filter><action android:name="android.accessibilityservice.AccessibilityService" /></intent-filter>
            <meta-data android:name="android.accessibilityservice"
                android:resource="@xml/bacy10_accessibility" />
        </service>
"""
    if content.count("    </application>") != 1:
        raise RuntimeError("Android manifest missing closing application")
    manifest.write_text(content.replace("    </application>", service + "    </application>"), encoding="utf-8")

    main_activity = native / "MainActivity.kt"
    change_one(main_activity, '                                "website" -> {',
               NATIVE_BRANCH + '\n                                "website" -> {')

    tools = agent / "phone_tools.py"
    change_one(tools, '            self.export_pdf_to_phone,\n',
               '            self.export_pdf_to_phone,\n'
               '            self.navigate_on_android,\n'
               '            self.inspect_current_android_screen,\n'
               '            self.tap_visible_android_label,\n'
               '            self.android_system_navigation,\n'
               '            self.enable_android_screen_controls,\n'
               '            self.draft_whatsapp_on_phone,\n'
               '            self.create_calendar_event_draft,\n'
               '            self.open_phone_photo_picker,\n')
    tools.write_text(tools.read_text(encoding="utf-8") + "\n" + EXTRA_TOOLS, encoding="utf-8")
    app = agent / "agent.py"
    current = app.read_text(encoding="utf-8")
    current = current.replace('                *self._end_call_tool.tools,\n', '')
    current = current.replace('                        # Tools\n',
        """                        # Native phone shortcuts
                        - For directions or the nearest airport, use navigate_on_android with 'airport near me' or the requested destination. The phone's map app determines the route. Never start a cloud browser for native directions.
                        - If browser work is slow or a tool fails, explain the problem and offer a workaround; never terminate the conversation because of a failed tool.
                        - For WhatsApp and email use compose drafts and let the owner review and send.
                        - For calendar use create_calendar_event_draft, and for photos open_phone_photo_picker; do not claim direct Google account API integration.
                        - Screen reading, tapping and global navigation require the owner to enable Android Accessibility. Never automate payments, passwords, banking or destructive confirmation screens.
                        - Stay available in the session for follow-up questions. End voice calls only through the owner's explicit Android hang-up control.

                        # Tools
""", 1)
    app.write_text(current, encoding="utf-8")

    controller = mobile / "lib/controllers/app_ctrl.dart"
    change_one(controller,
        "          connectionError = 'LiveKit room connected, but BACY-10 has not joined. Deploy the bacy-10 Python agent to LiveKit Cloud first.';\n          await session.end();\n          appScreenState = AppScreenState.welcome;",
        "          connectionError = 'Connected, but the voice agent is still joining. You can stay here and try again shortly.';\n          appScreenState = AppScreenState.agent;")
    change_one(controller,
        "  void sendMessage() async {\n    isSendButtonEnabled = false;",
        "  void sendMessage() async {\n    isSendButtonEnabled = false;")
    change_one(controller,
        "    await session.sendText(text);\n",
        "    try {\n      await session.sendText(text);\n    } catch (error) {\n"
        "      connectionError = 'Message could not be delivered. Check the connection and try again.';\n"
        "      notifyListeners();\n    }\n")
    # Reduce browser tool stalls and keep user-facing errors contained.
    browser = agent / "browser.py"
    current = browser.read_text(encoding="utf-8")
    current = current.replace("timeout_ms: int = 15_000", "timeout_ms: int = 10_000", 1)
    browser.write_text(current, encoding="utf-8")
    pubspec = mobile / "pubspec.yaml"
    current = pubspec.read_text(encoding="utf-8")
    current = current.replace("version: 1.3.0+17", "version: 1.4.0+18")
    pubspec.write_text(current, encoding="utf-8")
