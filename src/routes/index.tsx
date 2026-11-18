import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { VoiceSculpture, type VoicePhase } from "@/components/VoiceSculpture";
import { askBacy } from "@/lib/bacy.functions";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "BACY-10 — Personal voice intelligence" },
      { name: "description", content: "BACY-10. A private voice-first British assistant." },
      { name: "theme-color", content: "#050608" },
    ],
  }),
  component: BacyVoice,
});

type HistoryMessage = { role: "user" | "assistant"; content: string };
type SpeechResult = { isFinal: boolean; 0: { transcript: string } };
type SpeechEvent = { results: ArrayLike<SpeechResult>; resultIndex: number };
type SpeechError = { error: string };
type Recognizer = {
  lang: string; continuous: boolean; interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechError) => void) | null;
  start: () => void; stop: () => void; abort: () => void;
};
type SpeechBrowser = Window & {
  SpeechRecognition?: new () => Recognizer;
  webkitSpeechRecognition?: new () => Recognizer;
};

function BacyVoice() {
  const ask = useServerFn(askBacy);
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
  const stream = useRef<MediaStream | null>(null);
  const meterContext = useRef<AudioContext | null>(null);
  const meterFrame = useRef<number | null>(null);
  const history = useRef<HistoryMessage[]>([]);
  const mounted = useRef(true);
  const firstTap = useRef(false);
  const busy = useRef(false);

  function stopMeter() {
    if (meterFrame.current !== null) cancelAnimationFrame(meterFrame.current);
    meterFrame.current = null;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    if (meterContext.current) void meterContext.current.close().catch(() => {});
    meterContext.current = null;
    if (mounted.current) setLevel(0);
  }

  useEffect(() => {
    mounted.current = true;
    const Speech = (window as SpeechBrowser).SpeechRecognition ?? (window as SpeechBrowser).webkitSpeechRecognition;
    setSpeechAvailable(Boolean(Speech));
    return () => {
      mounted.current = false;
      recognizer.current?.abort();
      stopMeter();
      window.speechSynthesis?.cancel();
    };
  }, []);

  async function startMeter() {
    // This stream exists only to visualise actual microphone input. It is not saved or uploaded.
    if (!navigator.mediaDevices?.getUserMedia) return;
    try {
      const capture = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (!mounted.current || !recognizer.current) {
        capture.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = capture;
      const audio = new AudioContext();
      meterContext.current = audio;
      if (audio.state === "suspended") await audio.resume();
      const analyser = audio.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.75;
      audio.createMediaStreamSource(capture).connect(analyser);
      const values = new Uint8Array(analyser.fftSize);
      let last = 0;
      const sample = (time: number) => {
        analyser.getByteTimeDomainData(values);
        let sum = 0;
        for (let i = 0; i < values.length; i++) {
          const v = (values[i] - 128) / 128;
          sum += v * v;
        }
        if (time - last > 55 && mounted.current) {
          setLevel(Math.min(1, Math.sqrt(sum / values.length) * 5.2));
          last = time;
        }
        meterFrame.current = requestAnimationFrame(sample);
      };
      meterFrame.current = requestAnimationFrame(sample);
    } catch {
      // Speech recognition may still work without a separate volume meter.
      if (mounted.current) setLevel(0);
    }
  }

  function say(text: string) {
    if (!mounted.current) return;
    if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) {
      setError("Speech playback is unavailable in this browser. Please use Chrome with device text-to-speech enabled.");
      setPhase("error");
      return;
    }
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = synth.getVoices();
    const british = voices.filter((voice) => /^en[-_]GB$/i.test(voice.lang));
    const choice = british.find((voice) => /daniel|oliver|male|george|ryan/i.test(voice.name))
      ?? british.find((voice) => /english|british/i.test(voice.name))
      ?? british[0] ?? null;
    if (choice) utterance.voice = choice;
    utterance.lang = "en-GB";
    utterance.rate = 0.94;
    utterance.pitch = 0.9;
    utterance.volume = 1;
    setVoiceLabel(choice ? choice.name : "Device voice");
    let hasStarted = false;
    // A reply on screen is not evidence that audio playback actually started.
    const watchdog = window.setTimeout(() => {
      if (!mounted.current || hasStarted) return;
      if (!synth.speaking) {
        setError("The browser returned a reply but did not start audio playback. Open the standalone preview in Chrome and check Android text-to-speech settings.");
        setPhase("error");
      }
    }, 10000);
    utterance.onstart = () => {
      hasStarted = true;
      window.clearTimeout(watchdog);
      if (mounted.current) setPhase("speaking");
    };
    utterance.onend = () => {
      window.clearTimeout(watchdog);
      if (mounted.current) setPhase("idle");
    };
    utterance.onerror = (event) => {
      window.clearTimeout(watchdog);
      if (!mounted.current || event.error === "interrupted" || event.error === "canceled") return;
      setError("The device could not play the response aloud. Check media volume and text-to-speech settings, then tap to try again.");
      setPhase("error");
    };
    synth.speak(utterance);
  }

  async function send(input: string) {
    const content = input.trim();
    if (!content || busy.current || !mounted.current) return;
    busy.current = true;
    stopMeter();
    setHeard(content);
    setReply("");
    setError("");
    setPhase("thinking");
    const next: HistoryMessage[] = [...history.current, { role: "user", content }].slice(-12);
    try {
      // Only real responses returned by the configured Lovable AI gateway are spoken.
      const result = await ask({ data: next });
      if (!mounted.current) return;
      if (result.error || !result.reply) {
        setError(result.error ?? "No reply came back from the AI service. Please try again.");
        setPhase("error");
        return;
      }
      const answer = result.reply.trim();
      history.current = [...next, { role: "assistant", content: answer }].slice(-12);
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

  function beginListening() {
    if (busy.current || recognizer.current) return;
    const Speech = (window as SpeechBrowser).SpeechRecognition ?? (window as SpeechBrowser).webkitSpeechRecognition;
    if (!Speech) {
      setError("Voice recognition isn't supported here. Open BACY-10 in Chrome on Android, or type your request.");
      setSpeechAvailable(false);
      setPhase("error");
      return;
    }
    window.speechSynthesis?.cancel();
    window.speechSynthesis?.resume(); // Unblock browser audio inside the user's tap gesture.
    firstTap.current = true;
    setError("");
    setReply("");
    setHeard("");
    setLevel(0);
    const instance = new Speech();
    recognizer.current = instance;
    instance.lang = "en-GB";
    instance.continuous = false;
    instance.interimResults = true;
    let finalText = "";
    let failed = false;
    let wasStopped = false;
    instance.onstart = () => { if (mounted.current) setPhase("listening"); };
    instance.onresult = (event) => {
      const finalParts: string[] = [];
      const provisionalParts: string[] = [];
      for (let i = 0; i < event.results.length; i++) {
        const segment = event.results[i];
        if (!segment) continue;
        const transcript = segment[0]?.transcript?.trim();
        if (!transcript) continue;
        if (segment.isFinal) finalParts.push(transcript);
        else provisionalParts.push(transcript);
      }
      finalText = finalParts.join(" ");
      if (mounted.current) setHeard([...finalParts, ...provisionalParts].join(" "));
    };
    instance.onerror = (event) => {
      // Android Chrome often ends recognition after one utterance; only actual errors get shown.
      if (event.error === "aborted") { wasStopped = true; return; }
      failed = true;
      if (!mounted.current) return;
      const message = event.error === "not-allowed" || event.error === "service-not-allowed"
        ? "Microphone access was blocked. Allow microphone permission in your browser and tap again."
        : event.error === "no-speech"
          ? "I didn't catch anything. Tap and speak again."
          : event.error === "network"
            ? "The browser's speech recognition service could not connect. Try again when online."
            : "Voice recognition stopped (" + event.error + "). Tap to try again or type instead.";
      setError(message);
      setPhase("error");
    };
    instance.onend = () => {
      if (recognizer.current === instance) recognizer.current = null;
      stopMeter();
      if (finalText.trim() && !failed) {
        void send(finalText);
      } else if (!failed && mounted.current) {
        setPhase("idle");
        if (wasStopped && !finalText.trim()) setHeard("");
      }
    };
    try {
      instance.start();
      setPhase("listening");
      // Never make recognition depend on this second, optional audio meter.
      void startMeter();
    } catch {
      recognizer.current = null;
      setError("Could not start the microphone. Try Chrome and allow microphone access.");
      setPhase("error");
    }
  }

  function tap() {
    if (textMode) return;
    if (phase === "listening") {
      recognizer.current?.stop();
      return;
    }
    if (phase === "thinking") return;
    if (phase === "speaking") {
      window.speechSynthesis?.cancel();
      setPhase("idle");
    }
    beginListening();
  }

  function submitTyped(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;
    setDraft("");
    setTextMode(false);
    void send(content);
  }

  const stateText = phase === "listening" ? "Listening" :
    phase === "thinking" ? "Thinking" :
    phase === "speaking" ? "Speaking" :
    phase === "error" ? "Connection needs attention" : "At your service";
  const instruction = phase === "listening" ? "Speak naturally. Tap to finish." :
    phase === "thinking" ? "Considering your request" :
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
        {textMode && <form className="voice-text-form" onSubmit={submitTyped}>
          <label className="voice-sr-only" htmlFor="voice-prompt">Message to BACY-10</label>
          <input id="voice-prompt" value={draft} onChange={(event) => setDraft(event.target.value)}
            autoFocus placeholder="Ask BACY-10…" maxLength={2000} />
          <button type="submit" disabled={!draft.trim()}>Send</button>
          <button type="button" onClick={() => setTextMode(false)}>Close</button>
        </form>}
        {(phase === "error" || !speechAvailable) && !textMode &&
          <button className="voice-text-fallback" type="button" onClick={() => setTextMode(true)}>Type instead</button>}
      </section>
      <span className="voice-footer" aria-hidden="true">{voiceLabel && phase === "speaking" ? "BRITISH VOICE · " + voiceLabel : "BACY-10 / VOICE INTERFACE"}</span>
    </main>
  );
}
