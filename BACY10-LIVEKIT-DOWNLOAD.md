# Bacy 10 — LiveKit, Android and cloud memory

This repository contains the web voice assistant and the source generator for the separate LiveKit/Gemini Android assistant.

## Existing cloud services

- **LiveKit token bridge:** `bacy10-livekit-bridge` at
  `https://bacy10-livekit-bridge.loopsecure-bacanyclinda.workers.dev/token`.
  Its Cloudflare secret bindings are configured; the LiveKit API key and secret remain server-side.
- **Cloud memory:** `bacy10-memory`, backed by the existing D1 database and authenticated through a Cloudflare service binding to the token bridge. Memory is not stored in the Git repository or embedded as a static personal profile in the APK.
- **LiveKit agent:** the Python agent `bacy-10` is now deployed to the existing LiveKit Cloud production project. The successful deployment is recorded in GitHub Actions run `45252101627`. A real Android room-join and voice session still needs device acceptance testing.

Never paste, commit, or package pairing codes, API keys, passwords, or LiveKit secrets.

## Build and verify the complete source

GitHub Actions → **BACY-10 LiveKit Complete Source**.

The workflow:
1. Downloads the pinned upstream source and applies the Bacy 10 upgrade scripts.
2. Runs source and cloud-memory security checks.
3. Runs Python/LiveKit agent tests, Flutter analysis and Android release compilation, and the Next.js frontend build.
4. Publishes the complete source ZIP and Android APK as private GitHub Release assets.

The primary downloads are published as **private GitHub Release assets** after all main-branch validation jobs pass. Open the repository's **Releases** page and choose the latest `BACY-10 V4.0 build` prerelease. Download `BACY10-LIVEKIT-FULL-SOURCE.zip` for the complete source or `app-release.apk` for Android. This release route does not depend on GitHub Actions artifact storage. Short-retention Actions artifacts may also appear when the separate Actions storage quota allows them, but use the Release assets as the dependable download.

## Deploy the real LiveKit agent

Before deployment, configure these GitHub Actions repository secrets:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `GOOGLE_API_KEY`
- `BACY10_AGENT_KEY` — a private random value of at least 32 characters, shared with the Lovable app's server-side secret.

For normal updates, pushing a validated change to `main` automatically deploys the tested agent to the existing LiveKit production agent after Python, Android and Next.js checks pass. The workflow rebuilds its source directly, so deployment does not depend on Actions artifact storage.

For a first deployment or a manually controlled operation, run **BACY-10 LiveKit Cloud Agent**:
- First deployment: choose `create`.
- Later updates: choose `deploy` and provide the existing LiveKit agent ID.

The workflow creates a temporary secrets file with restrictive permissions and removes it after deployment. Do not add credentials to the APK, source ZIP or repository.

## Install the Android release

Use the [BACY-10 V4.0 build 239 release](https://github.com/bacanyclinda-cloud/bacy-10-voice-assistant/releases/tag/bacy10-v4.0.0-build-45256107943). Download [app-release.apk](https://github.com/bacanyclinda-cloud/bacy-10-voice-assistant/releases/download/bacy10-v4.0.0-build-45256107943/app-release.apk) and install it on Android. Because this is a privately distributed testing APK, Android may ask you to allow installation from the browser or file manager. Open the app and enter your private pairing code once. The app stores it using Android encrypted storage and requests short-lived LiveKit room credentials from the HTTPS token bridge. Hands-free wake is **off by default**. The owner must enable it from the hands-free permissions panel; a persistent notification appears while listening, and it can be disabled from the panel or notification. Wake detection uses Android speech recognition, on-device when available; otherwise the device's speech provider may process audio. It is not a dedicated offline hardware hotword detector.

The release package ID is `za.co.bacy10.personalassistant`. The APK was successfully built and uploaded, but it is a privately signed testing build, not a Play Store production signing package. Real-device acceptance testing remains outstanding.

**Web app memory note:** the existing Lovable web interface currently stores conversation history in that browser's local storage. The deployed D1-backed cloud memory sync is integrated into the separate Android/LiveKit package; do not assume the web interface's chat history is cloud-synchronised.

## Real-device acceptance checks

1. Confirm the token bridge health endpoint reports that its server configuration is ready.
2. The Python agent is already deployed to LiveKit Cloud; connect from the Android app and confirm the agent joins the room.
3. Test microphone input, natural voice output and interruption on the actual Android phone.
4. Test phone actions only after Android permissions are granted.
5. Test memory save, restore after reinstall, offline queueing and owner-requested deletion.
6. Confirm the assistant reports genuine failures rather than pretending an unavailable action succeeded.

A successful source build is not proof of live microphone, voice, LiveKit deployment or Android device behaviour. Those require a real device and live service checks.
