# BACY-10 — Complete LiveKit Source Download

This is the **real** LiveKit agent source from the tutorial:
https://www.youtube.com/watch?v=Fhm8goKN6rM

The source package is created by the GitHub Actions workflow **BACY-10 LiveKit Complete Source**.

## Download ZIP
1. Open **Actions** in this repository.
2. Choose **BACY-10 LiveKit Complete Source**.
3. Open the latest successful workflow run.
4. Under **Artifacts**, select `BACY10-LIVEKIT-FULL-SOURCE` and download the ZIP.
5. Extract the downloaded ZIP.

The source packager clones pinned upstream tutorial commit `d1cf71e40c72d2429af766646bea4869ba736c77`, including Python LiveKit agent, Playwright browser tools, Next.js frontend, and complete Flutter Android project.

## What to compile
Open `BACY10-LIVEKIT-FULL-SOURCE/mobile` in Android Studio or use the Flutter CLI:
```bash
flutter pub get
flutter build apk --debug
```

Before connecting, set your own LiveKit sandbox token ID in `mobile/assets/.env`. Start the Python agent from the `agent` directory with real LiveKit and Google Gemini credentials. Read `README-BACY10.md` inside the ZIP for complete commands.

### Credentials / safety
Never put `LIVEKIT_API_SECRET`, `GOOGLE_API_KEY`, `OPENAI_API_KEY` or a pasted token in mobile Dart code, GitHub, or the APK. The template's development sandbox is not a production authentication service.

### What has been verified
The workflow checks the package's required files and Python syntax, then attempts Python dependency tests and Flutter compilation. See GitHub Actions job logs for actual status. A passing syntax check does **not** prove end-to-end LiveKit/Gemini voice works; real accounts, mic and Android testing are still required.

This package is intentionally isolated from your existing Lovable BACY-10 website. It does not overwrite your current web/voice assistant code.

### Upstream
Original source: https://github.com/ruxakK/jarvis-voice-butler

Respect the author's rights and the licenses included with the upstream Flutter and frontend projects.
