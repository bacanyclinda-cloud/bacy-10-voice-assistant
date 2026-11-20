type Env = Record<string, string | undefined>;
export type TtsResult = { audio: string; mediaType: string } | { error: string; code: string };

const MAX_AUDIO = 3_500_000;

async function finish(response: Response, provider: string): Promise<TtsResult> {
  if (!response.ok) {
    const s = response.status;
    if (s === 401) return { error: `${provider} rejected the voice key (401).`, code: "auth" };
    if (s === 402) return { error: `${provider} voice credits are exhausted (402).`, code: "credits" };
    if (s === 403) return { error: `${provider} denied access (403).`, code: "denied" };
    if (s === 429) return { error: `${provider} is rate limited (429). Please wait a moment.`, code: "rate" };
    return { error: `${provider} voice service returned an error (${s}).`, code: "upstream" };
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!bytes.byteLength) return { error: "The voice service returned empty audio.", code: "empty" };
  if (bytes.byteLength > MAX_AUDIO) return { error: "The audio reply was too large to play safely.", code: "too_large" };
  return { audio: Buffer.from(bytes).toString("base64"), mediaType: "audio/mpeg" };
}

/** Voice 2: alternative OpenAI voice via the owner's key or the Lovable gateway. */
export async function speakVoiceTwo(text: string, env: Env): Promise<TtsResult> {
  const direct = env["OPENAI_API_KEY"];
  const lovable = env["LOVABLE_API_KEY"];
  const key = direct || lovable;
  if (!key) return { error: "Voice 2 is not configured on the server.", code: "unconfigured" };
  const viaGateway = !direct;
  const res = await fetch(viaGateway ? "https://ai.gateway.lovable.dev/v1/audio/speech" : "https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: viaGateway ? "openai/gpt-4o-mini-tts" : "gpt-4o-mini-tts",
      input: text,
      voice: "nova",
      response_format: "mp3",
      instructions: "Speak as BACY-10 in warm, natural British English. Sound genuinely human and expressive: relaxed pacing, gentle smiles in the voice, natural pauses. Never robotic or theatrical. Do not add or remove words.",
    }),
    signal: AbortSignal.timeout(25_000),
  });
  return finish(res, "OpenAI");
}

/** Voice 3: ElevenLabs, only when the owner has added ELEVENLABS_API_KEY. */
export async function speakVoiceThree(text: string, env: Env): Promise<TtsResult> {
  const key = env["ELEVENLABS_API_KEY"];
  if (!key) return { error: "ElevenLabs needs a key. Add ELEVENLABS_API_KEY in the project secrets.", code: "needs_key" };
  const voiceId = env["ELEVENLABS_VOICE_ID"] || "22N9cF8z0o7y23njdyaY"; // Florence: British female, gentle and natural
  if (!/^[A-Za-z0-9]{10,40}$/.test(voiceId)) return { error: "ELEVENLABS_VOICE_ID is not a valid voice ID.", code: "bad_voice" };
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": key, "Content-Type": "application/json" },
    body: JSON.stringify({ text, model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.45, similarity_boost: 0.75, style: 0.4, use_speaker_boost: true } }),
    signal: AbortSignal.timeout(25_000),
  });
  return finish(res, "ElevenLabs");
}

export function backupVoiceStatus(env: Env) {
  return {
    voice2: Boolean(env["OPENAI_API_KEY"] || env["LOVABLE_API_KEY"]),
    voice3: Boolean(env["ELEVENLABS_API_KEY"]),
  };
}
