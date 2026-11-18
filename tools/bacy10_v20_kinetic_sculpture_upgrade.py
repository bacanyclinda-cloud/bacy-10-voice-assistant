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

/// Three-dimensional kinetic mineral core.
/// A projected toroidal mesh with real face normals, studio lighting,
/// two rotating axes and a glass eye. No old light waves or 2D ribbons.
class BacyLiveOrb extends StatefulWidget {
  const BacyLiveOrb({super.key});
  @override
  State<BacyLiveOrb> createState() => _BacyLiveOrbState();
}

class _BacyLiveOrbState extends State<BacyLiveOrb> with SingleTickerProviderStateMixin {
  late final AnimationController motion = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 13500))..repeat();

  @override
  void dispose() {
    motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final room = context.read<AppCtrl>().room;
    final session = context.read<sdk.Session>();
    return AnimatedBuilder(
      animation: Listenable.merge([motion, room, session.agent]),
      builder: (context, _) {
        final speaking = room.localParticipant?.isSpeaking ?? false;
        final agentState = session.agent.agentState;
        final replying = agentState == sdk.AgentState.speaking;
        final thinking = agentState == sdk.AgentState.thinking;
        final connected = session.connectionState == sdk.ConnectionState.connected;
        final level = (room.localParticipant?.audioLevel ?? 0.0).clamp(0.0, 1.0);
        final strength = speaking ? (0.62 + level * .9).clamp(0.0, 1.4).toDouble()
            : replying ? .82 : thinking ? .55 : connected ? .34 : .15;
        final state = speaking ? 'YOU ARE SPEAKING' :
            replying ? 'BACY-10 IS SPEAKING' :
            thinking ? 'PROCESSING' : connected ? 'LISTENING' : 'STANDBY';

        return RepaintBoundary(child: Stack(fit: StackFit.expand, children: [
          CustomPaint(painter: _KineticCorePainter(motion.value, strength)),
          Positioned(
            bottom: 0, left: 0, right: 0,
            child: Text(state, textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFFAFCBC0), fontSize: 10,
                letterSpacing: 2.4, fontWeight: FontWeight.w600))),
        ]));
      },
    );
  }
}

class _Vec {
  const _Vec(this.x, this.y, this.z);
  final double x, y, z;

  _Vec operator -(_Vec b) => _Vec(x-b.x, y-b.y, z-b.z);
  _Vec cross(_Vec b) => _Vec(y*b.z-z*b.y, z*b.x-x*b.z, x*b.y-y*b.x);
  double dot(_Vec b) => x*b.x+y*b.y+z*b.z;
  double get length => math.sqrt(x*x+y*y+z*z);

  _Vec rotated(double yaw, double pitch, double roll) {
    final cy=math.cos(yaw), sy=math.sin(yaw);
    final cx=math.cos(pitch), sx=math.sin(pitch);
    final cz=math.cos(roll), sz=math.sin(roll);
    final x0=x*cy+z*sy, z0=z*cy-x*sy;
    final y1=y*cx-z0*sx, z1=y*sx+z0*cx;
    return _Vec(x0*cz-y1*sz, x0*sz+y1*cz, z1);
  }
}

class _Face {
  const _Face(this.path, this.z, this.shade, this.ring);
  final Path path;
  final double z, shade;
  final int ring;
}

class _KineticCorePainter extends CustomPainter {
  _KineticCorePainter(this.phase, this.voice);
  final double phase, voice;

  static const dark = Color(0xFF0A1212);
  static const enamel = Color(0xFFE4F3EC);
  static const emerald = Color(0xFF5DAB8F);
  static const charcoal = Color(0xFF21312D);
  static const highlight = Color(0xFFF8FFF9);

  Offset project(_Vec p, Offset center, double radius) {
    final perspective = 3.7 / (3.7 - p.z * .6);
    return Offset(center.dx + p.x * radius * perspective,
      center.dy + p.y * radius * perspective);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final t = phase * math.pi * 2;
    final c = Offset(size.width * .5, size.height * .48);
    final r = math.min(size.width, size.height) * .35;
    final pulsation = 1 + .024 * voice + .008 * math.sin(t * 2.7);

    // Soft off-camera studio reflection and deep graphite space.
    canvas.drawCircle(c, r * 1.50, Paint()
      ..shader = RadialGradient(colors: [
        emerald.withValues(alpha: .17 + .06 * voice),
        charcoal.withValues(alpha: .16),
        Colors.transparent],
        stops: const [0, .50, 1]).createShader(
          Rect.fromCircle(center: c, radius: r * 1.50)));

    // Volumetric core: smoked mineral glass with distinct surface refraction.
    final sphere = r * .36 * pulsation;
    canvas.drawCircle(c, sphere * 1.3, Paint()
      ..color = emerald.withValues(alpha: .28 + voice * .1)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 22));
    canvas.drawCircle(c, sphere, Paint()
      ..shader = RadialGradient(
        center: const Alignment(-.40, -.44), radius: 1.05,
        colors: [highlight, const Color(0xFFC5E4D5),
          const Color(0xFF608D7A), const Color(0xFF203B32),
          const Color(0xFF0B1513)],
        stops: const [0, .19, .45, .76, 1],
      ).createShader(Rect.fromCircle(center: c, radius: sphere)));

    // Torus surfaces are built as projected 3D quads.
    // Draw far polygons before near polygons to expose physical depth.
    final faces = <_Face>[];
    const majorSegments=76;
    const tubeSegments=14;
    final light = const _Vec(-.35, -.58, .74);
    for (var ring=0; ring<2; ring++) {
      final yaw=t * (ring==0 ? .35 : -.28) + ring*1.15;
      final pitch=(ring==0 ? .35 : 1.05) + math.sin(t*.27+ring)*.18;
      final roll=(ring==0 ? .28 : -1.12) + t*(ring==0 ? .12 : -.09);
      final tube=ring==0 ? .135 : .102;
      final major=ring==0 ? .82 : .62;
      _Vec surface(int uStep, int vStep) {
        final u=uStep * math.pi * 2 / majorSegments;
        final v=vStep * math.pi * 2 / tubeSegments;
        final width=major+tube*math.cos(v);
        return _Vec(width*math.cos(u),
          width*math.sin(u), tube*math.sin(v))
          .rotated(yaw,pitch,roll);
      }
      for(var u=0;u<majorSegments;u++) {
        for(var v=0;v<tubeSegments;v++) {
          final a=surface(u,v), b=surface(u+1,v),
              d=surface(u,v+1), e=surface(u+1,v+1);
          final normal=(b-a).cross(d-a);
          final length=normal.length;
          final facing=length < 0.000001 ? 0.0 :
              normal.dot(light)/length;
          final lum=(.22+.70*math.max(0.0,facing)+
              .10*math.max(0.0,-facing)).clamp(.0,1.0).toDouble();
          final path=Path();
          final pa=project(a,c,r*pulsation), pb=project(b,c,r*pulsation),
            pe=project(e,c,r*pulsation), pd=project(d,c,r*pulsation);
          path.moveTo(pa.dx,pa.dy);
          path.lineTo(pb.dx,pb.dy);
          path.lineTo(pe.dx,pe.dy);
          path.lineTo(pd.dx,pd.dy);
          path.close();
          faces.add(_Face(path,(a.z+b.z+d.z+e.z)*.25,lum,ring));
        }
      }
    }
    faces.sort((a,b)=>a.z.compareTo(b.z));
    for(final f in faces) {
      final base=f.ring==0 ? emerald : enamel;
      final color=Color.lerp(dark,base,f.shade) ?? base;
      canvas.drawPath(f.path, Paint()..color=color);
    }

    // The core is in front of some parts of the gyroscope, giving eye-depth.
    final lens=r*.30;
    canvas.drawCircle(c,lens,Paint()..shader=RadialGradient(
      center: const Alignment(-.42,-.38), radius: 1.04,
      colors:[const Color(0xFFEDFFF3), const Color(0xFF86BBA3),
        const Color(0xFF294B3C), const Color(0xFF0C1815)],
      stops:const [0,.30,.68,1])
        .createShader(Rect.fromCircle(center:c,radius:lens)));

    // Tiny travelling reflection, like a moving product studio softbox.
    final glint=Offset(c.dx-lens*.34+math.cos(t*.35)*lens*.06,
      c.dy-lens*.38);
    canvas.drawOval(Rect.fromCenter(
      center:glint,width:lens*.35,height:lens*.18),
      Paint()
        ..color=highlight.withValues(alpha: .54 + voice*.25)
        ..maskFilter=const MaskFilter.blur(BlurStyle.normal,7));
    canvas.drawCircle(c,lens*.96,Paint()
      ..style=PaintingStyle.stroke
      ..strokeWidth=1.6
      ..color=enamel.withValues(alpha: .52));
  }

  @override
  bool shouldRepaint(covariant _KineticCorePainter old)=>
    phase!=old.phase || voice!=old.voice;
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
