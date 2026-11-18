import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { VoiceSculpture, type VoicePhase } from "@/components/VoiceSculpture";
import { askBacy } from "@/lib/bacy.functions";
import { readSpeechResults, type BrowserSpeechResult } from "@/lib/speech-results";

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
    setLevel(0);
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
      window.speechSynthesis?.cancel();
      window.speechSynthesis?.resume();
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
      const transcript = finalText.trim() || bestText.trim();
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
