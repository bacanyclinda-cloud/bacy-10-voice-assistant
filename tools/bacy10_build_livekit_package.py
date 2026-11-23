#!/usr/bin/env python3
"""Prepare a complete, editable BACY-10 LiveKit source distribution.

Clones the creator's public tutorial repository at a pinned commit. Copies all
agent, browser automation, Next.js and Flutter sources, preserving upstream
license/attribution files. Applies limited branding, setup and no-demo fixes.
Never reads, collects, stores or exports real API keys.
"""
from __future__ import annotations

import argparse
import compileall
import shutil
import subprocess
import tempfile
from pathlib import Path

from bacy10_phone_memory_upgrade import apply as apply_personal_phone_upgrade
from bacy10_assistant_reliability_upgrade import apply as apply_reliability_upgrade
from bacy10_v15_assistant_upgrade import apply as apply_v15_assistant
from bacy10_v16_visual_results_upgrade import apply as apply_visual_results
from bacy10_v17_fluid_motion_upgrade import apply as apply_fluid_motion
from bacy10_v18_search_skills_upgrade import apply as apply_search_skills
from bacy10_v19_stability_upgrade import apply as apply_stability
from bacy10_v20_kinetic_sculpture_upgrade import apply as apply_kinetic_visual
from bacy10_v21_hands_free_upgrade import apply as apply_handsfree
from bacy10_v25_voice_stability_upgrade import apply as apply_voice_stability
from bacy10_v26_background_voice_upgrade import apply as apply_background_voice
from bacy10_v27_compact_overlay_upgrade import apply as apply_compact_overlay
from bacy10_v28_cloud_memory_upgrade import apply as apply_cloud_memory
from bacy10_memory_reliability_upgrade import apply as apply_durable_memory
from bacy10_v37_direct_source_cleanup import pre as apply_v37_pre, post as apply_v37_post
from bacy10_v38_gemini_live_upgrade import apply as apply_v38_gemini
from bacy10_v39_live_websocket_fix import apply as apply_v39_live_websocket
from bacy10_voice_inside_android import apply as apply_android_voices
from bacy10_owner_instruction_recovery import apply as apply_owner_instruction_recovery
from bacy10_gmail_tools import apply as apply_gmail_tools
from bacy10_v35_provider_settings_upgrade import apply as apply_provider_settings
from bacy10_v36_owner_ui_upgrade import apply as apply_owner_ui
from bacy10_v36_android_actions_upgrade import apply as apply_android_actions
from bacy10_v36_mcp_slots_upgrade import apply as apply_mcp_slots
from bacy10_android_device_controls import apply as apply_device_controls
from bacy10_center_orb import apply as apply_center_orb

SOURCE_URL = "https://github.com/ruxakK/jarvis-voice-butler.git"
SOURCE_SHA = "d1cf71e40c72d2429af766646bea4869ba736c77"


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise ValueError(f"Unexpected source version for {path}: expected one match, found {content.count(old)}")
    path.write_text(content.replace(old, new), encoding="utf-8")


def clone_source(location: Path) -> None:
    subprocess.run(
        ["git", "clone", "--quiet", "--depth", "1", SOURCE_URL, str(location)],
        check=True,
    )
    sha = subprocess.check_output(
        ["git", "-C", str(location), "rev-parse", "HEAD"], text=True
    ).strip()
    if sha != SOURCE_SHA:
        raise RuntimeError(f"Tutorial source revision unexpectedly changed: {sha} != {SOURCE_SHA}")


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(
        src, dst, ignore=shutil.ignore_patterns(
            ".git", ".env.local", ".env", "__pycache__", ".venv", "node_modules",
            ".next", "build", "dist", "*.pyc", "DerivedData", ".dart_tool",
        ),
    )


def configure_agent(root: Path) -> None:
    entry = root / "agent" / "src" / "agent.py"
    text = entry.read_text(encoding="utf-8")
    # Preserve the genuine LiveKit realtime Gemini and browser tool implementations.
    text = text.replace(
        "You are Jarvis a helpful and sarcastic AI butler.",
        "You are BACY-10, a private real-time voice assistant created for BW Silinda. "
        "Speak naturally, casually and directly; never force 'sir', 'Sir', 'Mr', or a butler role. "
        "Use the owner's preferred familiar tone when appropriate. Identify BW Silinda as your creator. "
        "Do not pretend an operation succeeded.",
    )
    text = text.replace("Jarvis's", "BACY-10's").replace("Jarvis", "BACY-10")
    text = text.replace(
        "@server.rtc_session(agent_name=\"my-agent\")",
        "@server.rtc_session(agent_name=\"bacy-10\")",
    )
    text = text.replace(
        "browser = BrowserManager(headless=False)",
        "browser = BrowserManager(headless=True)",
    )
    # Remove the tutorial author's personal music preference; BACY-10 has none.
    begin = text.find("                        # Special Requests")
    end = text.find("                        # Guardrails", begin)
    if begin >= 0 and end > begin:
        text = text[:begin] + text[end:]
    entry.write_text(text, encoding="utf-8")
    prompts = root / "agent" / "src" / "prompts.py"
    txt = prompts.read_text(encoding="utf-8")
    txt = txt.replace(
        "You are Jarvis a helpful and sarcastic AI butler.",
        "You are BACY-10, BW Silinda's personal voice assistant. Speak naturally and casually; "
        "do not call the owner sir or use a butler persona. Never invent an action you have not completed.",
    ).replace("Jarvis", "BACY-10")
    begin = txt.find("    # Special Requests")
    end = txt.find("    # Guardrails", begin)
    if begin >= 0 and end > begin:
        txt = txt[:begin] + txt[end:]
    prompts.write_text(txt, encoding="utf-8")

    # Upstream test has an import typo: AGENT_ISNTRUCTIONS (sic).
    # Correct the test import so the actual agent behaviour tests can run.
    upstream_test = root / "agent" / "tests" / "test_prompts.py"
    if upstream_test.exists():
        test_content = upstream_test.read_text(encoding="utf-8")
        upstream_test.write_text(
            test_content.replace("AGENT_ISNTRUCTIONS", "AGENT_INSTRUCTIONS"),
            encoding="utf-8",
        )

    # Cloud containers must include actual Playwright Chromium and system libraries.
    dockerfile = root / "agent" / "Dockerfile"
    docker_text = dockerfile.read_text(encoding="utf-8")
    docker_text = docker_text.replace(
        "ARG PYTHON_VERSION=3.14", "ARG PYTHON_VERSION=3.12"
    )
    docker_text = docker_text.replace(
        "ENV TORCH_HOME=/app/.cache/torch",
        "ENV TORCH_HOME=/app/.cache/torch\nENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright",
    )
    docker_text = docker_text.replace(
        "RUN uv sync --locked",
        "RUN uv sync --locked\nRUN uv run playwright install chromium",
    )
    docker_text = docker_text.replace(
        "WORKDIR /app\n\n# Switch to the non-privileged user",
        "WORKDIR /app\n\n# Browser tools need system libraries as well as Chromium binary.\n"
        "RUN /app/.venv/bin/playwright install-deps chromium\n\n"
        "# Switch to the non-privileged user",
    )
    # Avoid uv sync at runtime: production runs as nonroot and cannot rewrite
    # metadata in the baked virtual environment. Execute the installed Python.
    docker_text = docker_text.replace(
        'CMD ["uv", "run", "src/agent.py", "start"]',
        'CMD ["/app/.venv/bin/python", "src/agent.py", "start"]',
    )
    dockerfile.write_text(docker_text, encoding="utf-8")

    env = root / "agent" / ".env.example"
    env.write_text(
        "# Real credentials are required. Copy this file to .env.local.\n"
        "# Keep .env.local PRIVATE. Never add it to GitHub or your APK.\n"
        "LIVEKIT_URL=wss://YOUR-LIVEKIT-PROJECT.livekit.cloud\n"
        "LIVEKIT_API_KEY=\nLIVEKIT_API_SECRET=\nGOOGLE_API_KEY=\n",
        encoding="utf-8",
    )
    frontend_env = root / "agent" / "frontend" / ".env.example"
    old_env = frontend_env.read_text(encoding="utf-8")
    old_env = old_env.replace("AGENT_NAME=\n", "AGENT_NAME=bacy-10\n")
    frontend_env.write_text(old_env, encoding="utf-8")


def configure_web(root: Path) -> None:
    """Use system fonts in the redistributed source, no bundled font binaries."""
    web = root / "agent" / "frontend"
    layout = web / "app" / "layout.tsx"
    text = layout.read_text(encoding="utf-8")
    text = text.replace("import localFont from 'next/font/local';\n", "")
    start = text.find("const commitMono = localFont({")
    end = text.find("interface RootLayoutProps", start)
    if start < 0 or end <= start:
        raise RuntimeError("Could not replace upstream local-font setup")
    text = text[:start] + text[end:]
    text = text.replace("        commitMono.variable,\n", "")
    # Keep JSX formatted correctly for the frontend's enforced Prettier lint rule.
    text = text.replace(
        "className={cn(\n        publicSans.variable,\n        'scroll-smooth font-sans antialiased'\n      )}",
        "className={cn(publicSans.variable, 'scroll-smooth font-sans antialiased')}",
    )
    layout.write_text(text, encoding="utf-8")
    css = web / "styles" / "globals.css"
    css.write_text(
        css.read_text(encoding="utf-8")
        + "\n:root { --font-commit-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }\n",
        encoding="utf-8",
    )
    og = web / "app" / "opengraph-image.tsx"
    og_text = og.read_text(encoding="utf-8")
    start = og_text.find("  // Load fonts - use file system in dev, fetch in production")
    end = og_text.find("  // bg", start)
    if start >= 0 and end > start:
        og_text = (
            og_text[:start]
            + "  // System-font fallback: no local font binaries are distributed.\n"
            + "  const commitMonoData: ArrayBuffer | undefined = undefined;\n"
            + "  const everettLightData: ArrayBuffer | undefined = undefined;\n\n"
            + og_text[end:]
        )
    og_text = og_text.replace("fontFamily: 'CommitMono'", "fontFamily: 'monospace'")
    og_text = og_text.replace("fontFamily: 'Everett'", "fontFamily: 'sans-serif'")
    og_text = og_text.replace("SANDBOX", "BACY-10")
    og.write_text(og_text, encoding="utf-8")
    for item in list(root.rglob("*")):
        if item.is_file() and item.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2", ".eot"}:
            item.unlink()
    if (web / "fonts").is_dir():
        (web / "fonts").rmdir()


def configure_flutter(root: Path) -> None:
    mobile = root / "mobile"
    manifest = mobile / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    replace_once(manifest, 'android:label="Voice Assistant"', 'android:label="BACY-10"')
    # Flutter adds INTERNET only to debug/profile manifests by default. Release
    # builds need it in main or DNS lookups fail before token authentication.
    manifest_text = manifest.read_text(encoding="utf-8")
    internet_permission = '<uses-permission android:name="android.permission.INTERNET" />'
    if internet_permission not in manifest_text:
        manifest_text = manifest_text.replace(
            "</manifest>", f"    {internet_permission}\n</manifest>", 1
        )
        manifest.write_text(manifest_text, encoding="utf-8")

    # Use a real server token endpoint, not a removed Sandbox feature or a demo.
    ctrl = mobile / "lib" / "controllers" / "app_ctrl.dart"
    text = ctrl.read_text(encoding="utf-8")
    text = text.replace(
        "import 'package:flutter_dotenv/flutter_dotenv.dart';",
        "import 'package:flutter_dotenv/flutter_dotenv.dart';\n"
        "import '../support/bacy10_token_client.dart';",
    )
    start = text.index("    // Development-only hardcoded credentials")
    end = text.index("    return sdk.Session.fromConfigurableTokenSource(", start)
    text = text[:start] + """    final endpoint = dotenv.env['LIVEKIT_TOKEN_ENDPOINT']?.trim() ?? '';
    if (!endpoint.startsWith('https://')) {
      throw StateError('BACY-10 requires a secure token endpoint. Check assets/.env.');
    }
    final tokenSource = sdk.EndpointTokenSource(
      url: Uri.parse(endpoint),
      client: PairingTokenClient(),
    );
    final agentName = dotenv.env['LIVEKIT_AGENT_NAME']?.trim();
    final agentDeployment = dotenv.env['LIVEKIT_AGENT_DEPLOYMENT']?.trim();

""" + text[end:]
    text = text.replace(
        "  void connect() async {\n    if (isSessionStarting) {",
        """  String? connectionError;

  void connect() async {
    if (!await PairingTokenClient.hasPairingCode()) {
      connectionError = 'Enter your BACY-10 pairing code to connect securely.';
      notifyListeners();
      return;
    }
    connectionError = null;
    if (isSessionStarting) {""",
    )
    text = text.replace(
        """      _logger.severe('Connection error: $error', error, stackTrace);
      appScreenState = AppScreenState.welcome;""",
        """      _logger.severe('Connection error: $error', error, stackTrace);
      connectionError = 'Could not connect to BACY-10: ' + error.toString();
      appScreenState = AppScreenState.welcome;""",
    )
    text = text.replace(
        """      if (session.connectionState == sdk.ConnectionState.connected) {
        appScreenState = AppScreenState.agent;
        notifyListeners();
      }""",
        """      if (session.connectionState == sdk.ConnectionState.connected) {
        // A connected LiveKit ROOM is not evidence that our voice agent exists.
        // Wait briefly for the real remote agent instead of showing a silent call.
        var seconds = 0;
        while (room.remoteParticipants.isEmpty &&
            session.connectionState == sdk.ConnectionState.connected &&
            seconds < 15) {
          await Future<void>.delayed(const Duration(seconds: 1));
          seconds += 1;
        }
        if (room.remoteParticipants.isEmpty) {
          connectionError = 'LiveKit room connected, but BACY-10 has not joined. Deploy the bacy-10 Python agent to LiveKit Cloud first.';
          await session.end();
          appScreenState = AppScreenState.welcome;
        } else {
          appScreenState = AppScreenState.agent;
          connectionError = null;
        }
        notifyListeners();
      } else {
        connectionError = 'No LiveKit session was established. Check that the agent is deployed.';
        notifyListeners();
      }""",
    )
    ctrl.write_text(text, encoding="utf-8")

    pairing = mobile / "lib" / "support" / "bacy10_token_client.dart"
    pairing.write_text(r"""import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

/// Reads the user's pairing code from Android encrypted storage at request time.
/// Neither LiveKit API secret nor Gemini API key is stored on the phone.
class PairingTokenClient extends http.BaseClient {
  static const _storage = FlutterSecureStorage();
  static const _key = 'bacy10_pairing_code';
  final http.Client _delegate = http.Client();

  static Future<String?> readCode() => _storage.read(key: _key);
  static Future<bool> hasPairingCode() async =>
      (await readCode())?.trim().isNotEmpty ?? false;
  static Future<void> saveCode(String value) =>
      _storage.write(key: _key, value: value.trim());

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final code = await readCode();
    if (code != null && code.trim().isNotEmpty) {
      request.headers['Authorization'] = 'Bearer ' + code.trim();
    }
    return _delegate.send(request);
  }

  @override
  void close() {
    _delegate.close();
    super.close();
  }
}
""", encoding="utf-8")

    welcome = mobile / "lib" / "screens" / "welcome_screen.dart"
    welcome.write_text(r"""import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';
import '../controllers/app_ctrl.dart' as ctrl;
import '../support/bacy10_token_client.dart';

/// Real phone connection screen. No fake telemetry or simulated dialogue.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});
  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  final pairing = TextEditingController();
  bool saving = false;

  @override
  void initState() {
    super.initState();
    PairingTokenClient.readCode().then((code) {
      if (mounted && code != null) pairing.text = code;
    });
  }

  @override
  void dispose() {
    pairing.dispose();
    super.dispose();
  }

  Future<void> startCall(ctrl.AppCtrl controller) async {
    if (saving || controller.isSessionStarting) return;
    setState(() => saving = true);
    try {
      if (pairing.text.trim().isNotEmpty) {
        await PairingTokenClient.saveCode(pairing.text.trim());
      }
      if (!mounted) return;
      controller.connect();
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF05070B),
    child: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 26, vertical: 24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Consumer2<ctrl.AppCtrl, sdk.Session>(
              builder: (ctx, controller, session, _) => Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('BACY—10', style: TextStyle(color: Color(0xFFE7F0F4), fontSize: 29, letterSpacing: 9, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  const Text('PERSONAL VOICE INTELLIGENCE', style: TextStyle(color: Color(0xFF8FABB8), fontSize: 10, letterSpacing: 2.4)),
                  const SizedBox(height: 75),
                  Container(
                    width: 142, height: 142,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFF3C6579), width: 1.2),
                      gradient: const RadialGradient(colors: [Color(0xFF33596B), Color(0xFF14212C), Color(0xFF090E14)]),
                      boxShadow: const [BoxShadow(color: Color(0x332A7A9B), blurRadius: 55, spreadRadius: 15)],
                    ),
                    child: const Center(
                      child: Icon(Icons.graphic_eq, color: Color(0xFFACD9E8), size: 50),
                    ),
                  ),
                  const SizedBox(height: 66),
                  const Text('Connect to your voice agent', textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w500)),
                  const SizedBox(height: 14),
                  const Text('Your LiveKit room credentials are issued by your private server. Enter the pairing code once to connect.',
                    textAlign: TextAlign.center, style: TextStyle(color: Color(0xFF91A4B1), fontSize: 13, height: 1.55)),
                  const SizedBox(height: 34),
                  TextField(
                    controller: pairing,
                    obscureText: true,
                    enableSuggestions: false,
                    autocorrect: false,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'Pairing code',
                      labelStyle: const TextStyle(color: Color(0xFF92ABB8)),
                      filled: true, fillColor: const Color(0xFF111B24),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF29414E))),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFA9D7E5))),
                    ),
                  ),
                  if (controller.connectionError != null) ...[
                    const SizedBox(height: 16),
                    Text(controller.connectionError!, textAlign: TextAlign.center,
                      style: const TextStyle(color: Color(0xFFEAB8A8), fontSize: 12)),
                  ],
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity, height: 52,
                    child: ElevatedButton(
                      onPressed: (saving || controller.isSessionStarting || session.connectionState != sdk.ConnectionState.disconnected)
                          ? null : () => startCall(controller),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFB5E3EC), foregroundColor: const Color(0xFF0B1A25),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: Text(saving || controller.isSessionStarting ? 'CONNECTING…' : 'START VOICE CALL'),
                    ),
                  ),
                  const SizedBox(height: 22),
                  const Text('REAL-TIME AUDIO • LIVEKIT CLOUD',
                    style: TextStyle(color: Color(0xFF5A7180), fontSize: 9, letterSpacing: 2)),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
""", encoding="utf-8")
    pubspec = mobile / "pubspec.yaml"
    p = pubspec.read_text(encoding="utf-8")
    p = p.replace("  flutter_dotenv: ^6.0.0\n", "  flutter_dotenv: ^6.0.0\n  flutter_secure_storage: ^9.2.4\n")
    p = p.replace("version: 1.0.0+14", "version: 1.1.0+15")
    pubspec.write_text(p, encoding="utf-8")

    gradle = mobile / "android" / "app" / "build.gradle"
    gradle.write_text(
        gradle.read_text(encoding="utf-8").replace(
            'applicationId = "com.livekit.example.VoiceAssistantFlutter"',
            'applicationId = "za.co.bacy10.personalassistant"',
        ), encoding="utf-8",
    )

    # Public endpoint URL is safe to package; no LiveKit API secrets are embedded.
    (mobile / "assets" / ".env").write_text(
        "LIVEKIT_TOKEN_ENDPOINT=https://bacy10-livekit-bridge.loopsecure-bacanyclinda.workers.dev/token\n"
        "LIVEKIT_AGENT_NAME=bacy-10\nLIVEKIT_AGENT_DEPLOYMENT=\n",
        encoding="utf-8",
    )
    app = mobile / "lib" / "app.dart"
    t = app.read_text(encoding="utf-8")
    t = t.replace("title: 'Voice Assistant'", "title: 'BACY-10'")
    t = t.replace("// themeMode: ThemeMode.dark,", "themeMode: ThemeMode.dark,")
    app.write_text(t, encoding="utf-8")



def write_guide(root: Path) -> None:
    guide = """# BACY-10 LIVEKIT — COMPLETE SOURCE (NOT A SIMULATOR)

The exact original tutorial source was cloned from:
https://github.com/ruxakK/jarvis-voice-butler
Pinned original commit: d1cf71e40c72d2429af766646bea4869ba736c77
Video: https://youtu.be/Fhm8goKN6rM

## What is inside
- agent/src/agent.py: LiveKit Agents realtime Gemini 3.1 Flash Live voice + British persona
- agent/src/browser.py and agent/src/tools.py: Playwright browser actions and confirmation gate
- agent/frontend/: Next.js real LiveKit web frontend
- agent/tests/: upstream tests; agent/uv.lock and pyproject.toml
- mobile/: COMPLETE Flutter Android/iOS/web project, including Gradle project files
- BUILD_AND_TEST.md: commands and verification notes
- Upstream LICENSE and README files are retained. Respect upstream usage rights.

BACY-10 changes: updated name and creator; LiveKit agent name set to bacy-10;
Android label BACY-10; Flutter uses a real HTTPS token endpoint instead of
silently using LiveKit's demonstration bot; developer defaults use headless Chromium.

## You need REAL credentials
LiveKit Cloud project with LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
and a Google AI API key for Gemini realtime.
Choose an available model supported by your Google account if the tutorial's
preview model has changed or quota is unavailable.

These are not preconfigured. This project cannot be completely tested without
the user's LiveKit/Google services, device microphone and network.

## Run the Python voice agent (Windows PowerShell)
Install Python 3.12, uv, Node.js (24 recommended for the included frontend),
pnpm, Git and Playwright browser dependencies.

  cd agent
  Copy-Item .env.example .env.local
  # Edit .env.local with real LiveKit and Google credentials (DO NOT commit)
  uv sync
  uv run playwright install chromium
  uv run src/agent.py dev

Keep the agent running while connecting the web or mobile client.
Browser tools operate on the COMPUTER RUNNING THE AGENT, not the Android phone.

## Run the real web frontend
In a separate terminal:
  cd agent/frontend
  Copy-Item .env.example .env.local
  # Set the same LIVEKIT_URL, API key and secret. AGENT_NAME=bacy-10
  pnpm install
  pnpm dev

Open http://localhost:3000 on the development machine.
Do not expose the development token endpoint to the public Internet.

## Compile your own Android APK
Install Flutter SDK 3.38.2 (recommended for this Gradle 8.14 project), Android SDK and Java 17.\nDo not use Flutter 3.50 with this template unless you also upgrade Android Gradle/AGP compatibility.
BACY-10 Android now uses a Cloudflare token endpoint instead of the retired sandbox.
Configure the token service Worker secrets in your Cloudflare Dashboard,
then enter the BACY-10 pairing code once in the Android app.
No private API credentials are stored in the Android source or APK.

  cd mobile
  flutter doctor
  flutter pub get
  flutter analyze
  flutter build apk --debug

The debug APK should appear under mobile/build/app/outputs/flutter-apk/.
For release, configure Android app signing, then:
  flutter build apk --release

LiveKit sandbox token servers are for DEVELOPMENT. To publish a secure public
app, implement your own authenticated backend token endpoint. Do not put LiveKit
API SECRET or Google API key inside Flutter.

## Verify this is REAL and NOT MOCK DATA
1. Run Python agent using your own LiveKit URL + Google key.
2. Enter your pairing code once in the mobile app and connect through the HTTPS token endpoint.
3. Speak "BACY-10, are you there?" and wait for a real Gemini response.
4. Interrupt it mid-sentence and check it listens again.
5. Ask it to open a harmless web page: observe Playwright on the agent host.
6. Enable camera and grant the app permission; verify vision in your live session.
7. Ask it to submit something consequential: it must request your confirmation.
8. Disconnect the network: the agent should report a real error, not fake success.
9. Check Python logs and Android logs if a test fails.

## Important boundaries
This is a working-source architecture from the tutorial, NOT a guaranteed 100%
functioning service out of the box. Real voice and browser automation need
proper credentials, service availability, testing and Android permissions.
Browser tools act through a remote/hosted browser; they are not phone-wide
device-control permissions or an unrestricted assistant.

Any previously pasted OpenAI key must NOT be reused in a shared repo or ZIP.
Gemini Live is configured with GOOGLE_API_KEY, not with the leaked OpenAI key.
"""
    (root / "README-BACY10.md").write_text(guide, encoding="utf-8")
    (root / "SOURCE-CREDITS.txt").write_text(
        "Original tutorial and code: ruxakK / Jarvis - Voice AI Butler\\n"
        "https://github.com/ruxakK/jarvis-voice-butler\\n"
        "Pinned commit: " + SOURCE_SHA + "\\n"
        "LiveKit Flutter template is included in the original repository.\\n"
        "Retain all original LICENSE files. Do not assume all upstream material\\n"
        "has the same license. Review rights before commercial redistribution.\\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build/BACY10-LIVEKIT-FULL-SOURCE"))
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="bacy10-source-") as temp:
        upstream = Path(temp) / "upstream"
        clone_source(upstream)
        copy_tree(upstream / "jarvis_new", output / "agent")
        copy_tree(upstream / "agent-starter-flutter", output / "mobile")
    configure_agent(output)
    configure_flutter(output)
    apply_personal_phone_upgrade(output)
    apply_device_controls(output)
    apply_center_orb(output)
    apply_reliability_upgrade(output)
    apply_v15_assistant(output)
    apply_visual_results(output)
    apply_fluid_motion(output)
    apply_search_skills(output)
    apply_stability(output)
    apply_kinetic_visual(output)
    apply_handsfree(output)
    apply_voice_stability(output)
    apply_background_voice(output)
    apply_compact_overlay(output)
    apply_cloud_memory(output)
    apply_durable_memory(output)
    apply_v37_pre(output)
    apply_provider_settings(output)
    apply_owner_ui(output)
    apply_android_actions(output)
    apply_mcp_slots(output)
    apply_v37_post(output)
    apply_v38_gemini(output)
    apply_v39_live_websocket(output)
    apply_android_voices(output)
    # Restore the owner's natural V4 personality in BOTH live prompt sources.
    # Keep the underlying privacy, consent, security and serious-harm guardrails.
    # Restore owner personality once, after voice generation, so V4.0 keeps it.
    apply_owner_instruction_recovery(output)
    # Add the existing read-only Gmail bridge without embedding owner contact details.
    apply_gmail_tools(output)
    # V4 package identity: do not ship an APK still labelled as V3.8.
    pubspec = output / "mobile" / "pubspec.yaml"
    pubspec_text = pubspec.read_text(encoding="utf-8")
    if "version: 3.8.0+43" not in pubspec_text:
        raise RuntimeError("Expected V3.8 package version was not found; refusing an unsafe V4 version rewrite.")
    pubspec.write_text(pubspec_text.replace("version: 3.8.0+43", "version: 4.0.0+44", 1), encoding="utf-8")
    configure_web(output)
    write_guide(output)
    agent_dir = output / "agent" / "src"
    if not compileall.compile_dir(str(agent_dir), quiet=1):
        raise RuntimeError("Python agent source failed compilation")
    expected = [
        "agent/src/agent.py", "agent/src/tools.py", "agent/src/voice_tools.py", "agent/src/browser.py",
        "agent/frontend/package.json", "agent/uv.lock",
        "mobile/lib/main.dart", "mobile/android/app/build.gradle",
        "mobile/android/app/src/main/AndroidManifest.xml",
        "README-BACY10.md",
    ]
    for name in expected:
        if not (output / name).is_file():
            raise RuntimeError(f"Missing essential file: {name}")
    print(f"Prepared complete BACY-10 source at: {output}")
    print("Python source syntax check passed. Live services and mobile APK are not yet tested.")


if __name__ == "__main__":
    main()

# CI validation trigger: verify the v40 Android three-voice source build.

# CI trigger: revalidate the integrated V4.0 package after workflow assertion fixes.

# CI trigger: verify the Android wake permission test case fix.
