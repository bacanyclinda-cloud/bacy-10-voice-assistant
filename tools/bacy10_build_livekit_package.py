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
        "You are BACY-10, a private real-time British voice assistant created for BW Silinda. "
        "Your owner is addressed as sir. Be confident, warm and capable, never robotic. "
        "Identify BW Silinda as your creator. Do not pretend an operation succeeded.",
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
        "You are BACY-10, BW Silinda's personal British voice assistant. Call your owner sir "
        "naturally and never invent an action you have not completed.",
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
    ctrl = mobile / "lib" / "controllers" / "app_ctrl.dart"
    # The tutorial falls back to the LiveKit showcase agent if not configured.
    # BACY-10 must never silently use a demo or pretend it is the user's own AI.
    old = """  void connect() async {
    if (isSessionStarting) {"""
    new = """  String? connectionError;

  void connect() async {
    final sandboxId = dotenv.env['LIVEKIT_SANDBOX_ID']?.replaceAll('"', '').trim();
    if (sandboxId == null || sandboxId.isEmpty || sandboxId == '<your-sandbox-id>') {
      connectionError = 'Connect BACY-10 to your own LiveKit project. Set LIVEKIT_SANDBOX_ID in assets/.env first.';
      notifyListeners();
      return;
    }
    connectionError = null;
    if (isSessionStarting) {"""
    replace_once(ctrl, old, new)
    # Prevent even accidental connections to the original public demo.
    old_demo = "tokenSource = sdk.EndpointTokenSource(url: Uri.parse(homepageAgentTokenEndpoint));"
    new_demo = "tokenSource = sdk.DevelopmentTokenSource(id: 'bacy-10-not-configured');"
    replace_once(ctrl, old_demo, new_demo)

    welcome = mobile / "lib" / "screens" / "welcome_screen.dart"
    replace_once(
        welcome,
        "                // Agent status indicator",
        """                Consumer<ctrl.AppCtrl>(
                  builder: (context, appCtrl, child) {
                    if (appCtrl.connectionError == null) return const SizedBox.shrink();
                    return Text(
                      appCtrl.connectionError!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.redAccent, fontSize: 13),
                    );
                  },
                ),
                // Agent status indicator""",
    )
    replace_once(
        welcome,
        "Start a call to chat with your voice agent. Need help getting set up? Check out the ",
        "Speak with BACY-10, your real LiveKit voice agent. Set up your own LiveKit connection first. See the ",
    )
    (mobile / "assets" / ".env").write_text(
        "# Development configuration only. Add your LiveKit sandbox ID here.\n"
        "# Never place LIVEKIT_API_SECRET, GOOGLE_API_KEY or OpenAI secrets in an APK.\n"
        "LIVEKIT_SANDBOX_ID=\nLIVEKIT_AGENT_NAME=bacy-10\nLIVEKIT_AGENT_DEPLOYMENT=\n",
        encoding="utf-8",
    )
    # Flutter's default files remain editable and the Android project is not a mock.
    main_dart = mobile / "lib" / "main.dart"
    txt = main_dart.read_text(encoding="utf-8")
    txt = txt.replace(
        "// The file is optional; without it the app connects to a default agent (see app_ctrl.dart)",
        "// BACY-10 requires your own LiveKit sandbox ID; no demo agent is used.",
    )
    main_dart.write_text(txt, encoding="utf-8")


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
Android label BACY-10; Flutter requires your own LiveKit sandbox instead of
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
In LiveKit Cloud enable a SANDBOX TOKEN SERVER for development.
Edit mobile/assets/.env and set LIVEKIT_SANDBOX_ID to your own sandbox ID.
The Flutter app will NOT connect to the tutorial's public demo by default.

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
2. Connect the mobile app using your project sandbox ID.
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
    configure_web(output)
    write_guide(output)
    agent_dir = output / "agent" / "src"
    if not compileall.compile_dir(str(agent_dir), quiet=1):
        raise RuntimeError("Python agent source failed compilation")
    expected = [
        "agent/src/agent.py", "agent/src/tools.py", "agent/src/browser.py",
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
