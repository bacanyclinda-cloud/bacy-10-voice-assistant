import { createFileRoute } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { Activity, ArrowDownRight, ArrowUpRight, AudioLines, CloudSun, Compass, Cpu, Headphones, LocateFixed, MapPin, Mic, MicOff, Navigation, Radio, Send, Settings2, ShieldCheck, Signal, Volume2, VolumeX, Zap } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Slider } from "@/components/ui/slider";
import reactorIcon from "@/assets/bacy-10-icon.png";
import { EnergyPresence, type PresenceMode } from "@/components/EnergyPresence";
import { classifyAssistantCommand, getOfflineReply, type ProtocolPreset } from "@/lib/bacy.commands";
import { askBacy } from "@/lib/bacy.functions";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "BACY-10 | Voice Assistant" },
      { name: "description", content: "Meet BACY-10 — your personal British voice assistant and command console." },
      { property: "og:title", content: "BACY-10 | Voice Assistant" },
      { property: "og:description", content: "A personal voice assistant, ready at your service." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: BacyAssistant,
});

type Message = { id: string; role: "assistant" | "user"; content: string; time: string; localOnly?: boolean };
type VoicePreferences = { voice: string; rate: number; pitch: number; effects: boolean; volume: number };
type WeatherReading = { place: string; temperature: number; feelsLike: number; humidity: number; wind: number; code: number };
type RecognitionResult = { isFinal: boolean; 0: { transcript: string } };
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> };
type RecognitionLike = { continuous: boolean; interimResults: boolean; lang: string; onresult: ((event: RecognitionEvent) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void };
type SpeechWindow = Window & { SpeechRecognition?: new () => RecognitionLike; webkitSpeechRecognition?: new () => RecognitionLike };
const WELCOME: Message = { id: "bacy-welcome", role: "assistant", content: "Good day. BACY-10 is online and at your service. How may I assist?", time: "READY" };
const DEFAULTS: VoicePreferences = { voice: "", rate: 0.94, pitch: 0.92, effects: true, volume: 42 };
const HISTORY_KEY = "bacy-10-conversation-v1";
const PREFERENCES_KEY = "bacy-10-voice-settings-v1";
const timeNow = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

function weatherDescription(code: number) {
  if (code === 0) return "Clear skies";
  if (code <= 2) return "Partly cloudy";
  if (code === 3) return "Overcast";
  if (code <= 48) return "Misty";
  if (code <= 57) return "Drizzle";
  if (code <= 67) return "Rain";
  if (code <= 77) return "Snow";
  if (code <= 82) return "Showers";
  if (code <= 86) return "Snow showers";
  if (code >= 95) return "Thunderstorms";
  return "Variable conditions";
}

function BacyAssistant() {
  const askBacyFn = useServerFn(askBacy);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [standby, setStandby] = useState(false);
  const [preferences, setPreferences] = useState(DEFAULTS);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [ready, setReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [interim, setInterim] = useState("");
  const [notice, setNotice] = useState("");
  const [weather, setWeather] = useState<WeatherReading | null>(null);
  const [weatherBusy, setWeatherBusy] = useState(false);
  const [routeInput, setRouteInput] = useState("");
  const [routeTarget, setRouteTarget] = useState("");
  const [ambientPlaying, setAmbientPlaying] = useState(false);
  const [networkLatency, setNetworkLatency] = useState<number | null>(null);
  const [online, setOnline] = useState(true);
  const [clock, setClock] = useState("");
  const [micLevel, setMicLevel] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<RecognitionLike | null>(null);
  const micStream = useRef<MediaStream | null>(null);
  const micAudio = useRef<AudioContext | null>(null);
  const micFrame = useRef<number | null>(null);
  const ambientRef = useRef<{ context: AudioContext; oscillators: OscillatorNode[]; gain: GainNode } | null>(null);
  const sequence = useRef(0);

  useEffect(() => {
    const refreshVoices = () => setVoices(window.speechSynthesis?.getVoices() ?? []);
    const savedHistory = window.localStorage.getItem(HISTORY_KEY);
    if (savedHistory) {
      try {
        const saved = JSON.parse(savedHistory) as Message[];
        if (Array.isArray(saved) && saved.length) setMessages(saved.slice(-24));
      } catch { window.localStorage.removeItem(HISTORY_KEY); }
    }
    const savedPreferences = window.localStorage.getItem(PREFERENCES_KEY);
    if (savedPreferences) {
      try { setPreferences({ ...DEFAULTS, ...(JSON.parse(savedPreferences) as Partial<VoicePreferences>) }); }
      catch { window.localStorage.removeItem(PREFERENCES_KEY); }
    }
    refreshVoices();
    window.speechSynthesis?.addEventListener("voiceschanged", refreshVoices);
    const updateOnline = () => setOnline(navigator.onLine);
    updateOnline();
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    const updateClock = () => setClock(timeNow());
    updateClock();
    const clockTimer = window.setInterval(updateClock, 15_000);
    setReady(true);
    return () => {
      window.speechSynthesis?.removeEventListener("voiceschanged", refreshVoices);
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
      window.clearInterval(clockTimer);
    };
  }, []);

  useEffect(() => {
    if (ready) {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-24)));
      window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
    }
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, preferences, ready]);

  useEffect(() => () => {
    recognitionRef.current?.stop();
    micStream.current?.getTracks().forEach((track) => track.stop());
    if (micFrame.current !== null) cancelAnimationFrame(micFrame.current);
    void micAudio.current?.close();
    ambientRef.current?.oscillators.forEach((oscillator) => oscillator.stop());
    void ambientRef.current?.context.close();
    window.speechSynthesis?.cancel();
  }, []);

  const makeMessage = (role: Message["role"], content: string, localOnly = false): Message => {
    sequence.current += 1;
    return { id: `${Date.now()}-${sequence.current}`, role, content, time: timeNow(), ...(localOnly ? { localOnly: true } : {}) };
  };

  const chime = (frequency = 660) => {
    if (!preferences.effects || preferences.volume === 0) return;
    try {
      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime((preferences.volume / 100) * 0.055, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.25);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.26);
      oscillator.onended = () => void context.close();
    } catch { /* Optional browser audio cue. */ }
  };

  const speak = (text: string) => {
    if (!window.speechSynthesis || !ready) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const british = voices.filter((voice) => /^en[-_]gb/i.test(voice.lang));
    utterance.voice = voices.find((voice) => voice.name === preferences.voice) ?? british.find((voice) => /google uk english|daniel|oliver/i.test(voice.name)) ?? british[0] ?? null;
    utterance.lang = utterance.voice?.lang ?? "en-GB";
    utterance.rate = preferences.rate;
    utterance.pitch = preferences.pitch;
    utterance.volume = Math.max(0.01, preferences.volume / 100);
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const answer = (content: string, localOnly = false, speakAloud = true) => {
    setMessages((current) => [...current, makeMessage("assistant", content, localOnly)].slice(-24));
    setNotice("");
    chime(760);
    if (speakAloud) speak(content);
  };

  const stopListening = () => {
    if (micFrame.current !== null) cancelAnimationFrame(micFrame.current);
    micFrame.current = null;
    micStream.current?.getTracks().forEach((track) => track.stop());
    micStream.current = null;
    void micAudio.current?.close();
    micAudio.current = null;
    setMicLevel(0);
    setListening(false);
    setInterim("");
  };

  const submitMessage = async (raw?: string) => {
    const text = (raw ?? draft).trim();
    if (!text || busy || weatherBusy) return;
    setDraft("");
    setInterim("");
    setNotice("");
    setMessages((current) => [...current, makeMessage("user", text)].slice(-24));
    chime(430);
    const intent = classifyAssistantCommand(text);
    if (standby && !(intent.type === "preset" && intent.preset === "full-power")) {
      answer("I am in standby, sir. Say or enter ‘full power’ to resume.", true, false);
      return;
    }
    if (intent.type === "preset") { runPreset(intent.preset); return; }
    if (intent.type === "weather") { void scanWeather(intent.location); return; }
    if (intent.type === "route") {
      setRouteTarget(intent.destination);
      answer(`Directions to ${intent.destination} are prepared. Select Open route to see the map.`, true);
      return;
    }
    if (intent.type === "ambient") {
      if ((intent.action === "start") !== ambientPlaying) toggleAmbient();
      else answer(ambientPlaying ? "Ambient audio is already playing." : "Ambient audio is already off.", true);
      return;
    }
    if (!online) { answer(getOfflineReply(text), true); return; }

    setBusy(true);
    const started = performance.now();
    const history = [...messages.filter((message) => !message.localOnly), makeMessage("user", text)]
      .slice(-12).map(({ role, content }) => ({ role, content }));
    try {
      const result = await askBacyFn({ data: history });
      setNetworkLatency(Math.round(performance.now() - started));
      if (result.error) {
        if (result.status !== 499) {
          setMessages((current) => [...current, makeMessage("assistant", result.error ?? "The conversation service is unavailable.", true)].slice(-24));
          setNotice(result.error);
        }
      } else if (result.reply) answer(result.reply);
      else answer("I don't have a reply just now. Please try again in a moment.", true, false);
    } catch {
      answer(getOfflineReply(text), true);
      setNotice("I couldn't reach the conversation service. Your conversation is still here on this device.");
    } finally { setBusy(false); }
  };

  const listen = async () => {
    if (listening) { recognitionRef.current?.stop(); stopListening(); return; }
    const Recognition = (window as SpeechWindow).SpeechRecognition ?? (window as SpeechWindow).webkitSpeechRecognition;
    if (!Recognition) { setNotice("Voice input isn't supported in this browser. Type your command below instead."); return; }
    if (!navigator.mediaDevices?.getUserMedia) { setNotice("Microphone access isn't available here. You can still type a command below."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStream.current = stream;
      const context = new AudioContext();
      micAudio.current = context;
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.frequencyBinCount);
      const measure = () => {
        analyser.getByteTimeDomainData(samples);
        let energy = 0;
        for (const sample of samples) energy += (sample - 128) ** 2;
        setMicLevel(Math.min(1, Math.sqrt(energy / samples.length) / 34));
        micFrame.current = requestAnimationFrame(measure);
      };
      measure();
      const recognition = new Recognition();
      recognition.lang = "en-GB";
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.onresult = (event) => {
        let finalText = "";
        let current = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          if (event.results[index]?.isFinal) finalText += event.results[index]?.[0].transcript ?? "";
          else current += event.results[index]?.[0].transcript ?? "";
        }
        setInterim(current);
        if (finalText.trim()) void submitMessage(finalText.trim());
      };
      recognition.onerror = (event) => {
        if (event.error !== "no-speech" && event.error !== "aborted") setNotice(event.error === "not-allowed" ? "Microphone permission was declined. You can type a command below." : "I couldn't hear that clearly. Please try again or type your command.");
      };
      recognition.onend = () => { recognitionRef.current = null; stopListening(); };
      recognitionRef.current = recognition;
      setListening(true);
      setNotice("");
      chime(520);
      recognition.start();
    } catch {
      stopListening();
      setNotice("Microphone permission is needed for voice input. You can still type a command below.");
    }
  };

  const locate = () => new Promise<{ latitude: number; longitude: number } | null>((resolve) => {
    if (!navigator.geolocation) { resolve(null); return; }
    navigator.geolocation.getCurrentPosition((position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }), () => resolve(null), { timeout: 7000, maximumAge: 300_000 });
  });

  const scanWeather = async (requested: string | null) => {
    setWeatherBusy(true);
    setNotice("");
    try {
      let latitude: number;
      let longitude: number;
      let place: string;
      if (requested) {
        const lookup = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(requested)}&count=1&language=en&format=json`);
        if (!lookup.ok) throw new Error("Location search is unavailable at the moment.");
        const result = await lookup.json() as { results?: { name: string; admin1?: string; country?: string; latitude: number; longitude: number }[] };
        const city = result.results?.[0];
        if (!city) { setNotice(`I couldn't find ${requested}. Try a nearby town or city.`); return; }
        latitude = city.latitude;
        longitude = city.longitude;
        place = [city.name, city.admin1, city.country].filter(Boolean).join(", ");
      } else {
        const current = await locate();
        if (!current) { setNotice("Share your location for a local scan, or type ‘weather in London’ to choose a place."); return; }
        latitude = current.latitude;
        longitude = current.longitude;
        place = "Current location";
      }
      const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto`);
      if (!response.ok) throw new Error("The weather service is unavailable at the moment.");
      const data = await response.json() as { current?: { temperature_2m: number; relative_humidity_2m: number; apparent_temperature: number; weather_code: number; wind_speed_10m: number } };
      if (!data.current) throw new Error("I couldn't retrieve a weather reading just now.");
      const reading = data.current;
      setWeather({ place, temperature: reading.temperature_2m, feelsLike: reading.apparent_temperature, humidity: reading.relative_humidity_2m, wind: reading.wind_speed_10m, code: reading.weather_code });
      answer(`Atmospheric scan complete for ${place}: ${weatherDescription(reading.weather_code)}, ${Math.round(reading.temperature_2m)} degrees, with ${Math.round(reading.wind_speed_10m)} kilometres per hour of wind.`, true);
    } catch (error) {
      const message = error instanceof Error ? error.message : "The weather service is unavailable at the moment.";
      setNotice(message);
      answer(`Atmospheric scan unavailable. ${message}`, true, false);
    } finally { setWeatherBusy(false); }
  };

  const toggleAmbient = () => {
    if (ambientRef.current) {
      const current = ambientRef.current;
      current.gain.gain.setTargetAtTime(0.0001, current.context.currentTime, 0.15);
      window.setTimeout(() => { current.oscillators.forEach((oscillator) => oscillator.stop()); void current.context.close(); }, 550);
      ambientRef.current = null;
      setAmbientPlaying(false);
      answer("Ambient audio is off. Back to quiet efficiency.", true);
      return;
    }
    try {
      const context = new AudioContext();
      const gain = context.createGain();
      gain.gain.value = (preferences.volume / 100) * 0.11;
      gain.connect(context.destination);
      const oscillators = [context.createOscillator(), context.createOscillator()];
      oscillators.forEach((oscillator, index) => {
        oscillator.type = index === 0 ? "sine" : "triangle";
        oscillator.frequency.value = index === 0 ? 110 : 164.81;
        oscillator.connect(gain);
        oscillator.start();
      });
      ambientRef.current = { context, oscillators, gain };
      setAmbientPlaying(true);
      answer("A soft ambient resonance is now playing. Say ‘stop ambient audio’ or tap the headphones to silence it.", true);
    } catch { setNotice("Ambient audio is unavailable in this browser."); }
  };

  function runPreset(preset: ProtocolPreset) {
    if (preset === "diagnostics") {
      answer(`Local browser diagnostics complete. Network ${online ? "online" : "offline"}${networkLatency === null ? "" : ` at ${networkLatency} milliseconds`}. Conversation archive contains ${Math.max(0, messages.length - 1)} recent entries. Your history stays on this device.`, true);
    } else if (preset === "atmosphere") void scanWeather(null);
    else if (preset === "standby") {
      setStandby(true);
      window.speechSynthesis?.cancel();
      setSpeaking(false);
      answer("Entering standby. Say ‘full power’ or enter that command whenever you're ready.", true, false);
    } else {
      setStandby(false);
      answer("Full power restored. All systems are yours to command.", true);
    }
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void submitMessage(); };
  const onRouteSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const destination = routeInput.trim();
    if (!destination) return;
    setRouteTarget(destination);
    setRouteInput("");
    answer(`Directions to ${destination} are prepared. Select Open route to see the map.`, true);
  };
  const changePreference = (key: keyof VoicePreferences, value: number | boolean | string) => setPreferences((current) => ({ ...current, [key]: value }));
  const status = speaking ? "Speaking" : busy ? "Thinking" : weatherBusy ? "Scanning" : standby ? "Standby" : listening ? "Listening" : "At your service";
  const presenceMode: PresenceMode = standby ? "standby" : listening ? "listening" : speaking ? "speaking" : busy || weatherBusy ? "thinking" : "idle";
  const code = speaking ? "VOICE OUT" : busy ? "PROCESSING" : weatherBusy ? "SCANNING" : standby ? "LOW POWER" : listening ? "VOICE IN" : "STANDBY READY";
  const orderedVoices = voices.filter((voice) => /^en[-_]gb/i.test(voice.lang)).concat(voices.filter((voice) => !/^en[-_]gb/i.test(voice.lang)));

  return <div className={`bacy-shell ${listening ? "mic-active" : ""} ${speaking ? "voice-active" : ""}`}>
    <header className="bacy-topbar">
      <div className="top-brand"><img className="brand-mark" src={reactorIcon} alt="" width={42} height={42} /><div><div className="brand-name">BACY<span>-10</span></div><div className="brand-caption">PERSONAL INTELLIGENCE SYSTEM</div></div></div>
      <div className="top-status"><span className={`signal-dot ${online ? "is-online" : "is-offline"}`} /><span className="top-status-label">{online ? "BROWSER ONLINE" : "OFFLINE"}</span><span className="top-divider" /><span className="top-clock">{clock || "--:--"}</span></div>
      <Sheet open={settingsOpen} onOpenChange={setSettingsOpen}>
        <SheetTrigger asChild><Button variant="ghost" size="icon" className="settings-trigger" aria-label="Open voice settings" title="Voice settings"><Settings2 /></Button></SheetTrigger>
        <SheetContent className="settings-sheet"><SheetHeader className="settings-header"><span className="section-kicker">INTERFACE CALIBRATION</span><SheetTitle>Voice settings</SheetTitle><SheetDescription>Choose how BACY-10 sounds when replying aloud.</SheetDescription></SheetHeader>
          <div className="settings-controls">
            <div className="setting-row"><Label htmlFor="voice-select">British voice</Label><select id="voice-select" className="voice-select" value={preferences.voice} onChange={(event) => changePreference("voice", event.target.value)}><option value="">Best available British voice</option>{orderedVoices.map((voice) => <option key={`${voice.name}-${voice.lang}`} value={voice.name}>{voice.name} · {voice.lang}</option>)}</select><span className="setting-hint">{voices.length ? `${orderedVoices.length} device voices available` : "Uses your device's voice when available"}</span></div>
            <div className="setting-row"><div className="setting-label-line"><Label htmlFor="voice-rate">Speaking pace</Label><span>{preferences.rate.toFixed(2)}×</span></div><Slider id="voice-rate" min={0.7} max={1.25} step={0.01} value={[preferences.rate]} onValueChange={(value) => changePreference("rate", value[0] ?? DEFAULTS.rate)} /><span className="setting-hint">Measured and unhurried</span></div>
            <div className="setting-row"><div className="setting-label-line"><Label htmlFor="voice-pitch">Voice pitch</Label><span>{preferences.pitch.toFixed(2)}</span></div><Slider id="voice-pitch" min={0.65} max={1.3} step={0.01} value={[preferences.pitch]} onValueChange={(value) => changePreference("pitch", value[0] ?? DEFAULTS.pitch)} /><span className="setting-hint">A composed, lower register</span></div>
            <div className="setting-row"><div className="setting-label-line"><Label htmlFor="audio-volume">Audio level</Label><span>{preferences.volume}%</span></div><Slider id="audio-volume" min={0} max={100} step={1} value={[preferences.volume]} onValueChange={(value) => changePreference("volume", value[0] ?? DEFAULTS.volume)} /><span className="setting-hint">Controls replies, chimes and ambient sound</span></div>
            <Button variant="outline" className="effect-setting" onClick={() => changePreference("effects", !preferences.effects)}>{preferences.effects ? <Volume2 /> : <VolumeX />}Interface chimes <span>{preferences.effects ? "ON" : "OFF"}</span></Button>
            {!voices.length && <p className="setting-note">Available voices come from your device. BACY-10 chooses the closest British voice it can find.</p>}
          </div>
        </SheetContent>
      </Sheet>
    </header>

    <main className="bacy-main">
      <section className="assistant-column">
        <div className="assistant-heading"><div><div className="section-kicker">VOICE CONSOLE <span>//</span> SESSION 01</div><h1>Your personal assistant.</h1></div><div className="secure-note"><ShieldCheck size={15} /><span>HISTORY ON THIS DEVICE</span></div></div>

        <section className={`reactor-stage ${standby ? "reactor-standby" : ""}`} aria-label={`BACY-10 status: ${status}`}>
          <div className="reactor-meta reactor-meta-left"><span className="micro-label">CORE OUTPUT</span><strong>{ready ? "READY" : "BOOT"}</strong></div><div className="reactor-meta reactor-meta-right"><span className="micro-label">MIC LEVEL</span><strong>{listening ? `${Math.round(micLevel * 100)}%` : speaking ? "VOICE" : "IDLE"}</strong></div>
          <div className="reactor-grid" aria-hidden="true" /><div className="reactor-aura" aria-hidden="true" />
          <EnergyPresence mode={presenceMode} level={micLevel} onActivate={() => void listen()} disabled={busy || standby} />
          <div className="reactor-status"><span className={`signal-dot ${standby ? "is-amber" : "is-online"}`} /><span>{code}</span></div><div className="reactor-subtitle" aria-live="polite">{standby ? "Awaiting your instruction" : listening ? (interim || "Listening for your voice…") : speaking ? "Responding aloud" : busy ? "Composing a reply" : ""}</div>
        </section>

        <div className="voice-controls"><div className="voice-control-copy"><span className="control-title">{standby ? "BACY-10 is in standby" : listening ? "Listening now" : "Speak with BACY-10"}</span><span className="control-subtitle">{standby ? "Type ‘full power’ to resume." : "Tap the animated core or use the command line."}</span></div><Button className={`mic-button ${listening ? "mic-button-on" : ""}`} onClick={() => void listen()} disabled={busy || standby} aria-label={listening ? "Stop listening" : "Start voice input"}>{listening ? <MicOff /> : <Mic />}<span>{listening ? "STOP LISTENING" : "TALK TO BACY-10"}</span></Button><Button className="sound-button" variant="outline" size="icon" onClick={() => { if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); } else if (messages.at(-1)?.role === "assistant") speak(messages.at(-1)?.content ?? "At your service."); }} aria-label={speaking ? "Stop spoken reply" : "Repeat last reply"} title={speaking ? "Stop spoken reply" : "Repeat last reply"}>{speaking ? <VolumeX /> : <Volume2 />}</Button></div>
        {notice && <div className="inline-notice" role="status"><Radio size={14} /><span>{notice}</span></div>}

        <section className="conversation-console" aria-label="Conversation">
          <div className="console-header"><div className="console-title"><span className="console-marker" />LIVE CONVERSATION</div><span>{messages.length - 1} ENTRIES <span className="console-separator">/</span> LOCAL ARCHIVE</span></div>
          <div className="conversation-log" aria-live="polite">
            {messages.slice(-5).map((message) => <article className={`message-row ${message.role === "user" ? "message-user" : "message-assistant"}`} key={message.id}><div className="message-timestamp">{message.time}</div><div className="message-body"><div className="message-sender">{message.role === "assistant" ? "BACY-10" : "YOU"}{message.localOnly && <span className="local-badge">LOCAL</span>}</div><p>{message.content}</p></div></article>)}
            {busy && <article className="message-row message-assistant"><div className="message-timestamp">NOW</div><div className="message-body"><div className="message-sender">BACY-10</div><p className="thinking-copy"><span /> Considering your request</p></div></article>}<div ref={endRef} />
          </div>
          <form className="command-form" onSubmit={onSubmit}><span className="command-prompt" aria-hidden="true">&gt;_</span><input aria-label="Type a command" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Type a question or command…" maxLength={2000} disabled={busy || weatherBusy} /><Button type="submit" size="icon" disabled={!draft.trim() || busy || weatherBusy} aria-label="Send command" title="Send command"><Send /></Button></form>
        </section>
      </section>

      <aside className="systems-column" aria-label="System panels">
        <section className="telemetry-section"><div className="section-kicker">SYSTEM STATUS <span>//</span> LIVE</div><div className="telemetry-list"><Telemetry icon={<Zap />} label="Local console" value={ready ? "READY" : "BOOTING"} detail="BROWSER RUNTIME" percent={ready ? 100 : 5} tone="cyan" /><Telemetry icon={<Signal />} label="Network link" value={networkLatency === null ? (online ? "ONLINE" : "OFFLINE") : `${networkLatency} ms`} detail={online ? "CONNECTED" : "NO SIGNAL"} percent={online ? 100 : 8} tone={online ? "cyan" : "amber"} /><Telemetry icon={<Cpu />} label="Memory matrix" value={`${Math.min(99, Math.round(((messages.length - 1) / 24) * 100))}%`} detail={`${Math.max(0, messages.length - 1)} / 24 ENTRIES`} percent={Math.min(99, Math.round(((messages.length - 1) / 24) * 100))} tone="blue" /></div><div className="security-line"><ShieldCheck size={15} /><span>Conversation history stays in this browser.</span></div></section>

        <section className="utility-section weather-section"><div className="utility-heading"><div><div className="section-kicker">ATMOSPHERIC SCAN</div><h2>Weather now</h2></div><CloudSun size={19} /></div>
          <div className="radar-scene" aria-label="Atmosphere scan indicator"><div className="radar-ring radar-ring-outer" /><div className="radar-ring radar-ring-middle" /><div className="radar-ring radar-ring-inner" /><span className="radar-sweep" /><span className="radar-origin" /><span className="radar-point radar-point-one" /><span className="radar-point radar-point-two" /><span className="radar-point radar-point-three" /><span className="radar-readout">{weatherBusy ? "SCANNING" : weather ? "LIVE DATA" : "AWAITING SCAN"}</span></div>
          {weather ? <div className="weather-reading"><div className="weather-place"><MapPin size={13} />{weather.place}</div><div className="weather-main"><strong>{Math.round(weather.temperature)}°</strong><span>{weatherDescription(weather.code)}</span></div><div className="weather-details"><span>FEELS {Math.round(weather.feelsLike)}°</span><span>WIND {Math.round(weather.wind)} km/h</span><span>HUMIDITY {weather.humidity}%</span></div></div> : <p className="utility-note">A current reading appears here after your first scan.</p>}
          <Button variant="outline" className="utility-action" onClick={() => void scanWeather(null)} disabled={weatherBusy}><LocateFixed />{weatherBusy ? "SCANNING…" : "SCAN MY AREA"}</Button>
        </section>

        <section className="utility-section route-section"><div className="utility-heading"><div><div className="section-kicker">ROUTE LOCATOR</div><h2>Find your way</h2></div><Compass size={19} /></div>
          <form className="route-form" onSubmit={onRouteSubmit}><MapPin size={15} /><input aria-label="Destination" value={routeInput} onChange={(event) => setRouteInput(event.target.value)} placeholder="Enter a destination" maxLength={120} /><Button type="submit" variant="ghost" size="icon" disabled={!routeInput.trim()} aria-label="Prepare route"><ArrowUpRight /></Button></form>
          {routeTarget ? <div className="route-prepared"><div className="route-destination"><Navigation size={13} /><span>{routeTarget}</span></div><a className="route-open" href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(routeTarget)}`} target="_blank" rel="noreferrer">OPEN ROUTE <ArrowUpRight size={13} /></a></div> : <p className="utility-note">Enter a destination to open directions on your map.</p>}
        </section>

        <section className="utility-section sound-section"><div className="utility-heading"><div><div className="section-kicker">TACTICAL MEDIA</div><h2>Ambient audio</h2></div><Headphones size={19} /></div><div className={`ambient-track ${ambientPlaying ? "ambient-active" : ""}`}><div className="track-art"><AudioLines size={18} /></div><div className="track-info"><strong>Quiet resonance</strong><span>{ambientPlaying ? "PLAYING · SYNTHESISED" : "SYNTHESISED · READY"}</span></div><Button variant="ghost" size="icon" onClick={toggleAmbient} aria-label={ambientPlaying ? "Stop ambient audio" : "Start ambient audio"} title={ambientPlaying ? "Stop ambient audio" : "Start ambient audio"}>{ambientPlaying ? <VolumeX /> : <Volume2 />}</Button></div><div className="track-wave" aria-hidden="true">{Array.from({ length: 26 }, (_, index) => <i key={index} className={ambientPlaying ? "wave-playing" : ""} />)}</div></section>
      </aside>

      <section className="protocol-section" aria-label="Quick protocols"><div className="protocol-label"><span className="section-kicker">QUICK PROTOCOLS</span><span>READY WHEN YOU ARE</span></div><div className="protocol-grid"><Protocol label="System diagnostics" code="01 / SCAN" icon={<Activity />} onClick={() => runPreset("diagnostics")} /><Protocol label="Atmospheric scan" code="02 / WEATHER" icon={<CloudSun />} onClick={() => void scanWeather(null)} disabled={weatherBusy} /><Protocol label={standby ? "Full power" : "Standby mode"} code={standby ? "04 / RESUME" : "03 / SUSPEND"} icon={standby ? <Zap /> : <ArrowDownRight />} onClick={() => runPreset(standby ? "full-power" : "standby")} /><Protocol label={ambientPlaying ? "Stop ambient" : "Ambient audio"} code="05 / MEDIA" icon={ambientPlaying ? <VolumeX /> : <AudioLines />} onClick={toggleAmbient} /></div></section>
    </main>

    <footer className="bacy-footer"><div><span className="footer-led" /> BACY-10 <span className="footer-muted">PERSONAL ASSISTANT</span></div><div>BRITISH ENGLISH <span className="footer-muted">·</span> {online ? "BROWSER ONLINE" : "OFFLINE MODE"}</div><span className="footer-time">{clock || "--:--"} LOCAL</span></footer>
  </div>;
}

function Telemetry({ icon, label, value, detail, percent, tone }: { icon: ReactNode; label: string; value: string; detail: string; percent: number; tone: "cyan" | "blue" | "amber" }) {
  return <div className={`telemetry-row tone-${tone}`}><div className="telemetry-copy"><span className="telemetry-icon">{icon}</span><div className="telemetry-label"><span>{label}</span><small>{detail}</small></div><strong>{value}</strong></div><div className="telemetry-bar" aria-label={`${label}: ${value}`}><span style={{ width: `${percent}%` }} /></div></div>;
}

function Protocol({ label, code, icon, onClick, disabled = false }: { label: string; code: string; icon: ReactNode; onClick: () => void; disabled?: boolean }) {
  return <Button variant="ghost" className="protocol-button" onClick={onClick} disabled={disabled}><span className="protocol-icon">{icon}</span><span className="protocol-copy"><strong>{label}</strong><small>{code}</small></span><ArrowUpRight className="protocol-arrow" /></Button>;
}