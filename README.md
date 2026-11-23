# Bacy 10

Bacy 10 is BW Silinda's private, voice-first personal assistant.

## Live application and current release

- **Web assistant:** https://bacy-orbit-voice-companion.lovable.app
- **Android and complete source:** [BACY-10 V4.0 build 238 private release](https://github.com/bacanyclinda-cloud/bacy-10-voice-assistant/releases/tag/bacy10-v4.0.0-build-45252101627)
- **Android APK:** [app-release.apk](https://github.com/bacanyclinda-cloud/bacy-10-voice-assistant/releases/download/bacy10-v4.0.0-build-45252101627/app-release.apk)
- **LiveKit agent:** `bacy-10`, deployed to the existing LiveKit Cloud production project.

The Android/LiveKit package uses the authenticated Cloudflare/D1 private-memory service after the phone is paired. The web assistant's conversation history remains browser-local; it is not currently synchronised with that cloud memory service. Real Android microphone, speaker, room-join and memory acceptance tests still need to be completed on a physical device.

## Current application

- React, TypeScript, TanStack Start and Vite.
- Lovable AI Gateway for server-side conversation; the configured model is selected in `src/lib/bacy.server.ts`.
- Real generated speech through the configured OpenAI-compatible speech endpoint.
- Browser speech recognition for microphone input (browser support and microphone permission required).
- A separate backup voice studio at `/backup`.
- Optional Gmail inbox-subject integration for the LiveKit agent, protected by a server-side agent key.
- Progressive Web App assets and responsive voice interface.

## Privacy and configuration

- Keep `LOVABLE_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_MAIL_API_KEY`, and `BACY10_AGENT_KEY` in the hosting provider's server-side secrets only.
- Never commit `.env` files, tokens, or private user data.
- Browser conversation continuity is stored locally in that browser. It is not cloud-synchronised memory and clearing browser storage removes it.
- Gmail integration currently reads limited inbox metadata; it does not send, delete, or modify email.
- LiveKit agent packaging is maintained separately by `tools/bacy10_build_livekit_package.py`.

## Development

Requires Bun (the lockfile is `bun.lock`).

```sh
bun install --frozen-lockfile
bun run dev
bun run test
bun run build
```

See `AGENTS.md` before changing the Lovable-managed database, secrets, or generated files.
