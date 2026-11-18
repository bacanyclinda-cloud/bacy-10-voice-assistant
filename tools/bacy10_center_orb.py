"""BACY-10 focused center voice orb: no toolbar, layout, voice, or routing changes."""
from pathlib import Path

ORB = r'''
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';

/// Continuously moving restrained blue/violet light field, centre-only.
class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});

  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb> with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 7200),
  )..repeat();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final connected = context.select<sdk.Session, bool>(
      (session) => session.connectionState == sdk.ConnectionState.connected,
    );
    return Center(
      child: AspectRatio(
        aspectRatio: 1,
        child: AnimatedBuilder(
          animation: controller,
          builder: (context, child) => CustomPaint(
            painter: _EnergyOrbPainter(controller.value, active: connected),
            child: const SizedBox.expand(),
          ),
        ),
      ),
    );
  }
}

class _EnergyOrbPainter extends CustomPainter {
  final double phase;
  final bool active;
  _EnergyOrbPainter(this.phase, {required this.active});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final c = Offset(w / 2, h / 2);
    final radius = math.min(w, h) * .34;
    final t = phase * math.pi * 2;
    final blue = const Color(0xFF5EA9E7);
    final violet = const Color(0xFF766CC5);
    final orange = const Color(0xFFC79067);

    // Broad atmospheric falloff; very low light against existing black UI.
    canvas.drawCircle(c, radius * 1.48, Paint()
      ..shader = RadialGradient(colors: [
        blue.withValues(alpha: active ? .075 : .035),
        violet.withValues(alpha: .027), Colors.transparent,
      ], stops: const [.05, .5, 1]).createShader(
        Rect.fromCircle(center: c, radius: radius * 1.48),
      ));

    // Transparent glass body; gentle internal scattering, not a flat cartoon ball.
    canvas.drawCircle(c, radius, Paint()
      ..shader = RadialGradient(
        center: const Alignment(-.37, -.36),
        radius: 1.16,
        colors: [
          const Color(0xFF203A57).withValues(alpha: .54),
          const Color(0xFF090D1D),
          const Color(0xFF080912),
          const Color(0xFF15233D),
        ],
        stops: const [0, .46, .83, 1],
      ).createShader(Rect.fromCircle(center: c, radius: radius)));

    final clip = Path()..addOval(Rect.fromCircle(center: c, radius: radius * .98));
    canvas.save();
    canvas.clipPath(clip);

    // Three moving luminous ribbons, projected as curved fiber-light strands.
    for (int band = 0; band < 3; band++) {
      final path = Path();
      final shift = t * (band.isEven ? 1 : -1) + band * 1.9;
      for (int i = 0; i <= 108; i++) {
        final x = c.dx + ((i / 108) * 2 - 1) * radius * 1.36;
        final local = (i / 108) * 2 - 1;
        final wave = math.sin(local * 4.7 + shift) * radius * (.18 + .024 * band) +
          math.sin(local * 8.0 - shift * .52) * radius * .035;
        final y = c.dy + wave + (band - 1) * radius * .21;
        if (i == 0) { path.moveTo(x, y); } else { path.lineTo(x, y); }
      }
      final color = band == 0 ? blue : (band == 1 ? violet : orange);
      canvas.drawPath(path, Paint()..color = color.withValues(alpha: .08)..strokeWidth = 15
        ..style = PaintingStyle.stroke..maskFilter = const MaskFilter.blur(BlurStyle.normal, 11));
      canvas.drawPath(path, Paint()..color = color.withValues(alpha: .48)..strokeWidth = .95
        ..style = PaintingStyle.stroke);
    }

    // Fine orbital mesh; varying opacity avoids harsh neon and artificial solid rings.
    for (int lat = -6; lat <= 6; lat++) {
      final p = Path();
      final y = lat / 8.0;
      final latRad = radius * math.sqrt(math.max(0, 1 - y * y));
      final wobble = math.sin(t * .57 + lat * .48) * .08;
      for (int step = 0; step <= 70; step++) {
        final u = (step / 70) * math.pi * 2;
        final x = c.dx + latRad * math.cos(u);
        final z = math.sin(u);
        final yy = c.dy + y * radius + (latRad * .12 + wobble * radius) * z;
        if (step == 0) { p.moveTo(x, yy); } else { p.lineTo(x, yy); }
      }
      canvas.drawPath(p, Paint()
        ..color = (lat < 0 ? blue : violet).withValues(alpha: .13)
        ..strokeWidth = .38..style = PaintingStyle.stroke);
    }
    for (int long = 0; long < 22; long++) {
      final a = long / 22 * math.pi * 2 + t * .16;
      final p = Path();
      for (int step = 0; step <= 65; step++) {
        final latitude = -math.pi / 2 + step / 65 * math.pi;
        final x = c.dx + radius * math.cos(latitude) * math.sin(a);
        final y = c.dy + radius * math.sin(latitude) * .91;
        if (step == 0) { p.moveTo(x, y); } else { p.lineTo(x, y); }
      }
      canvas.drawPath(p, Paint()
        ..color = blue.withValues(alpha: .045)
        ..strokeWidth = .34..style = PaintingStyle.stroke);
    }
    canvas.restore();

    // Subtle rim with two independent rotations; highlight stays thin.
    final rect = Rect.fromCircle(center: c, radius: radius);
    canvas.drawArc(rect, t * .15, math.pi * 1.12, false, Paint()
      ..shader = SweepGradient(
        colors: [blue.withValues(alpha: .12), blue.withValues(alpha: .60),
          violet.withValues(alpha: .31), blue.withValues(alpha: .12)],
      ).createShader(rect)
      ..style = PaintingStyle.stroke..strokeWidth = 1.4);
    canvas.drawArc(rect, -t * .12 + 2.6, math.pi * .53, false, Paint()
      ..color = orange.withValues(alpha: .27)..style = PaintingStyle.stroke..strokeWidth = .65);
  }

  @override
  bool shouldRepaint(covariant _EnergyOrbPainter oldDelegate) =>
      oldDelegate.phase != phase || oldDelegate.active != active;
}
'''

def apply(root: Path) -> None:
    mobile = root / "mobile/lib"
    (mobile / "widgets/bacy_live_orb.dart").write_text(ORB, encoding="utf-8")
    screen = mobile / "screens/agent_screen.dart"
    text = screen.read_text(encoding="utf-8")
    needle = "import '../controllers/app_ctrl.dart';"
    if needle not in text:
        raise RuntimeError("Cannot locate agent centre widget import")
    text = text.replace(needle, needle + "\nimport '../widgets/bacy_live_orb.dart';", 1)
    start = text.find("                    return const components.AudioVisualizerWidget(")
    end = text.find("\n                  }),", start)
    if start < 0 or end < 0:
        raise RuntimeError("Unable to locate current 5-bar voice visualizer")
    text = text[:start] + "                    return const BacyLiveOrb();" + text[end:]
    screen.write_text(text, encoding="utf-8")
