# BACY-10 — Android + always-on LiveKit deployment

The real BACY-10 implementation is based on [the creator's public tutorial](https://github.com/ruxakK/jarvis-voice-butler).

## What's fixed
- The Android client now uses a secure HTTPS `EndpointTokenSource`, **not** `LIVEKIT_SANDBOX_ID`.
- A pairing code is stored in Android encrypted storage and sent as an Authorization bearer header when requesting a short-lived room token.
- LiveKit's private API key and secret remain on the Cloudflare token server. Gemini remains in the cloud-hosted Python agent.
- The app identifies errors instead of silently connecting to a showcase bot.
- Android package ID: `za.co.bacy10.personalassistant` (separate from the old demo package).

## Cloudflare token endpoint
Live bridge:
`https://bacy10-livekit-bridge.loopsecure-bacanyclinda.workers.dev/token`

Status:
`https://bacy10-livekit-bridge.loopsecure-bacanyclinda.workers.dev/health`

**Important:** The Worker is already deployed, but it only works after its secret bindings have been configured. A health response with `configured:false` means the private keys are missing.

In Cloudflare dashboard, open Workers & Pages → `bacy10-livekit-bridge` → Settings → Variables and Secrets. Add these **secret** bindings:
- `LIVEKIT_API_KEY`: your LiveKit API key
- `LIVEKIT_API_SECRET`: your LiveKit API secret
- `BACY10_PAIRING_KEY`: a long private pairing code you choose; enter the **same** code on your phone

`LIVEKIT_URL` is already configured as a normal variable.

Do not paste secrets in GitHub files, the app's source, screenshots or conversations.

## Deploy the real agent to LiveKit Cloud (24/7)
LiveKit Cloud hosts the **Python voice agent**, not Cloudflare Workers. Open this repo's Settings → Secrets and variables → Actions. Create these four repository secrets:
- `LIVEKIT_URL` (your wss:// project URL)
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `GOOGLE_API_KEY` (your valid Gemini key)

Then choose Actions → **BACY-10 LiveKit Cloud Agent** → Run workflow → `create`. This uses the official LiveKit CLI to upload the real agent Dockerfile and register `bacy-10`. Agent deployment depends on your project's quota, the Google model's availability and Docker build.

For later updates, choose `deploy` and enter the existing LiveKit agent ID.

## Install the corrected Android app
Actions → **BACY-10 LiveKit Complete Source** → latest successful run → Artifacts → `BACY10-LIVEKIT-ANDROID-DEBUG`.

Extract the APK artifact ZIP if needed, then install `app-debug.apk`. The new Android app has its own package ID; it will not silently reuse the old demo app's credentials.

Open the app, paste the Cloudflare Worker pairing code once, and tap START VOICE CALL. It connects to the LiveKit room and explicitly dispatches the `bacy-10` agent.

## Live acceptance test
1. Verify Cloudflare `/health` reports `configured:true`.
2. Verify the LiveKit Cloud agent is deployed and running.
3. Connect Android; say 'Hello, BACY-10'; listen for a genuine response.
4. Interrupt, toggle the camera, test a harmless browser request, and disconnect/reconnect.
5. Observe LiveKit Cloud logs and quotas during testing.

No keys are bundled into the APK or source ZIP; voice and browser controls cannot work until the real cloud agent has been deployed and credentials configured. Cloud services may have usage charges.
