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

class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});
  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb> with SingleTickerProviderStateMixin {
  late final AnimationController motion = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 12500))..repeat();

  @override
  void dispose() {
    motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = context.read<sdk.Session>();
    final room = context.read<AppCtrl>().room;
    return AnimatedBuilder(
      animation: Listenable.merge([motion, session.agent, room]),
      builder: (context, _) {
        final talking = room.localParticipant?.isSpeaking ?? false;
        final state = session.agent.agentState;
        final reply = state == sdk.AgentState.speaking;
        final thinking = state == sdk.AgentState.thinking;
        final ready = session.connectionState == sdk.ConnectionState.connected;
        final audio = room.localParticipant?.audioLevel ?? 0.0;
        final energy = talking ? (0.72 + audio * 1.4).clamp(0.0, 1.65).toDouble()
          : reply ? 0.8 : thinking ? 0.43 : .19;
        final caption = talking ? 'YOU ARE SPEAKING'
          : reply ? 'BACY-10 IS SPEAKING'
          : thinking ? 'THINKING'
          : ready ? 'LISTENING'
          : 'READY';

        return RepaintBoundary(child: Stack(fit: StackFit.expand, children: [
          CustomPaint(painter: _PearlSculpture(motion.value, energy)),
          Positioned(left: 0, right: 0, bottom: 0,
            child: Text(caption, textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFFD3C8BA),
                fontWeight: FontWeight.w500,
                fontSize: 10, letterSpacing: 2.2))),
        ]));
      },
    );
  }
}

class _V {
  const _V(this.x, this.y, this.z);
  final double x, y, z;

  _V rotate(double yaw, double pitch) {
    final cy = math.cos(yaw), sy = math.sin(yaw);
    final cx = math.cos(pitch), sx = math.sin(pitch);
    final a = x * cy + z * sy;
    final b = z * cy - x * sy;
    return _V(a, y * cx - b * sx, y * sx + b * cx);
  }
}

class _Slice {
  _Slice(this.path, this.depth, this.color, this.shade);
  final Path path;
  final double depth;
  final Color color;
  final double shade;
}

class _PearlSculpture extends CustomPainter {
  _PearlSculpture(this.phase, this.energy);
  final double phase, energy;

  static const porcelain = Color(0xFFF6ECE0);
  static const champagne = Color(0xFFD2A979);
  static const blush = Color(0xFFD89C83);
  static const graphite = Color(0xFF0E1115);

  Offset projection(_V v, Offset origin, double radius) {
    final depth = 3.9 / (3.9 - v.z * .37);
    return Offset(origin.dx + v.x * depth * radius,
        origin.dy + v.y * depth * radius);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final origin = Offset(size.width / 2, size.height * .46);
    final radius = math.min(size.width, size.height) * .37;
    final spin = phase * math.pi * 2;
    final scale = 1 + energy * .035 + .01 * math.sin(spin * 2.1);

    // Dark, warm cinematic photographic environment.
    canvas.drawCircle(origin, radius * 1.55, Paint()
      ..shader = RadialGradient(
        colors: [
          champagne.withValues(alpha: .14 + energy * .075),
          blush.withValues(alpha: .038),
          Colors.transparent],
        stops: const [0, .48, 1],
      ).createShader(Rect.fromCircle(center: origin, radius: radius * 1.55)));

    canvas.drawCircle(origin, radius * 1.01 * scale, Paint()
      ..shader = RadialGradient(
        center: const Alignment(-.25, -.36),
        radius: 1.24,
        colors: [
          const Color(0xFF333339),
          const Color(0xFF16171A),
          const Color(0xFF08090C),
          const Color(0xFF21201F),
        ],
        stops: const [0, .39, .78, 1],
      ).createShader(Rect.fromCircle(
        center: origin, radius: radius * 1.01 * scale)));

    // Frosted porcelain core sits deep in the gyroscope assembly.
    canvas.drawCircle(origin, radius * (.255 + energy * .025), Paint()
      ..shader = RadialGradient(
        center: const Alignment(-.45, -.48),
        radius: 1.05,
        colors: [
          const Color(0xFFF6EDE0),
          const Color(0xFFD5BFAF),
          const Color(0xFF6D5750),
          const Color(0xFF191619),
        ],
        stops: const [0, .36, .72, 1],
      ).createShader(Rect.fromCircle(
        center: origin, radius: radius * (.255 + energy * .025))));
    canvas.drawCircle(origin, radius * .075, Paint()
      ..color = porcelain.withValues(alpha: .24 + energy * .26)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 22));

    // Six curved glass-ceramic blades wrap in true 3D, front blades
    // occluding back blades as the sculpture rotates.
    final slices = <_Slice>[];
    final yaw = spin * .54;
    final pitch = .48 + math.sin(spin * .37) * .37;
    for (int petal = 0; petal < 6; petal++) {
      final base = petal * math.pi / 3;
      final hue = petal.isEven ? porcelain : champagne;
      for (int seg = 0; seg < 48; seg++) {
        final u0 = seg / 48.0;
        final u1 = (seg + 1) / 48.0;
        _V surface(double u, int side) {
          final theta = base + u * math.pi * 1.12 + spin * .12;
          final amp = .19 + .74 * math.sin(u * math.pi);
          final ridge = math.sin(u * math.pi * 1.76 + petal * .46) * .2;
          final distance = amp * scale + (side == 0 ? -.078 : .078);
          return _V(
            distance * math.cos(theta),
            (u - .5) * 1.5 + ridge + (side == 0 ? -.046 : .046),
            distance * math.sin(theta) * .62 + math.cos(theta * 2) * .18
          ).rotate(yaw, pitch);
        }
        final a = surface(u0, 0);
        final b = surface(u0, 1);
        final d = surface(u1, 0);
        final e = surface(u1, 1);
        final poly = Path()
          ..moveTo(projection(a, origin, radius).dx, projection(a, origin, radius).dy)
          ..lineTo(projection(b, origin, radius).dx, projection(b, origin, radius).dy)
          ..lineTo(projection(e, origin, radius).dx, projection(e, origin, radius).dy)
          ..lineTo(projection(d, origin, radius).dx, projection(d, origin, radius).dy)
          ..close();
        final depth = (a.z + b.z + d.z + e.z) / 4;
        final shade = (.54 + depth * .25 +
          math.sin(u0 * math.pi) * .34).clamp(.18, 1.0).toDouble();
        slices.add(_Slice(poly, depth, hue, shade));
      }
    }
    slices.sort((a, b) => a.depth.compareTo(b.depth));
    for (final piece in slices) {
      final color = Color.lerp(const Color(0xFF382F2D),
          piece.color, piece.shade) ?? porcelain;
      canvas.drawPath(piece.path, Paint()
        ..color = color.withValues(alpha: .85));
    }

    // A handful of sharp porcelain specular glints, not cartoon outlines.
    for (int ring = 0; ring < 3; ring++) {
      final path = Path();
      for (int i = 0; i <= 95; i++) {
        final a = i / 95.0 * math.pi * 2;
        final x = math.cos(a) * (0.84 - ring * .14);
        final y = math.sin(a) * .5;
        final z = math.sin(a + spin * .4 + ring) * .56;
        final p = projection(_V(x, y, z).rotate(
          spin * (.33 + ring * .08) + ring * 1.04,
          -.3 + ring * .47), origin, radius);
        if (i == 0) path.moveTo(p.dx, p.dy);
        else path.lineTo(p.dx, p.dy);
      }
      canvas.drawPath(path, Paint()
        ..color = porcelain.withValues(alpha: .24 + energy * .14)
        ..style = PaintingStyle.stroke
        ..strokeWidth = ring == 0 ? 1.1 : .55);
    }

    final rim = Rect.fromCircle(center: origin, radius: radius * 1.01 * scale);
    canvas.drawArc(rim, .4 + spin * .15, math.pi * 1.14, false, Paint()
      ..shader = SweepGradient(colors: [
        porcelain.withValues(alpha: .02),
        porcelain.withValues(alpha: .52),
        champagne.withValues(alpha: .2),
        porcelain.withValues(alpha: .02)],
      ).createShader(rim)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.35);

    // Small vertical reflections cue the depth and state without neon waves.
    canvas.drawOval(Rect.fromCenter(
      center: Offset(origin.dx - radius * .31, origin.dy - radius * .35),
      width: radius * .19, height: radius * .52), Paint()
        ..color = porcelain.withValues(alpha: .14)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 18));
  }

  @override
  bool shouldRepaint(covariant _PearlSculpture old) =>
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
