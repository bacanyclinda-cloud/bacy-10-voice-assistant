"""BACY-10 focused center voice orb: no toolbar, layout, voice, or routing changes."""
from pathlib import Path

ORB = r'''
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';

/// A continuously moving cinematic mesh sphere; only the centre voice visual changes.
class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});

  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb> with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 9400),
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
    final t = phase * math.pi * 2;
    final radius = math.min(w, h) * .395 * (1 + (active ? .012 : .005) * math.sin(t * 2));
    final blue = const Color(0xFF4BB8FF);
    final violet = const Color(0xFF9A65ED);
    final orange = const Color(0xFFDE8F75);

    // Broad atmospheric falloff; very low light against existing black UI.
    canvas.drawCircle(c, radius * 1.48, Paint()
      ..shader = RadialGradient(colors: [
        blue.withValues(alpha: active ? .14 : .065),
        violet.withValues(alpha: .055), Colors.transparent,
      ], stops: const [.05, .5, 1]).createShader(
        Rect.fromCircle(center: c, radius: radius * 1.48),
      ));


    // Soft multidirectional ribbons pass behind the sphere, like flowing
    // fabric made of light. Nothing changes outside the centre widget.
    for (int ribbon = 0; ribbon < 5; ribbon++) {
      final flow = Path();
      final spread = (ribbon - 2) / 5.0;
      for (int i = 0; i <= 110; i++) {
        final unit = i / 110.0;
        final x = c.dx + (unit * 2 - 1) * radius * 1.95;
        final yy = c.dy + spread * radius * 0.70 +
            math.sin(unit * math.pi * (2.0 + ribbon * .23) + t * .43 + ribbon * 1.17) * radius * .40 +
            math.sin(unit * 13 + ribbon + t * .17) * radius * .045;
        if (i == 0) { flow.moveTo(x, yy); } else { flow.lineTo(x, yy); }
      }
      final hue = ribbon.isEven ? violet : blue;
      canvas.drawPath(flow, Paint()
        ..color = hue.withValues(alpha: .065)
        ..style = PaintingStyle.stroke
        ..strokeWidth = radius * .17
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 22));
      canvas.drawPath(flow, Paint()
        ..color = hue.withValues(alpha: .25)
        ..style = PaintingStyle.stroke
        ..strokeWidth = .8);
    }

    // A blue-violet glass edge, plus a subtle warm highlight.
    canvas.drawCircle(c, radius * 1.012, Paint()
      ..color = blue.withValues(alpha: active ? .35 : .20)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.3
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9));

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
    for (int band = 0; band < 5; band++) {
      final path = Path();
      final shift = t * (band.isEven ? .85 : -.67) + band * .9;
      for (int i = 0; i <= 108; i++) {
        final x = c.dx + ((i / 108) * 2 - 1) * radius * 1.36;
        final local = (i / 108) * 2 - 1;
        final wave = math.sin(local * 4.7 + shift) * radius * (.14 + .018 * band) +
          math.sin(local * 8.0 - shift * .52) * radius * .035;
        final y = c.dy + wave + (band - 2) * radius * .13;
        if (i == 0) { path.moveTo(x, y); } else { path.lineTo(x, y); }
      }
      final color = band == 4 ? orange : (band.isEven ? blue : violet);
      canvas.drawPath(path, Paint()..color = color.withValues(alpha: .12)..strokeWidth = 22
        ..style = PaintingStyle.stroke..maskFilter = const MaskFilter.blur(BlurStyle.normal, 15));
      canvas.drawPath(path, Paint()..color = color.withValues(alpha: .60)..strokeWidth = 1.2
        ..style = PaintingStyle.stroke);
    }

    // Fine orbital mesh; varying opacity avoids harsh neon and artificial solid rings.
    for (int lat = -18; lat <= 18; lat++) {
      final p = Path();
      final y = lat / 20.0;
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
    for (int long = 0; long < 40; long++) {
      final a = long / 40 * math.pi * 2 + t * .16;
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

    // Thousands of independent sapphire/purple light points form curved
    // latitude rows, like the elegant perforated mesh in the user's reference.
    // Dot size is kept small so it looks photographic rather than cartoonish.
    final dots = Paint()..style = PaintingStyle.fill;
    for (int row = -25; row <= 25; row++) {
      final lat = row / 26.0;
      final span = math.sqrt(math.max(0.0, 1 - lat * lat));
      for (int col = 0; col < 70; col++) {
        final azimuth = col / 70.0 * math.pi * 2 + t * .14;
        final depth = math.cos(azimuth);
        final warp = math.sin(t * .83 + lat * 5.4 + azimuth * 2.3) * .055;
        final x = c.dx + radius * span * (math.sin(azimuth + warp) * .93);
        final y = c.dy + radius * (lat * .91 +
          math.sin(azimuth * 2.0 - t * .7 + lat * 3) * .13 * span);
        final brightness = (0.45 + 0.55 * depth).clamp(0.0, 1.0).toDouble();
        final shimmer = .65 + .35 * math.sin(t * 2.4 + row * .17 + col * .11);
        final alpha = (brightness * shimmer * (active ? .73 : .56)).clamp(0.0, 1.0).toDouble();
        dots.color = (row < 0 ? blue : violet).withValues(alpha: alpha);
        canvas.drawCircle(Offset(x, y), (depth > 0 ? .8 : .46), dots);
      }
    }

    canvas.restore();

    // Subtle rim with two independent rotations; highlight stays thin.
    final rect = Rect.fromCircle(center: c, radius: radius);
    canvas.drawArc(rect, t * .15, math.pi * 1.12, false, Paint()
      ..shader = SweepGradient(
        colors: [blue.withValues(alpha: .24), blue.withValues(alpha: .93),
          violet.withValues(alpha: .85), blue.withValues(alpha: .20)],
      ).createShader(rect)
      ..style = PaintingStyle.stroke..strokeWidth = 1.8);
    canvas.drawArc(rect, -t * .12 + 2.6, math.pi * .53, false, Paint()
      ..color = orange.withValues(alpha: .52)..style = PaintingStyle.stroke..strokeWidth = .65);
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
