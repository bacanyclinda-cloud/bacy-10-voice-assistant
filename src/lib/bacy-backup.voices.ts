export type BackupVoice = "voice1" | "voice2" | "voice3";

export const BACKUP_VOICES: Record<BackupVoice, { label: string; detail: string }> = {
  voice1: { label: "Voice 1", detail: "Original BACY-10 voice (same as the main app)" },
  voice2: { label: "Voice 2", detail: "Alternative expressive OpenAI voice (nova)" },
  voice3: { label: "ElevenLabs", detail: "ElevenLabs voice — needs the owner's ElevenLabs key" },
};

/** Returns the requested voice when the text is a voice-switch command, otherwise null. */
export function parseVoiceSwitch(text: string): BackupVoice | null {
  const t = text.toLowerCase().replace(/bacy[\s-]*10|bacy ten/g, "").trim();
  if (!/\b(use|switch|change|go back|back to|set|select)\b/.test(t) && !/^voice\s/.test(t)) return null;
  if (/eleven\s*labs|elevenlabs/.test(t)) return "voice3";
  if (/\b(original|default|normal|usual)\b.*\bvoice\b/.test(t)) return "voice1";
  const m = t.match(/\bvoice\s*(one|two|three|1|2|3)\b/);
  if (!m) return null;
  return ({ one: "voice1", "1": "voice1", two: "voice2", "2": "voice2", three: "voice3", "3": "voice3" } as const)[m[1] as "1"];
}
