"""BACY-10: Visual explanations and real generated image previews on Android."""
from pathlib import Path

RESULT_DART = r'''
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class BacyResult {
  final String kind, title, summary;
  final List<String> steps, inputs, outputs;
  final Uint8List? image;
  const BacyResult({required this.kind, required this.title, this.summary = '',
    this.steps = const [], this.inputs = const [], this.outputs = const [], this.image});
}

class BacyResults {
  static final current = ValueNotifier<BacyResult?>(null);
  static void close() => current.value = null;
  static void lesson(Map<String, dynamic> request) {
    List<String> values(String key) => request[key] is List
      ? (request[key] as List).take(9).map((x) => x.toString()).toList()
      : <String>[];
    current.value = BacyResult(
      kind: 'lesson', title: (request['title'] ?? 'Visual explanation').toString(),
      summary: (request['summary'] ?? '').toString(),
      steps: values('steps'), inputs: values('inputs'), outputs: values('outputs'));
  }
  static void imageResult(Uint8List bytes) => current.value = BacyResult(
    kind: 'image', title: 'AI image created', image: bytes,
    summary: 'Generated image from the configured AI image service.');
}

class BacyResultsPanel extends StatelessWidget {
  const BacyResultsPanel({super.key});

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<BacyResult?>(
    valueListenable: BacyResults.current,
    builder: (context, result, _) {
      if (result == null) return const SizedBox.shrink();
      return SafeArea(child: Center(child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 550, maxHeight: 620),
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 65),
          decoration: BoxDecoration(
            color: const Color(0xFC071827),
            borderRadius: BorderRadius.circular(23),
            border: Border.all(color: const Color(0xFF326483)),
            boxShadow: [BoxShadow(color: const Color(0xFF1A4269).withValues(alpha: .36),
              blurRadius: 38, spreadRadius: 4)]),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.fromLTRB(17, 12, 8, 8),
              child: Row(children: [
                Icon(result.kind == 'image' ? Icons.auto_awesome : Icons.account_tree_rounded,
                  color: const Color(0xFF7FDCF1)),
                const SizedBox(width: 12),
                Expanded(child: Text(result.title, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Color(0xFFECF5FA), fontSize: 17,
                    fontWeight: FontWeight.w600))),
                IconButton(onPressed: BacyResults.close, tooltip: 'Close result',
                  icon: const Icon(Icons.close, color: Color(0xFFB4C8D6))),
              ]),
            ),
            Flexible(child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(18, 0, 18, 19),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                if (result.summary.isNotEmpty) Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: Text(result.summary, style: const TextStyle(
                    color: Color(0xFFC2D2DC), fontSize: 14, height: 1.5))),
                if (result.image != null) ...[
                  ClipRRect(borderRadius: BorderRadius.circular(14),
                    child: Image.memory(result.image!, fit: BoxFit.contain,
                      gaplessPlayback: true)),
                  const SizedBox(height: 13),
                  FilledButton.icon(
                    onPressed: () async {
                      try {
                        await const MethodChannel('bacy10/image_save').invokeMethod<String>(
                          'saveImage', {'bytes': result.image!});
                      } catch (_) { }
                    },
                    icon: const Icon(Icons.download_rounded),
                    label: const Text('Save image to Pictures')),
                ],
                if (result.inputs.isNotEmpty || result.outputs.isNotEmpty)
                  Container(padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: const Color(0xFF112A3A),
                      borderRadius: BorderRadius.circular(13)),
                    child: Column(children: [
                      Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8,
                        children: result.inputs.map((x) => _node(x, const Color(0xFF72DAF5))).toList()),
                      const Icon(Icons.arrow_downward_rounded, color: Color(0xFFAF98E4)),
                      _node(result.title, const Color(0xFFBEA3EE)),
                      const Icon(Icons.arrow_downward_rounded, color: Color(0xFFAF98E4)),
                      Wrap(alignment: WrapAlignment.center, spacing: 8, runSpacing: 8,
                        children: result.outputs.map((x) => _node(x, const Color(0xFF8EE3B7))).toList()),
                    ])),
                for (var i = 0; i < result.steps.length; i++)
                  Padding(padding: const EdgeInsets.only(top: 13),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      CircleAvatar(radius: 12, backgroundColor: const Color(0xFF145069),
                        child: Text((i + 1).toString(), style: const TextStyle(
                          fontSize: 12, color: Color(0xFF9AE4F2)))),
                      const SizedBox(width: 10),
                      Expanded(child: Text(result.steps[i], style: const TextStyle(
                        color: Color(0xFFEBF3FA), fontSize: 13, height: 1.5))),
                    ])),
              ]),
            )),
          ]),
        ))));
    },
  );

  Widget _node(String label, Color color) => Container(
    constraints: const BoxConstraints(maxWidth: 150),
    decoration: BoxDecoration(color: color.withValues(alpha: .13),
      border: Border.all(color: color.withValues(alpha: .50)),
      borderRadius: BorderRadius.circular(9)),
    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
    child: Text(label, textAlign: TextAlign.center,
      style: const TextStyle(color: Color(0xFFE9F4F9), fontSize: 12)));
}
'''

SAVER = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.app.Activity
import android.content.ContentValues
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class BacyImageSaver(activity: Activity, engine: FlutterEngine) {
    init {
        MethodChannel(engine.dartExecutor.binaryMessenger, "bacy10/image_save")
            .setMethodCallHandler { call, result ->
                if (call.method != "saveImage") { result.notImplemented(); return@setMethodCallHandler }
                try {
                    if (Build.VERSION.SDK_INT < 29) {
                        result.error("UNSUPPORTED", "Android 10 or later is required.", null)
                        return@setMethodCallHandler
                    }
                    val bytes = call.argument<ByteArray>("bytes")
                    if (bytes == null || bytes.isEmpty() || bytes.size > 6_500_000) {
                        result.error("SIZE", "No image or image too large.", null)
                        return@setMethodCallHandler
                    }
                    val values = ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, "BACY10_" + System.currentTimeMillis() + ".png")
                        put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
                        put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/BACY10")
                    }
                    val uri = activity.contentResolver.insert(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                        ?: throw IllegalStateException("Could not create image.")
                    activity.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                        ?: throw IllegalStateException("Could not write image.")
                    result.success("Saved in Pictures/BACY10.")
                } catch (_: Exception) {
                    result.error("SAVE", "Could not save the generated image.", null)
                }
            }
    }
}
'''

PYTOOLS = r'''
    @function_tool()
    async def show_visual_lesson(self, context: RunContext, title: str, summary: str,
                                 steps: list[str], inputs: list[str], outputs: list[str]) -> str:
        """Display numbered steps and a process diagram in the app's floating result window.
        Args:
            title: Short topic or process title.
            summary: One sentence explaining the concept.
            steps: A sequence of 3 to 8 simple explanatory steps.
            inputs: Up to six materials or starting conditions.
            outputs: Up to six products or ending conditions.
        """
        ctx = get_job_context()
        people = list(ctx.room.remote_participants.values())
        if not people:
            raise ToolError("The Android phone is not connected.")
        command = json.dumps({"kind": "lesson", "title": title[:120], "summary": summary[:1500],
            "steps": steps[:8], "inputs": inputs[:6], "outputs": outputs[:6]})
        try:
            output = await ctx.room.local_participant.perform_rpc(
                destination_identity=people[0].identity, method="bacy10.visual",
                payload=command, response_timeout=12.0)
            if not json.loads(output).get("ok", False):
                raise ValueError("The phone rejected the visual result.")
            return "The step-by-step diagram is showing on the phone."
        except Exception as error:
            raise ToolError("Could not show visual result: " + str(error)) from error

    @function_tool()
    async def generate_image_with_ai(self, context: RunContext, prompt: str) -> str:
        """Create a REAL original AI image using the server-side Gemini image model and display it on the phone.
        Args:
            prompt: Detailed description of the requested image.
        """
        import os
        import asyncio
        import base64
        import urllib.request
        import urllib.error
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not key:
            raise ToolError("Image generation needs a configured server-side Google API key.")
        if len(prompt.strip()) not in range(4, 1801):
            raise ToolError("Describe an image in 4 to 1800 characters.")

        def make_image():
            request_body = json.dumps({
                "contents": [{"parts": [{"text": prompt.strip()}]}],
                "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
            }).encode("utf-8")
            error_text = "No usable image was returned."
            for model in ("gemini-3.1-flash-image", "gemini-2.5-flash-image"):
                req = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
                    data=request_body,
                    headers={"Content-Type": "application/json", "x-goog-api-key": key},
                    method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=55) as response:
                        output = json.loads(response.read(15_000_000))
                    for candidate in output.get("candidates", []):
                        for part in candidate.get("content", {}).get("parts", []):
                            payload = part.get("inlineData") or part.get("inline_data")
                            if payload and payload.get("data"):
                                blob = base64.b64decode(payload["data"], validate=True)
                                if len(blob) > 6_500_000:
                                    raise ValueError("The generated picture is too large.")
                                return blob, payload.get("mimeType", "image/png")
                except urllib.error.HTTPError as error:
                    error_text = "AI image service HTTP " + str(error.code)
                except Exception as error:
                    error_text = type(error).__name__
            raise RuntimeError(error_text)
        try:
            picture, mime = await asyncio.to_thread(make_image)
            ctx = get_job_context()
            clients = list(ctx.room.remote_participants.values())
            if not clients:
                raise RuntimeError("Phone disconnected before image delivery.")
            stream = await ctx.room.local_participant.stream_bytes(
                name="bacy10-generated-image.png",
                topic="bacy10.image", mime_type=mime,
                total_size=len(picture),
                destination_identities=[clients[0].identity])
            try:
                for start in range(0, len(picture), 15000):
                    await stream.write(picture[start:start + 15000])
            finally:
                await stream.aclose()
            return "The generated image is ready in your BACY-10 result window."
        except Exception as error:
            raise ToolError("Image generation could not finish: " + str(error)) from error
'''

def once(path: Path, before: str, after: str) -> None:
    s=path.read_text(encoding="utf-8")
    if s.count(before)!=1:
        raise RuntimeError(f"Expected one anchor {str(path)} {before[:70]}: {s.count(before)}")
    path.write_text(s.replace(before,after,1),encoding="utf-8")

def apply(root: Path) -> None:
    mobile=root/"mobile"
    native=mobile/"android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    (native/"BacyImageSaver.kt").write_text(SAVER,encoding="utf-8")
    (mobile/"lib/support/bacy_results.dart").write_text(RESULT_DART,encoding="utf-8")
    once(native/"MainActivity.kt",
        '        bacyWake = BacyWakeListener(this, flutterEngine)',
        '        bacyWake = BacyWakeListener(this, flutterEngine)\n        BacyImageSaver(this, flutterEngine)')
    controller=mobile/"lib/controllers/app_ctrl.dart"
    once(controller,"import '../support/bacy10_memory.dart';",
        "import '../support/bacy10_memory.dart';\n"
        "import '../support/bacy_results.dart';\n"
        "import 'dart:typed_data';")
    once(controller,"    room.registerRpcMethod('bacy10.memory', (request) async {",
        """    room.registerRpcMethod('bacy10.visual', (request) async {
      if (room.agentParticipant?.identity != request.callerIdentity) {
        return jsonEncode({'ok': false, 'message': 'Unauthorized visual sender.'});
      }
      try {
        final data = jsonDecode(request.payload) as Map<String, dynamic>;
        if (data['kind'] != 'lesson') return jsonEncode({'ok': false});
        BacyResults.lesson(data);
        return jsonEncode({'ok': true});
      } catch (_) { return jsonEncode({'ok': false}); }
    });
    room.registerByteStreamHandler('bacy10.image', (reader, identity) {
      if (room.agentParticipant?.identity != identity) return;
      reader.readAll().then((chunks) {
        final builder = BytesBuilder(copy: false);
        for (final chunk in chunks) { builder.add(chunk); }
        final bytes = builder.takeBytes();
        if (bytes.isNotEmpty && bytes.length <= 6500000) BacyResults.imageResult(bytes);
      }).catchError((Object _) {});
    });
    room.registerRpcMethod('bacy10.memory', (request) async {""")
    once(controller,"    room.unregisterRpcMethod('bacy10.memory');",
        "    room.unregisterRpcMethod('bacy10.memory');\n"
        "    room.unregisterRpcMethod('bacy10.visual');\n"
        "    room.unregisterByteStreamHandler('bacy10.image');")
    screen=mobile/"lib/screens/agent_screen.dart"
    once(screen,"import '../controllers/app_ctrl.dart';",
        "import '../controllers/app_ctrl.dart';\nimport '../support/bacy_results.dart';")
    once(screen,"              _buildLayoutSwitcher(ctx, agentLayoutState),",
        "              _buildLayoutSwitcher(ctx, agentLayoutState),\n"
        "              const Positioned.fill(child: BacyResultsPanel()),")
    tools=root/"agent/src/phone_tools.py"
    once(tools,"            self.open_phone_photo_picker,",
        "            self.open_phone_photo_picker,\n"
        "            self.show_visual_lesson,\n"
        "            self.generate_image_with_ai,")
    tools.write_text(tools.read_text(encoding="utf-8")+"\n"+PYTOOLS,encoding="utf-8")
    instructions=root/"agent/src/agent.py"
    once(instructions,"                        # Native phone shortcuts",
        """                        # Native generation and explanatory skills
                        - To explain a process like photosynthesis, call show_visual_lesson with a title, short explanation, accurate steps, inputs and outputs. Explain it aloud too.
                        - To draw or generate an original image of a car, cat or other subject, call generate_image_with_ai and show the generated image inside the app. Never claim success when the image model fails.
                        - For a PDF, call export_pdf_to_phone with complete text so the file is created in Downloads/BACY10.
                        - Give a quick answer immediately before launching long web or image tasks and remain available for follow-up questions.

                        # Native phone shortcuts""")
    pubspec=mobile/"pubspec.yaml"
    once(pubspec,"version: 1.5.0+19","version: 1.6.0+20")
