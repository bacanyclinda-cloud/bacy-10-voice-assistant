export type ProtocolPreset = "diagnostics" | "atmosphere" | "standby" | "full-power";

export type AssistantIntent =
  | { type: "preset"; preset: ProtocolPreset }
  | { type: "weather"; location: string | null }
  | { type: "route"; destination: string }
  | { type: "ambient"; action: "start" | "stop" }
  | { type: "conversation" };

export function classifyAssistantCommand(text: string): AssistantIntent {
  const input = text.trim();
  if (/\b(system diagnostics|run diagnostics|full diagnostics|diagnostics)\b/i.test(input)) {
    return { type: "preset", preset: "diagnostics" };
  }
  if (/\b(standby|stand by|quiet mode)\b/i.test(input)) {
    return { type: "preset", preset: "standby" };
  }
  if (/\b(full power|power up|resume systems)\b/i.test(input)) {
    return { type: "preset", preset: "full-power" };
  }
  if (/\b(ambient|soundtrack|background music)\b/i.test(input)) {
    return { type: "ambient", action: /\b(stop|off|silence|end)\b/i.test(input) ? "stop" : "start" };
  }

  const routeMatch = input.match(/\b(?:route|directions|navigate|map)\s+(?:to|for)\s+(.+?)[?.!]*$/i)
    ?? input.match(/\bgo\s+to\s+(.+?)[?.!]*$/i);
  if (routeMatch?.[1]?.trim()) {
    return { type: "route", destination: routeMatch[1].trim() };
  }

  const weatherMatch = input.match(/\b(?:weather|forecast|temperature|atmospheric scan)\b(?:\s+(?:in|for|at)\s+(.+?))?[?.!]*$/i);
  if (weatherMatch) {
    return { type: "weather", location: weatherMatch[1]?.trim() || null };
  }

  return { type: "conversation" };
}

export function getOfflineReply(text: string): string {
  const input = text.toLowerCase();
  if (/\b(hello|hi|hey|good morning|good afternoon|good evening)\b/.test(input)) {
    return "Good day. BACY-10 is here and ready to assist. What would you like me to take care of?";
  }
  if (/\b(who are you|your name|what are you)\b/.test(input)) {
    return "I am BACY-10, your personal voice assistant. My usual conversation link is unavailable just now, but my system controls remain at your service.";
  }
  if (/\b(help|what can you do|capabilities)\b/.test(input)) {
    return "I can run system diagnostics, scan local weather, prepare directions, and manage your ambient audio. Voice and typed commands are both available.";
  }
  if (/\b(time|clock)\b/.test(input)) {
    return `The local time is ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}. My full conversation link is currently offline.`;
  }
  return "My conversation link is temporarily offline, so I cannot answer that reliably. Your command is still here; please try again shortly.";
}