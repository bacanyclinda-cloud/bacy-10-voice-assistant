"""BACY-10 v2.1 direct launch, foreground wake-phrase service, no pairing-code UI.

Android requires RECORD_AUDIO permission and foreground-service notification.
The service is opt-in through one-time Android permission, automatically starts
on later launches, and pauses during the LiveKit call to avoid microphone
contention. Android does not guarantee DSP-grade screen-off hotword detection.
"""
from pathlib import Path

WAKE_BRIDGE = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.Manifest
import android.app.Activity
import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class BacyWakeListener(private val activity: Activity, engine: FlutterEngine) {
    private var sink: EventChannel.EventSink? = null
    init {
        EventChannel(engine.dartExecutor.binaryMessenger, "bacy10/wake_events")
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    sink = events
                }
                override fun onCancel(arguments: Any?) { sink = null }
            })
        MethodChannel(engine.dartExecutor.binaryMessenger, "bacy10/assistant")
            .setMethodCallHandler { call, result ->
                try {
                    when (call.method) {
                        "startWake" -> {
                            BacyWakeService.voiceCallActive = false
                            val granted = activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                                PackageManager.PERMISSION_GRANTED
                            if (!granted) {
                                activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 8011)
                                result.success("Allow microphone once in Android's permission popup.")
                            } else {
                                BacyWakeService.start(activity)
                                result.success("Background wake detection is on, while Android permits it.")
                            }
                        }
                        "pauseWake", "stopWake" -> {
                            BacyWakeService.voiceCallActive = true
                            BacyWakeService.stop(activity)
                            result.success("Wake microphone paused during the live voice call.")
                        }
                        "assistantRole" -> {
                            if (Build.VERSION.SDK_INT >= 29) {
                                val roles = activity.getSystemService(Context.ROLE_SERVICE) as RoleManager
                                if (roles.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
                                    activity.startActivityForResult(
                                        roles.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT), 8021)
                                    result.success("Select BACY-10 as your Android default assistant.")
                                } else result.success("Your phone does not expose a selectable assistant role.")
                            } else {
                                activity.startActivity(Intent("android.settings.VOICE_INPUT_SETTINGS"))
                                result.success("Android assistant settings opened.")
                            }
                        }
                        else -> result.notImplemented()
                    }
                } catch (_: Exception) {
                    result.success("Android did not allow the requested voice operation.")
                }
            }
    }

    fun emitWake() {
        Handler(Looper.getMainLooper()).post { sink?.success("wake") }
    }

    fun stop() {
        sink = null
    }
}
'''

WAKE_SERVICE = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.os.Bundle
import java.util.Locale

/**
 * Visible microphone foreground service. Android's SpeechRecognizer is not a
 * hardware hotword detector; the OS can stop it while locked or under battery
 * pressure. Owner can stop it from the permanent notification.
 */
class BacyWakeService : Service() {
    companion object {
        private const val CHANNEL = "bacy10_wake"
        private const val NOTICE = 7401
        const val ACTION_STOP = "com.livekit.example.VoiceAssistantFlutter.STOP_WAKE"
        @Volatile var voiceCallActive: Boolean = false

        fun start(context: Context) {
            if (voiceCallActive) return
            if (Build.VERSION.SDK_INT >= 23 &&
                context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
                    PackageManager.PERMISSION_GRANTED) return
            val intent = Intent(context, BacyWakeService::class.java)
            try { context.startForegroundService(intent) }
            catch (_: Exception) { /* Android may block background starts. */ }
        }
        fun stop(context: Context) {
            try { context.stopService(Intent(context, BacyWakeService::class.java)) }
            catch (_: Exception) {}
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private var speech: SpeechRecognizer? = null
    private var stopping = false
    private var failureCount = 0
    private var restarting = false
    private var busy = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        val notice = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notice.createNotificationChannel(NotificationChannel(
            CHANNEL, "BACY-10 hands-free microphone", NotificationManager.IMPORTANCE_LOW))
        val open = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
        }
        val openIntent = PendingIntent.getActivity(this, 4001, open,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val stopIntent = PendingIntent.getService(this, 4002,
            Intent(this, BacyWakeService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("BACY-10 is listening")
            .setContentText("Say Hey BACY, Hey Enzo, or Hey Bro • Tap to open")
            .setContentIntent(openIntent)
            .setOngoing(true)
            .addAction(Notification.Action.Builder(
                android.R.drawable.ic_menu_close_clear_cancel, "Stop listening", stopIntent).build())
            .build()
        startForeground(NOTICE, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            voiceCallActive = true
            stopSelf()
            return START_NOT_STICKY
        }
        if (!voiceCallActive && !stopping) begin()
        return START_STICKY
    }

    private fun begin() {
        if (speech != null || stopping) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED || !SpeechRecognizer.isRecognitionAvailable(this)) {
            stopSelf()
            return
        }
        speech = if (Build.VERSION.SDK_INT >= 31 &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
            SpeechRecognizer.createOnDeviceSpeechRecognizer(this)
        } else SpeechRecognizer.createSpeechRecognizer(this)

        speech?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() { busy = true }
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() { busy = false }
            override fun onEvent(eventType: Int, params: Bundle?) {}
            override fun onPartialResults(partialResults: Bundle?) {
                if (matches(partialResults)) wake()
            }
            override fun onResults(results: Bundle?) {
                busy = false
                if (matches(results)) wake() else restart()
            }
            override fun onError(error: Int) {
                busy = false
                if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ||
                    error == SpeechRecognizer.ERROR_CLIENT) {
                    failureCount += 1
                } else failureCount = (failureCount + 1).coerceAtMost(20)
                if (failureCount > 25) {
                    stopSelf()
                    return
                }
                restart()
            }
        })
        listen()
    }

    private fun matches(results: Bundle?): Boolean {
        val strings = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
        return strings.any {
            val phrase = it.lowercase(Locale.ROOT).replace(Regex("[^a-z0-9 ]"), " ")
            listOf("hey bacy", "hey basi", "hey bacey", "hey enzo", "hey bro")
                .any { hotword -> phrase.contains(hotword) }
        }
    }

    private fun wake() {
        if (stopping) return
        voiceCallActive = true
        stopping = true
        speech?.cancel()
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("bacy10_wake", true)
        }
        try { startActivity(intent) }
        catch (_: Exception) {
            val notice = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            // Android 10+ may block background activity launches. The owner
            // can tap the ongoing notification and the assistant opens.
            notice.notify(NOTICE + 1, Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("BACY-10 heard your wake phrase")
                .setContentText("Tap to open the voice assistant")
                .setAutoCancel(true)
                .setContentIntent(PendingIntent.getActivity(this, 4003, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE))
                .build())
        }
        stopSelf()
    }

    private fun listen() {
        if (stopping || voiceCallActive) return
        val request = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 4)
        }
        try { speech?.startListening(request) }
        catch (_: Exception) { restart() }
    }

    private fun restart() {
        if (stopping || restarting || voiceCallActive) return
        restarting = true
        val delay = (900 + failureCount.coerceAtMost(8) * 400).toLong()
        handler.postDelayed({
            restarting = false
            if (stopping || voiceCallActive) return@postDelayed
            try { speech?.cancel() } catch (_: Exception) {}
            listen()
        }, delay)
    }

    override fun onDestroy() {
        stopping = true
        handler.removeCallbacksAndMessages(null)
        try { speech?.cancel(); speech?.destroy() } catch (_: Exception) {}
        speech = null
        super.onDestroy()
    }
}
'''

WELCOME = r'''
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';
import '../controllers/app_ctrl.dart' as app;
import '../support/bacy10_token_client.dart';
import '../widgets/bacy_live_orb.dart';

/// The owner never has to paste a secret into the BACY-10 home screen.
/// An existing encrypted device credential is used silently. No secret
/// is embedded in this APK. A new device needs secure owner enrolment.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});
  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> with WidgetsBindingObserver {
  bool initializing = true;
  bool isAuthorized = false;
  bool connecting = false;
  String? assistantStatus;
  StreamSubscription<dynamic>? wakeSubscription;
  static const native = MethodChannel('bacy10/assistant');
  static const wakes = EventChannel('bacy10/wake_events');

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    wakeSubscription = wakes.receiveBroadcastStream().listen((event) async {
      if (event == 'wake' && mounted) await _resumeVoice();
    }, onError: (Object _) {});
    _resumeVoice();
  }

  Future<void> _resumeVoice() async {
    if (connecting) return;
    connecting = true;
    try {
      isAuthorized = await PairingTokenClient.hasPairingCode();
      if (!mounted) return;
      setState(() => initializing = false);
      if (!isAuthorized) {
        setState(() => assistantStatus =
            'This installation needs secure device authorization. Your API key is never stored in the app.');
        return;
      }
      await native.invokeMethod<String>('pauseWake');
      if (!mounted) return;
      context.read<app.AppCtrl>().connect();
    } catch (_) {
      if (mounted) setState(() => assistantStatus =
        'Could not start voice. Check your connection and retry.');
    } finally {
      connecting = false;
      if (mounted) setState(() => initializing = false);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && mounted &&
        !context.read<app.AppCtrl>().isSessionStarting &&
        context.read<app.AppCtrl>().session.connectionState == sdk.ConnectionState.disconnected) {
      _resumeVoice();
    }
  }

  Future<void> _chooseDefaultAssistant() async {
    try {
      final result = await native.invokeMethod<String>('assistantRole');
      if (mounted) setState(() => assistantStatus = result);
    } catch (_) {
      if (mounted) setState(() => assistantStatus =
          'Open Android Settings → Default apps → Digital assistant.');
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    wakeSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF0B0A0B),
    child: SafeArea(child: Consumer2<app.AppCtrl, sdk.Session>(
      builder: (ctx, controller, session, _) => Stack(children: [
        Positioned(top: 14, right: 15,
          child: IconButton(
            tooltip: 'Choose as Android assistant',
            onPressed: _chooseDefaultAssistant,
            icon: const Icon(Icons.settings_voice_rounded, color: Color(0xFFE7CFB4)))),
        Center(child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 510),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Text('BACY—10', style: TextStyle(
              fontSize: 28, letterSpacing: 5.5, fontWeight: FontWeight.w300,
              color: Color(0xFFF4EBDF))),
            const SizedBox(height: 4),
            const Text('PERSONAL INTELLIGENCE', style: TextStyle(
              fontSize: 10, letterSpacing: 1.8, color: Color(0xFFD3BCA6))),
            const SizedBox(height: 24),
            const SizedBox(width: 320, height: 320, child: BacyLiveOrb()),
            const SizedBox(height: 14),
            Text(initializing ? 'Starting voice…' :
                controller.connectionError ?? assistantStatus ??
                (isAuthorized ? 'Connecting automatically…' : 'Device authorization required'),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: Color(0xFFD8C7B6))),
            if (controller.connectionError != null && isAuthorized) ...[
              const SizedBox(height: 15),
              OutlinedButton.icon(
                onPressed: _resumeVoice, icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry connection')),
            ],
          ]),
        )),
      ]),
    )),
  );
}
'''

def one(path: Path, anchor: str, replacement: str):
    s=path.read_text(encoding="utf-8")
    if s.count(anchor)!=1: raise RuntimeError("Unexpected Android source: "+str(path)+" anchor="+anchor[:70])
    path.write_text(s.replace(anchor,replacement,1),encoding="utf-8")

def apply(root: Path):
    mobile=root/"mobile"
    native=mobile/"android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    (native/"BacyWakeListener.kt").write_text(WAKE_BRIDGE,encoding="utf-8")
    (native/"BacyWakeService.kt").write_text(WAKE_SERVICE,encoding="utf-8")
    (mobile/"lib/screens/welcome_screen.dart").write_text(WELCOME,encoding="utf-8")

    main=native/"MainActivity.kt"
    one(main,"    override fun onDestroy() {",
        '''    override fun onResume() {
        super.onResume()
        if (!BacyWakeService.voiceCallActive &&
            checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            BacyWakeService.start(this)
        } else if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED) {
            val prefs = getSharedPreferences("bacy10_permissions", MODE_PRIVATE)
            if (!prefs.getBoolean("mic_requested", false)) {
                prefs.edit().putBoolean("mic_requested", true).apply()
                requestPermissions(arrayOf(android.Manifest.permission.RECORD_AUDIO), 8011)
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 8011 &&
            checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED) {
            BacyWakeService.start(this)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("bacy10_wake", false)) {
            bacyWake?.emitWake()
        }
    }

    override fun onDestroy() {''')
    manifest=mobile/"android/app/src/main/AndroidManifest.xml"
    one(manifest,'    <queries>',
        '    <queries>\n        <intent><action android:name="android.speech.RecognitionService" /></intent>')
    one(manifest,'    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />',
        '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />\n'
        '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />')
    one(manifest,'    <uses-permission android:name="android.permission.RECORD_AUDIO" />',
        '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n'
        '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />')
    one(manifest,'        <service android:name="de.julianassmann.flutter_background.IsolateHolderService"',
        '        <service android:name=".BacyWakeService"\n'
        '            android:exported="false" android:foregroundServiceType="microphone" />\n'
        '        <service android:name="de.julianassmann.flutter_background.IsolateHolderService"')
    ctrl=mobile/"lib/controllers/app_ctrl.dart"
    one(ctrl,'      await session.start();',
        '''      // Do not compete for the microphone with the wake detector.
      try { await const MethodChannel('bacy10/assistant')
          .invokeMethod<String>('pauseWake'); } catch (_) {}
      await session.start();''')
    one(ctrl,'    await session.end();\n    session.restoreMessageHistory',
        '''    await session.end();
    try { await const MethodChannel('bacy10/assistant')
        .invokeMethod<String>('startWake'); } catch (_) {}
    session.restoreMessageHistory''')
    pub=mobile/"pubspec.yaml"
    one(pub,"version: 2.0.0+24","version: 2.1.0+25")
