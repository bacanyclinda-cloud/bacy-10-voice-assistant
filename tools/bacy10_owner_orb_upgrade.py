"""Owner-confirmed profile and subtle animated BACY-10 central voice orb.
Stored in the user's PRIVATE GitHub repository, not in the public APK.
Personal facts are not passwords, identity documents or banking credentials.
"""
from pathlib import Path

OWNER_PROFILE = """
BACY-10 PRIVATE OWNER CONTEXT. Refer to this only during the owner's paired voice sessions.
Keep replies natural; address the owner as bro or sir according to tone.
OWNER IDENTITY:
- Full name: Basani Welcome Silinda. Signature: BW Silinda. Previously used Bacany Clinda.
- Country: South Africa. Area: Chochocho / Bushbuckridge, Mpumalanga, near Mbombela; earlier reference near Buford Bridge, with Tshuma and Shakung nearby. Exact address not confirmed.
- Professional contact phone: 063 724 6209. Preferred contact email: bacanyclinda@gmail.com. Another provided email: basanisilinda@gmail.com.
- Girlfriend: Mari Shai, named by the owner. Family: lives with two children; names and ages not provided.
- No confirmed birthday, identity number, exact street address, parents' names or children's names; don't invent them.
EDUCATION:
- Matric completed 2024 with a Bachelor's pass in South Africa.
- Seven reported matric subjects: Pure Mathematics, Physical Sciences, Life Sciences, Agricultural Sciences, Religion Studies, Sepedi Home Language, English First Additional Language.
- Presently a UNISA distance-learning student in teacher education / Foundation Phase focus; don't assert a specific awarded qualification.
- Modules discussed: INS1502, GRT1501, IED1501, PSC1501, CAD1501, EST1501.
- Education interests: Grade R, early childhood development, foundation phase teaching, educational psychology, mathematics education and teaching methods.
- Also helped with Grade 11 mathematics Paper 2/trigonometry, English Paper 2, Life Sciences, Agricultural Sciences, Physical Sciences, Sepedi and Life Orientation exam resources.
EXPERIENCE AND WORK GOALS:
- Worked in an internet café, assisting people with computers, internet access and customer needs; knows basic computer software.
- Practical farming experience outside formal company employment. Familiar with general manual/physical work.
- Has been seeking South African entry-level jobs around Bushbuckridge, Acornhoek, Hazyview and Mbombela, including retail, cashier, clothing shops, cleaning, hardware, general worker and customer support roles.
- Interested in entrepreneurship, software products for companies, technology employment and presenting working prototypes to businesses such as Rain.
BUSINESS AND TECHNOLOGY PROJECTS:
- BACY-10 / BACY05TEN: private Jarvis-style personal voice and computer assistant with LiveKit, Gemini/other AI models, Python, Flutter, Kotlin, Flutter/Android, Next.js, voice and camera, browser/PC operations, web search, secure pairing, multiple intelligence modes and computer/phone control ambitions.
- Loop Secure / Loop phone / earlier Bacy Enterprise: financed Android phone device management. Device Owner provisioning by Android setup QR or USB ADB, offline repayment countdown, time-based device lock, factory reset safeguards, developer/ADB restrictions, signed automatic updates, remote administration, temporary unlock durations of five minutes, thirty minutes and twenty-four hours, keep emergency calls/essential Settings, Wi-Fi, banking apps and OTP messages available.
- Loop Secure commercial work: Rain South Africa proposals; possible price R595 per month and optional R8,000 one-time setup, financing/payments and in-app payment workflows. Has discussed EFT admin verification, Pay@ references, OneVoucher, iKhokha integration difficulties, recurring payments and payment history. No assumption that all integrations are live.
- MBMF: native Android Admin and Client mobile-device financing suite using Kotlin, Jetpack Compose, WorkManager, Room, DevicePolicyManager, Supabase and secure HTTPS, with customer registration done by admin, QR enrollment, repayments and reports.
- ZORA South Africa: planned large multi-category e-commerce business, Supabase backend, catalog of thousands of products, admin operations, mobile-first design, and Brevo messaging.
- ENZO Tools: Windows phone servicing application for diagnostics and device provisioning, Android ADB, Qualcomm, MediaTek and Unisoc integrations; proposed not confirmed fully built.
- XM MT5 automated forex robot experiments focused on EURUSD, demo trading, rapid entries and small-profits strategy. Results not verified.
- Also explored VPN sharing between Android phones, laptop-linked assistant, Python/JS dashboards, construction concrete slab quotations, local/global electronics and retail suppliers, business ideas and academic study guides.
TOOLS, TECH AND USER PREFERENCES:
- Uses Android phone and a Windows laptop, often phone-only; previous laptop HP Celeron N3060, 4 GB RAM.
- Has used or explored GitHub, GitHub Actions, Cloudflare Workers, Flutter, Kotlin, Python, Node.js, Next.js, LiveKit, uv, Supabase, Android Studio/Gradle, Lovable, Canva, Figma, Playwright, Gemini, ChatGPT and Codex.
- Wants a powerful natural British-style voice assistant, real device actions, voice/text chat, reasoning, web research, reminders and computer/Android control.
- Likes short plain English, conversational 'bro', meaningful working results, minimal manual copying, real builds, transparent progress and no mock actions.
- UI preference for BACY-10: existing dark Android call controls and layout stay unchanged; only center voice display becomes a realistic softly moving blue-violet luminous sphere; restrained color, not cartoon, no excessive icons.
- Enjoys South African Maskandi music and has requested authentic instruments and Zulu male vocals for music creation.
- Values low-cost or free developer tools and owner control over private repositories, independent copies/backups and secure keys.
- Past details may go out of date. Ask if uncertain and never claim an untested business integration or career achievement is complete.
SECURITY:
- This context is not authorization to disclose personal data to strangers or to post it to websites.
- Treat account numbers, PINs, OTPs, CVVs, passwords, API keys, ID numbers and secret tokens as out of scope; don't store or reveal them.
- Always confirm consequential actions like messages, purchases, transactions and changing sensitive settings. Explain Android limitations when they apply.
"""

ORB_DART = r'''
import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Continuously rendered, subtle luminous sphere: not a static image or cartoon.
/// Only replaces the existing five-column voice visualizer.
class BacyVoiceOrb extends StatefulWidget {
  const BacyVoiceOrb({super.key});
  @override
  State<BacyVoiceOrb> createState() => _BacyVoiceOrbState();
}
class _BacyVoiceOrbState extends State<BacyVoiceOrb> with SingleTickerProviderStateMixin {
  late final AnimationController phase = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 6800),
  )..repeat();
  @override
  void dispose() { phase.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => Center(
    child: SizedBox(
      width: 285,
      height: 285,
      child: AnimatedBuilder(
        animation: phase,
        builder: (context, child) => CustomPaint(
          painter: _BacyOrbPainter(phase.value),
        ),
      ),
    ),
  );
}

class _BacyOrbPainter extends CustomPainter {
  final double phase;
  _BacyOrbPainter(this.phase);

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.365;
    final t = phase * math.pi * 2;
    final envelope = 0.995 + 0.018 * math.sin(t);
    final r = radius * envelope;
    final bounds = Rect.fromCircle(center: c, radius: r);

    // Restrained bloom and inner depth, with a genuinely black background.
    canvas.drawCircle(c, r * 1.31, Paint()
      ..shader = RadialGradient(colors: [
        const Color(0x144E9FCF), const Color(0x073967BD), Colors.transparent
      ]).createShader(Rect.fromCircle(center: c, radius: r * 1.31)));
    canvas.drawCircle(c, r * 1.04, Paint()
      ..shader = const RadialGradient(colors: [
        Color(0xFF152943), Color(0xFF080F1F), Color(0xFF04060B)
      ], stops: [0.0, 0.67, 1.0]).createShader(bounds));

    // Transparent flowing light filaments mimic a refractive spherical surface.
    for (var i = 0; i < 26; i++) {
      final f = (i / 25.0) * math.pi * 2.0 + t * (0.16 + (i % 4) * 0.05);
      final y = math.sin(f + math.sin(t * 0.7)) * r * (0.10 + 0.80 * (i / 26));
      final length = math.sqrt(math.max(0, r * r - y * y));
      final path = Path()..moveTo(c.dx - length, c.dy + y);
      path.cubicTo(
        c.dx - length * 0.28, c.dy + y - 23 * math.sin(t + i * 0.51),
        c.dx + length * 0.22, c.dy + y + 19 * math.cos(t * 0.7 + i),
        c.dx + length, c.dy + y,
      );
      final col = i % 6 == 0 ? const Color(0xFF8C83CE) : const Color(0xFF4E9DBF);
      canvas.drawPath(path, Paint()
        ..color = col.withValues(alpha: 0.055 + 0.05 * math.abs(math.sin(t + i)))
        ..strokeWidth = 0.5 + (i % 4) * 0.21
        ..style = PaintingStyle.stroke);
    }

    // Fine particles are sparse to avoid an artificial or busy look.
    for (var k = 0; k < 80; k++) {
      final a = k * 2.399963 + t * 0.17;
      final rr = r * math.sqrt((k + .5) / 80);
      final p = c + Offset(math.cos(a) * rr * .97, math.sin(a) * rr * .97);
      canvas.drawCircle(p, k % 10 == 0 ? 0.9 : 0.46,
        Paint()..color = const Color(0xFF93C9E7).withValues(alpha: 0.09 + (k % 6) * .014));
    }
    canvas.drawCircle(c, r * .985, Paint()
      ..shader = const SweepGradient(colors: [
        Color(0x554BA3D4), Color(0x88928AD5), Color(0xAA7ACBE3),
        Color(0x665D8BBC), Color(0x554BA3D4)
      ], stops: [0, .23, .55, .79, 1], transform: GradientRotation(.23))
          .createShader(bounds)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.25);
    canvas.drawArc(bounds, t * .16, math.pi * .58, false, Paint()
      ..color = const Color(0x449BC9D5)
      ..strokeWidth = 1.35
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4));
  }
  @override
  bool shouldRepaint(covariant _BacyOrbPainter oldDelegate) => oldDelegate.phase != phase;
}
'''

def apply(root: Path) -> None:
    src = root / "agent/src"
    (src / "owner_context.py").write_text("OWNER_PROFILE = " + repr(OWNER_PROFILE) + "\\n", encoding="utf-8")
    entry = src / "agent.py"
    agent_text = entry.read_text(encoding="utf-8")
    agent_text = agent_text.replace("from phone_tools import PhoneTools",
                                    "from phone_tools import PhoneTools\\nfrom owner_context import OWNER_PROFILE", 1)
    agent_text = agent_text.replace(
        "instructions=textwrap.dedent(", "instructions=OWNER_PROFILE + '\\n\\n' + textwrap.dedent(", 1)
    entry.write_text(agent_text, encoding="utf-8")

    mobile = root / "mobile"
    (mobile / "lib/widgets/bacy10_voice_orb.dart").write_text(ORB_DART, encoding="utf-8")
    screen = mobile / "lib/screens/agent_screen.dart"
    dart = screen.read_text(encoding="utf-8")
    dart = dart.replace("import 'dart:math' show max;", "import 'dart:math' show max;\\nimport '../widgets/bacy10_voice_orb.dart';", 1)
    before = '''                    return const components.AudioVisualizerWidget(
                      options: components.AudioVisualizerWidgetOptions(
                        barCount: 5,
                        width: 32,
                        minHeight: 32,
                        maxHeight: 320,
                        // color: Theme.of(ctx).colorScheme.primary,
                      ),
                    );'''
    if before not in dart:
        raise RuntimeError("Could not find five-bar visualizer. Left original intact.")
    dart = dart.replace(before, "                    return const BacyVoiceOrb();", 1)
    screen.write_text(dart, encoding="utf-8")

    # Owner explicitly requests the GitHub profile instead of a manual memory screen.
    welcome = mobile / "lib/screens/welcome_screen.dart"
    dart = welcome.read_text(encoding="utf-8")
    dart = dart.replace("import 'bacy10_memory_screen.dart';\\n", "", 1)
    start = dart.find("                  TextButton.icon(\\n")
    if start >= 0 and "My private memory" in dart[start:start + 450]:
        end = dart.index("                  const SizedBox(height: 22),", start)
        # Preserve surrounding spacing; remove only the editable memory control.
        dart = dart[:start] + dart[end:]
        welcome.write_text(dart, encoding="utf-8")
    memory_screen = mobile / "lib/screens/bacy10_memory_screen.dart"
    if memory_screen.exists():
        memory_screen.unlink()
