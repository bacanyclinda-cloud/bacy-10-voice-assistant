import { useEffect, useRef } from "react";

export type VoicePhase = "idle" | "listening" | "thinking" | "speaking" | "error";

const vertexShader = `#version 300 es
in vec2 aPosition;
void main(){ gl_Position = vec4(aPosition, 0.0, 1.0); }
`;

// This is an original real-time GPU sculpture, not a picture or simulated status panel.
// The physical form responds to the microphone's measured RMS and the actual app state.
const fragmentShader = `#version 300 es
precision highp float;
uniform vec2 uResolution;
uniform float uTime;
uniform float uActivity;
uniform float uMode;
out vec4 outColor;
#define PI 3.141592653589793

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 x) {
  vec2 i = floor(x), f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0,0.0)), f.x),
             mix(hash(i + vec2(0.0,1.0)), hash(i + vec2(1.0,1.0)), f.x), f.y);
}
float fbm(vec2 p) {
  float v=0.0;
  v += .5 * noise(p); p *= 2.02;
  v += .25 * noise(p); p *= 2.04;
  v += .125 * noise(p); p *= 2.01;
  v += .0625 * noise(p);
  return v;
}
void main(){
  vec2 uv = (gl_FragCoord.xy - uResolution * 0.5) / uResolution.y;
  float t = uTime;
  float activity = clamp(uActivity, 0., 1.);
  float slow = t * (.16 + uMode * .12);
  vec2 p = uv * 1.55;
  p.y += .03 * sin(t * .41);
  p.x += .022 * sin(t * .2);
  float angle = atan(p.y, p.x);
  float dist = length(p);
  float warp = sin(angle * 3.0 + slow * 1.1) * .054
             + sin(angle * 5.0 - slow * .75) * .029
             + sin(angle * 8.0 + slow * .31) * .011;
  warp += (fbm(p * 3.6 + vec2(slow * .6,-slow * .28)) - .5) * (.12 + activity * .07);
  float radius = .78 + warp + activity * .085 * sin(angle * 4.0 + t * 2.1);
  float d = dist - radius;
  float inner = smoothstep(.065, -.085, d);
  float z = sqrt(max(.0, 1.0 - pow(dist / max(.24,radius), 2.0)));
  vec3 N = normalize(vec3(p.x * 1.02, p.y * 1.11, z * 1.1 + .001));
  float n = fbm(p * 4.1 + vec2(slow * .8, -slow * .3));
  float n2 = fbm(p * 6.1 + vec2(-slow * .46, slow * .71));
  vec3 L1 = normalize(vec3(-.48, .82, 1.1));
  vec3 L2 = normalize(vec3(.72, -.36, .86));
  float diffuse = pow(max(dot(N,L1),.0), 1.6);
  float spec1 = pow(max(dot(reflect(-L1,N),vec3(0.,0.,1.)),.0), 43.);
  float spec2 = pow(max(dot(reflect(-L2,N),vec3(0.,0.,1.)),.0), 18.);
  float fresnel = pow(1.0 - max(N.z, .0), 2.8);

  // Refracted, shifting light bands give the sculpture a layered depth.
  float flowing = sin(p.y * 12.0 + p.x * 6.7 + n * 15.0 - slow * 5.0);
  float flowing2 = sin(p.x * -9.0 + p.y * 14.0 + n2 * 19.0 + slow * 4.2);
  float layers = pow(max(.0,flowing * .5 + flowing2 * .32 + .18), 2.0);

  vec3 steel = vec3(.045,.068,.092);
  vec3 jade = vec3(.16,.40,.46);
  vec3 pearl = vec3(.69,.82,.89);
  vec3 lavender = vec3(.29,.32,.56);
  vec3 body = mix(steel, jade, clamp(n * 1.45 - .38,0.,1.));
  body = mix(body, lavender, clamp(n2 * .9 - .22,0.,.5));
  body += pearl * (diffuse * .19 + layers * .23);
  body += vec3(.68,.84,.97) * spec1 * .73;
  body += vec3(.45,.56,.9) * spec2 * .21;
  body += mix(vec3(.12,.34,.53),vec3(.62,.83,.85),n) * fresnel * (.46 + activity * .27);
  body += vec3(.16,.50,.55) * (activity * .08);

  // The glow is self-lit, so its transparency keeps the form floating in space.
  float edgeGlow = exp(-abs(d) * 8.0) * .14;
  float aura = exp(-max(d,.0)*4.6) * .075;
  vec3 bg = vec3(.009,.011,.018);
  bg += vec3(.016,.026,.035) * exp(-dot(uv,uv) * 1.9);
  vec3 color = bg;
  color += vec3(.12,.27,.34) * aura;
  color += vec3(.32,.53,.7) * edgeGlow;
  color = mix(color,body,inner * (.90 - n * .08));
  // Faint drifting fragments are a visual atmosphere, never mock telemetry.
  vec2 starGrid = floor((uv + vec2(t * .002,-t * .001)) * 65.0);
  vec2 local = fract((uv + vec2(t * .002,-t * .001)) * 65.0) - .5;
  float chance = step(.992,hash(starGrid));
  float dust = chance * smoothstep(.09,.0,length(local)) * .11 * (1.0 - inner);
  color += vec3(.28,.35,.45) * dust;

  // ACES-style tone map.
  color = (color*(2.51*color+.03))/(color*(2.43*color+.59)+.14);
  color = pow(clamp(color,.0,1.0),vec3(.93));
  outColor = vec4(color,1.0);
}`;

export function VoiceSculpture({ phase, level }: { phase: VoicePhase; level: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const live = useRef({ phase, level });
  useEffect(() => { live.current = { phase, level }; }, [phase, level]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, powerPreference: "low-power" });
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let stopped = false;
    let elapsed = 0;
    let lastTime = 0;

    function resize() {
      if (!canvas) return;
      const w = Math.max(1,canvas.clientWidth), h = Math.max(1,canvas.clientHeight);
      // Maximum pixels keep Android phones cool during long conversations.
      const scale = Math.min(window.devicePixelRatio || 1, 1.5, Math.sqrt(690000 / (w*h)));
      const pxw = Math.max(1,Math.floor(w*scale)), pxh = Math.max(1,Math.floor(h*scale));
      if (canvas.width !== pxw || canvas.height !== pxh) { canvas.width = pxw; canvas.height = pxh; }
      if (gl) gl.viewport(0,0,pxw,pxh);
    }
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    if (!gl) {
      const context = canvas.getContext("2d");
      if (!context) { observer.disconnect(); return; }
      const draw2D = (ms: number) => {
        if (stopped) return;
        const dt = Math.min(48, ms-lastTime); lastTime=ms;
        if (!reduced.matches) elapsed += Math.max(0,dt)/1000;
        const w=canvas.width,h=canvas.height,cx=w/2,cy=h/2;
        context.clearRect(0,0,w,h);
        context.fillStyle="#050608";context.fillRect(0,0,w,h);
        const radius = Math.min(w,h)*.31, act=live.current.phase==="listening"?live.current.level:0;
        context.save(); context.translate(cx,cy);
        const background = context.createRadialGradient(0,0,0,0,0,radius*1.7);
        background.addColorStop(0,"rgba(49,106,141,.16)");background.addColorStop(1,"rgba(0,0,0,0)");
        context.fillStyle=background;context.beginPath();context.arc(0,0,radius*1.7,0,Math.PI*2);context.fill();
        for(let k=0;k<19;k++){
          context.beginPath();
          for(let i=0;i<=180;i++){
            const a=i/180*Math.PI*2;
            const ripple=Math.sin(a*3+elapsed*.4+k*.2)*(.09+act*.2);
            const rr=radius*(.73+k*.011)*(1+ripple);
            const x=rr*Math.cos(a),y=rr*Math.sin(a)*(.87+Math.sin(k*.5)*.04);
            i?context.lineTo(x,y):context.moveTo(x,y);
          }
          context.closePath();context.strokeStyle=`rgba(132,206,226,${.07+(k%4)*.012})`;context.lineWidth=1.3;context.stroke();
        }
        const fill=context.createRadialGradient(-radius*.2,-radius*.2,1,0,0,radius*.83);
        fill.addColorStop(0,"rgba(174,224,230,.52)");fill.addColorStop(.45,"rgba(28,75,104,.23)");fill.addColorStop(1,"rgba(10,29,54,0)");
        context.fillStyle=fill;context.beginPath();context.ellipse(0,0,radius*.86,radius*.77,0,0,Math.PI*2);context.fill();
        context.restore();
        if (!reduced.matches) frame=requestAnimationFrame(draw2D);
      };
      frame=requestAnimationFrame(draw2D);
      return () => { stopped=true;cancelAnimationFrame(frame);observer.disconnect(); };
    }

    function compile(type: number, source: string) {
      const shader = gl!.createShader(type);
      if (!shader) return null;
      gl!.shaderSource(shader,source);
      gl!.compileShader(shader);
      if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
        console.warn("BACY-10 sculpture shader error",gl!.getShaderInfoLog(shader));
        gl!.deleteShader(shader);
        return null;
      }
      return shader;
    }
    const vs=compile(gl.VERTEX_SHADER,vertexShader),fs=compile(gl.FRAGMENT_SHADER,fragmentShader);
    if (!vs || !fs) {
      gl.clearColor(.01,.015,.02,1);gl.clear(gl.COLOR_BUFFER_BIT);
      observer.disconnect();
      return;
    }
    const program=gl.createProgram();
    if (!program){observer.disconnect();return;}
    gl.attachShader(program,vs);gl.attachShader(program,fs);
    gl.linkProgram(program);
    gl.deleteShader(vs);gl.deleteShader(fs);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS)){
      console.warn("BACY-10 sculpture link error",gl.getProgramInfoLog(program));
      gl.deleteProgram(program);observer.disconnect();return;
    }
    const buffer=gl.createBuffer();
    if(!buffer){gl.deleteProgram(program);observer.disconnect();return;}
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    gl.useProgram(program);
    const loc=gl.getAttribLocation(program,"aPosition");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
    const resolution=gl.getUniformLocation(program,"uResolution");
    const time=gl.getUniformLocation(program,"uTime");
    const activity=gl.getUniformLocation(program,"uActivity");
    const mode=gl.getUniformLocation(program,"uMode");
    const draw=(ms:number)=>{
      if(stopped)return;
      if(!document.hidden && (ms-lastTime > 32 || reduced.matches)){
        const delta=Math.min(70,ms-lastTime);
        if(!reduced.matches) elapsed+=Math.max(0,delta)/1000;
        lastTime=ms;
        gl.uniform2f(resolution,canvas.width,canvas.height);
        gl.uniform1f(time,elapsed);
        const state=live.current;
        const act=state.phase==="listening"?Math.min(1,state.level):
          state.phase==="speaking"?.35:state.phase==="thinking"?.2:state.phase==="error"?.025:.07;
        gl.uniform1f(activity,act);
        gl.uniform1f(mode,state.phase==="listening"?1:state.phase==="speaking"?1.4:state.phase==="thinking"?.85:0);
        gl.drawArrays(gl.TRIANGLES,0,6);
      }
      if(!reduced.matches)frame=requestAnimationFrame(draw);
    };
    frame=requestAnimationFrame(draw);
    const onMotion=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(draw);};
    reduced.addEventListener("change",onMotion);
    return()=>{
      stopped=true;cancelAnimationFrame(frame);reduced.removeEventListener("change",onMotion);
      observer.disconnect();gl.deleteBuffer(buffer);gl.deleteProgram(program);
    };
  }, []);

  return <canvas className="voice-sculpture" ref={canvasRef} aria-hidden="true" />;
}
