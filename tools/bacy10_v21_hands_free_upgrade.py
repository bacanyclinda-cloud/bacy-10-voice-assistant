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
    private var pendingWake = activity.intent?.getBooleanExtra("bacy10_wake", false) == true ||
        activity.intent?.action == Intent.ACTION_ASSIST
    init {
        EventChannel(engine.dartExecutor.binaryMessenger, "bacy10/wake_events")
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    sink = events
                    if (pendingWake) {
                        pendingWake = false
                        Handler(Looper.getMainLooper()).post { sink?.success("wake") }
                    }
                }
                override fun onCancel(arguments: Any?) { sink = null }
            })
        MethodChannel(engine.dartExecutor.binaryMessenger, "bacy10/assistant")
            .setMethodCallHandler { call, result ->
                try {
                    when (call.method) {
                        "startWake" -> {
                            val prefs = activity.getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
                            val enabled = prefs.getBoolean("handsfree_enabled", false)
                            val granted = activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                                PackageManager.PERMISSION_GRANTED
                            if (!enabled) {
                                result.success("Hands-free wake is off. Enable it from the hands-free permissions panel.")
                            } else if (!granted) {
                                result.success("Microphone permission is missing. Re-enable hands-free from its permissions panel.")
                            } else {
                                BacyWakeService.voiceCallActive = false
                                BacyWakeService.start(activity)
                                result.success("Hands-free wake is active while Android permits it.")
                            }
                        }
                        "disableWake" -> {
                            activity.getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
                                .edit().putBoolean("handsfree_enabled", false).apply()
                            BacyWakeService.voiceCallActive = true
                            BacyWakeService.stop(activity)
                            result.success("Hands-free wake is off.")
                        }
                        "pauseWake", "stopWake" -> {
                            BacyWakeService.voiceCallActive = true
                            BacyWakeService.stop(activity)
                            result.success("Wake microphone paused during the live voice call.")
                        }
                        "wakePermissionState" -> {
                            val mic = activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                                PackageManager.PERMISSION_GRANTED
                            val notice = Build.VERSION.SDK_INT < 33 ||
                                activity.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
                                    PackageManager.PERMISSION_GRANTED
                            val power = activity.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager
                            result.success(mapOf(
                                "microphone" to mic,
                                "notifications" to notice,
                                "batteryUnrestricted" to (Build.VERSION.SDK_INT < 23 ||
                                    power.isIgnoringBatteryOptimizations(activity.packageName)),
                                "speechRecognizerAvailable" to android.speech.SpeechRecognizer.isRecognitionAvailable(activity),
                                "wakeServiceRunning" to BacyWakeService.running,
                                "handsfreeEnabled" to activity.getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
                                    .getBoolean("handsfree_enabled", false)))
                        }
                        "requestWakePermissions" -> {
                            val prefs = activity.getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
                            prefs.edit().putBoolean("handsfree_enabled", true).apply()
                            val needs = mutableListOf<String>()
                            if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
                                PackageManager.PERMISSION_GRANTED) needs.add(Manifest.permission.RECORD_AUDIO)
                            if (Build.VERSION.SDK_INT >= 33 &&
                                activity.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
                                    PackageManager.PERMISSION_GRANTED)
                                needs.add(Manifest.permission.POST_NOTIFICATIONS)
                            if (needs.isNotEmpty()) {
                                activity.requestPermissions(needs.toTypedArray(), 8011)
                                result.success("Allow microphone and notification permissions to enable hands-free wake.")
                            } else {
                                BacyWakeService.voiceCallActive = false
                                BacyWakeService.start(activity)
                                result.success("Hands-free wake is enabled.")
                            }
                        }
                        "batterySettings" -> {
                            activity.startActivity(Intent(
                                android.provider.Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
                            result.success("Allow BACY-10 unrestricted battery use in Android Settings.")
                        }
                        "appPermissions" -> {
                            activity.startActivity(Intent(
                                android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                android.net.Uri.parse("package:" + activity.packageName)))
                            result.success("Android app permission settings opened.")
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
        Handler(Looper.getMainLooper()).post {
            if (sink != null) sink?.success("wake")
            else pendingWake = true
        }
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
        @Volatile var running: Boolean = false

        fun start(context: Context) {
            val prefs = context.getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
            if (!prefs.getBoolean("handsfree_enabled", false) || voiceCallActive) return
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
            .setContentText("Say Hey BACY • Tap to open")
            .setContentIntent(openIntent)
            .setOngoing(true)
            .addAction(Notification.Action.Builder(
                android.R.drawable.ic_menu_close_clear_cancel, "Stop listening", stopIntent).build())
            .build()
        try {
            startForeground(NOTICE, notification)
            running = true
        } catch (_: Exception) {
            stopSelf()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val prefs = getSharedPreferences("bacy10_permissions", Context.MODE_PRIVATE)
        if (intent?.action == ACTION_STOP) {
            prefs.edit().putBoolean("handsfree_enabled", false).apply()
            voiceCallActive = true
            stopSelf()
            return START_NOT_STICKY
        }
        if (!prefs.getBoolean("handsfree_enabled", false)) {
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
            override fun onReadyForSpeech(params: Bundle?) { failureCount = 0 }
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
                if (error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
                    stopSelf()
                    return
                }
                failureCount = (failureCount + 1).coerceAtMost(16)
                restart()
            }
        })
        listen()
    }

    private fun matches(results: Bundle?): Boolean {
        val strings = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
        return strings.any {
            val phrase = it.lowercase(Locale.ROOT).replace(Regex("[^a-z0-9 ]"), " ")
            listOf("hey bacy", "hey basi", "hey bacey")
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
            // A fresh instance avoids continuous ERROR_RECOGNIZER_BUSY loops.
            try { speech?.destroy() } catch (_: Exception) {}
            speech = null
            begin()
        }, delay)
    }

    override fun onDestroy() {
        running = false
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

/// Voice opens directly for already-authorised devices. After reinstall,
/// permission recovery is accessible from a discrete dialog, not a home key form.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});
  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> with WidgetsBindingObserver {
  bool loading = true;
  bool authorised = false;
  bool starting = false;
  String? status;
  StreamSubscription<dynamic>? wakeEvents;
  static const _native = MethodChannel('bacy10/assistant');
  static const _wakes = EventChannel('bacy10/wake_events');

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    wakeEvents = _wakes.receiveBroadcastStream().listen((value) {
      if (value == 'wake' && mounted) {
        _openVoice();
      }
    }, onError: (Object _) {});
    _check();
  }

  Future<void> _check() async {
    bool available = false;
    try { available = await PairingTokenClient.hasPairingCode(); }
    catch (_) { available = false; }
    if (!mounted) return;
    setState(() {
      loading = false;
      authorised = available;
      status = available ? null : 'Restore your secure voice connection after reinstalling.';
    });
    if (available) await _openVoice();
  }

  Future<void> _openVoice() async {
    if (!mounted || starting || !authorised) return;
    final ctrl = context.read<app.AppCtrl>();
    if (ctrl.isSessionStarting ||
        ctrl.session.connectionState == sdk.ConnectionState.connected ||
        ctrl.session.connectionState == sdk.ConnectionState.reconnecting) return;
    setState(() {
      starting = true;
      status = 'Connecting to BACY-10…';
    });
    try {
      await _native.invokeMethod<String>('pauseWake');
      if (!mounted) return;
      ctrl.connect();
    } catch (_) {
      if (mounted) setState(() => status = 'Connection could not start. Tap Retry.');
    } finally {
      if (mounted) setState(() => starting = false);
    }
  }

  Future<void> _activate() async {
    final input = TextEditingController();
    String? error;
    final saved = await showDialog<String>(
      context: context,
      builder: (dialog) => StatefulBuilder(
        builder: (dialog, refresh) => AlertDialog(
          backgroundColor: const Color(0xFF161B1A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Text('Restore voice connection',
              style: TextStyle(color: Color(0xFFF2F4F1), fontWeight: FontWeight.w600)),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            const Text(
              'Your old app was removed, so Android erased its secure connection. '
              'You only need to restore it once; future launches connect automatically.',
              style: TextStyle(color: Color(0xFFC8D3D0), height: 1.5),
            ),
            const SizedBox(height: 17),
            TextField(
              controller: input,
              obscureText: true,
              enableSuggestions: false,
              autocorrect: false,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Private connection code',
                labelStyle: TextStyle(color: Color(0xFFB9CAC4)),
                border: OutlineInputBorder(),
              ),
            ),
            TextButton.icon(
              onPressed: () async {
                final data = await Clipboard.getData('text/plain');
                if (data?.text != null) {
                  input.text = data!.text!.trim();
                  refresh(() => error = null);
                }
              },
              icon: const Icon(Icons.content_paste_rounded, size: 17),
              label: const Text('Paste copied code'),
            ),
            if (error != null)
              Text(error!, style: const TextStyle(color: Color(0xFFE7A3A3))),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialog),
              child: const Text('Later')),
            FilledButton(
              onPressed: () {
                final value = input.text.trim();
                if (!RegExp(r'^[A-Za-z0-9_-]{20,160}$').hasMatch(value)) {
                  refresh(() => error = 'Enter the secure code previously issued to you.');
                  return;
                }
                Navigator.pop(dialog, value);
              },
              child: const Text('Connect voice'),
            ),
          ],
        ),
      ),
    );
    input.dispose();
    if (saved == null || !mounted) return;
    try {
      await PairingTokenClient.saveCode(saved);
      if (!mounted) return;
      setState(() { authorised = true; status = null; });
      await _openVoice();
    } catch (_) {
      if (mounted) setState(() => status = 'Could not store the connection securely.');
    }
  }

  Future<void> _handsFreePermissions() async {
    try {
      final current = await _native.invokeMapMethod<String, dynamic>(
        'wakePermissionState',
      );
      if (!mounted) return;
      final mic = current?['microphone'] == true;
      final notices = current?['notifications'] == true;
      final battery = current?['batteryUnrestricted'] == true;
      final recognizer = current?['speechRecognizerAvailable'] == true;
      final active = current?['wakeServiceRunning'] == true;
      final enabled = current?['handsfreeEnabled'] == true;
      await showDialog<void>(
        context: context,
        builder: (dialog) => AlertDialog(
          backgroundColor: const Color(0xFF111521),
          title: const Text(
            'Hands-free permissions',
            style: TextStyle(color: Color(0xFFF4F5FC)),
          ),
          content: Text(
            'Microphone: ' + (mic ? 'Allowed' : 'Needs permission') +
            '\nNotifications: ' + (notices ? 'Allowed' : 'Needs permission') +
            '\nBattery: ' + (battery ? 'Unrestricted' : 'Restricted') +
            '\nSpeech recognition: ' + (recognizer ? 'Available' : 'Not available') +
            '\nWake listening: ' + (active ? 'Running' : 'Not running') +
            '\nHands-free setting: ' + (enabled ? 'Enabled' : 'Off') +
            '\n\nWake detection uses Android speech recognition (on-device when available; otherwise the system provider may process audio). '
            'A persistent notification appears while listening. You can turn it off here or from that notification. '
            'Android may still restrict wake detection with the screen locked.',
            style: const TextStyle(
              height: 1.5, color: Color(0xFFC7D4E6), fontSize: 13),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try {
                  await _native.invokeMethod<String>('requestWakePermissions');
                } catch (_) {}
              },
              child: Text(active ? 'Refresh permissions' : 'Enable hands-free'),
            ),
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try {
                  await _native.invokeMethod<String>('batterySettings');
                } catch (_) {}
              },
              child: const Text('Battery settings'),
            ),
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try { await _native.invokeMethod<String>('disableWake'); } catch (_) {}
                if (mounted) setState(() => status = 'Hands-free wake is off.');
              },
              child: const Text('Turn off wake listening'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(dialog),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (_) {
      try {
        await _native.invokeMethod<String>('appPermissions');
      } catch (_) {}
    }
  }

  Future<void> _requestAssistantRole() async {
    try { await _native.invokeMethod<String>('assistantRole'); }
    catch (_) {
      if (mounted) setState(() =>
          status = 'Open Android Settings → Default apps → Digital assistant.');
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && authorised && mounted) {
      _openVoice();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    wakeEvents?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF080B0B),
    child: SafeArea(child: Consumer2<app.AppCtrl, sdk.Session>(
      builder: (ctx, controller, session, _) => Stack(children: [
        Positioned(top: 19, left: 23, right: 20,
          child: Row(children: [
            Container(
              width: 42, height: 42, alignment: Alignment.center,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(13),
                border: Border.all(color: const Color(0xFF5E7E73)),
                gradient: const LinearGradient(colors: [
                  Color(0xFF1E3430), Color(0xFF0F1616)])),
              child: const Text('B', style: TextStyle(
                fontSize: 25, fontWeight: FontWeight.w800,
                color: Color(0xFFE9F6EF))),
            ),
            const SizedBox(width: 11),
            const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('BACY-10', style: TextStyle(
                fontSize: 19, letterSpacing: .7,
                fontWeight: FontWeight.w700, color: Color(0xFFF0F4F2))),
              Text('VOICE INTELLIGENCE', style: TextStyle(
                fontSize: 9, letterSpacing: 1.9,
                color: Color(0xFF9DB7A9))),
            ]),
            const Spacer(),
            IconButton(
              tooltip: 'Hands-free permissions',
              onPressed: _handsFreePermissions,
              icon: const Icon(Icons.tune_rounded, color: Color(0xFFD5DAF8)),
            ),
            IconButton(
              onPressed: _requestAssistantRole,
              tooltip: 'Default Android assistant',
              icon: const Icon(Icons.settings_voice_rounded,
                color: Color(0xFFDBEAE0))),
          ])),
        Center(child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const SizedBox(height: 14),
            const SizedBox(width: 322, height: 322, child: BacyLiveOrb()),
            const SizedBox(height: 19),
            const Text('BACY-10', style: TextStyle(
              fontSize: 26, letterSpacing: 1.1,
              fontWeight: FontWeight.w600,
              color: Color(0xFFF1F8F3))),
            const SizedBox(height: 6),
            Text(
              loading ? 'Starting…' :
              !authorised ? 'CONNECTION NEEDS RESTORING' :
              controller.isSessionStarting ? 'CONNECTING TO VOICE' : 'VOICE ASSISTANT',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFF8EB5A2),
                letterSpacing: 2.1, fontSize: 10, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 15),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 26),
              child: Text(controller.connectionError ?? status ??
                'Your assistant starts automatically when connected.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Color(0xFFD3DFD9), height: 1.5, fontSize: 13)),
            ),
            const SizedBox(height: 18),
            if (!loading && !authorised)
              FilledButton.icon(
                onPressed: _activate,
                icon: const Icon(Icons.lock_open_rounded),
                label: const Text('RESTORE VOICE CONNECTION'),
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFFDCECDF),
                  foregroundColor: const Color(0xFF14281C),
                  minimumSize: const Size(270, 51),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(26)),
                ),
              ),
            if (authorised && !controller.isSessionStarting)
              OutlinedButton.icon(
                onPressed: _openVoice,
                icon: const Icon(Icons.mic_rounded),
                label: const Text('RECONNECT VOICE'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFDAE9DC),
                  minimumSize: const Size(245, 47),
                ),
              ),
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
        val prefs = getSharedPreferences("bacy10_permissions", MODE_PRIVATE)
        val enabled = prefs.getBoolean("handsfree_enabled", false)
        val microphoneMissing =
            checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED
        val noticeMissing = android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                android.content.pm.PackageManager.PERMISSION_GRANTED
        if (enabled && !microphoneMissing && !noticeMissing && !BacyWakeService.voiceCallActive) {
            BacyWakeService.start(this)
        } else if (!enabled || microphoneMissing || noticeMissing) {
            BacyWakeService.stop(this)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 8011) {
            val prefs = getSharedPreferences("bacy10_permissions", MODE_PRIVATE)
            val enabled = prefs.getBoolean("handsfree_enabled", false)
            val micGranted = checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED
            val noticeGranted = android.os.Build.VERSION.SDK_INT < 33 ||
                checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) ==
                    android.content.pm.PackageManager.PERMISSION_GRANTED
            if (enabled && micGranted && noticeGranted) {
                BacyWakeService.voiceCallActive = false
                BacyWakeService.start(this)
            } else {
                prefs.edit().putBoolean("handsfree_enabled", false).apply()
                BacyWakeService.stop(this)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("bacy10_wake", false) ||
            intent.action == Intent.ACTION_ASSIST) {
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
    one(pub,"version: 2.0.0+24","version: 2.4.0+28")
