"""BACY-10 v2.6 -- keep active LiveKit microphone session in foreground service
when Android Home is pressed; switch wake and voice services correctly.
Only patches the post-v2.5 generated app.
"""
from pathlib import Path

VOICE_SERVICE = r'''
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
import android.os.IBinder

/** User-visible foreground microphone service for a currently active
 * LiveKit conversation. Mic audio remains owned by the Flutter WebRTC client.
 * Start from an Activity while foreground, before the owner presses Home.
 */
class BacyVoiceService : Service() {
    companion object {
        private const val CHANNEL = "bacy10_live_voice"
        private const val NOTICE = 7410
        @Volatile var running = false

        fun start(context: Context): Boolean {
            if (context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
                PackageManager.PERMISSION_GRANTED) return false
            return try {
                val i = Intent(context, BacyVoiceService::class.java)
                if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(i)
                else context.startService(i)
                true
            } catch (_: Exception) { false }
        }
        fun stop(context: Context) {
            try { context.stopService(Intent(context, BacyVoiceService::class.java)) }
            catch (_: Exception) {}
        }
    }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        try {
            val notifications =
                getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= 26) {
                notifications.createNotificationChannel(NotificationChannel(
                    CHANNEL, "BACY-10 active voice conversation",
                    NotificationManager.IMPORTANCE_LOW))
            }
            val open = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
            }
            val click = PendingIntent.getActivity(this, 4110, open,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            val notice = (if (Build.VERSION.SDK_INT >= 26)
                    Notification.Builder(this, CHANNEL)
                else Notification.Builder(this))
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("BACY-10 voice active")
                .setContentText("Keep talking hands-free. Tap to expand.")
                .setOngoing(true)
                .setContentIntent(click).build()
            startForeground(NOTICE, notice)
            running = true
        } catch (_: Exception) { running = false; stopSelf() }
    }
    override fun onStartCommand(intent: Intent?, flags: Int, id: Int): Int =
        START_NOT_STICKY
    override fun onDestroy() { running = false; super.onDestroy() }
}
'''

def one(path: Path, old: str, new: str) -> None:
    s=path.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError(f"v26 anchor missing ({n}): {path}, {old[:75]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

def apply(root: Path) -> None:
    mobile=root/"mobile"
    native=mobile/"android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    (native/"BacyVoiceService.kt").write_text(VOICE_SERVICE,encoding="utf-8")
    bridge=native/"BacyWakeListener.kt"
    one(bridge,'                        "startWake" -> {',
        '''                        "startVoiceForeground" -> {
                            BacyWakeService.voiceCallActive = true
                            BacyWakeService.stop(activity)
                            result.success(BacyVoiceService.start(activity))
                        }
                        "stopVoiceForeground" -> {
                            BacyVoiceService.stop(activity)
                            result.success(true)
                        }
                        "startWake" -> {''')
    one(bridge, '''                                "wakeServiceRunning" to BacyWakeService.running))''',
        '''                                "wakeServiceRunning" to BacyWakeService.running,
                                "voiceServiceRunning" to BacyVoiceService.running))''')
    manifest=mobile/"android/app/src/main/AndroidManifest.xml"
    one(manifest,'        <service android:name=".BacyWakeService"',
        '        <service android:name=".BacyVoiceService" android:exported="false" '
        'android:foregroundServiceType="microphone" />\n'
        '        <service android:name=".BacyWakeService"')
    ctrl=mobile/"lib/controllers/app_ctrl.dart"
    one(ctrl,'''      await session.start();
      if (session.connectionState == sdk.ConnectionState.connected) {''',
        '''      // Keep Android aware of an active mic call before going home.
      try {
        final started = await const MethodChannel('bacy10/assistant')
            .invokeMethod<bool>('startVoiceForeground');
        if (started != true) _logger.warning('Background mic service denied.');
      } catch (error) {
        _logger.warning('Background mic service unavailable: $error');
      }
      await session.start();
      if (session.connectionState == sdk.ConnectionState.connected) {''')
    one(ctrl,'''      // Don't abruptly unmount an active call just because a tool or
      // connection failed. The user can retry from the same screen.
      notifyListeners();''',
        '''      // Failed LiveKit setup must not leave the wake listener disabled.
      try {
        await const MethodChannel('bacy10/assistant')
            .invokeMethod<bool>('stopVoiceForeground');
        await const MethodChannel('bacy10/assistant')
            .invokeMethod<String>('startWake');
      } catch (_) {}
      notifyListeners();''')
    one(ctrl,'''      try {
        await const MethodChannel('bacy10/assistant')
            .invokeMethod<String>('startWake');
      } catch (_) {}
      if (!_hasCleanedUp) {''',
        '''      try {
        await const MethodChannel('bacy10/assistant')
            .invokeMethod<bool>('stopVoiceForeground');
        await const MethodChannel('bacy10/assistant')
            .invokeMethod<String>('startWake');
      } catch (_) {}
      if (!_hasCleanedUp) {''')
    # Make the orb visibly react to BOTH voices, not tiny invisible changes.
    orb=mobile/"lib/widgets/bacy_live_orb.dart"
    one(orb,'''        final level = (room.localParticipant?.audioLevel ?? 0.0)
            .clamp(0.0, 1.0)
            .toDouble();''',
        '''        final level = (room.localParticipant?.audioLevel ?? 0.0)
            .clamp(0.0, 1.0).toDouble();
        final agentLevel = (room.agentParticipant?.audioLevel ?? 0.0)
            .clamp(0.0, 1.0).toDouble();''')
    one(orb,'''        final energy = userSpeaking
            ? (0.42 + level * 1.15).clamp(0.0, 1.55).toDouble()
            : agentSpeaking
                ? 0.81
                : thinking
                    ? 0.43
                    : connected ? .22 : .12;''',
        '''        final energy = userSpeaking
            ? (0.60 + level * 1.30).clamp(0.0, 1.8).toDouble()
            : agentSpeaking
                ? (0.67 + agentLevel * 1.15).clamp(0.0, 1.8).toDouble()
                : thinking ? .43 : connected ? .22 : .12;''')
    one(orb,'''                  energy: energy,
                ),''',
        '''                  energy: energy,
                  userSpeaking: userSpeaking,
                  agentSpeaking: agentSpeaking,
                ),''')
    one(orb,'''  const _ReferenceHaloPainter({required this.phase, required this.energy});
  final double phase;
  final double energy;''',
        '''  const _ReferenceHaloPainter({
    required this.phase, required this.energy,
    required this.userSpeaking, required this.agentSpeaking,
  });
  final double phase;
  final double energy;
  final bool userSpeaking;
  final bool agentSpeaking;''')
    one(orb,'''    final radius = baseRadius *
        (1 + .016 * energy + .008 * math.sin(time * 1.5));''',
        '''    final active = userSpeaking || agentSpeaking;
    final beat = math.sin(time * (active ? 23.0 : 3.2));
    final radius = baseRadius *
        (1 + (active ? .055 : .008) * beat + .042 * energy);
    final voiceGlow = active ? .29 + energy * .19 : .10 + energy * .07;''')
    one(orb,'''            blue.withValues(alpha: .17 + .08 * energy),
            violet.withValues(alpha: .09),''',
        '''            (userSpeaking ? cyan : violet)
                .withValues(alpha: (.15 + voiceGlow).clamp(0.0, 1.0)),
            (agentSpeaking ? pink : blue)
                .withValues(alpha: (.08 + .13 * energy).clamp(0.0, 1.0)),''')
    one(orb,'''      colors: const [violet, pink, violet, cyan, blue, cyan, violet],''',
        '''      colors: userSpeaking
          ? const [cyan, blue, cyan, blue, cyan, blue, cyan]
          : agentSpeaking
              ? const [pink, violet, pink, violet, pink, violet, pink]
              : const [violet, pink, violet, cyan, blue, cyan, violet],''')
    one(orb,'''        ..strokeWidth = 2.25 + .8 * energy''',
        '''        ..strokeWidth = 2.25 + (active ? 2.7 : .8) * energy''')
    one(orb,'''  bool shouldRepaint(covariant _ReferenceHaloPainter old) =>
      old.phase != phase || old.energy != energy;''',
        '''  bool shouldRepaint(covariant _ReferenceHaloPainter old) =>
      old.phase != phase || old.energy != energy ||
      old.userSpeaking != userSpeaking ||
      old.agentSpeaking != agentSpeaking;''')

    image=root/"agent/src/image_provider.py"
    one(image,'raise ImageProviderError("Image generation quota reached. Please try again later.") from e',
        'raise ImageProviderError("Google image quota reached. No picture was created. '
        'Wait for the quota to reset or enable billing on the server project.") from e')
    tests=root/"agent/tests/test_background_voice.py"
    tests.write_text('''from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_real_mic_service_is_declared():
    source=(ROOT/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/BacyVoiceService.kt').read_text()
    manifest=(ROOT/'mobile/android/app/src/main/AndroidManifest.xml').read_text()
    assert 'startForeground' in source
    assert 'BacyVoiceService' in manifest
    assert 'foregroundServiceType="microphone"' in manifest
def test_microphone_call_service_handoff():
    src=(ROOT/'mobile/lib/controllers/app_ctrl.dart').read_text()
    assert "invokeMethod<bool>('startVoiceForeground')" in src
    assert "invokeMethod<bool>('stopVoiceForeground')" in src
def test_reactive_orb_both_voices():
    src=(ROOT/'mobile/lib/widgets/bacy_live_orb.dart').read_text()
    assert 'agentLevel' in src
    assert 'userSpeaking ? cyan' in src
    assert 'agentSpeaking ? pink' in src
''',encoding="utf-8")
    one(mobile/"pubspec.yaml","version: 2.5.0+29","version: 2.6.0+30")
