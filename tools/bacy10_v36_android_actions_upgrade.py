"""Repair Android app launching, drafts and overly broad prompt refusals.

Preserves consent for calls/messages and Android Accessibility; only owner RPC
can call these tools. No automation of scams or credential collection.
"""
from pathlib import Path

EXTRA_PY = '''
    @function_tool()
    async def compose_whatsapp_message_on_phone(self, context: RunContext, message: str) -> str:
        """Open a WhatsApp draft with a message but no chosen recipient.

        The owner selects a chat, reviews it and manually sends the message.
        """
        return str((await self._phone("bacy10.phone", {
            "action": "device", "operation": "whatsapp_compose", "body": message
        })).get("message"))
'''

def once(path,old,new):
 s=path.read_text(encoding='utf-8')
 n=s.count(old)
 if n!=1: raise RuntimeError(f"v36 Android anchor {path}: {n} for {old[:60]!r}")
 path.write_text(s.replace(old,new,1),encoding='utf-8')

def apply(root:Path):
 native=root/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/MainActivity.kt'
 once(native,'                            val lookup = requested.lowercase(Locale.ROOT)',"""                            val lookup = requested.lowercase(Locale.ROOT)
                                .removePrefix("the ").removeSuffix(" application").removeSuffix(" app")
                            if (lookup in setOf("phone", "dialer", "call", "calls")) {
                                startActivity(Intent(Intent.ACTION_DIAL))
                                result.success("Opened Phone dialer. Choose a contact or number and tap Call.")
                                return@setMethodCallHandler
                            }
                            if (lookup in setOf("messages", "sms", "text messages")) {
                                startActivity(Intent(Intent.ACTION_SENDTO,
                                    android.net.Uri.parse("smsto:")))
                                result.success("Opened Messages. Choose a recipient and review your draft.")
                                return@setMethodCallHandler
                            }
                            if (lookup in setOf("settings", "android settings")) {
                                startActivity(Intent(android.provider.Settings.ACTION_SETTINGS))
                                result.success("Opened Android settings.")
                                return@setMethodCallHandler
                            }""")
 once(native, '                                "settings" to "com.android.settings"',
 '''                                "settings" to "com.android.settings",
                                "instagram" to "com.instagram.android",
                                "tiktok" to "com.zhiliaoapp.musically",
                                "signal" to "org.thoughtcrime.securesms",
                                "discord" to "com.discord",
                                "snapchat" to "com.snapchat.android",
                                "google meet" to "com.google.android.apps.tachyon",
                                "google drive" to "com.google.android.apps.docs",
                                "google photos" to "com.google.android.apps.photos",
                                "google calendar" to "com.google.android.calendar",
                                "google contacts" to "com.google.android.contacts"''')
 once(native,'                                "whatsapp_draft" -> {',"""                                "whatsapp_compose" -> {
                                    val body=call.argument<String>("body")?.trim()?.take(1800).orEmpty()
                                    if (body.isEmpty()) "Tell me the message to draft."
                                    else {
                                        val intent=Intent(Intent.ACTION_SEND).apply {
                                            type="text/plain"
                                            putExtra(Intent.EXTRA_TEXT,body)
                                            setPackage("com.whatsapp")
                                        }
                                        try {
                                            startActivity(intent)
                                            "Opened WhatsApp message draft. Select recipient and tap Send."
                                        } catch (_: android.content.ActivityNotFoundException) {
                                            val fallback=Intent(Intent.ACTION_SEND).apply {
                                                type="text/plain"
                                                putExtra(Intent.EXTRA_TEXT,body)
                                            }
                                            startActivity(Intent.createChooser(fallback,"Choose messaging app"))
                                            "Opened the Android share sheet. Choose WhatsApp to review the draft."
                                        }
                                    }
                                }
                                "whatsapp_draft" -> {""")
 once(native,'''                                    if (!number.matches(Regex("[+0-9() -]{3,24}"))) "Provide a valid phone number."
                                    else {
                                        startActivity(Intent(Intent.ACTION_DIAL,''',
 '''                                    if (number.isNotEmpty() && !number.matches(Regex("[+0-9() -]{3,24}"))) "Provide a valid phone number."
                                    else {
                                        startActivity(Intent(Intent.ACTION_DIAL,''')
 manifest=root/'mobile/android/app/src/main/AndroidManifest.xml'
 s=manifest.read_text(encoding='utf-8')
 if s.count('<queries>')!=1: raise RuntimeError('Android queries section missing')
 if '<package android:name="com.whatsapp" />' not in s:
  s=s.replace('<queries>','<queries>\n        <package android:name="com.whatsapp" />\n        <package android:name="com.whatsapp.w4b" />\n        <package android:name="com.google.android.apps.photos" />',1)
 manifest.write_text(s,encoding='utf-8')

 tools=root/'agent/src/phone_tools.py'
 with tools.open('a',encoding='utf-8') as file:file.write('\n'+EXTRA_PY)
 once(tools,'            self.draft_whatsapp_on_phone,\n',
 '            self.draft_whatsapp_on_phone,\n            self.compose_whatsapp_message_on_phone,\n')
 once(tools,'async def open_phone_dialer(self, context: RunContext, phone_number: str)',
 'async def open_phone_dialer(self, context: RunContext, phone_number: str = "")')

 agent=root/'agent/src/agent.py'
 guidance="""                        # Reliable phone actions and helpful normal requests
                        - For ordinary programming, JavaScript, HTML, websites and practice examples, help directly and concretely. Avoid blanket keyword-based refusals.
                        - If owner says open WhatsApp, call open_android_app("WhatsApp"). If owner wants a WhatsApp draft without number, use compose_whatsapp_message_on_phone. If a recipient number is available use draft_whatsapp_on_phone.
                        - For Phone or dialer without a number, call open_android_app("Phone"). With a number, call open_phone_dialer. Do not claim a call was placed.
                        - For Messages, call open_android_app("Messages"); with a number use draft_sms_message and let owner review before sending.
                        - For Android controls, always use phone tools, never the remote browser. When an app isn't found, call list_installed_android_apps and try its exact name.
                        - For current facts and web searches call search_the_web, use readable results and cite the source where possible. Retry a browser search if direct search fails; don't invent results.
                        - Provide fictional non-collecting examples for local security awareness and login-page design practice. Never assist actual fraud, credential theft, or deceptive phishing delivery.
                        - Be helpful and concise. Don't recite policy boilerplate for harmless tasks; explain a genuine blocker briefly when needed.

"""
 once(agent,'                        # Tools\n',guidance+'                        # Tools\n')
 old='- Stay within safe, lawful, and appropriate use; decline harmful or out-of-scope requests.'
 s=agent.read_text(encoding='utf-8')
 s=s.replace(old,'- Handle coding requests on their merits, not based on alarming keywords alone. Offer non-collecting simulations for practice but do not facilitate real fraud or credential theft.')
 agent.write_text(s,encoding='utf-8')
 prompt=root/'agent/src/prompts.py'
 s=prompt.read_text(encoding='utf-8')
 s=s.replace(old,'- Assist with ordinary code and fictional local test cases. Do not facilitate real fraud or theft.')
 prompt.write_text(s,encoding='utf-8')

 (root/'agent/tests/test_android_v36.py').write_text("""from pathlib import Path
R=Path(__file__).resolve().parents[2]
def test_android_app_drafts():
 k=(R/'mobile/android/app/src/main/kotlin/com/livekit/example/VoiceAssistant/MainActivity.kt').read_text()
 assert '"whatsapp_compose" ->' in k
 assert 'setPackage("com.whatsapp")' in k
 assert 'lookup in setOf("phone", "dialer"' in k
 assert '"instagram" to "com.instagram.android"' in k
def test_phone_agent_tools():
 p=(R/'agent/src/phone_tools.py').read_text()
 a=(R/'agent/src/agent.py').read_text()
 assert "self.compose_whatsapp_message_on_phone" in p
 assert "open_android_app" in a
 assert "search_the_web" in a
 assert 'Fictional' in a or 'fictional' in a
""",encoding='utf-8')
