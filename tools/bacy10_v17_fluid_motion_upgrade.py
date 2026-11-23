"""Replace BACY-10's static dotted orb with voice-reactive, liquid-glass fluid motion."""
from pathlib import Path

FLUID = r'''
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart' as sdk;
import 'package:provider/provider.dart';
import '../controllers/app_ctrl.dart';

/// Premium fluid-light lens. Reacts to real LiveKit user speech and agent state.
/// This is a custom GPU-backed Flutter canvas, NOT a cartoon or a dotted ball.
class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});
  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb> with SingleTickerProviderStateMixin {
  late final AnimationController motion = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 10000))..repeat();

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
      animation: Listenable.merge([motion, room, session.agent]),
      builder: (context, child) {
        final isUserSpeaking = room.localParticipant?.isSpeaking ?? false;
        final state = session.agent.agentState;
        final isAgentSpeaking = state == sdk.AgentState.speaking;
        final isThinking = state == sdk.AgentState.thinking;
        final isListening = state == sdk.AgentState.listening;
        final listening = isUserSpeaking || isListening;
        final currentLevel = isUserSpeaking
          ? (room.localParticipant?.audioLevel ?? 0.0) : 0.0;
        final voice = isUserSpeaking ? (.5 + currentLevel * .5)
          : (isAgentSpeaking ? .78 : isThinking ? .33 : .17);
        final status = isUserSpeaking ? 'YOU ARE SPEAKING'
          : isAgentSpeaking ? 'BACY-10 IS SPEAKING'
          : isThinking ? 'THINKING'
          : listening ? 'LISTENING'
          : session.connectionState == sdk.ConnectionState.connected ? 'CONNECTED'
          : 'READY';

        return LayoutBuilder(builder: (context, constraints) {
          final side = math.min(constraints.maxWidth, constraints.maxHeight);
          if (!side.isFinite || side <= 1) return const SizedBox.shrink();
          return Stack(fit: StackFit.expand, children: [
            CustomPaint(
              painter: _FluidLensPainter(time: motion.value, intensity: voice,
                listening: listening, speaking: isAgentSpeaking, thinking: isThinking)),
            Positioned(
              left: 0, right: 0, bottom: 2,
              child: Text(status, textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 9, letterSpacing: 2.5,
                  fontWeight: FontWeight.w500, color: Color(0xFFBDCFDA))),
            ),
          ]);
        });
      },
    );
  }
}

class _FluidLensPainter extends CustomPainter {
  final double time, intensity;
  final bool listening, speaking, thinking;
  const _FluidLensPainter({required this.time, required this.intensity,
    required this.listening, required this.speaking, required this.thinking});

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2 - 4);
    final r = math.min(size.width, size.height) * .355;
    final spin = time * 2 * math.pi;
    const ice = Color(0xFF61E4F4);
    const azure = Color(0xFF2498E8);
    const lilac = Color(0xFFA2A2FF);
    const rose = Color(0xFFD8A4F3);
    final pulse = 1 + math.sin(spin * 2.5) * .018 + intensity * .075;

    // Atmospheric bloom, out-of-focus studio light, not a geometric logo.
    canvas.drawCircle(c, r * 1.44, Paint()
      ..shader = RadialGradient(
        colors: [
          azure.withValues(alpha: .16 + intensity * .18),
          lilac.withValues(alpha: .07),
          Colors.transparent],
        stops: const [0, .5, 1],
      ).createShader(Rect.fromCircle(center: c, radius: r * 1.44)));

    // Outlying silk ribbons have smooth sinuous motion and blur into the space.
    for (var ribbon = 0; ribbon < 5; ribbon++) {
      final p = Path();
      final offset = (ribbon - 2) * r * .2;
      for (var n = 0; n <= 150; n++) {
        final x = (n / 150 - .5) * r * 2.95;
        final falloff = math.exp(-x * x / (r * r * 1.8));
        final y = offset +
          math.sin(x / r * (2 + ribbon * .21) + spin * (.36 + ribbon * .06)
            + ribbon * 1.2) * r * .33 * falloff +
          math.cos(x / r * 4.3 - spin * .3) * r * .045;
        if (n == 0) { p.moveTo(c.dx + x, c.dy + y); }
        else { p.lineTo(c.dx + x, c.dy + y); }
      }
      final color = ribbon.isEven ? lilac : ice;
      canvas.drawPath(p, Paint()
        ..color = color.withValues(alpha: .10 + intensity * .08)
        ..strokeWidth = 20
        ..style = PaintingStyle.stroke
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16));
      canvas.drawPath(p, Paint()
        ..color = color.withValues(alpha: .22 + intensity * .22)
        ..strokeWidth = .9
        ..style = PaintingStyle.stroke);
    }

    // Translucent spherical glass volume with thick optical edge and refraction.
    canvas.drawCircle(c, r * pulse, Paint()
      ..shader = RadialGradient(
        center: const Alignment(-.32, -.28), radius: 1.24,
        colors: [
          const Color(0xFF668DAB).withValues(alpha: .45),
          const Color(0xFF152B48).withValues(alpha: .9),
          const Color(0xFF050D1D).withValues(alpha: .98),
          const Color(0xFF254A6E).withValues(alpha: .92),
        ],
        stops: const [0, .36, .77, 1],
      ).createShader(Rect.fromCircle(center: c, radius: r * pulse)));

    final inside = Path()..addOval(Rect.fromCircle(center: c, radius: r * pulse));
    canvas.save();
    canvas.clipPath(inside);

    // Shear multiple membranes through a coherent rotating volumetric flow field.
    // Each filament moves in 3D-like perspective, not a uniform dotted mesh.
    for (int filament = -26; filament <= 26; filament++) {
      final yFraction = filament / 27;
      final opacity = (1 - yFraction.abs()) * (.13 + intensity * .26);
      final path = Path();
      for (var step = 0; step <= 145; step++) {
        final u = step / 145 * 2 - 1;
        final profile = math.sqrt(math.max(0, 1 - u * u));
        final wave = math.sin(u * 5.9 + spin * .64 + yFraction * 4) * .12
          + math.cos(u * 9.3 - spin * .42 + yFraction * 3) * .045;
        final warp = yFraction * .68 + wave;
        final x = c.dx + u * r * pulse * 1.07;
        final y = c.dy + (warp * profile + yFraction * .30) * r * pulse;
        if (step == 0) { path.moveTo(x, y); }
        else { path.lineTo(x, y); }
      }
      final color = filament % 5 == 0 ? rose : filament.isOdd ? azure : ice;
      if (filament % 7 == 0) {
        canvas.drawPath(path, Paint()
          ..color = color.withValues(alpha: opacity * .72)
          ..strokeWidth = 10
          ..style = PaintingStyle.stroke
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9));
      }
      canvas.drawPath(path, Paint()
        ..shader = LinearGradient(
          colors: [color.withValues(alpha: .01),
            color.withValues(alpha: opacity),
            lilac.withValues(alpha: opacity * 1.6),
            color.withValues(alpha: .01)],
          stops: const [0, .30, .67, 1],
        ).createShader(Rect.fromLTRB(c.dx - r, c.dy - r, c.dx + r, c.dy + r))
        ..style = PaintingStyle.stroke
        ..strokeWidth = .45 + (filament % 7 == 0 ? .9 : .2));
    }

    // Luminous central ribbon rolls and undulates to the microphone/agent state.
    for (var band = 0; band < 6; band++) {
      final path = Path();
      final shift = spin * (band.isEven ? .45 : -.51) + band * .84;
      for (int step = 0; step <= 170; step++) {
        final u = step / 170 * 2 - 1;
        final a = math.sin(u * 4.3 + shift) * r * (.11 + intensity * .09);
        final b = math.cos(u * 6.8 - shift * .6) * r * .05;
        final y = c.dy + (band - 2.5) * r * .115 + a + b;
        final x = c.dx + u * r * 1.4;
        if (step == 0) { path.moveTo(x, y); }
        else { path.lineTo(x, y); }
      }
      final color = band.isEven ? ice : lilac;
      canvas.drawPath(path, Paint()
        ..color = color.withValues(alpha: .12 + intensity * .20)
        ..strokeWidth = 9
        ..style = PaintingStyle.stroke
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 9));
      canvas.drawPath(path, Paint()
        ..color = color.withValues(alpha: .55 + intensity * .38)
        ..strokeWidth = .9
        ..style = PaintingStyle.stroke);
    }
    canvas.restore();

    // Complex thin refractive edge, travelling glints and internal lens flare.
    final rim = Rect.fromCircle(center: c, radius: r * pulse);
    canvas.drawArc(rim, spin * .28, math.pi * 1.10, false, Paint()
      ..shader = SweepGradient(colors: [
        ice.withValues(alpha: .02), ice.withValues(alpha: .83),
        rose.withValues(alpha: .37), lilac.withValues(alpha: .88),
        ice.withValues(alpha: .02)]).createShader(rim)
      ..strokeWidth = 1.9..style = PaintingStyle.stroke);
    canvas.drawArc(rim, -spin * .19 + 2.7, math.pi * .44, false, Paint()
      ..color = rose.withValues(alpha: .28)
      ..strokeWidth = 4..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5));
    canvas.drawCircle(Offset(c.dx - r * .32, c.dy - r * .43), r * .2, Paint()
      ..shader = RadialGradient(colors: [
        ice.withValues(alpha: .12), Colors.transparent
      ]).createShader(Rect.fromCircle(
        center: Offset(c.dx - r * .32, c.dy - r * .43), radius: r * .2)));
  }

  @override
  bool shouldRepaint(covariant _FluidLensPainter old) =>
    old.time != time || old.intensity != intensity ||
    old.listening != listening || old.speaking != speaking || old.thinking != thinking;
}
'''

def apply(root: Path) -> None:
    dst = root / "mobile/lib/widgets/bacy_live_orb.dart"
    if not dst.exists(): raise RuntimeError("BACY-10 orb missing")
    dst.write_text(FLUID, encoding="utf-8")
    pubspec = root/"mobile/pubspec.yaml"
    s=pubspec.read_text(encoding="utf-8")
    if "version: 1.6.0+20" not in s: raise RuntimeError("Unexpected app version")
    pubspec.write_text(s.replace("version: 1.6.0+20", "version: 1.7.0+21"),encoding="utf-8")
