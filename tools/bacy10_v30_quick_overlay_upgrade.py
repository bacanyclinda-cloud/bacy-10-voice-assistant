"""BACY-10 v3.0: launch directly into a floating voice bar, not full-screen Flutter.

A transparent launcher shows the existing overlay. Android first-time permissions
and an explicit '+' action may open the full app. Never fake an active connection.
"""
from pathlib import Path

LAUNCHER = r'''package com.livekit.example.VoiceAssistantFlutter

import android.app.Activity
import android.content.Intent
import android.os.Bundle

/** App-icon entry point. Keep the Home screen visible behind BACY-10. */
class BacyOverlayLauncherActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (BacyCompactOverlayService.permitted(this)) {
            val active = BacyVoiceService.running
            BacyCompactOverlayService.show(
                this, if (active) "LISTENING" else "DISCONNECTED")
            if (!active) BacyWakeListener.current?.emitWakeIfAttached()
        } else {
            // One-time Android permissions and connection recovery need a UI.
            startActivity(Intent(this, MainActivity::class.java).apply {
                putExtra("bacy10_setup", true)
                addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
            })
        }
        finish()
        @Suppress("DEPRECATION")
        overridePendingTransition(0, 0)
    }
}
'''

def once(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        raise RuntimeError(f"BACY-10 quick launcher anchor mismatch ({text.count(before)}): {path}: {before[:70]!r}")
    path.write_text(text.replace(before, after, 1), encoding="utf-8")

def apply(root: Path) -> None:
    native = root / "mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant"
    manifest = root / "mobile/android/app/src/main/AndroidManifest.xml"
    (native / "BacyOverlayLauncherActivity.kt").write_text(LAUNCHER, encoding="utf-8")
    main_launcher = '''            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
'''
    once(manifest, main_launcher, "")
    once(manifest, '''        <!-- Don't delete the meta-data below.''', '''        <activity
            android:name=".BacyOverlayLauncherActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:excludeFromRecents="true"
            android:noHistory="true"
            android:theme="@android:style/Theme.Translucent.NoTitleBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        <!-- Don't delete the meta-data below.''')

    bar = native / "BacyCompactOverlayService.kt"
    once(bar, '(92 * density).toInt()', '(79 * density).toInt()')
    once(bar, 'y = (28 * density).toInt()', 'y = (17 * density).toInt()')
    once(bar, 'private val cyan = Color.rgb(63, 202, 255)',
         'private val cyan = Color.rgb(38, 130, 244)')
    once(bar, 'private val violet = Color.rgb(176, 115, 254)',
         'private val violet = Color.rgb(93, 119, 241)')
    once(bar, 'private val white = Color.rgb(240, 246, 255)',
         'private val white = Color.rgb(31, 43, 63)')
    once(bar, 'private val text = Color.rgb(160, 173, 205)',
         'private val text = Color.rgb(82, 103, 135)')
    once(bar, 'paint.color = Color.rgb(9, 12, 29)',
         'paint.color = Color.rgb(249, 251, 255)')
    once(bar, 'paint.setShadowLayer(10*d, 0f, 2*d, Color.argb(160, 0, 0, 0))',
         'paint.setShadowLayer(13*d, 0f, 3*d, Color.argb(85, 29, 48, 89))')
    once(bar, '''intArrayOf(cyan, violet, Color.rgb(67, 106, 218)),''',
         '''intArrayOf(Color.rgb(235, 240, 255), Color.rgb(198, 215, 252), Color.rgb(233, 226, 253)),''')

    start = bar.read_text(encoding="utf-8")
    a = start.index('            // Proprietary single blue-violet floating energy globe.')
    b = start.index('            if (!stopped) postInvalidateDelayed(44)', a)
    draw = '''            val midY = h * .5f
            // '+' expands the full app ONLY on deliberate owner action.
            paint.color = text
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 2.4f*d
            paint.strokeCap = Paint.Cap.ROUND
            canvas.drawLine(34*d, midY-9*d, 34*d, midY+9*d, paint)
            canvas.drawLine(25*d, midY, 43*d, midY, paint)
            paint.style = Paint.Style.FILL

            paint.typeface = android.graphics.Typeface.create("sans-serif-medium", 0)
            paint.textSize = 16*d
            paint.color = white
            val label = when (currentState) {
                "DISCONNECTED" -> "Connect BACY-10"
                "CONNECTING" -> "Connecting..."
                "WAKE" -> "Hey Bro"
                else -> "Ask BACY-10"
            }
            canvas.drawText(label, 61*d, midY+6*d, paint)

            // Audio reactive bars: owner blue, assistant violet.
            val waveformX = w-140*d
            for (i in 0..4) {
                val phase = t*(if (speaking) 11.0 else 2.3)+i*.9
                val height = (4 + (if (speaking) 12 else 3) *
                    (.5+.5*sin(phase))).toFloat()*d
                paint.color = if (currentState == "AI SPEAKING") violet else cyan
                canvas.drawRoundRect(RectF(
                    waveformX+i*9*d, midY-height, waveformX+(i*9+3)*d,
                    midY+height), 2*d, 2*d, paint)
            }
            // Microphone within blue circular button.
            val micX = w-39*d
            paint.color = Color.rgb(181, 218, 255)
            canvas.drawCircle(micX, midY, 25*d, paint)
            paint.color = Color.rgb(28, 90, 178)
            canvas.drawRoundRect(RectF(micX-5*d, midY-12*d,
                micX+5*d, midY+5*d), 5*d, 5*d, paint)
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 1.8f*d
            canvas.drawArc(RectF(micX-10*d, midY-6*d,
                micX+10*d, midY+12*d), 0f, 180f, false, paint)
            canvas.drawLine(micX, midY+12*d, micX, midY+17*d, paint)
            canvas.drawLine(micX-5*d, midY+17*d, micX+5*d, midY+17*d, paint)
            paint.style = Paint.Style.FILL
'''
    bar.write_text(start[:a] + draw + start[b:], encoding="utf-8")
    touch = '''        override fun onTouchEvent(event: MotionEvent): Boolean {
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
        }'''
    revised_touch = '''        private var downY = 0f
        override fun onTouchEvent(event: MotionEvent): Boolean {
            val density = resources.displayMetrics.density
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> { downY = event.y; return true }
                MotionEvent.ACTION_UP -> {
                    // Swipe down to dismiss, without stopping the call.
                    if (event.y - downY > 25*density) {
                        hide(this@BacyCompactOverlayService)
                        return true
                    }
                    val expand = event.x < 58*density
                    val mic = event.x > width-80*density
                    if (expand || (mic && !BacyVoiceService.running &&
                            BacyWakeListener.current?.emitWakeIfAttached() != true)) {
                        // Full screen ONLY for explicit expand or reconnect.
                        hide(this@BacyCompactOverlayService)
                        val open = Intent(this@BacyCompactOverlayService,
                            MainActivity::class.java).apply {
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or
                                Intent.FLAG_ACTIVITY_SINGLE_TOP)
                            putExtra("bacy10_wake", true)
                        }
                        try { startActivity(open) } catch (_: Exception) {}
                    } else if (mic && !BacyVoiceService.running) {
                        currentState = "CONNECTING"
                        invalidate()
                    }
                    return true
                }
            }
            return true
        }'''
    once(bar, touch, revised_touch)
    wake = native / "BacyWakeService.kt"
    once(wake, '''        val displayed = BacyCompactOverlayService.show(this, "WAKE")
        val forwarded = BacyWakeListener.current?.emitWakeIfAttached() == true''',
         '''        val forwarded = BacyWakeListener.current?.emitWakeIfAttached() == true
        val displayed = BacyCompactOverlayService.show(
            this, if (forwarded || BacyVoiceService.running) "WAKE" else "DISCONNECTED")''')

    old_test = root / "agent/tests/test_floating_capsule.py"
    once(old_test, "assert '(92 * density)' in s", "assert '(79 * density)' in s")
    pubspec = root / "mobile/pubspec.yaml"
    once(pubspec, 'version: 2.9.0+33', 'version: 3.0.0+34')

    (root / "agent/tests/test_quick_overlay.py").write_text('''from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]/'mobile/android/app/src/main'
NS='{http://schemas.android.com/apk/res/android}'

def test_app_icon_opens_only_overlay():
    root=ET.parse(ROOT/'AndroidManifest.xml').getroot()
    activities=root.find('application').findall('activity')
    launcher=[]
    for act in activities:
        for filt in act.findall('intent-filter'):
            actions=[a.get(NS+'name') for a in filt.findall('action')]
            cats=[a.get(NS+'name') for a in filt.findall('category')]
            if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in cats:
                launcher.append(act.get(NS+'name'))
    assert launcher == ['.BacyOverlayLauncherActivity']
    src=(ROOT/'kotlin/com/livekit/example/VoiceAssistant/BacyOverlayLauncherActivity.kt').read_text()
    assert 'BacyCompactOverlayService.show' in src
    assert 'if (BacyCompactOverlayService.permitted(this))' in src
    assert 'BacyVoiceService.running' in src

def test_light_compact_bar_and_explicit_expand():
    src=(ROOT/'kotlin/com/livekit/example/VoiceAssistant/BacyCompactOverlayService.kt').read_text()
    assert 'Ask BACY-10' in src
    assert 'Color.rgb(249, 251, 255)' in src
    assert 'Gravity.BOTTOM' in src
    assert 'val expand = event.x < 58*density' in src
    assert 'TYPE_APPLICATION_OVERLAY' in src
    assert 'version: 3.0.0+34' in (ROOT.parents[3]/'pubspec.yaml').read_text()
''',encoding='utf-8')
