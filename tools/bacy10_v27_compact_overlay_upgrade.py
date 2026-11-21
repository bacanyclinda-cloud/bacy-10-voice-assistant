"""BACY-10 v2.7: proprietary compact voice capsule at the screen bottom.
Build after the v2.6 microphone foreground service. No full-screen launch on
wake phrase; requires explicit owner-granted Android overlay permission.
"""
from pathlib import Path

OVERLAY = r'''
package com.livekit.example.VoiceAssistantFlutter

import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Shader
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/** A small animated BACY-10 panel, not an imitation of Gemini.
 * Permission is user-granted. Does not listen to the mic itself:
 * the existing LiveKit room or wake foreground service handles audio.
 */
class BacyCompactOverlayService : Service() {
    companion object {
        @Volatile var running = false
        private var currentState = "LISTENING"
        fun permitted(c: Context) =
            Build.VERSION.SDK_INT < 23 || Settings.canDrawOverlays(c)
        fun show(c: Context, state: String = "LISTENING"): Boolean {
            if (!permitted(c)) return false
            return try {
                c.startService(Intent(c, BacyCompactOverlayService::class.java)
                    .putExtra("state", state))
                true
            } catch (_: Exception) { false }
        }
        fun hide(c: Context) {
            if (!running) return
            try { c.stopService(Intent(c, BacyCompactOverlayService::class.java)) }
            catch (_: Exception) {}
        }
        fun update(c: Context, state: String) {
            if (running) show(c, state)
        }
    }
    private var manager: WindowManager? = null
    private var view: MiniPanel? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, id: Int): Int {
        currentState = intent?.getStringExtra("state")?.take(32) ?: currentState
        if (!permitted(this)) { stopSelf(); return START_NOT_STICKY }
        if (view == null) try {
            val density = resources.displayMetrics.density
            manager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val width = min(
                resources.displayMetrics.widthPixels - (24 * density).toInt(),
                (396 * density).toInt())
            val params = WindowManager.LayoutParams(
                width, (92 * density).toInt(),
                if (Build.VERSION.SDK_INT >= 26)
                    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                else WindowManager.LayoutParams.TYPE_PHONE,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                android.graphics.PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
                y = (28 * density).toInt()
            }
            view = MiniPanel(this)
            manager?.addView(view, params)
            running = true
        } catch (_: Exception) { stopSelf() }
        view?.invalidate()
        return START_NOT_STICKY
    }
    override fun onDestroy() {
        running = false
        try { view?.let { manager?.removeView(it) } } catch (_: Exception) {}
        view = null
        manager = null
        super.onDestroy()
    }

    private inner class MiniPanel(c: Context) : View(c) {
        private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        private val since = SystemClock.uptimeMillis()
        private var stopped = false
        private val cyan = Color.rgb(63, 202, 255)
        private val violet = Color.rgb(176, 115, 254)
        private val white = Color.rgb(240, 246, 255)
        private val text = Color.rgb(160, 173, 205)

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            if (width <= 0) return
            val d = resources.displayMetrics.density
            val w = width.toFloat()
            val h = height.toFloat()
            val t = (SystemClock.uptimeMillis() - since) / 1000.0
            val speaking = currentState == "YOU SPEAKING" ||
                currentState == "AI SPEAKING"
            val rect = RectF(2*d, 4*d, w-2*d, h-4*d)
            paint.reset(); paint.isAntiAlias = true
            paint.color = Color.rgb(9, 12, 29)
            paint.setShadowLayer(10*d, 0f, 2*d, Color.argb(160, 0, 0, 0))
            canvas.drawRoundRect(rect, 26*d, 26*d, paint)
            paint.clearShadowLayer()
            paint.style = Paint.Style.STROKE; paint.strokeWidth = 1.1f*d
            paint.shader = LinearGradient(0f, 0f, w, 0f,
                intArrayOf(cyan, violet, Color.rgb(67, 106, 218)),
                null, Shader.TileMode.CLAMP)
            paint.alpha = 190
            canvas.drawRoundRect(rect, 26*d, 26*d, paint)
            paint.shader = null
            paint.style = Paint.Style.FILL; paint.alpha = 255

            // Proprietary single blue-violet floating energy globe.
            val x = 47*d
            val y = h*.5f
            val radius = (17.0 + if (speaking) 2.7*sin(t*8) else 1.0*sin(t*2))
                .toFloat()*d
            val grad = android.graphics.RadialGradient(
                x-4*d, y-5*d, radius*1.9f,
                intArrayOf(cyan, Color.rgb(91, 83, 222),
                    Color.argb(130, 94, 42, 164), Color.TRANSPARENT),
                null, Shader.TileMode.CLAMP)
            paint.shader = grad
            canvas.drawCircle(x, y, radius*1.9f, paint)
            paint.shader = null
            paint.color = if (currentState == "YOU SPEAKING") cyan else violet
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 1.5f*d
            val path = Path()
            for (i in 0..90) {
                val angle = i * Math.PI * 2.0 / 90.0
                val r = radius * (1 + .065*sin(3*angle+t*1.45))
                val xx = x + (cos(angle)*r).toFloat()
                val yy = y + (sin(angle)*r).toFloat()
                if (i==0) path.moveTo(xx, yy) else path.lineTo(xx, yy)
            }
            path.close()
            canvas.drawPath(path, paint)
            paint.style = Paint.Style.FILL

            paint.typeface = android.graphics.Typeface.create(
                "sans-serif-medium", android.graphics.Typeface.BOLD)
            paint.color = white; paint.textSize = 15*d
            canvas.drawText("BACY-10", 81*d, 38*d, paint)
            paint.typeface = android.graphics.Typeface.create("sans-serif", 0)
            paint.color = text; paint.textSize = 11*d
            val subtitle = when(currentState) {
                "YOU SPEAKING" -> "I'm listening..."
                "AI SPEAKING" -> "Speaking to you"
                "CONNECTING" -> "Connecting to voice"
                "DISCONNECTED" -> "Tap to reconnect"
                "WAKE" -> "Hey Bro — I'm here"
                else -> "Your assistant is ready"
            }
            canvas.drawText(subtitle, 81*d, 57*d, paint)

            // Moving slim voice lights are BACY-10's own identity.
            for (i in 0..3) {
                val energy = (1.0+sin(t*(if (speaking) 8 else 3)+i*.8))*.5
                val height = (3 + energy*11).toFloat()*d
                paint.color = if (i%2==0) cyan else violet
                canvas.drawRoundRect(RectF(
                    w-(78-i*11)*d, h*.50f-height,
                    w-(74-i*11)*d, h*.50f+height),
                    2*d, 2*d, paint)
            }
            paint.color = text; paint.textSize = 21*d
            canvas.drawText("×", w-32*d, h*.5f+7*d, paint)
            if (!stopped) postInvalidateDelayed(44)
        }
        override fun onTouchEvent(event: MotionEvent): Boolean {
            if (event.action == MotionEvent.ACTION_UP) {
                val density = resources.displayMetrics.density
                if (event.x > width-47*density) {
                    hide(this@BacyCompactOverlayService)
                } else {
                    hide(this@BacyCompactOverlayService)
                    val open = Intent(this@BacyCompactOverlayService,
                        MainActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or
                            Intent.FLAG_ACTIVITY_SINGLE_TOP)
                        putExtra("bacy10_wake", true)
                    }
                    try { startActivity(open) } catch (_: Exception) {}
                }
            }
            return true
        }
        override fun onDetachedFromWindow() {
            stopped=true; super.onDetachedFromWindow()
        }
    }
}
'''

def one(p: Path, old: str, new: str) -> None:
    s=p.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1: raise RuntimeError(f"v27 anchor mismatch: {p}, count={n}, {old[:90]!r}")
    p.write_text(s.replace(old,new,1),encoding="utf-8")

def apply(root: Path) -> None:
    mobile=root/"mobile"
    native=mobile/"android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    (native/"BacyCompactOverlayService.kt").write_text(OVERLAY,encoding="utf-8")
    manifest=mobile/"android/app/src/main/AndroidManifest.xml"
    one(manifest,'        <service android:name=".BacyVoiceService"',
        '        <service android:name=".BacyCompactOverlayService" android:exported="false" />\n'
        '        <service android:name=".BacyVoiceService"')
    one(manifest, '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />',
        '    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />\n'
        '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />')

    bridge=native/"BacyWakeListener.kt"
    one(bridge,
        'class BacyWakeListener(private val activity: Activity, engine: FlutterEngine) {',
        '''class BacyWakeListener(private val activity: Activity, engine: FlutterEngine) {
    companion object { @Volatile var current: BacyWakeListener? = null }
    fun emitWakeIfAttached(): Boolean {
        val attached = sink != null
        emitWake()
        return attached
    }''')
    one(bridge, '''    init {
        EventChannel(engine.dartExecutor.binaryMessenger, "bacy10/wake_events")''',
        '''    init {
        current = this
        EventChannel(engine.dartExecutor.binaryMessenger, "bacy10/wake_events")''')
    one(bridge,'''    fun stop() {
        sink = null
    }''',
        '''    fun stop() {
        if (current === this) current = null
        sink = null
    }''')
    one(bridge,'                        "startWake" -> {',
        '''                        "floatingPermission" -> {
                            result.success(BacyCompactOverlayService.permitted(activity))
                        }
                        "requestFloatingPermission" -> {
                            if (!BacyCompactOverlayService.permitted(activity)) {
                                activity.startActivity(Intent(
                                    android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                    android.net.Uri.parse("package:" + activity.packageName)))
                                result.success("Allow display over other apps for BACY-10.")
                            } else result.success("Floating BACY-10 is already allowed.")
                        }
                        "setFloatingStatus" -> {
                            val state = call.argument<String>("state") ?: "LISTENING"
                            BacyCompactOverlayService.update(activity, state)
                            result.success(true)
                        }
                        "startWake" -> {''')
    one(bridge, '''                                "voiceServiceRunning" to BacyVoiceService.running))''',
        '''                                "voiceServiceRunning" to BacyVoiceService.running,
                                "floatingPanelAllowed" to BacyCompactOverlayService.permitted(activity)))''')

    wake=native/"BacyWakeService.kt"
    s=wake.read_text(encoding="utf-8")
    start=s.index("    private fun wake() {")
    end=s.index("    private fun listen() {",start)
    s=s[:start]+'''    private fun wake() {
        if (stopping) return
        voiceCallActive = true
        stopping = true
        speech?.cancel()
        // Wake phrase displays only BACY-10's capsule, not a full Activity.
        val displayed = BacyCompactOverlayService.show(this, "WAKE")
        val forwarded = BacyWakeListener.current?.emitWakeIfAttached() == true
        if (!displayed || !forwarded) {
            // Cold/killed Flutter cannot receive a wake callback. Offer
            // a user-tappable notice instead of pretending voice connected.
            val expand = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
                putExtra("bacy10_wake", true)
            }
            val notice = Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle("BACY-10 heard Hey Bro")
                .setContentText("Tap to open the voice connection")
                .setContentIntent(PendingIntent.getActivity(this, 4003, expand,
                    PendingIntent.FLAG_UPDATE_CURRENT or
                        PendingIntent.FLAG_IMMUTABLE))
                .setAutoCancel(true).build()
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.notify(NOTICE+1, notice)
        }
        stopSelf()
    }

'''+s[end:]
    wake.write_text(s,encoding="utf-8")

    main=native/"MainActivity.kt"
    one(main,'''    override fun onResume() {
        super.onResume()''',
        '''    override fun onResume() {
        super.onResume()
        BacyCompactOverlayService.hide(this)''')
    one(main,'    override fun onRequestPermissionsResult(',
        '''    override fun onStop() {
        // Home button keeps the existing WebRTC call alive, with a tiny UI.
        if (BacyVoiceService.running)
            BacyCompactOverlayService.show(this, "LISTENING")
        super.onStop()
    }

    override fun onRequestPermissionsResult(''')

    ctrl=mobile/"lib/controllers/app_ctrl.dart"
    one(ctrl,'    session.addListener(_handleSessionChange);',
        '''    session.addListener(_handleSessionChange);
    room.addListener(_syncCompactSpeechStatus);
    session.agent.addListener(_syncCompactSpeechStatus);''')
    one(ctrl,'    session.removeListener(_handleSessionChange);',
        '''    session.removeListener(_handleSessionChange);
    room.removeListener(_syncCompactSpeechStatus);
    session.agent.removeListener(_syncCompactSpeechStatus);''')
    one(ctrl,'  sdk.ConnectionState _lastConnectionState = sdk.ConnectionState.disconnected;',
        '''  String _lastCompactStatus = '';

  void _syncCompactSpeechStatus() {
    if (_hasCleanedUp) return;
    final state = session.connectionState != sdk.ConnectionState.connected
        ? 'DISCONNECTED'
        : room.localParticipant?.isSpeaking == true
            ? 'YOU SPEAKING'
            : session.agent.agentState == sdk.AgentState.speaking
                ? 'AI SPEAKING' : 'LISTENING';
    if (_lastCompactStatus == state) return;
    _lastCompactStatus = state;
    try {
      unawaited(const MethodChannel('bacy10/assistant')
          .invokeMethod<bool>('setFloatingStatus', {'state': state}));
    } catch (_) {}
  }

  sdk.ConnectionState _lastConnectionState = sdk.ConnectionState.disconnected;''')
    one(ctrl,'    final state = session.connectionState;\n    // The Session also notifies',
        '    final state = session.connectionState;\n    _syncCompactSpeechStatus();\n    // The Session also notifies')

    welcome=mobile/"lib/screens/welcome_screen.dart"
    one(welcome,"      final active = current?['wakeServiceRunning'] == true;",
        """      final active = current?['wakeServiceRunning'] == true;
      final floating = current?['floatingPanelAllowed'] == true;""")
    one(welcome,"            '\\nWake listening: ' + (active ? 'Running' : 'Not running') +",
        "            '\\nWake listening: ' + (active ? 'Running' : 'Not running') +\n"
        "            '\\nFloating voice: ' + (floating ? 'Allowed' : 'Needs permission') +")
    one(welcome,'''          actions: [
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try {
                  await _native.invokeMethod<String>('requestWakePermissions');''',
        '''          actions: [
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try {
                  await _native.invokeMethod<String>('requestFloatingPermission');
                } catch (_) {}
              },
              child: const Text('Floating voice'),
            ),
            TextButton(
              onPressed: () async {
                Navigator.pop(dialog);
                try {
                  await _native.invokeMethod<String>('requestWakePermissions');''')
    one(mobile/"pubspec.yaml","version: 2.6.0+30","version: 2.7.0+31")
    (root/"agent/tests/test_floating_capsule.py").write_text('''from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_native_floating_bacy10_ui():
    s=(ROOT/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/BacyCompactOverlayService.kt').read_text()
    assert 'TYPE_APPLICATION_OVERLAY' in s
    assert 'Settings.canDrawOverlays' in s
    assert 'Gravity.BOTTOM' in s
    assert '(92 * density)' in s
def test_hotword_does_not_launch_full_activity():
    s=(ROOT/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/BacyWakeService.kt').read_text()
    a=s.index('private fun wake()')
    b=s.index('private fun listen()',a)
    assert 'BacyCompactOverlayService.show' in s[a:b]
    assert 'startActivity(intent)' not in s[a:b]
def test_home_press_keeps_call_and_small_overlay():
    s=(ROOT/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/MainActivity.kt').read_text()
    assert 'BacyVoiceService.running' in s
    assert 'BacyCompactOverlayService.show(this, "LISTENING")' in s
''',encoding="utf-8")
