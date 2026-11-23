# Bacy 10 — LiveKit, Android and cloud memory

This repository contains the web voice assistant and the source generator for the separate LiveKit/Gemini Android assistant.

## Existing cloud services

- **LiveKit token bridge:** `bacy10-livekit-bridge` at
  `https://bacy10-livekit-bridge.loopsecure-bacanyclinda.workers.dev/token`.
  Its Cloudflare secret bindings are configured; the LiveKit API key and secret remain server-side.
- **Cloud memory:** `bacy10-memory`, backed by the existing D1 database and authenticated through a Cloudflare service binding to the token bridge. Memory is not stored in the Git repository or embedded as a static personal profile in the APK.
- **LiveKit agent:** the Python agent named `bacy-10` must be deployed to LiveKit Cloud separately. A connected room alone does not prove the agent joined.

Never paste, commit, or package pairing codes, API keys, passwords, or LiveKit secrets.

## Build and verify the complete source

GitHub Actions → **BACY-10 LiveKit Complete Source**.

The workflow:
1. Downloads the pinned upstream source and applies the Bacy 10 upgrade scripts.
2. Runs source and cloud-memory security checks.
3. Runs Python/LiveKit agent tests, Flutter analysis and Android release compilation, and the Next.js frontend build.
4. Optionally uploads the source ZIP and release APK as short-retention artifacts.

The source ZIP artifact is named `BACY10-LIVEKIT-FULL-SOURCE`. The Android release APK artifact is named `BACY10-v40-ORIGINAL-ID-RELEASE`. Artifact upload can be delayed or skipped if GitHub Actions storage quota is exhausted; the build and test jobs are designed to run independently of artifact storage.

## Deploy the real LiveKit agent

Before deployment, configure these GitHub Actions repository secrets:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `GOOGLE_API_KEY`
- `BACY10_AGENT_KEY` — a private random value of at least 32 characters, shared with the Lovable app's server-side secret.

Then run **BACY-10 LiveKit Cloud Agent**:
- First deployment: choose `create`.
- Later updates: choose `deploy` and provide the existing LiveKit agent ID.

The workflow creates a temporary secrets file with restrictive permissions and removes it after deployment. Do not add credentials to the APK, source ZIP or repository.

## Install the Android release

Download `BACY10-v40-ORIGINAL-ID-RELEASE` from a successful **BACY-10 LiveKit Complete Source** workflow run. Install the APK on Android and enter the private pairing code once. The app stores it using Android encrypted storage and requests short-lived LiveKit room credentials from the HTTPS token bridge.

The release package ID is `za.co.bacy10.personalassistant`. This is a release build for testing; production distribution still needs a properly signed release and real-device acceptance testing.

## Real-device acceptance checks

1. Confirm the token bridge health endpoint reports that its server configuration is ready.
2. Deploy the Python agent to LiveKit Cloud and confirm the agent joins the room.
3. Test microphone input, natural voice output and interruption on the actual Android phone.
4. Test phone actions only after Android permissions are granted.
5. Test memory save, restore after reinstall, offline queueing and owner-requested deletion.
6. Confirm the assistant reports genuine failures rather than pretending an unavailable action succeeded.

A successful source build is not proof of live microphone, voice, LiveKit deployment or Android device behaviour. Those require a real device and live service checks.
