import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Real OpenAI speech. OPENAI_API_KEY is read exclusively on the server.
 * No keys, mocked audio, or placeholder success responses are sent to clients.
 */
export const speakBacy = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    z.object({ text: z.string().trim().min(1).max(1600) }).parse(input))
  .handler(async ({ data }) => {
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
            "Speak the supplied words exactly as BACY-10, a private British gentleman's assistant. " +
            "Use a consistent, natural, unmistakably modern British English accent. " +
            "Sound genuinely human: warm, calm, close and conversational, with a rich masculine tone, " +
            "natural breathing, subtle expression and easy changes of rhythm. " +
            "Be poised and quietly confident, with gentle authority; never robotic, flat or theatrical. " +
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
