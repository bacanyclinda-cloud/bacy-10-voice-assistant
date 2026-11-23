# Bacy 10 — current architecture and verification plan

## What is in the repository now

- **Web assistant:** TanStack Start, TypeScript and React, with a private voice-first interface.
- **Conversation model:** the configured Lovable AI Gateway model is called server-side. The primary and backup web pages retain a bounded local conversation history; the model receives only the most recent 12 messages.
- **Speech:** browser microphone recognition plus server-generated speech. The primary web voice is natural British English; alternative voices are optional server-side providers.
- **Gmail:** the LiveKit agent can request a limited number of inbox message subjects, senders and dates through a read-only server route. The route checks the private agent bearer key. No email body, send, delete or modify operation is exposed.
- **Android/LiveKit source:** `tools/bacy10_build_livekit_package.py` downloads the pinned upstream source and applies the Bacy 10 upgrades for Gemini Live, hands-free wake (explicit opt-in, persistent notification and a clear off switch), Android device controls, provider settings, MCP connections, voice choices and cloud memory.
- **Cloud services:** the Cloudflare token bridge mints short-lived LiveKit room tokens. The separate `bacy10-memory` Worker uses D1 and the token bridge's service binding for owner-paired cloud memory.
- **Memory privacy:** no private owner contact, relationship or location profile is baked into the APK. Android facts and conversation turns are stored through the paired cloud-memory service; the web app's history is local to its browser and is not cloud-synchronised.
- **Security:** server keys stay in hosting secrets; Android provider keys are kept in encrypted storage; error telemetry and server logs redact common credentials and personal identifiers.

## Build and test

The GitHub Actions workflows run the web build, lint and Vitest suite. The full LiveKit source workflow independently regenerates the source for Python/LiveKit tests, Flutter analysis and Android release compilation, and the Next.js frontend build. Source/APK artifacts are optional short-retention downloads because GitHub artifact storage can be exhausted.

## Remaining real-world verification

1. Confirm the integrated source workflow passes every job.
2. Deploy the Python agent to LiveKit Cloud using the manual deployment workflow only after its required GitHub secrets are configured.
3. Test Android microphone permission, persistent wake notification, actual Gemini Live connection, voice switching and interruption on the real phone.
4. Test screen reading and taps on ordinary apps, and verify banking/payment pages are blocked.
5. Test cloud-memory save, restore after reinstall, offline queueing, individual forget and full reset on a paired phone.
6. Confirm the deployed web app and installed APK are running the intended commits.

A successful source build is not proof of a live agent, real microphone, TTS playback, or production deployment.
