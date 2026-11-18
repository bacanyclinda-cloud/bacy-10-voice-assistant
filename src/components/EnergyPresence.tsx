import { useEffect, useRef } from "react";

/**
 * An original, high-density canvas presence. No static reactor art, no GPU or
 * microphone permissions of its own: it follows the actual assistant state.
 */
export type PresenceMode = "idle" | "listening" | "speaking" | "thinking" | "standby";

export function EnergyPresence({
  mode,
  level,
  onActivate,
  disabled = false,
}: {
  mode: PresenceMode;
  level: number;
  onActivate: () => void;
  disabled?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const liveRef = useRef({ mode, level });

  useEffect(() => {
    liveRef.current = { mode, level };
  }, [mode, level]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d", { alpha: true });
    if (!canvas || !ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let width = 0;
    let height = 0;
    let dpr = 1;
    let frame = 0;
    let lastFrame = -Infinity;
    let stopped = false;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      render(performance.now());
    };

    const render = (timestamp: number) => {
      if (stopped) return;
      const { mode: current, level: mic } = liveRef.current;
      const t = reduceMotion.matches ? 0 : timestamp * 0.001;
      const activity = current === "listening"
        ? Math.min(1, 0.22 + mic * 2.1)
        : current === "speaking" ? 0.6 + Math.sin(t * 5.4) * 0.18
        : current === "thinking" ? 0.42
        : current === "standby" ? 0.035 : 0.14;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      const cx = width / 2;
      const cy = height / 2;
      const r = Math.min(width, height) * 0.285;
      const drift = Math.sin(t * 0.58) * r * 0.045;

      // Quiet, sparse dust gives the object a real sense of depth.
      for (let i = 0; i < 60; i += 1) {
        const theta = i * 2.3999632297;
        const distance = r * (1.24 + ((i * 37) % 31) / 55);
        const x = cx + Math.cos(theta + t * 0.018) * distance;
        const y = cy + Math.sin(theta + t * 0.015) * distance * 0.87;
        const alpha = (0.07 + (i % 7) * 0.016) * (current === "standby" ? 0.35 : 1);
        ctx.fillStyle = `rgba(146, 232, 215, ${alpha})`;
        ctx.beginPath();
        ctx.arc(x, y, i % 11 === 0 ? 1.35 : 0.7, 0, Math.PI * 2);
        ctx.fill();
      }

      // The center is a soft illuminated volume, not a flat icon.
      const halo = ctx.createRadialGradient(cx, cy + drift, r * 0.05, cx, cy, r * 1.53);
      halo.addColorStop(0, `rgba(187, 253, 229, ${0.10 + activity * 0.12})`);
      halo.addColorStop(0.3, `rgba(53, 208, 183, ${0.075 + activity * 0.11})`);
      halo.addColorStop(0.68, "rgba(10, 85, 91, 0.085)");
      halo.addColorStop(1, "rgba(7, 23, 32, 0)");
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy + drift, r * 1.54, 0, Math.PI * 2);
      ctx.fill();

      ctx.save();
      ctx.globalCompositeOperation = "lighter";

      // Flowing, three-dimensional filaments; each travels at a different angle.
      for (let strand = 0; strand < 48; strand += 1) {
        const normalized = strand / 47;
        const tilt = strand * 2.39996;
        const thickness = 0.6 + (strand % 5) * 0.18;
        const radius = r * (0.53 + normalized * 0.68);
        const depth = Math.sin(tilt + t * 0.27);
        ctx.beginPath();
        for (let point = 0; point <= 152; point += 1) {
          const a = (point / 152) * Math.PI * 2;
          const ripple = Math.sin(a * 3 + tilt * 1.5 + t * (0.42 + normalized * 0.65)) * (0.045 + activity * 0.085)
            + Math.sin(a * 7 - t * 0.8 + strand) * 0.022;
          const radial = radius * (1 + ripple);
          const x = cx + Math.cos(a + tilt * 0.11) * radial * (0.91 + Math.abs(depth) * 0.12);
          const y = cy + drift + Math.sin(a + tilt * 0.11) * radial * (0.58 + Math.abs(depth) * 0.25)
            + Math.cos(a * 2.1 + tilt + t * 0.33) * r * 0.055;
          if (point === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        const opacity = (0.09 + (1 - normalized) * 0.14 + activity * 0.13) * (current === "standby" ? 0.35 : 1);
        ctx.strokeStyle = strand % 7 === 0
          ? `rgba(232, 224, 192, ${opacity})`
          : strand % 3 === 0
            ? `rgba(101, 184, 243, ${opacity})`
            : `rgba(120, 255, 220, ${opacity})`;
        ctx.lineWidth = thickness;
        ctx.stroke();
      }

      // The inner ribbons flex and brighten with the microphone or spoken reply.
      for (let i = 0; i < 9; i += 1) {
        ctx.beginPath();
        const turn = i * 0.65 + t * (0.36 + activity * 0.3);
        for (let j = 0; j < 130; j += 1) {
          const pct = j / 129;
          const a = pct * Math.PI * 2;
          const wave = Math.sin(5 * a + turn) * r * (0.025 + activity * 0.065);
          const x = cx + (r * 0.3 + i * r * 0.047 + wave) * Math.cos(a + turn * 0.14);
          const y = cy + drift + (r * 0.28 + i * r * 0.037 + wave) * Math.sin(a + turn * 0.14) * 0.72;
          if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(180, 255, 234, ${0.055 + activity * 0.085})`;
        ctx.lineWidth = 0.9;
        ctx.stroke();
      }

      const core = ctx.createRadialGradient(cx - r * 0.08, cy - r * 0.13 + drift, 0, cx, cy + drift, r * 0.57);
      core.addColorStop(0, `rgba(219, 255, 238, ${0.33 + activity * 0.22})`);
      core.addColorStop(0.18, `rgba(92, 235, 207, ${0.18 + activity * 0.12})`);
      core.addColorStop(0.55, "rgba(35, 163, 157, 0.045)");
      core.addColorStop(1, "rgba(19, 100, 116, 0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(cx, cy + drift, r * 0.61, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    const loop = (timestamp: number) => {
      if (stopped) return;
      if (timestamp - lastFrame >= 32) {
        render(timestamp);
        lastFrame = timestamp;
      }
      if (!reduceMotion.matches) frame = requestAnimationFrame(loop);
    };
    const updateMotion = () => {
      cancelAnimationFrame(frame);
      if (reduceMotion.matches) render(0);
      else frame = requestAnimationFrame(loop);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    reduceMotion.addEventListener("change", updateMotion);
    resize();
    updateMotion();
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      reduceMotion.removeEventListener("change", updateMotion);
    };
  }, []);

  return (
    <button
      type="button"
      className={`presence-trigger presence-${mode}`}
      onClick={onActivate}
      disabled={disabled}
      aria-label={mode === "listening" ? "Stop listening" : "Start listening to BACY-10"}
      title={mode === "listening" ? "Stop listening" : "Tap to speak"}
    >
      <span className="presence-space" aria-hidden="true" />
      <canvas ref={canvasRef} className="presence-canvas" aria-hidden="true" />
      <span className="presence-crosshair" aria-hidden="true" />
    </button>
  );
}
