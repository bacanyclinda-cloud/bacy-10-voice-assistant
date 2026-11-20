import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { askBacyBackup, getBackupVoiceStatus, speakBacyBackup } from "@/lib/bacy-backup.functions";
import { speakBacy } from "@/lib/bacy.speech.functions";
import { BACKUP_VOICES, parseVoiceSwitch, type BackupVoice } from "@/lib/bacy-backup.voices";

export const Route = createFileRoute("/backup")({
  head: () => ({ meta: [{ title: "BACY-10 — Backup Voice Studio" }] }),
  component: BackupStudio,
});

type ChatMessage = { role: "user" | "assistant"; content: string };
type SpeechItem = { isFinal: boolean; 0: { transcript: string } };
type Recognizer = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { results: ArrayLike<SpeechItem> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void; stop(): void; abort(): void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => Recognizer;
  webkitSpeechRecognition?: new () => Recognizer;
};
type TtsResponse = { audio: string; mediaType?: string } | { error: string };

const surface: React.CSSProperties = {
  minHeight: "100dvh", padding: "28px 20px 65px", color: "#ebf6ff",
  background: "radial-gradient(ellipse at 50% 25%,#123b5d,#080f1b 56%,#04070c)",
  fontFamily: "system-ui, sans-serif",
};
const panel: React.CSSProperties = {
  background: "rgba(8,20,34,.86)", border: "1px solid #284760",
  padding: 17, borderRadius: 18, marginTop: 17,
};
const voiceButton: React.CSSProperties = {
  background: "#132b40", color: "#e5f7ff", border: "1px solid #41627b",
  borderRadius: 12, padding: "13px 10px", fontWeight: 600, flex: 1,
};
const goButton: React.CSSProperties = {
  background: "#a8e7ff", color: "#04131e", border: 0,
  padding: "12px 17px", borderRadius: 12, fontWeight: 700,
};

function BackupStudio() {
  const ask = useServerFn(askBacyBackup);
  const speakBackup = useServerFn(speakBacyBackup);
  const speakOriginal = useServerFn(speakBacy);
  const fetchStatus = useServerFn(getBackupVoiceStatus);

  const [voice, setVoiceState] = useState<BackupVoice>("voice1");
  const [expressive, setExpressive] = useState(false);
  const [capabilities, setCapabilities] = useState({ voice2: false, voice3: false });
  const [phase, setPhase] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [message, setMessage] = useState("");
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [microphoneSupported, setMicrophoneSupported] = useState(true);
  const selectedVoice = useRef<BackupVoice>("voice1");
  const availability = useRef({ voice2: false, voice3: false });
  const conversation = useRef<ChatMessage[]>([]);
  const audio = useRef<AudioContext | null>(null);
  const currentSound = useRef<AudioBufferSourceNode | null>(null);
  const currentMic = useRef<Recognizer | null>(null);
  const playingId = useRef(0);
  const mounted = useRef(true);
  const busy = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const saved = localStorage.getItem("bacy10-backup-selected-voice");
    if (saved === "voice1" || saved === "voice2" || saved === "voice3") {
      selectedVoice.current = saved; setVoiceState(saved);
    }
    setMicrophoneSupported(Boolean((window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition));
    void fetchStatus().then(result => {
      if (!mounted.current) return;
      const next = { voice2: result.voice2, voice3: result.voice3 };
      availability.current = next; setCapabilities(next);
    }).catch(() => setError("Could not check which voice providers are configured."));
    return () => {
      mounted.current = false;
      playingId.current++;
      currentMic.current?.abort();
      try { currentSound.current?.stop(); } catch { /* already stopped */ }
      if (audio.current) void audio.current.close().catch(() => {});
    };
  }, [fetchStatus]);

  function unlockAudio() {
    try {
      if (!audio.current || audio.current.state === "closed") audio.current = new AudioContext();
      void audio.current.resume();
    } catch { setError("Sound is blocked. Try opening this page directly in Chrome."); }
  }
  function stopAudio() {
    playingId.current++;
    try { currentSound.current?.stop(); } catch { /* already stopped */ }
    currentSound.current = null;
  }

  const say = useCallback(async (words: string, chosen: BackupVoice) => {
    const requestId = ++playingId.current;
    try { currentSound.current?.stop(); } catch { /* already stopped */ }
    currentSound.current = null;
    try {
      let response: TtsResponse;
      if (chosen === "voice1") {
        response = await speakOriginal({ data: { text: words.slice(0, 1600) } });
      } else {
        response = await speakBackup({ data: { voice: chosen, text: words.slice(0, 1200) } });
      }
      if (!mounted.current || requestId !== playingId.current) return;
      if ("error" in response || !response.audio) {
        setError("error" in response ? response.error : "No real speech audio returned.");
        setPhase("idle");
        return;
      }
      const ctx = audio.current;
      if (!ctx) throw Error("Tap to activate the speaker");
      const decoded = await ctx.decodeAudioData(Uint8Array.from(atob(response.audio), c => c.charCodeAt(0)).buffer);
      if (!mounted.current || requestId !== playingId.current) return;
      await ctx.resume();
      if (ctx.state !== "running") throw Error("Speaker is suspended");
      const source = ctx.createBufferSource();
      source.buffer = decoded;
      source.connect(ctx.destination);
      currentSound.current = source;
      source.onended = () => {
        if (currentSound.current === source) {
          currentSound.current = null;
          if (mounted.current) setPhase("idle");
        }
      };
      setPhase("speaking");
      source.start();
    } catch {
      if (!mounted.current || requestId !== playingId.current) return;
      setError("Could not play speech, but your text reply remains available. Tap again or try Chrome.");
      setPhase("idle");
    }
  }, [speakOriginal, speakBackup]);

  function chooseVoice(next: BackupVoice, announce = true) {
    unlockAudio();
    if (next === "voice3" && !availability.current.voice3) {
      setError("ElevenLabs needs ELEVENLABS_API_KEY saved privately in Lovable Secrets.");
      return;
    }
    if (next === "voice2" && !availability.current.voice2) {
      setError("Voice 2's AI voice provider is not configured.");
      return;
    }
    stopAudio();
    setError("");
    selectedVoice.current = next;
    setVoiceState(next);
    localStorage.setItem("bacy10-backup-selected-voice", next);
    if (announce) {
      const text = next === "voice1" ? "The original web voice is selected, sir." :
        next === "voice2" ? "Voice two is ready, sir." :
          "Florence is ready, sir. How can I help you?";
      setReply(text);
      void say(text, next);
    }
  }

  async function send(text: string) {
    const prompt = text.trim();
    if (!prompt || busy.current) return;
    unlockAudio();
    stopAudio();
    setError(""); setHeard(prompt);
    const command = parseVoiceSwitch(prompt);
    if (command) { chooseVoice(command); return; }
    busy.current = true;
    setPhase("thinking");
    const history: ChatMessage[] = [...conversation.current, { role: "user", content: prompt }].slice(-12);
    try {
      const answer = await ask({ data: { history, expressive } });
      if (!mounted.current) return;
      if (!("reply" in answer) || !answer.reply) {
        setError("error" in answer ? answer.error : "The assistant returned no answer.");
        setPhase("idle");
        return;
      }
      const responseText = answer.reply.trim();
      conversation.current = [...history, { role: "assistant", content: responseText }].slice(-12);
      setReply(responseText);
      await say(responseText, selectedVoice.current);
    } catch {
      if (mounted.current) {
        setPhase("idle"); setError("The backup conversation is unavailable. Please try again.");
      }
    } finally { busy.current = false; }
  }

  function microphone() {
    unlockAudio();
    stopAudio();
    if (currentMic.current) { currentMic.current.stop(); return; }
    const Speech = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!Speech || !window.isSecureContext) {
      setError("Microphone unavailable. Use the text field below or open in Chrome with HTTPS.");
      return;
    }
    if (busy.current) return;
    setError("");
    const listener = new Speech();
    currentMic.current = listener;
    listener.lang = /^en([-_]|$)/i.test(navigator.language) ? navigator.language : "en-GB";
    listener.continuous = false;
    listener.interimResults = true;
    let finalText = "", failed = false;
    listener.onresult = event => {
      const parts: string[] = [];
      for (let i = 0; i < event.results.length; i++) if (event.results[i]?.[0]) parts.push(event.results[i][0].transcript);
      finalText = parts.join(" ").trim();
      setHeard(finalText);
    };
    listener.onerror = event => {
      failed = true;
      setError(event.error === "not-allowed" ? "Allow Chrome to use your microphone." : "Voice input error: " + event.error);
    };
    listener.onend = () => {
      currentMic.current = null;
      if (!mounted.current) return;
      setPhase("idle");
      if (!failed && finalText) void send(finalText);
    };
    try { setPhase("listening"); listener.start(); }
    catch { currentMic.current = null; setPhase("idle"); setError("Microphone could not start."); }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = message.trim();
    if (!text) return;
    unlockAudio();
    setMessage("");
    void send(text);
  }

  return (
    <main style={surface}>
      <div style={{ maxWidth: 620, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <small style={{ letterSpacing: 3, color: "#83b4d3" }}>BACY—10 / SECONDARY</small>
          <a href="/" style={{ color: "#98d9f7", fontSize: 13 }}>Original assistant ↗</a>
        </div>
        <h1 style={{ fontSize: 29, fontWeight: 500, marginTop: 24, marginBottom: 6 }}>Backup voice studio</h1>
        <p style={{ color: "#9cb5ca", fontSize: 13, lineHeight: 1.6 }}>
          A separate browser-based backup. It does not replace the existing Android LiveKit voice, personality or settings.
        </p>
        <div style={{
          width: 158, height: 158, margin: "27px auto 20px", borderRadius: "50%",
          background: "radial-gradient(circle at 42% 32%,#77c2e7,#2a658f 26%,#0a2642 65%,#070c15 82%)",
          border: "1px solid #4c83b2", boxShadow: "0 0 66px #27678b70", opacity: phase === "thinking" ? .55 : 1,
        }} aria-hidden="true" />
        <div style={{ textAlign: "center", fontSize: 12, color: "#a2c8db" }}>● {phase.toUpperCase()} · {BACKUP_VOICES[voice].label}</div>
        <section style={panel}>
          <div style={{ fontSize: 12, color: "#8fa9c3", marginBottom: 12 }}>SELECT VOICE — ONLY FOR THIS BACKUP PAGE</div>
          <div style={{ display: "flex", gap: 7 }}>
            {(["voice1", "voice2", "voice3"] as const).map(v => (
              <button key={v} type="button" onClick={() => chooseVoice(v)}
                aria-pressed={voice === v}
                style={{ ...voiceButton, borderColor: voice === v ? "#a3e7ff" : "#41627b",
                  background: voice === v ? "#245374" : "#132b40" }}>
                {v === "voice1" ? "Original" : v === "voice2" ? "Voice 2" : "Girl voice"}
              </button>
            ))}
          </div>
          <p style={{ fontSize: 12, color: "#b1c7d9", lineHeight: 1.5, marginBottom: 0 }}>
            {voice === "voice3" ? "Florence — natural British female voice via ElevenLabs." : BACKUP_VOICES[voice].detail}
          </p>
          <p style={{ color: "#7fabbf", fontSize: 11 }}>
            Voice 2: {capabilities.voice2 ? "configured" : "not configured"} · ElevenLabs: {capabilities.voice3 ? "configured" : "needs API key"}
          </p>
        </section>
        <section style={panel}>
          <label style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 13 }}>
            <input type="checkbox" checked={expressive} onChange={e => setExpressive(e.target.checked)} />
            More expressive opinions and conversational warmth (optional)
          </label>
          <p style={{ fontSize: 11, color: "#9cb5ca" }}>
            You can ask philosophical questions and get a reasoned choice. AI doesn't have human feelings.
          </p>
        </section>
        <section style={panel}>
          <p style={{ minHeight: 24, fontSize: 13, color: "#a4c6dd", whiteSpace: "pre-wrap" }}>{heard ? "You: " + heard : "Say: BACY-10, switch to voice three"}</p>
          <div aria-live="polite" style={{ minHeight: 62, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
            {reply || "I'm here whenever you need me."}
          </div>
          {error && <p role="alert" style={{ color: "#ffd89f", lineHeight: 1.5, fontSize: 13 }}>{error}</p>}
          <button type="button" onClick={microphone} disabled={phase === "thinking"}
            style={{ ...goButton, width: "100%", marginTop: 18 }}>
            {phase === "listening" ? "Stop listening" : microphoneSupported ? "🎙 Talk to BACY-10" : "Microphone unavailable"}
          </button>
          <form onSubmit={submit} style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <label htmlFor="backup-message" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden" }}>Your message</label>
            <input id="backup-message" value={message} onChange={e => setMessage(e.target.value)}
              placeholder="Type a message or voice command" maxLength={2000}
              style={{ minWidth: 0, flex: 1, borderRadius: 10, background: "#071522", color: "white",
                border: "1px solid #38566d", padding: 12, fontSize: 14 }} />
            <button style={goButton} type="submit" disabled={phase === "thinking"}>Send</button>
          </form>
          <p style={{ fontSize: 11, color: "#829fb3", marginBottom: 0 }}>
            Voice 3 uses your ElevenLabs allowance. This page uses Lovable AI for conversation, independently of LiveKit.
          </p>
        </section>
      </div>
    </main>
  );
}
