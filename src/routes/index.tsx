import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { VoiceSculpture, type VoicePhase } from "@/components/VoiceSculpture";
import { askBacy } from "@/lib/bacy.functions";
import { speakBacy } from "@/lib/bacy.speech.functions";
import { readSpeechResults, type BrowserSpeechResult } from "@/lib/speech-results";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "BACY-10 — Personal voice intelligence" },
      { name: "description", content: "BACY-10. A private voice-first British assistant." },
      { property: "og:title", content: "BACY-10 — Personal voice intelligence" },
      { property: "og:description", content: "A private voice-first British assistant, ready at your service." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "theme-color", content: "#050608" },
    ],
  }),
  component: BacyVoice,
});

type HistoryMessage = { role: "user" | "assistant"; content: string };
type SpeechEvent = { results: ArrayLike<BrowserSpeechResult>; resultIndex: number };
type SpeechError = { error: string };
type Recognizer = {
  lang: string; continuous: boolean; interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechError) => void) | null;
  onaudiostart?: (() => void) | null;
  onspeechstart?: (() => void) | null;
  onspeechend?: (() => void) | null;
  start: () => void; stop: () => void; abort: () => void;
};
type SpeechBrowser = Window & {
  SpeechRecognition?: new () => Recognizer;
  webkitSpeechRecognition?: new () => Recognizer;
};

function BacyVoice() {
  const ask = useServerFn(askBacy);
  const speak = useServerFn(speakBacy);
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [level, setLevel] = useState(0);
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");
  const [textMode, setTextMode] = useState(false);
  const [draft, setDraft] = useState("");
  const [speechAvailable, setSpeechAvailable] = useState(true);
  const [voiceLabel, setVoiceLabel] = useState("");
  const recognizer = useRef<Recognizer | null>(null);
  // Recognition controls the microphone itself. A second getUserMedia capture
  // can disrupt the browser recognition service on Android.
  const recognitionWatchdog = useRef<number | null>(null);
  const recognitionRetry = useRef<number | null>(null);
  const manuallyStopped = useRef(false);
  const history = useRef<HistoryMessage[]>([]);
  const mounted = useRef(true);
  const firstTap = useRef(false);
  const busy = useRef(false);
  const audioContext = useRef<AudioContext | null>(null);
  const activeAudio = useRef<AudioBufferSourceNode | null>(null);
  const audioRequestNumber = useRef(0);

  useEffect(() => {
    mounted.current = true;
    const Speech = (window as SpeechBrowser).SpeechRecognition ?? (window as SpeechBrowser).webkitSpeechRecognition;
    setSpeechAvailable(Boolean(Speech));
    return () => {
      mounted.current = false;
      if (recognitionWatchdog.current !== null) clearTimeout(recognitionWatchdog.current);
      if (recognitionRetry.current !== null) clearTimeout(recognitionRetry.current);
      recognizer.current?.abort();
      audioRequestNumber.current++;
      try { activeAudio.current?.stop(); } catch {}
      if (audioContext.current) void audioContext.current.close().catch(() => {});
    };
  }, []);


  function unlockAudio() {
    try {
      if (!audioContext.current || audioContext.current.state === "closed") {
        audioContext.current = new AudioContext();
      }
      const context = audioContext.current;
      // Unlock the speaker synchronously during a real tap.
      void context.resume().catch(() => {});
      const silent = context.createBufferSource();
      silent.buffer = context.createBuffer(1, 1, 22050);
      silent.connect(context.destination);
      silent.start();
    } catch {
      // Real playback errors will be reported when the audio is returned.
    }
  }

  async function say(text: string) {
    if (!mounted.current) return;
    const request = ++audioRequestNumber.current;
    try { activeAudio.current?.stop(); } catch {}
    activeAudio.current = null;
    setError("");
    setPhase("thinking");
    try {
      const result = await speak({ data: { text: text.slice(0, 1600) } });
      if (!mounted.current || request !== audioRequestNumber.current) return;
      if (!("audio" in result) || !result.audio) {
        setError(result.error || "The AI voice service returned no audio. Your reply is available in text.");
        setPhase("error");
        return;
      }
      const ctx = audioContext.current;
      if (!ctx || ctx.state === "closed") {
        setError("The speaker could not be unlocked. Tap BACY-10 in Chrome to allow audio playback.");
        setPhase("error");
        return;
      }
      const bytes = Uint8Array.from(Array.from(atob(result.audio)), character => character.charCodeAt(0));
      const decoded = await ctx.decodeAudioData(bytes.buffer);
      if (!mounted.current || request !== audioRequestNumber.current) return;
      await ctx.resume();
      if (ctx.state !== "running") throw new Error("Audio output is suspended");
      const source = ctx.createBufferSource();
      source.buffer = decoded;
      source.connect(ctx.destination);
      activeAudio.current = source;
      source.onended = () => {
        if (activeAudio.current === source) {
          activeAudio.current = null;
          if (mounted.current) setPhase("idle");
        }
      };
      setVoiceLabel("Natural British voice");
      setPhase("speaking");
      source.start();
    } catch (err) {
      if (!mounted.current || request !== audioRequestNumber.current) return;
      console.error("BACY-10 real speech playback failed", err instanceof Error ? err.name : "unknown");
      setError("Real AI voice audio could not play in this browser. Open BACY-10 directly in Chrome.");
      setPhase("error");
    }
  }

  async function send(input: string) {
    const content = input.trim();
    if (!content || busy.current || !mounted.current) return;
    busy.current = true;
    setLevel(0);
    setHeard(content);
    setReply("");
    setError("");
    setPhase("thinking");
    const next: HistoryMessage[] = [...history.current, { role: "user" as const, content }].slice(-12);
    try {
      // Only real responses returned by the configured Lovable AI gateway are spoken.
      const result = await ask({ data: next });
      if (!mounted.current) return;
      if (!("reply" in result) || !result.reply) {
        setError("error" in result ? result.error : "No reply came back from the AI service. Please try again.");
        setPhase("error");
        return;
      }
      const answer = result.reply.trim();
      history.current = [...next, { role: "assistant" as const, content: answer }].slice(-12);
      setReply(answer);
      say(answer);
    } catch {
      if (!mounted.current) return;
      setError("BACY-10 could not reach the AI service. Please check the connection and try again.");
      setPhase("error");
    } finally {
      busy.current = false;
    }
  }

  function beginListening(attempt = 0) {
    if (busy.current || recognizer.current || !mounted.current) return;
    if (recognitionRetry.current !== null) {
      window.clearTimeout(recognitionRetry.current);
      recognitionRetry.current = null;
    }
    const Speech = (window as SpeechBrowser).SpeechRecognition ?? (window as SpeechBrowser).webkitSpeechRecognition;
    if (!Speech) {
      setSpeechAvailable(false);
      setError("This browser cannot recognise speech. Open the direct BACY-10 link in Chrome on Android, or type instead.");
      setPhase("error");
      return;
    }
    if (!window.isSecureContext) {
      setError("Voice needs HTTPS. Open the direct BACY-10 preview link in Chrome.");
      setPhase("error");
      return;
    }
    if (attempt === 0) {
      unlockAudio();
      audioRequestNumber.current++;
      try { activeAudio.current?.stop(); } catch {}
      activeAudio.current = null;
      manuallyStopped.current = false;
      firstTap.current = true;
      setHeard("");
      setReply("");
      setError("");
    }
    setLevel(0);
    const instance = new Speech();
    recognizer.current = instance;
    // Listening language follows the English-language device; speaking remains
    // a separate British text-to-speech setting.
    instance.lang = /^en([-_]|$)/i.test(navigator.language) ? navigator.language : "en-GB";
    instance.continuous = false;
    instance.interimResults = true;
    let bestText = "";
    let finalText = "";
    let failed = false;
    let retryNoSpeech = false;
    let started = false;
    instance.onstart = () => {
      started = true;
      if (recognitionWatchdog.current !== null) {
        window.clearTimeout(recognitionWatchdog.current);
        recognitionWatchdog.current = null;
      }
      if (mounted.current) setPhase("listening");
    };
    instance.onaudiostart = () => {
      if (mounted.current) setPhase("listening");
    };
    instance.onspeechstart = () => {
      if (mounted.current) setLevel(0.8);
    };
    instance.onspeechend = () => {
      if (mounted.current) setLevel(0.1);
    };
    instance.onresult = (event) => {
      const transcript = readSpeechResults(event.results);
      finalText = transcript.final;
      bestText = transcript.best;
      if (mounted.current) {
        setHeard(transcript.best);
        // Visual response is driven by recognised speech, not synthetic volume.
        if (transcript.best) setLevel(0.5);
      }
    };
    instance.onerror = (event) => {
      if (event.error === "aborted" && manuallyStopped.current) return;
      if (event.error === "no-speech" && attempt < 1 && !manuallyStopped.current) {
        retryNoSpeech = true;
        return;
      }
      failed = true;
      if (!mounted.current) return;
      const message = event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "Microphone access was denied. Open BACY-10 directly in Chrome and allow the microphone."
        : event.error === "audio-capture"
          ? "No usable microphone was detected by the browser. Check microphone access on Android."
          : event.error === "network"
            ? "The browser's speech-recognition service could not connect. Try Chrome with internet access."
            : event.error === "no-speech"
              ? "The microphone stopped without recognising any words. Speak as you tap, or choose Type instead."
              : event.error === "aborted"
                ? "Voice recognition was interrupted by the browser. Tap to try again."
                : "Voice recognition error: " + event.error + ". Try Chrome or type instead.";
      setError(message);
      setPhase("error");
    };
    instance.onend = () => {
      if (recognitionWatchdog.current !== null) {
        window.clearTimeout(recognitionWatchdog.current);
        recognitionWatchdog.current = null;
      }
      if (recognizer.current === instance) recognizer.current = null;
      if (!mounted.current) return;
      setLevel(0);
      // Android can return a valid interim word but finish before marking isFinal.
      const transcript = bestText.trim() || finalText.trim();
      if (transcript && !failed) {
        void send(transcript);
      } else if (retryNoSpeech && !manuallyStopped.current) {
        // Retry once only. Never silently spin the microphone indefinitely.
        setPhase("listening");
        recognitionRetry.current = window.setTimeout(() => {
          recognitionRetry.current = null;
          beginListening(attempt + 1);
        }, 200);
      } else if (!failed && !manuallyStopped.current) {
        setError(started
          ? "The microphone session ended but the browser returned no words. Try Chrome directly, or choose Type instead."
          : "The browser closed the microphone before listening started. Open the direct link in Chrome.");
        setPhase("error");
      } else if (!failed) {
        setPhase("idle");
      }
    };
    try {
      setPhase("listening");
      instance.start();
      recognitionWatchdog.current = window.setTimeout(() => {
        recognitionWatchdog.current = null;
        if (!mounted.current || recognizer.current !== instance || started) return;
        failed = true;
        setError("The browser did not start listening. Allow microphone permission and open the standalone preview in Chrome.");
        setPhase("error");
        recognizer.current = null;
        instance.abort();
      }, 14000);
    } catch (caught) {
      recognizer.current = null;
      setLevel(0);
      const detail = caught instanceof Error ? caught.message : "unknown browser error";
      setError("Could not start voice recognition: " + detail + ". Try Chrome and allow the microphone.");
      setPhase("error");
    }
  }

  function tap() {
    if (textMode) return;
    if (phase === "listening") {
      if (recognizer.current) {
        manuallyStopped.current = true;
        recognizer.current.stop();
      } else if (recognitionRetry.current !== null) {
        window.clearTimeout(recognitionRetry.current);
        recognitionRetry.current = null;
        setPhase("idle");
      }
      return;
    }
    if (phase === "thinking") return;
    if (phase === "speaking") {
      audioRequestNumber.current++;
      try { activeAudio.current?.stop(); } catch {}
      activeAudio.current = null;
      setPhase("idle");
    }
    unlockAudio();
    beginListening();
  }

  function testSpeaker() {
    // Explicit real-AI speaker test, not a fictional assistant reply.
    unlockAudio();
    const testLine = "Good day, sir. This is BACY-10. I'm right here, ready to help.";
    setError("");
    setReply(testLine);
    void say(testLine);
  }

  function submitTyped(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;
    setDraft("");
    setTextMode(false);
    unlockAudio();
    void send(content);
  }

  const stateText = phase === "listening" ? "Listening" :
    phase === "thinking" ? (reply ? "Preparing AI voice" : "Thinking") :
    phase === "speaking" ? "Speaking" :
    phase === "error" ? "Connection needs attention" : "At your service";
  const instruction = phase === "listening" ? "Speak naturally. Tap to finish." :
    phase === "thinking" ? (reply ? "Generating speech audio" : "Considering your request") :
    phase === "speaking" ? "Tap to interrupt and speak" :
    phase === "error" ? "Tap to try again" : "Tap anywhere to speak";

  return (
    <main className={`bacy-voice-screen phase-${phase}`}>
      <div className="voice-grain" aria-hidden="true" />
      <div className="voice-top" aria-hidden="true">
        <span className="voice-monogram">BACY<span>—</span>10</span>
        <span className="voice-signature">PERSONAL INTELLIGENCE</span>
      </div>
      <VoiceSculpture phase={phase} level={level} />
      <button type="button" className="voice-touch-layer" onClick={tap}
        disabled={phase === "thinking" || textMode}
        aria-label={phase === "listening" ? "Finish listening" : "Speak with BACY-10"} />
      <section className="voice-floor" aria-live="polite">
        <div className="voice-phase"><i className={`voice-led led-${phase}`} aria-hidden="true" />{stateText}</div>
        {error ? <p className="voice-error" role="alert">{error}</p> :
          <p className="voice-live-text">{phase === "listening" ? (heard || "I'm listening, sir.") :
            phase === "thinking" ? heard :
            reply || (firstTap.current && heard ? heard : "")}</p>}
        {!textMode && <p className="voice-instruction">{instruction}</p>}
        {!textMode && <button className="voice-text-fallback voice-hear-button" type="button" onClick={testSpeaker}>Hear BACY-10</button>}
        {textMode && <form className="voice-text-form" onSubmit={submitTyped}>
          <label className="voice-sr-only" htmlFor="voice-prompt">Message to BACY-10</label>
          <input id="voice-prompt" value={draft} onChange={(event) => setDraft(event.target.value)}
            autoFocus placeholder="Ask BACY-10…" maxLength={2000} />
          <button type="submit" disabled={!draft.trim()}>Send</button>
          <button type="button" onClick={() => setTextMode(false)}>Close</button>
        </form>}
        {(phase === "error" || !speechAvailable) && !textMode &&
          <div className="voice-recovery">
            <button className="voice-text-fallback" type="button" onClick={() => setTextMode(true)}>Type instead</button>
          </div>}
      </section>
      <span className="voice-footer" aria-hidden="true">{voiceLabel && phase === "speaking" ? "AI-GENERATED · " + voiceLabel : "BACY-10 / AI-GENERATED VOICE"}</span>
    </main>
  );
}
