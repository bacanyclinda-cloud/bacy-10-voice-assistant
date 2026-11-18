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

/// BACY-10's living plasma sphere. Blue, violet and amber light folds
/// through a dark translucent globe, matching the owner's energy reference.
/// Only this centre object changes; every surrounding control is preserved.
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
    final room = context.read<AppCtrl>().room;
    final session = context.read<sdk.Session>();
    return AnimatedBuilder(
      animation: Listenable.merge([_motion, room, session.agent]),
      builder: (context, _) {
        final userSpeaking = room.localParticipant?.isSpeaking ?? false;
        final agentState = session.agent.agentState;
        final agentSpeaking = agentState == sdk.AgentState.speaking;
        final thinking = agentState == sdk.AgentState.thinking;
        final connected =
            session.connectionState == sdk.ConnectionState.connected;
        final level = (room.localParticipant?.audioLevel ?? 0.0)
            .clamp(0.0, 1.0)
            .toDouble();
        final energy = userSpeaking
            ? (0.58 + level * 1.25).clamp(0.0, 1.75).toDouble()
            : agentSpeaking
                ? 0.92
                : thinking
                    ? 0.47
                    : connected
                        ? 0.33
                        : 0.18;
        final status = userSpeaking
            ? 'YOU ARE SPEAKING'
            : agentSpeaking
                ? 'BACY-10 IS SPEAKING'
                : thinking
                    ? 'PROCESSING'
                    : connected
                        ? 'LISTENING'
                        : 'STANDBY';
        return RepaintBoundary(
          child: Stack(
            fit: StackFit.expand,
            children: [
              CustomPaint(
                painter: _EnergySpherePainter(
                  phase: _motion.value,
                  energy: energy,
                ),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Text(
                  status,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFFD5D7F5),
                    letterSpacing: 2.4,
                    fontWeight: FontWeight.w600,
                    fontSize: 10,
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

class _EnergySpherePainter extends CustomPainter {
  const _EnergySpherePainter({required this.phase, required this.energy});

  final double phase;
  final double energy;

  static const Color electric = Color(0xFF13BBFF);
  static const Color blue = Color(0xFF2B56FF);
  static const Color violet = Color(0xFF9955FF);
  static const Color hotPink = Color(0xFFEF65FA);
  static const Color amber = Color(0xFFFF9C45);
  static const Color white = Color(0xFFE7F5FF);

  Paint glow(Color color, double opacity, double stroke, double blur) =>
      Paint()
        ..color = color.withValues(alpha: opacity.clamp(0.0, 1.0).toDouble())
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = stroke
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, blur);

  @override
  void paint(Canvas canvas, Size size) {
    if (size.width <= 0 || size.height <= 0) return;
    final t = phase * math.pi * 2;
    final c = Offset(size.width * .5, size.height * .465);
    final r = math.min(size.width, size.height) * .344;
    final pulse = 1 + energy * .025 + .012 * math.sin(t * 2.3);
    final radius = r * pulse;
    final globe = Rect.fromCircle(center: c, radius: radius);

    // Cinematic colored atmosphere around the otherwise black space.
    canvas.drawCircle(
      c,
      radius * 1.57,
      Paint()
        ..shader = RadialGradient(
          colors: [
            blue.withValues(alpha: .18 + .08 * energy),
            violet.withValues(alpha: .10),
            Colors.transparent,
          ],
          stops: const [0, .47, 1],
        ).createShader(Rect.fromCircle(center: c, radius: radius * 1.57)),
    );
    final amberCentre = Offset(c.dx + radius * .49, c.dy + radius * .32);
    canvas.drawCircle(
      amberCentre,
      radius * .85,
      Paint()
        ..shader = RadialGradient(
          colors: [
            amber.withValues(alpha: .14 + .08 * energy),
            hotPink.withValues(alpha: .04),
            Colors.transparent,
          ],
        ).createShader(
          Rect.fromCircle(center: amberCentre, radius: radius * .85),
        ),
    );

    // Behind the glass: long, silky plasma trails break outside the sphere.
    for (var strand = 0; strand < 12; strand++) {
      final path = Path();
      final position = (strand - 5.5) / 5.5;
      for (var step = 0; step <= 170; step++) {
        final u = step / 170.0;
        final x = (u * 2 - 1) * radius * 1.43;
        final envelope = math.exp(-math.pow(x / (radius * 1.40), 2));
        final y = position * radius * .69 +
            math.sin(x / radius * (3.0 + strand * .13) +
                    t * (.58 + strand * .017) + strand * .55) *
                radius * (.12 + .07 * energy) * envelope +
            math.cos(x / radius * 4.8 - t * .28 + strand) *
                radius * .039;
        final point = Offset(c.dx + x, c.dy + y);
        if (step == 0) {
          path.moveTo(point.dx, point.dy);
        } else {
          path.lineTo(point.dx, point.dy);
        }
      }
      final color = strand % 4 == 0
          ? amber
          : strand % 3 == 0
              ? hotPink
              : strand.isEven
                  ? electric
                  : violet;
      canvas.drawPath(path, glow(color, .12 + .05 * energy, 16, 18));
      canvas.drawPath(path, glow(color, .20 + .15 * energy, 1.05, 1.6));
    }

    // The deep transparent body does NOT look like a flat solid colored disk.
    canvas.drawCircle(
      c,
      radius,
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(-.15, -.22),
          radius: 1.18,
          colors: [
            const Color(0xFF03102C),
            const Color(0xFF080B31),
            const Color(0xFF160C37),
            const Color(0xFF070919),
            const Color(0xFF12112E),
          ],
          stops: const [0, .28, .52, .83, 1],
        ).createShader(globe),
    );

    canvas.save();
    canvas.clipPath(Path()..addOval(globe));

    // Volumetric light clouds live inside the dark body, in opposing corners.
    final blueCentre = Offset(c.dx - radius * .47, c.dy - radius * .30);
    canvas.drawCircle(
      blueCentre,
      radius * .98,
      Paint()
        ..shader = RadialGradient(
          colors: [
            electric.withValues(alpha: .22 + energy * .10),
            blue.withValues(alpha: .15),
            Colors.transparent,
          ],
          stops: const [0, .48, 1],
        ).createShader(
          Rect.fromCircle(center: blueCentre, radius: radius * .98),
        ),
    );
    final warm = Offset(c.dx + radius * .55, c.dy + radius * .36);
    canvas.drawCircle(
      warm,
      radius * .88,
      Paint()
        ..shader = RadialGradient(
          colors: [
            amber.withValues(alpha: .25 + energy * .11),
            hotPink.withValues(alpha: .13),
            Colors.transparent,
          ],
          stops: const [0, .47, 1],
        ).createShader(
          Rect.fromCircle(center: warm, radius: radius * .88),
        ),
    );

    // Different wave frequencies and radial perspective create a liquid-
    // electric surface, rather than a stack of identical hair-thin lines.
    final surfaceGradient = LinearGradient(
      begin: Alignment.centerLeft,
      end: Alignment.centerRight,
      colors: [
        electric.withValues(alpha: .80),
        blue.withValues(alpha: .68),
        violet.withValues(alpha: .89),
        hotPink.withValues(alpha: .88),
        amber.withValues(alpha: .97),
      ],
      stops: const [0, .26, .49, .68, 1],
    ).createShader(globe);
    for (var filament = 0; filament < 32; filament++) {
      final depth = (filament - 15.5) / 16.0;
      final path = Path();
      for (var step = 0; step <= 180; step++) {
        final u = step / 180.0 * 2 - 1;
        final x = u * radius * 1.33;
        final y = depth * radius * .61 +
            math.sin(u * 4.8 + t * .42 + depth * 3.3) *
                radius * (.14 + energy * .037) +
            math.sin(u * 8.1 - t * .28 + depth * 8.2) *
                radius * .070 +
            math.cos(u * 13.0 + t * .17 + filament * .14) *
                radius * .013;
        if (step == 0) {
          path.moveTo(c.dx + x, c.dy + y);
        } else {
          path.lineTo(c.dx + x, c.dy + y);
        }
      }
      final alpha = .26 + (.30 * (1 - depth.abs())) + energy * .10;
      canvas.drawPath(
        path,
        Paint()
          ..color = violet.withValues(alpha: alpha * .20)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 6
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9),
      );
      canvas.drawPath(
        path,
        Paint()
          ..shader = surfaceGradient
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = filament % 7 == 0 ? 1.25 : .53,
      );
    }

    // Dynamic turbulent ribbons drift across the front like electric silk.
    for (var ribbon = 0; ribbon < 7; ribbon++) {
      final path = Path();
      final spread = (ribbon - 3.0) * radius * .155;
      for (var i = 0; i <= 185; i++) {
        final x = (i / 185.0 * 2 - 1) * radius * 1.38;
        final fold = math.sin(x / radius * 2.95 +
                t * (ribbon.isEven ? .81 : -.66) +
                ribbon * .92) * radius * (.20 + .055 * energy);
        final micro = math.sin(x / radius * 9.0 - t * .50 + ribbon * 1.3)
            * radius * .055;
        final point = Offset(c.dx + x, c.dy + spread + fold + micro);
        if (i == 0) {
          path.moveTo(point.dx, point.dy);
        } else {
          path.lineTo(point.dx, point.dy);
        }
      }
      final color = ribbon == 6
          ? amber
          : ribbon == 5
              ? hotPink
              : ribbon.isEven
                  ? electric
                  : violet;
      canvas.drawPath(path, glow(color, .35 + energy * .10, 15, 15));
      canvas.drawPath(path, glow(color, .47 + energy * .18, 4, 4.8));
      canvas.drawPath(
        path,
        Paint()
          ..color = Color.lerp(color, white, .28)!.withValues(
            alpha: (.60 + energy * .17).clamp(0.0, 1.0).toDouble(),
          )
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = .94,
      );
    }

    // Flickering points of energized material in three dimensional depth.
    for (var i = 0; i < 100; i++) {
      final angle = i * 2.399963229728653 + t * .13;
      final distance = math.sqrt((i + .5) / 100.0) * radius * .98;
      final point = Offset(
        c.dx + math.cos(angle) * distance,
        c.dy + math.sin(angle) * distance * .87,
      );
      final shimmer = .24 + .50 *
          (.5 + .5 * math.sin(t * 3.2 + i * .43));
      final color = point.dx > c.dx + radius * .10 ? amber : electric;
      canvas.drawCircle(
        point,
        i % 6 == 0 ? 1.25 : .55,
        Paint()..color = color.withValues(alpha: shimmer),
      );
    }
    canvas.restore();

    // Different colored refractive rim segments are non-uniform and glowing.
    final rim = Rect.fromCircle(center: c, radius: radius * 1.015);
    final sweep = SweepGradient(
      transform: GradientRotation(t * .15),
      colors: [
        electric.withValues(alpha: .15),
        electric.withValues(alpha: .99),
        blue.withValues(alpha: .53),
        violet.withValues(alpha: .92),
        amber.withValues(alpha: .96),
        hotPink.withValues(alpha: .75),
        electric.withValues(alpha: .15),
      ],
      stops: const [0, .21, .36, .56, .75, .90, 1],
    ).createShader(rim);
    canvas.drawArc(
      rim, t * .028, math.pi * 2, false,
      Paint()
        ..shader = sweep
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10),
    );
    canvas.drawArc(
      rim, t * .028, math.pi * 2, false,
      Paint()
        ..shader = sweep
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.85,
    );

    // Broken floating corona tendrils above and below the spherical body.
    for (var arc = 0; arc < 15; arc++) {
      final p = Path();
      final side = arc.isEven ? -1.0 : 1.0;
      final ax = side * radius * (.52 + arc % 5 * .087);
      for (var step = 0; step <= 70; step++) {
        final unit = step / 70.0;
        final theta = unit * math.pi * 1.4 + t * (.12 + arc * .004) + arc * 1.18;
        final orbit = radius * (.93 + .07 * math.sin(theta * 2 + arc));
        final x = c.dx + ax * math.cos(theta) * .6 +
            orbit * math.cos(theta) * .63;
        final y = c.dy + (arc.isEven ? -1 : 1) *
            orbit * math.sin(theta) * (.50 + arc % 3 * .11);
        if (step == 0) {
          p.moveTo(x, y);
        } else {
          p.lineTo(x, y);
        }
      }
      final color = arc % 4 == 0
          ? amber
          : arc.isEven ? violet : electric;
      canvas.drawPath(p, glow(color, .095, 6, 8));
      canvas.drawPath(p, glow(color, .24 + energy * .08, .5, .6));
    }
  }

  @override
  bool shouldRepaint(covariant _EnergySpherePainter old) =>
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
