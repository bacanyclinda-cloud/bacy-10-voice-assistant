"""BACY-10 v1.5 Android assistant role, foreground wake phrases and genuine screen sharing.

Applied after existing privacy, device control and reliability transforms.
"""
from pathlib import Path

WAKE_SERVICE = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.Manifest
import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import java.util.Locale

/**
 * Wake phrase detection only while BACY-10's foreground welcome page is visible.
 * Never starts a background microphone, and stops before joining LiveKit voice.
 * System default-assistant invocation is separately requested from Android.
 */
class BacyWakeListener(private val activity: Activity, engine: FlutterEngine) {
    private val handler = Handler(Looper.getMainLooper())
    private var sink: EventChannel.EventSink? = null
    private var recognizer: SpeechRecognizer? = null
    private var enabled = false
    private var restarting = false
    private var hasPendingRestart = false

    init {
        EventChannel(engine.dartExecutor.binaryMessenger, "bacy10/wake_events")
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) { sink = events }
                override fun onCancel(arguments: Any?) { sink = null; stop() }
            })
        MethodChannel(engine.dartExecutor.binaryMessenger, "bacy10/assistant")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "startWake" -> {
                        when {
                            activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED -> {
                                activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 8011)
                                result.success("Allow microphone access, then turn on hands-free again.")
                            }
                            !SpeechRecognizer.isRecognitionAvailable(activity) ->
                                result.success("Speech recognition is unavailable on this device.")
                            else -> {
                                start()
                                result.success("Listening for Hey BACY, Hey Enzo or Hey Bro while this screen is open.")
                            }
                        }
                    }
                    "stopWake" -> { stop(); result.success("Hands-free paused.") }
                    "assistantRole" -> {
                        if (Build.VERSION.SDK_INT >= 29) {
                            val mgr = activity.getSystemService(Context.ROLE_SERVICE) as RoleManager
                            if (mgr.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
                                activity.startActivityForResult(mgr.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT), 8021)
                                result.success("Choose BACY-10 in Android's default assistant prompt.")
                            } else result.success("The assistant role is not available on this phone.")
                        } else {
                            activity.startActivity(Intent("android.settings.VOICE_INPUT_SETTINGS"))
                            result.success("Choose BACY-10 in Android assistant settings, if supported.")
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun start() {
        stop()
        enabled = true
        recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
        recognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onError(error: Int) {
                if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) stop()
                else scheduleRestart()
            }
            override fun onResults(results: Bundle?) {
                val words = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
                val matched = words.any { text ->
                    val normalized = text.lowercase(Locale.ROOT)
                        .replace(Regex("[^a-z0-9 ]"), " ").replace(Regex("\\s+"), " ").trim()
                    listOf("hey bacy", "hey basi", "hey bacey", "hey enzo", "hey bro")
                        .any { normalized.contains(it) }
                }
                if (matched) {
                    stop()
                    sink?.success("wake")
                } else scheduleRestart()
            }
        })
        listen()
    }

    private fun listen() {
        if (!enabled) return
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
        }
        try { recognizer?.startListening(intent) } catch (_: Exception) { scheduleRestart() }
    }

    private fun scheduleRestart() {
        if (!enabled || hasPendingRestart) return
        hasPendingRestart = true
        handler.postDelayed({
            hasPendingRestart = false
            if (!enabled) return@postDelayed
            try { recognizer?.cancel() } catch (_: Exception) { }
            listen()
        }, 950L)
    }

    fun stop() {
        enabled = false
        handler.removeCallbacksAndMessages(null)
        hasPendingRestart = false
        try { recognizer?.cancel(); recognizer?.destroy() } catch (_: Exception) { }
        recognizer = null
    }
}
'''

def one(path: Path, old: str, new: str):
    t=path.read_text(encoding="utf-8")
    if t.count(old)!=1:
        raise RuntimeError(f"Expected one anchor in {path}: {old[:90]}, found {t.count(old)}")
    path.write_text(t.replace(old,new,1),encoding="utf-8")

def apply(root: Path):
    mobile=root/"mobile"
    native=mobile/"android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    (native/"BacyWakeListener.kt").write_text(WAKE_SERVICE,encoding="utf-8")
    activity=native/"MainActivity.kt"
    one(activity, '    private val channelName = "bacy10/phone"',
        '    private val channelName = "bacy10/phone"\n'
        '    private var bacyWake: BacyWakeListener? = null\n\n'
        '    override fun onDestroy() {\n'
        '        bacyWake?.stop()\n'
        '        super.onDestroy()\n'
        '    }')
    one(activity, '        super.configureFlutterEngine(flutterEngine)',
        '        super.configureFlutterEngine(flutterEngine)\n'
        '        bacyWake = BacyWakeListener(this, flutterEngine)')
    manifest=mobile/"android/app/src/main/AndroidManifest.xml"
    one(manifest, '<action android:name="android.intent.action.MAIN"/>',
        '<action android:name="android.intent.action.MAIN"/>')
    one(manifest, '            </intent-filter>\n        </activity>',
        '            </intent-filter>\n'
        '            <intent-filter>\n'
        '                <action android:name="android.intent.action.ASSIST"/>\n'
        '                <category android:name="android.intent.category.DEFAULT"/>\n'
        '            </intent-filter>\n'
        '        </activity>')
    one(manifest, '    <uses-permission android:name="android.permission.CAMERA" />',
        '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n'
        '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />\n'
        '    <uses-permission android:name="android.permission.CAMERA" />')
    one(manifest, '    </application>',
        '        <service android:name="de.julianassmann.flutter_background.IsolateHolderService"\n'
        '            android:exported="false" android:foregroundServiceType="mediaProjection" />\n'
        '    </application>')
    pubspec=mobile/"pubspec.yaml"
    one(pubspec, '  livekit_client: ^2.10.0',
        '  livekit_client: ^2.10.0\n  flutter_background: ^1.3.1')
    one(pubspec, 'version: 1.4.0+18','version: 1.5.0+19')

    ctrl=mobile/"lib/controllers/app_ctrl.dart"
    one(ctrl, "import 'dart:convert';", "import 'dart:convert';\nimport 'package:flutter_background/flutter_background.dart';")
    one(ctrl, '''  void toggleScreenShare() {
    isScreenshareEnabled = !isScreenshareEnabled;
    notifyListeners();
  }''', '''
  Future<void> toggleScreenShare() async {
    if (isScreenshareEnabled) {
      try {
        await room.localParticipant?.setScreenShareEnabled(false);
        isScreenshareEnabled = false;
        await FlutterBackground.disableBackgroundExecution();
        connectionError = null;
      } catch (error) {
        connectionError = 'Could not stop screen sharing: $error';
      }
      notifyListeners();
      return;
    }
    if (session.connectionState != sdk.ConnectionState.connected) {
      connectionError = 'Connect to the voice assistant before sharing your screen.';
      notifyListeners();
      return;
    }
    try {
      final allowed = await sdk.Hardware.instance.requestCapturePermission();
      if (!allowed) {
        connectionError = 'Screen capture was cancelled. Nothing was shared.';
        notifyListeners();
        return;
      }
      final configured = await FlutterBackground.initialize(
        androidConfig: const FlutterBackgroundAndroidConfig(
          notificationTitle: 'BACY-10 screen sharing',
          notificationText: 'Your screen is visible to BACY-10. Return to the app to stop.',
          shouldRequestBatteryOptimizationsOff: false,
        ),
      );
      if (!configured || !await FlutterBackground.enableBackgroundExecution()) {
        connectionError = 'Android did not allow the screen sharing foreground service.';
        notifyListeners();
        return;
      }
      await room.localParticipant?.setScreenShareEnabled(true);
      isScreenshareEnabled = true;
      connectionError = null;
    } catch (error) {
      connectionError = 'Screen sharing did not start: $error';
      try { await FlutterBackground.disableBackgroundExecution(); } catch (_) {}
    }
    notifyListeners();
  }''')
    one(ctrl, '  Future<void> disconnect() async {\n    await session.end();',
        '  Future<void> disconnect() async {\n'
        '    if (isScreenshareEnabled) await toggleScreenShare();\n'
        '    await session.end();')
    bar=mobile/"lib/widgets/control_bar.dart"
    one(bar, '''              const Flexible(
                flex: 1,
                fit: FlexFit.tight,
                child: FloatingGlassButton(
                  sfIcon: sf.SFIcons.sf_arrow_up_square_fill,
                  // onTap: () => appCtrl.toggleScreenShare(),
                ),
              ),''', '''              Flexible(
                flex: 1,
                fit: FlexFit.tight,
                child: Selector<AppCtrl, bool>(
                  selector: (context, app) => app.isScreenshareEnabled,
                  builder: (context, isSharing, child) => FloatingGlassButton(
                    sfIcon: sf.SFIcons.sf_arrow_up_square_fill,
                    isActive: isSharing,
                    onTap: () => context.read<AppCtrl>().toggleScreenShare(),
                  ),
                ),
              ),''')
    welcome=mobile/"lib/screens/welcome_screen.dart"
    one(welcome,"import 'package:flutter/material.dart';",
        "import 'dart:async';\nimport 'package:flutter/services.dart';\nimport 'package:flutter/material.dart';")
    one(welcome,'  bool initializing = true;',
        '''  bool initializing = true;
  bool wakeListening = false;
  String? wakeMessage;
  StreamSubscription<dynamic>? _wakeEvents;
  static const _wakeChannel = MethodChannel('bacy10/assistant');
  static const _wakeStream = EventChannel('bacy10/wake_events');

  Future<void> _toggleWake() async {
    try {
      final response = await _wakeChannel.invokeMethod<String>(
        wakeListening ? 'stopWake' : 'startWake',
      );
      if (!mounted) return;
      setState(() {
        wakeListening = !wakeListening && (response?.startsWith('Listening') ?? false);
        wakeMessage = response;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => wakeMessage = 'Android speech recognition is not available.');
    }
  }

  Future<void> _chooseAssistant() async {
    try {
      final response = await _wakeChannel.invokeMethod<String>('assistantRole');
      if (mounted) setState(() => wakeMessage = response);
    } catch (_) {
      if (mounted) setState(() => wakeMessage = 'Open Android Settings → Default apps → Digital assistant.');
    }
  }

  @override
  void dispose() {
    _wakeEvents?.cancel();
    _wakeChannel.invokeMethod<String>('stopWake').catchError((Object _) => null);
    super.dispose();
  }''')
    one(welcome,'    _restore();',
        '''    _restore();
    _wakeEvents = _wakeStream.receiveBroadcastStream().listen((event) {
      if (event != 'wake' || !mounted) return;
      setState(() {
        wakeListening = false;
        wakeMessage = 'Wake phrase recognised. Starting voice…';
      });
      context.read<app.AppCtrl>().connect();
    }, onError: (Object _) {
      if (mounted) setState(() => wakeListening = false);
    });''')
    one(welcome, '''                const SizedBox(height: 19),
                SizedBox(''',
        '''                const SizedBox(height: 12),
                Wrap(alignment: WrapAlignment.center, spacing: 9, runSpacing: 8, children: [
                  OutlinedButton.icon(
                    onPressed: _chooseAssistant,
                    icon: const Icon(Icons.settings_voice_rounded, size: 17),
                    label: const Text('Default assistant'),
                  ),
                  OutlinedButton.icon(
                    onPressed: initializing ? null : _toggleWake,
                    icon: Icon(wakeListening ? Icons.hearing_rounded : Icons.mic_none, size: 17),
                    label: Text(wakeListening ? 'Stop wake listening' : 'Enable Hey BACY'),
                  ),
                ]),
                if (wakeMessage != null) Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 6),
                  child: Text(wakeMessage!, textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 12, color: Color(0xFFB6CEE0))),
                ),
                const SizedBox(height: 19),
                SizedBox(''')
    agent=mobile/"lib/screens/agent_screen.dart"
    one(agent, '''        buildScreenShareView: (ctx) => Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: Colors.green.withValues(alpha: 0.3),
          ),
          child: const Text('Screenshare View'),
        ),''', '''        buildScreenShareView: (ctx) => Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: const Color(0xFF0F1C2A),
            border: Border.all(color: const Color(0xFF3E6988), width: 1),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(Icons.screen_share_rounded, color: Color(0xFF92D7E9)),
            SizedBox(height: 6),
            Text('Screen is being shared', textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFFD5E9F3), fontSize: 11)),
          ]),
        ),''')
