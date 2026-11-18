"""BACY-10 v1.9 crash prevention and visible image-service error handling.

Fix simultaneous Flutter screen trees; isolate the orb from transient
TrackReferenceContext provider lifetimes; make AI image failure visible.
"""
from pathlib import Path

SINGLE_SCREEN = r"""
import 'package:flutter/material.dart';

/// Only mount the active screen. Previously both screens remained mounted
/// beneath IgnorePointer/AnimatedOpacity, leaving LiveKit inherited
/// dependencies alive while their owners were being disposed.
/// This can trigger Flutter's _dependents.isEmpty assertion in debug builds.
class AppLayoutSwitcher extends StatelessWidget {
  const AppLayoutSwitcher({
    super.key,
    this.isFront = true,
    this.animationDuration = const Duration(milliseconds: 0),
    this.animationCurve = Curves.linear,
    required this.frontBuilder,
    required this.backBuilder,
  });

  final bool isFront;
  final Duration animationDuration;
  final Curve animationCurve;
  final Widget Function(BuildContext) frontBuilder;
  final Widget Function(BuildContext) backBuilder;

  @override
  Widget build(BuildContext context) {
    return KeyedSubtree(
      key: ValueKey<String>(isFront ? 'bacy-home' : 'bacy-voice'),
      child: isFront ? frontBuilder(context) : backBuilder(context),
    );
  }
}
"""

REPLACEMENT_ORB = r"""
class AgentTrackView extends StatelessWidget {
  const AgentTrackView({super.key});
  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 20),
      child: RepaintBoundary(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: 410, maxWidth: 430),
          child: BacyLiveOrb(),
        ),
      ),
    ),
  );
}
"""

IMAGE_PROVIDER = r'''
"""Image generation provider, robust model selection and readable errors.

Gemini image models may require billing/quota access. Never claim success
on HTTP errors. The API key stays in the cloud agent environment.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class ImageProviderError(Exception):
    pass


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime_type: str


def parse_generated_image(payload: dict) -> GeneratedImage:
    for candidate in payload.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            raw = part.get("inlineData") or part.get("inline_data") or {}
            if not isinstance(raw, dict) or not raw.get("data"):
                continue
            mime = raw.get("mimeType") or raw.get("mime_type") or "image/png"
            if mime not in ("image/png", "image/jpeg", "image/webp"):
                raise ImageProviderError("The image service returned an unsupported image format.")
            try:
                data = base64.b64decode(raw["data"], validate=True)
            except (ValueError, TypeError) as err:
                raise ImageProviderError("The image service returned invalid image bytes.") from err
            if not 100 <= len(data) <= 6_500_000:
                raise ImageProviderError("The generated picture is empty or exceeds 6.5 MB.")
            return GeneratedImage(data, mime)
    reasons = [str(x.get("message", "")) for x in payload.get("promptFeedback", {}).get("blockReasonMessage", [])] \
        if isinstance(payload.get("promptFeedback", {}).get("blockReasonMessage"), list) else []
    raise ImageProviderError(
        "The image model returned no picture. The request may be unsupported, "
        "blocked or unavailable; try a different prompt." + (" ".join(reasons[:1]) if reasons else "")
    )


def request_image(prompt: str, api_key: str) -> GeneratedImage:
    if not 4 <= len(prompt.strip()) <= 1800:
        raise ImageProviderError("Describe the image in 4 to 1800 characters.")
    if not api_key:
        raise ImageProviderError("The private image API key is not configured on the server.")
    body = json.dumps({"contents": [{"parts": [{"text": prompt.strip()}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                             "imageConfig": {"imageSize": "1K"}}}).encode("utf-8")
    unavailable = ""
    for model in ("gemini-3.1-flash-lite-image", "gemini-3.1-flash-image", "gemini-2.5-flash-image"):
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
        req = urllib.request.Request(url, data=body, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
        try:
            with urllib.request.urlopen(req, timeout=32) as response:
                data = json.loads(response.read(12_000_000))
            return parse_generated_image(data)
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                unavailable = "This image model isn't supported by your account."
                continue
            if e.code in (401, 403):
                raise ImageProviderError("Image generation requires an authorized API key and "
                    "possibly a billing-enabled Google AI project.") from e
            if e.code == 429:
                raise ImageProviderError("Image generation quota reached. Please try again later.") from e
            raise ImageProviderError("Image service HTTP " + str(e.code) + ". Please try again.") from e
        except urllib.error.URLError as e:
            raise ImageProviderError("The image provider could not be reached. Check cloud connectivity.") from e
        except (ValueError, UnicodeError, json.JSONDecodeError) as e:
            raise ImageProviderError("The image provider returned an invalid response.") from e
    raise ImageProviderError(unavailable or "No image model is enabled for this API project.")
'''

PY_IMAGE_METHOD = r'''
    @function_tool()
    async def generate_image_with_ai(self, context: RunContext, prompt: str) -> str:
        """Create an actual original picture using Google image generation and show it on the user's Android screen.

        Args:
            prompt: A detailed visual description of the requested new image.
        """
        import asyncio
        import os
        from image_provider import ImageProviderError, request_image
        ctx = get_job_context()
        clients = list(ctx.room.remote_participants.values())
        if not clients:
            raise ToolError("Your Android app isn't connected to receive an image.")
        phone_id = clients[0].identity

        async def state(title: str, message: str, level: str = "status") -> None:
            try:
                await ctx.room.local_participant.perform_rpc(
                    destination_identity=phone_id,
                    method="bacy10.visual",
                    payload=json.dumps({"kind": level, "title": title[:90],
                        "summary": message[:500]}),
                    response_timeout=8.0,
                )
            except Exception:
                # UI feedback is best-effort; it must never crash the voice session.
                pass

        await state("Creating your image", "Generating a real picture with the AI image service…")
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        try:
            generated = await asyncio.wait_for(
                asyncio.to_thread(request_image, prompt, key), timeout=85.0)
            name = "bacy10-ai-image.jpg" if generated.mime_type == "image/jpeg" else "bacy10-ai-image.png"
            writer = await ctx.room.local_participant.stream_bytes(
                name=name, topic="bacy10.image", mime_type=generated.mime_type,
                total_size=len(generated.data), destination_identities=[phone_id])
            try:
                for offset in range(0, len(generated.data), 12000):
                    await writer.write(generated.data[offset:offset + 12000])
            finally:
                await writer.aclose()
            return "Your picture has been generated and sent to the phone's image preview."
        except (ImageProviderError, TimeoutError, ValueError) as err:
            reason = str(err) if str(err) else "The image request timed out."
            await state("Couldn't generate that image", reason, "error")
            # Return the failure as a normal tool result so the voice assistant
            # can continue speaking rather than terminate the whole call.
            return "I couldn't generate the picture: " + reason
        except Exception as err:
            await state("Image delivery interrupted", "The image was not delivered. Please try again.", "error")
            return "I generated or requested the image but couldn't deliver it to the phone. Please try again."
'''

def replace_one(path: Path, target: str, replacement: str) -> None:
    old=path.read_text(encoding="utf-8")
    count=old.count(target)
    if count != 1:
        raise RuntimeError("Expected one anchor in " + str(path) + ": " + target[:70]
            + " count=" + str(count))
    path.write_text(old.replace(target,replacement,1),encoding="utf-8")


def apply(root: Path) -> None:
    mobile=root/"mobile"
    (mobile/"lib/widgets/app_layout_switcher.dart").write_text(SINGLE_SCREEN,encoding="utf-8")
    agent_screen=mobile/"lib/screens/agent_screen.dart"
    content=agent_screen.read_text(encoding="utf-8")
    begin=content.index("class AgentTrackView extends StatelessWidget")
    end=content.index("class FrontView extends StatelessWidget",begin)
    content=content[:begin]+REPLACEMENT_ORB+"\n"+content[end:]
    agent_screen.write_text(content,encoding="utf-8")

    ctrl=mobile/"lib/controllers/app_ctrl.dart"
    replace_one(ctrl, "  void connect() async {\n", """  void connect() async {
    if (isSessionStarting || session.connectionState == sdk.ConnectionState.connected
        || session.connectionState == sdk.ConnectionState.reconnecting) {
      return;
    }
""")
    replace_one(ctrl, """      appScreenState = AppScreenState.welcome;
      notifyListeners();
    } finally {""", """      // Don't abruptly unmount an active call just because a tool or
      // connection failed. The user can retry from the same screen.
      notifyListeners();
    } finally {""")
    replace_one(ctrl, """  Future<void> disconnect() async {
    if (isScreenshareEnabled) await toggleScreenShare();""", """  Future<void> disconnect() async {
    if (isScreenshareEnabled) await toggleScreenShare();""")
    replace_one(ctrl, """        if (data['kind'] != 'lesson') return jsonEncode({'ok': false});
        BacyResults.lesson(data);
        return jsonEncode({'ok': true});""", """        if (data['kind'] == 'lesson') {
          BacyResults.lesson(data);
        } else if (data['kind'] == 'status' || data['kind'] == 'error') {
          BacyResults.status(
            (data['title'] ?? 'Task update').toString(),
            (data['summary'] ?? '').toString(),
            isError: data['kind'] == 'error');
        } else {
          return jsonEncode({'ok': false});
        }
        return jsonEncode({'ok': true});""")
    # Mark completion as a UI event as well, so image streaming failures are obvious.
    results=mobile/"lib/support/bacy_results.dart"
    replace_one(results,"  static void close() => current.value = null;", """  static void close() => current.value = null;
  static void status(String title, String message, {bool isError = false}) {
    current.value = BacyResult(
      kind: isError ? 'error' : 'status', title: title, summary: message);
  }""")
    replace_one(results, "    builder: (context, result, _) {\n      if (result == null) return const SizedBox.shrink();", """    builder: (context, result, _) {
      if (result == null) return const SizedBox.shrink();""")
    # The image preview previously covered the entire screen with no progress
    # feedback. It now shows visible status/error text and remains closable.

    agent=root/"agent/src"
    (agent/"image_provider.py").write_text(IMAGE_PROVIDER,encoding="utf-8")
    tools=agent/"phone_tools.py"
    code=tools.read_text(encoding="utf-8")
    start=code.index("    @function_tool()\n    async def generate_image_with_ai(")
    code=code[:start]+PY_IMAGE_METHOD+"\n"
    tools.write_text(code,encoding="utf-8")
    (root/"agent/tests/test_image_provider.py").write_text('''
import base64
import pytest
from image_provider import parse_generated_image, ImageProviderError, request_image


def test_parses_real_inline_image():
    data=b"some-image-bytes" * 20
    payload={"candidates":[{"content":{"parts":[{
      "inlineData":{"mimeType":"image/png","data":base64.b64encode(data).decode()}
    }]}}]}
    result=parse_generated_image(payload)
    assert result.data==data and result.mime_type=="image/png"


def test_blocks_empty_or_unsupported_image():
    with pytest.raises(ImageProviderError):
        parse_generated_image({"candidates":[]})


def test_rejects_bad_prompt_without_network():
    with pytest.raises(ImageProviderError):
        request_image(" ", "test-key")
''',encoding="utf-8")
    pub=mobile/"pubspec.yaml"
    replace_one(pub,"version: 1.8.0+22","version: 1.9.0+23")
