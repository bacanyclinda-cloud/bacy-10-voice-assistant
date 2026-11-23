"""BACY-10 kinetic pearl sculpture: a totally different 3D visual language.

No dotted sphere, cyan waves, neon purple or liquid-metal blobs. The moving
form is a translucent, faceted porcelain-glass kinetic sculpture with warm
champagne/ivory studio reflections, and reacts to real LiveKit voice states.
"""
from pathlib import Path

SCULPTURE = r'''
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';
import '../controllers/app_ctrl.dart';

/// The user's requested reference: a soft blue-to-violet inner glow with one
/// irregular, luminous cyan/purple perimeter. No plasma lines through the
/// centre and no metal, ribbons or hard spherical grid.
class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});

  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 11500),
  )..repeat();

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = context.read<sdk.Session>();
    final room = context.read<AppCtrl>().room;
    return AnimatedBuilder(
      animation: Listenable.merge([_motion, room, session.agent]),
      builder: (context, _) {
        final connected =
            session.connectionState == sdk.ConnectionState.connected;
        final userSpeaking = connected &&
            (room.localParticipant?.isSpeaking ?? false);
        final agentSpeaking =
            connected && session.agent.agentState == sdk.AgentState.speaking;
        final thinking =
            connected && session.agent.agentState == sdk.AgentState.thinking;
        final level = (room.localParticipant?.audioLevel ?? 0.0)
            .clamp(0.0, 1.0)
            .toDouble();
        final energy = userSpeaking
            ? (0.42 + level * 1.15).clamp(0.0, 1.55).toDouble()
            : agentSpeaking
                ? 0.81
                : thinking
                    ? 0.43
                    : connected ? .22 : .12;
        final status = !connected
            ? 'STANDBY'
            : userSpeaking
                ? 'YOU ARE SPEAKING'
                : agentSpeaking
                    ? 'BACY-10 IS SPEAKING'
                    : thinking ? 'PROCESSING' : 'LISTENING';

        return RepaintBoundary(
          child: Stack(
            fit: StackFit.expand,
            children: [
              CustomPaint(
                painter: _ReferenceHaloPainter(
                  phase: _motion.value,
                  energy: energy,
                ),
              ),
              Positioned(
                left: 0, right: 0, bottom: 0,
                child: Text(
                  status,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 2.4,
                    color: Color(0xFFBFD2E9),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ReferenceHaloPainter extends CustomPainter {
  const _ReferenceHaloPainter({required this.phase, required this.energy});
  final double phase;
  final double energy;

  static const cyan = Color(0xFF39C9FF);
  static const blue = Color(0xFF528BFF);
  static const violet = Color(0xFFA680FF);
  static const pink = Color(0xFFDA6CFB);

  // Soft irregular motion, comparable to the bright organic contour in the
  // reference, not a circular orbit or a waveform crossing the disc.
  double radiusAt(double angle, double time) {
    return 1.0
        + .047 * math.sin(3 * angle + time * .70)
        + .032 * math.sin(5 * angle - time * .49 + 1.0)
        + .018 * math.sin(9 * angle + time * .23 - .6)
        + .010 * math.sin(13 * angle - time * .29);
  }

  Path contour(Offset center, double radius, double time, double inset) {
    final p = Path();
    const segments = 260;
    for (var i = 0; i <= segments; i++) {
      final a = (i / segments) * math.pi * 2;
      final k = (radiusAt(a, time) - inset) * radius;
      final x = center.dx + math.cos(a) * k;
      final y = center.dy + math.sin(a) * k;
      if (i == 0) {
        p.moveTo(x, y);
      } else {
        p.lineTo(x, y);
      }
    }
    return p..close();
  }

  @override
  void paint(Canvas canvas, Size size) {
    if (size.shortestSide < 2) return;
    final time = phase * math.pi * 2;
    final centre = Offset(size.width * .5, size.height * .46);
    final baseRadius = size.shortestSide * .342;
    final radius = baseRadius *
        (1 + .016 * energy + .008 * math.sin(time * 1.5));

    final glowRect =
        Rect.fromCircle(center: centre, radius: radius * 1.56);
    canvas.drawCircle(
      centre,
      radius * 1.56,
      Paint()
        ..shader = RadialGradient(
          colors: [
            blue.withValues(alpha: .17 + .08 * energy),
            violet.withValues(alpha: .09),
            const Color(0xFF040714).withValues(alpha: .03),
            Colors.transparent,
          ],
          stops: const [0, .48, .75, 1],
        ).createShader(glowRect),
    );

    // Entire main surface is a gently shaded disc with deep optical volume,
    // fading to dark at its edge, like the supplied screenshot.
    final outline = contour(centre, radius, time, 0);
    final bodyRect = Rect.fromCircle(center: centre, radius: radius);
    canvas.drawPath(
      outline,
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(-.39, -.31),
          radius: 1.25,
          colors: [
            const Color(0xFF215BC3),
            const Color(0xFF273EA8),
            const Color(0xFF392D91),
            const Color(0xFF1D1C60),
            const Color(0xFF11143C),
          ],
          stops: const [0, .27, .53, .82, 1],
        ).createShader(bodyRect),
    );

    canvas.save();
    canvas.clipPath(outline);

    // Almost invisible layers of concentric fine gauze around the inside.
    // These create depth without the crisscross neon lines from the old UI.
    for (var index = 0; index < 45; index++) {
      final inset = .12 + index * .012;
      final ring = contour(centre, radius, time * .33 + index * .038, inset);
      canvas.drawPath(
        ring,
        Paint()
          ..color = (index.isEven ? blue : violet).withValues(
            alpha: .023 + energy * .008,
          )
          ..style = PaintingStyle.stroke
          ..strokeWidth = .55,
      );
    }

    // Natural, soft-focus blue upper light and violet lower light.
    final upper = Offset(centre.dx - radius * .33, centre.dy - radius * .28);
    canvas.drawCircle(
      upper,
      radius * .92,
      Paint()
        ..shader = RadialGradient(
          colors: [
            const Color(0xFF1F70EC).withValues(alpha: .42),
            cyan.withValues(alpha: .095),
            Colors.transparent,
          ],
          stops: const [0, .48, 1],
        ).createShader(
          Rect.fromCircle(center: upper, radius: radius * .92),
        ),
    );
    final lower = Offset(centre.dx + radius * .29, centre.dy + radius * .39);
    canvas.drawCircle(
      lower,
      radius * .84,
      Paint()
        ..shader = RadialGradient(
          colors: [
            const Color(0xFF8145E4).withValues(alpha: .39),
            pink.withValues(alpha: .12),
            Colors.transparent,
          ],
          stops: const [0, .55, 1],
        ).createShader(
          Rect.fromCircle(center: lower, radius: radius * .84),
        ),
    );

    // Sparse pinpricks in and around the lens, intentionally low-key.
    for (var n = 0; n < 27; n++) {
      final angle = n * 2.399963229728653;
      final distance = radius * (.56 + (n % 9) * .051);
      final x = centre.dx + math.cos(angle) * distance;
      final y = centre.dy + math.sin(angle) * distance;
      final op = .12 + .19 *
          (.5 + .5 * math.sin(time * 1.6 + n * .78));
      canvas.drawCircle(
        Offset(x, y), n % 5 == 0 ? 1.1 : .57,
        Paint()..color = (n.isEven ? cyan : violet).withValues(alpha: op),
      );
    }
    canvas.restore();

    // Three passes of blurred light form the ONLY main perimeter.
    // Cyan dominates the top/left; violet and magenta trace the lower edge.
    final sweep = SweepGradient(
      startAngle: 0,
      endAngle: math.pi * 2,
      colors: const [violet, pink, violet, cyan, blue, cyan, violet],
      stops: const [0, .14, .30, .53, .67, .82, 1],
      transform: GradientRotation(time * .035),
    ).createShader(bodyRect);

    for (final spread in <double>[15, 7]) {
      canvas.drawPath(
        outline,
        Paint()
          ..shader = sweep
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = spread == 15 ? 7 : 3.7
          ..maskFilter =
              MaskFilter.blur(BlurStyle.normal, spread),
      );
    }
    canvas.drawPath(
      outline,
      Paint()
        ..shader = sweep
        ..strokeWidth = 2.25 + .8 * energy
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke,
    );

    // A second delicate teal trace, offset from the primary halo,
    // echoes the slim wisp at the bottom of the supplied image.
    final accent = contour(centre, radius, time + 2.2, .016);
    canvas.drawPath(
      accent,
      Paint()
        ..color = cyan.withValues(alpha: .19 + .07 * energy)
        ..strokeWidth = .65
        ..style = PaintingStyle.stroke,
    );
  }

  @override
  bool shouldRepaint(covariant _ReferenceHaloPainter old) =>
      old.phase != phase || old.energy != energy;
}

'''

def apply(root: Path) -> None:
    dst=root/"mobile/lib/widgets/bacy_live_orb.dart"
    if not dst.exists(): raise RuntimeError("BACY-10 orb file missing")
    dst.write_text(SCULPTURE,encoding="utf-8")
    welcome=root/"mobile/lib/screens/welcome_screen.dart"
    s=welcome.read_text(encoding="utf-8")
    s=s.replace("color: const Color(0xFF05070C)","color: const Color(0xFF0B0A0B)")
    s=s.replace("const Color(0xFFBCD7EB)","const Color(0xFFF0D6BA)")
    s=s.replace("const Color(0xFF0B1521)","const Color(0xFF211710)")
    s=s.replace("const Color(0xFFBFCEDC)","const Color(0xFFD3C5B7)")
    welcome.write_text(s,encoding="utf-8")
    pal=root/"mobile/lib/ui/color_pallette.dart"
    s=pal.read_text(encoding="utf-8")
    s=s.replace("0xFF002CF2","0xFFC7996A")
    s=s.replace("0xFF070707","0xFF0B0A0B")
    s=s.replace("0xFF131313","0xFF191513")
    s=s.replace("0xFF202020","0xFF26211E")
    s=s.replace("0xFF090C17","0xFF291E18")
    pal.write_text(s,encoding="utf-8")
    version=root/"mobile/pubspec.yaml"
    s=version.read_text(encoding="utf-8")
    if "version: 1.9.0+23" not in s: raise RuntimeError("Unexpected app version")
    version.write_text(s.replace("version: 1.9.0+23","version: 2.0.0+24"),encoding="utf-8")
