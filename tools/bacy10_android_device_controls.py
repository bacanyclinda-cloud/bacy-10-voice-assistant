"""Expand native Android phone commands while keeping consent and system controls."""
from pathlib import Path

KOTLIN_BRANCH = r'''
                        "deviceAction" -> {
                            val action = call.argument<String>("action")?.trim()?.lowercase(Locale.ROOT).orEmpty()
                            val message: String = when (action) {
                                "list_apps" -> {
                                    val query = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                                    val apps = packageManager.queryIntentActivities(query, 0)
                                        .map { it.loadLabel(packageManager).toString().trim() }
                                        .filter { it.isNotBlank() }.distinct().sorted().take(200)
                                    if (apps.isEmpty) "Android did not expose any installed launchable apps."
                                    else "Installed apps: " + apps.joinToString(", ")
                                }
                                "torch" -> {
                                    val on = call.argument<Boolean>("enabled") == true
                                    val camera = getSystemService(android.content.Context.CAMERA_SERVICE)
                                        as android.hardware.camera2.CameraManager
                                    val flash = camera.cameraIdList.firstOrNull {
                                        camera.getCameraCharacteristics(it).get(
                                            android.hardware.camera2.CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
                                    }
                                    if (flash == null) "No available flashlight on this phone."
                                    else if (android.os.Build.VERSION.SDK_INT >= 23 &&
                                        checkSelfPermission(android.Manifest.permission.CAMERA) !=
                                        android.content.pm.PackageManager.PERMISSION_GRANTED) {
                                        requestPermissions(arrayOf(android.Manifest.permission.CAMERA), 3123)
                                        "Please allow BACY-10 camera permission, then ask again to toggle the flashlight."
                                    } else {
                                        camera.setTorchMode(flash, on)
                                        if (on) "Flashlight on." else "Flashlight off."
                                    }
                                }
                                "alarm" -> {
                                    val hour = call.argument<Int>("hour") ?: -1
                                    val minute = call.argument<Int>("minute") ?: -1
                                    if (hour !in 0..23 || minute !in 0..59) "Please give a valid time."
                                    else {
                                        val intent = Intent(android.provider.AlarmClock.ACTION_SET_ALARM)
                                        intent.putExtra(android.provider.AlarmClock.EXTRA_HOUR, hour)
                                        intent.putExtra(android.provider.AlarmClock.EXTRA_MINUTES, minute)
                                        intent.putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, false)
                                        startActivity(intent)
                                        "Opened the clock to set an alarm. Confirm it if prompted."
                                    }
                                }
                                "timer" -> {
                                    val seconds = call.argument<Int>("seconds") ?: 0
                                    if (seconds < 1 || seconds > 86400) "Choose a timer from 1 second to 24 hours."
                                    else {
                                        val intent = Intent(android.provider.AlarmClock.ACTION_SET_TIMER)
                                        intent.putExtra(android.provider.AlarmClock.EXTRA_LENGTH, seconds)
                                        intent.putExtra(android.provider.AlarmClock.EXTRA_SKIP_UI, false)
                                        startActivity(intent)
                                        "Opened the clock to set a timer. Confirm it if prompted."
                                    }
                                }
                                "show_alarms" -> {
                                    startActivity(Intent(android.provider.AlarmClock.ACTION_SHOW_ALARMS))
                                    "Opened the alarm list."
                                }
                                "settings" -> {
                                    val section = call.argument<String>("section")?.trim()?.lowercase(Locale.ROOT).orEmpty()
                                    val uri = when (section) {
                                        "wifi", "wi-fi", "internet" -> android.provider.Settings.ACTION_WIFI_SETTINGS
                                        "bluetooth" -> android.provider.Settings.ACTION_BLUETOOTH_SETTINGS
                                        "sound", "volume" -> android.provider.Settings.ACTION_SOUND_SETTINGS
                                        "display", "brightness" -> android.provider.Settings.ACTION_DISPLAY_SETTINGS
                                        "location", "gps" -> android.provider.Settings.ACTION_LOCATION_SOURCE_SETTINGS
                                        "apps" -> android.provider.Settings.ACTION_APPLICATION_SETTINGS
                                        "battery" -> android.provider.Settings.ACTION_BATTERY_SAVER_SETTINGS
                                        "nfc" -> android.provider.Settings.ACTION_NFC_SETTINGS
                                        "notifications" -> android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS
                                        "accessibility" -> android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS
                                        "airplane" -> android.provider.Settings.ACTION_AIRPLANE_MODE_SETTINGS
                                        else -> android.provider.Settings.ACTION_SETTINGS
                                    }
                                    startActivity(Intent(uri))
                                    "Opened Android settings. Change protected settings on the system screen."
                                }
                                "volume" -> {
                                    val percent = call.argument<Int>("percent") ?: -1
                                    if (percent !in 0..100) "Specify a media volume from zero to one hundred."
                                    else {
                                        val mgr = getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
                                        val max = mgr.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC)
                                        mgr.setStreamVolume(android.media.AudioManager.STREAM_MUSIC, max * percent / 100, 0)
                                        "Set media volume to " + percent.toString() + " percent."
                                    }
                                }
                                "media" -> {
                                    val mode = call.argument<String>("media_command")?.lowercase(Locale.ROOT).orEmpty()
                                    val code = when (mode) {
                                        "play" -> android.view.KeyEvent.KEYCODE_MEDIA_PLAY
                                        "pause" -> android.view.KeyEvent.KEYCODE_MEDIA_PAUSE
                                        "next" -> android.view.KeyEvent.KEYCODE_MEDIA_NEXT
                                        "previous" -> android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS
                                        else -> 0
                                    }
                                    if (code == 0) "Supported media actions: play, pause, next, previous."
                                    else {
                                        val mgr = getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
                                        mgr.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, code))
                                        mgr.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, code))
                                        "Requested " + mode + " from the active music app."
                                    }
                                }
                                "dial" -> {
                                    val number = call.argument<String>("number")?.trim().orEmpty()
                                    if (!number.matches(Regex("[+0-9() -]{3,24}"))) "Provide a valid phone number."
                                    else {
                                        startActivity(Intent(Intent.ACTION_DIAL,
                                            android.net.Uri.parse("tel:" + android.net.Uri.encode(number))))
                                        "Opened the dialer. Review the number and tap Call."
                                    }
                                }
                                "sms" -> {
                                    val number = call.argument<String>("number")?.trim().orEmpty()
                                    val body = call.argument<String>("message")?.take(1600).orEmpty()
                                    if (!number.matches(Regex("[+0-9() -]{3,24}")) || body.isEmpty()) {
                                        "Provide a recipient number and message."
                                    } else {
                                        val intent = Intent(Intent.ACTION_SENDTO,
                                            android.net.Uri.parse("smsto:" + android.net.Uri.encode(number)))
                                        intent.putExtra("sms_body", body)
                                        startActivity(intent)
                                        "Opened an SMS draft. Review it and tap Send."
                                    }
                                }
                                "website" -> {
                                    val url = call.argument<String>("url")?.trim().orEmpty()
                                    if ((!url.startsWith("https://") && !url.startsWith("http://")) || url.length > 1200) {
                                        "Give me an HTTP or HTTPS website URL."
                                    } else {
                                        startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
                                        "Opened the link in your browser."
                                    }
                                }
                                else -> "This phone action is not supported on this device."
                            }
                            result.success(message)
                        }
'''

PY_TOOLS = r'''
    @function_tool()
    async def list_installed_android_apps(self, context: RunContext) -> str:
        """List the installed launchable apps visible on the owner's phone."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "list_apps"})).get("message"))

    @function_tool()
    async def set_phone_torch(self, context: RunContext, enabled: bool) -> str:
        """Turn the physical Android flashlight on or off."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "torch", "enabled": enabled})).get("message"))

    @function_tool()
    async def set_phone_alarm(self, context: RunContext, hour: int, minute: int) -> str:
        """Open phone clock to set alarm at local 24-hour time.
        Args:
            hour: Hour zero to twenty-three.
            minute: Minute zero to fifty-nine.
        """
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "alarm", "hour": hour, "minute": minute})).get("message"))

    @function_tool()
    async def set_phone_timer(self, context: RunContext, seconds: int) -> str:
        """Open phone clock to set countdown timer in seconds, maximum one day."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "timer", "seconds": seconds})).get("message"))

    @function_tool()
    async def show_phone_alarms(self, context: RunContext) -> str:
        """Open phone alarm list for the owner to review."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "show_alarms"})).get("message"))

    @function_tool()
    async def open_device_settings(self, context: RunContext, section: str = "") -> str:
        """Open system settings for WiFi, Bluetooth, sound, display, location, apps, battery, NFC and more. Protected toggles need owner confirmation."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "settings", "section": section})).get("message"))

    @function_tool()
    async def set_media_volume(self, context: RunContext, percent: int) -> str:
        """Set media audio volume on phone from zero to one hundred percent."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "volume", "percent": percent})).get("message"))

    @function_tool()
    async def control_phone_media(self, context: RunContext, media_command: str) -> str:
        """Send play, pause, next or previous button to active phone media app.
        Args:
            media_command: play, pause, next or previous
        """
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "media", "media_command": media_command})).get("message"))

    @function_tool()
    async def open_phone_dialer(self, context: RunContext, phone_number: str) -> str:
        """Open Android dialer with entered number; owner confirms call."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "dial", "number": phone_number})).get("message"))

    @function_tool()
    async def draft_sms_message(self, context: RunContext, phone_number: str, message: str) -> str:
        """Create an Android SMS draft for owner to review and send."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "sms", "number": phone_number, "message": message})).get("message"))

    @function_tool()
    async def open_website_on_phone(self, context: RunContext, url: str) -> str:
        """Open an HTTP or HTTPS website in owner's Android browser."""
        return str((await self._phone("bacy10.phone", {"action": "device", "operation": "website", "url": url})).get("message"))
'''

def apply(root: Path) -> None:
    mobile = root / "mobile"
    kotlin = mobile / "android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/MainActivity.kt"
    k = kotlin.read_text(encoding="utf-8")
    needle = '                        "openCamera" -> {'
    if k.count(needle) != 1: raise RuntimeError("Missing Android phone action insertion point")
    kotlin.write_text(k.replace(needle, KOTLIN_BRANCH + '\n' + needle, 1), encoding="utf-8")
    manifest = mobile / "android/app/src/main/AndroidManifest.xml"
    xml = manifest.read_text(encoding="utf-8")
    permission = '<uses-permission android:name="com.android.alarm.permission.SET_ALARM" />'
    if permission not in xml:
        xml = xml.replace('</manifest>', '    ' + permission + '\n</manifest>')
    manifest.write_text(xml, encoding="utf-8")

    ctrl = mobile / "lib/controllers/app_ctrl.dart"
    dart = ctrl.read_text(encoding="utf-8")
    needle = """          default:
            message = 'Unsupported phone action.';"""
    replacement = """          case 'device':
            final forwarded = Map<String, dynamic>.from(command);
            forwarded['action'] = command['operation'];
            message = await channel.invokeMethod<String>('deviceAction', forwarded);
            break;
""" + needle
    if dart.count(needle) != 1: raise RuntimeError("Missing Dart RPC switch location")
    ctrl.write_text(dart.replace(needle, replacement, 1), encoding="utf-8")

    toolfile = root / "agent/src/phone_tools.py"
    tooltext = toolfile.read_text(encoding="utf-8")
    needle = '            self.forget_about_me,\n'
    extra = '''            self.list_installed_android_apps,
            self.set_phone_torch,
            self.set_phone_alarm,
            self.set_phone_timer,
            self.show_phone_alarms,
            self.open_device_settings,
            self.set_media_volume,
            self.control_phone_media,
            self.open_phone_dialer,
            self.draft_sms_message,
            self.open_website_on_phone,
'''
    if tooltext.count(needle) != 1: raise RuntimeError("Missing registered phone tool list")
    tooltext = tooltext.replace(needle, needle + extra, 1)
    tooltext = tooltext.replace('            return value\n',
        '            if not value.get("ok", False):\n'
        '                raise ToolError(str(value.get("message", "The phone rejected the action.")))\n'
        '            return value\n', 1)
    toolfile.write_text(tooltext + '\n' + PY_TOOLS, encoding="utf-8")

    agent = root / "agent/src/agent.py"
    instructions = agent.read_text(encoding="utf-8")
    needle = "                        # Tools\n"
    more = """                        - List installed Android apps first when unsure of exact name.
                        - Use the native phone tool for flashlight, clock alarms, countdown timers, volume, media, dialing, messages and opening phone settings.
                        - Android protected settings may need the owner to confirm the change.
                        - Do not claim any SMS was sent, call was placed, or alarm was set unless confirmed.
                        - Phone settings are not identical to the Google Gemini default-assistant privileges.

"""
    if instructions.count(needle) != 1: raise RuntimeError("Missing agent instructions placement")
    agent.write_text(instructions.replace(needle, more + needle, 1), encoding="utf-8")
