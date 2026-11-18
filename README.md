# BACY-10 Voice Assistant

Build an AI voice assistant named BACY-10 with a British persona inspired by Jarvis from Iron Man.

User's request:
"Yeah, but um, what I ,I wanted it to have a voice, uh, to-to have that British, that-that to King, that kind of talking, everything. And uh, I want to change its name not to Jarvis, but I can call it B, A, C, Y, uh, Ten, zero five ten, I mean, m- ten"

Locked:
- Name: BACY-10
- Persona & Voice: Sophisticated, articulate, courteous British AI assistant (inspired by Jarvis: "At your service, sir", witty, composed, highly competent). Speaks responses aloud using SpeechSynthesis with prioritized British English voices (e.g. Google UK English Male/Female, Daniel, Oliver, or system en-GB) with pitch and rate controls. Listens via Web Speech Recognition with live microphone audio reactive visualization.
- Visual Theme & HUD: Futuristic sci-fi holographic interface. Deep dark palette (#050b14, #0b1528) with glowing neon cyan/blue (#00f5ff, #38bdf8) and subtle amber accents (#f59e0b). Glassmorphic HUD cards with neon borders, corner brackets, and subtle scanline/hex grid background.
- Central Core / Arc Reactor: Prominent animated arc reactor / audio waveform visualizer at the center that pulses dynamically when idle, listening, or speaking.
- Capabilities & Modules:
  1. Voice & Text Console: Real-time two-way voice conversation (hands-free wake/listening or push-to-talk button) and a terminal command prompt for typing. Monospace chat logs showing user requests and BACY-10's responses.
  2. Live Telemetry & System Diagnostics: Futuristic gauges showing simulated power core levels, network latency, memory matrix, and security status.
  3. Utility Protocols: Weather scanner with animated radar graphics, Route/Map locator widget, and a Tactical Media player with sci-fi ambient soundtracks and sound effects.
  4. Protocol Presets: Quick-trigger buttons for "System Diagnostics", "Atmospheric Scan", "Standby Mode", and "Full Power".
  5. Audio Effects: Synthesized Web Audio API sci-fi boot sound, interface beeps, and audio confirmation chimes.

Open:
- PWA ready with mobile touch controls and responsive layouts so it installs on Android home screens as a full-screen app.
- AI integration: Wire conversational intelligence using Lovable AI edge functions with fallback intelligent contextual replies.
- Settings drawer for customizing voice rate, pitch, selected voice, and sound effects volume.

build a real working app, not a clickable prototype; walk through each flow as its user would and design what the pictures leave out, as a product designer would for this product: the steps a flow needs to finish and how the app responds to what the user does, including the moments its users will actually run into, like waiting on something or finding nothing yet. Add nothing a user of this product would never meet, and keep an app the user wants simple, simple.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/355e526a-79bf-42df-8266-b29dd080a616).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
