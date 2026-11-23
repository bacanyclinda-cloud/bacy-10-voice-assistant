import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Real OpenAI speech. OPENAI_API_KEY is read exclusively on the server.
 * No keys, mocked audio, or placeholder success responses are sent to clients.
 */
export const getBacyVoiceOptions = createServerFn({ method: "GET" }).handler(async () => {
  const key = process.env["ELEVENLABS_API_KEY"];
  if (!key) return { elevenLabsConfigured: false, voices: [] as Array<{ id: string; name: string }> };
  try {
    const response = await fetch("https://api.elevenlabs.io/v1/voices", {
      headers: { "xi-api-key": key },
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok) return { elevenLabsConfigured: false, voices: [] as Array<{ id: string; name: string }> };
    const payload = await response.json() as { voices?: Array<{ voice_id?: string; name?: string }> };
    const voices = (payload.voices ?? [])
      .filter((voice) => typeof voice.voice_id === "string" && /^[A-Za-z0-9]{10,40}$/.test(voice.voice_id) && typeof voice.name === "string")
      .map((voice) => ({ id: voice.voice_id!, name: voice.name! }))
      .slice(0, 100);
    return { elevenLabsConfigured: true, voices };
  } catch {
    return { elevenLabsConfigured: false, voices: [] as Array<{ id: string; name: string }> };
  }
});

export const speakBacy = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    z.object({
      text: z.string().trim().min(1).max(1600),
      provider: z.enum(["openai", "elevenlabs"]).optional().default("openai"),
      voiceId: z.string().regex(/^[A-Za-z0-9]{10,40}$/).optional(),
    }).parse(input))
  .handler(async ({ data }) => {
    if (data.provider === "elevenlabs") {
      const key = process.env["ELEVENLABS_API_KEY"];
      if (!key) return { error: "ElevenLabs is not configured. Add ELEVENLABS_API_KEY as a server-side secret." };
      const voiceId = data.voiceId || process.env["ELEVENLABS_VOICE_ID"] || "22N9cF8z0o7y23njdyaY";
      try {
        const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}?output_format=mp3_44100_128`, {
          method: "POST",
          headers: { "xi-api-key": key, "Content-Type": "application/json" },
          body: JSON.stringify({
            text: data.text,
            model_id: "eleven_multilingual_v2",
            voice_settings: { stability: 0.45, similarity_boost: 0.75, style: 0.35, use_speaker_boost: true },
          }),
          signal: AbortSignal.timeout(25000),
        });
        if (!response.ok) {
          if (response.status === 401) return { error: "ElevenLabs rejected its server key (401)." };
          if (response.status === 403) return { error: "ElevenLabs denied this voice or account access (403)." };
          if (response.status === 404) return { error: "That ElevenLabs voice no longer exists or is unavailable." };
          if (response.status === 429) return { error: "ElevenLabs rate limit or usage allowance reached (429)." };
          return { error: "ElevenLabs returned an error (" + response.status + ")." };
        }
        const bytes = new Uint8Array(await response.arrayBuffer());
        if (!bytes.byteLength) return { error: "ElevenLabs returned empty audio." };
        if (bytes.byteLength > 3_500_000) return { error: "The audio reply was too large to play safely." };
        return { audio: Buffer.from(bytes).toString("base64"), mediaType: "audio/mpeg", provider: "elevenlabs" };
      } catch (error) {
        console.error("BACY-10 ElevenLabs request failed", error instanceof Error ? error.name : "unknown");
        return { error: "Could not reach ElevenLabs. Check the server connection and try again." };
      }
    }
    // Prefer the owner's own secure OpenAI key when present. Otherwise use
    // Lovable's existing project-managed gateway key for real, generated audio.
    // Neither secret is returned to the browser or checked into GitHub.
    const directKey = process.env["OPENAI_API_KEY"];
    const lovableKey = process.env["LOVABLE_API_KEY"];
    const usingLovable = !directKey && Boolean(lovableKey);
    const apiKey = directKey || lovableKey;
    if (!apiKey) {
      return { error: "Real AI voice is not configured. Add OPENAI_API_KEY as a server-side secret." };
    }

    try {
      const response = await fetch(usingLovable
        ? "https://ai.gateway.lovable.dev/v1/audio/speech"
        : "https://api.openai.com/v1/audio/speech", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
          ...(usingLovable ? { "Lovable-API-Key": apiKey, "X-Lovable-AIG-SDK": "vercel-ai-sdk" } : {}),
        },
        body: JSON.stringify({
          model: usingLovable ? "openai/gpt-4o-mini-tts" : "gpt-4o-mini-tts",
          input: data.text,
          voice: "onyx",
          response_format: "mp3",
          instructions:
            "Speak the supplied words exactly as Bacy 10, BW Silinda's personal assistant. " +
            "Use a consistent, natural modern British English accent with a warm, relaxed masculine tone. " +
            "Sound conversational, expressive and confident, with natural pauses and varied rhythm. " +
            "Do not force formal titles, scripted butler phrases, exaggerated authority or theatrical delivery. " +
            "Do not add or remove words.",
        }),
        signal: AbortSignal.timeout(25000),
      });

      if (!response.ok) {
        // Do not include upstream response bodies: they can expose sensitive details.
        if (response.status === 401) return { error: usingLovable ? "Lovable rejected the project voice key (401)." : "OpenAI rejected the voice key (401). Please check the server secret." };
        if (response.status === 403) return { error: "The voice provider denied access (403). Check the project permission or credits." };
        if (response.status === 402) return { error: "Lovable voice credits are exhausted (402). Add a fresh OPENAI_API_KEY to the server to use your own API account." };
        if (response.status === 429) return { error: "The AI voice service is rate limited or has reached its usage allowance (429)." };
        if (response.status === 400 || response.status === 404) return { error: "The OpenAI speech model or voice is unavailable for this project." };
        return { error: "The OpenAI speech service returned an error (" + response.status + ")." };
      }

      const bytes = new Uint8Array(await response.arrayBuffer());
      if (!bytes.byteLength) return { error: "The speech service returned an empty audio file." };
      if (bytes.byteLength > 3_500_000) return { error: "The audio reply was too large to play safely." };
      return { audio: Buffer.from(bytes).toString("base64"), mediaType: "audio/mpeg", provider: usingLovable ? "lovable" : "openai" };
    } catch (error) {
      console.error("BACY-10 voice service request failed", error instanceof Error ? error.name : "unknown");
      return { error: "Could not reach OpenAI's voice service. Please check the network and try again." };
    }
  });
