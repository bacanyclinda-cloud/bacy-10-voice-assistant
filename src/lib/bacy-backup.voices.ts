export type BackupVoice = "voice1" | "voice2" | "voice3";

export const BACKUP_VOICES: Record<BackupVoice, { label: string; detail: string }> = {
  voice1: { label: "Voice 1", detail: "Original web voice (Android Gemini voice stays unchanged)" },
  voice2: { label: "Voice 2", detail: "Expressive alternative voice from OpenAI" },
  voice3: { label: "ElevenLabs", detail: "Separate ElevenLabs voice — requires its own API key" },
};

/** Interpret a user-issued command without changing normal speech content. */
export function parseVoiceSwitch(text: string): BackupVoice | null {
  const t = text.toLowerCase().replace(/\b(?:hey|hi|hello)\b[,! ]*/g, "")
    .replace(/\b(?:bacy\s*[- ]?\s*10|bacy\s+ten|basic\s*[- ]?\s*10|basic\s+ten)\b[ ,]*/g, "").trim();
  if (!/\b(?:use|switch|change|set|select|go back|back to|return to)\b/.test(t) && !/^voice\s/.test(t)) return null;
  if (/\beleven\s*labs?\b/.test(t) || /\belevenlabs\b/.test(t)) return "voice3";
  if (/\b(?:original|default|normal|usual|first)\b.*\bvoice\b|\b(?:go back|back|return)\b.*\b(?:original|default)\b/.test(t)) return "voice1";
  const match = t.match(/\b(?:voice|number)\s*(one|two|three|1|2|3)\b/);
  if (!match) return null;
  const voices: Record<string, BackupVoice> = {
    one: "voice1", "1": "voice1", two: "voice2", "2": "voice2", three: "voice3", "3": "voice3",
  };
  return voices[match[1]] ?? null;
}
