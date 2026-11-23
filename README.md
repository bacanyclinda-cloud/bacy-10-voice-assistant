# Bacy 10

Bacy 10 is BW Silinda's private, voice-first personal assistant.

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
