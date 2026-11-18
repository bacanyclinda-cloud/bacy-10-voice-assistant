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
    const apiKey = process.env["OPENAI_API_KEY"];
    if (!apiKey) {
      return { error: "The AI voice key is not configured yet. Add OPENAI_API_KEY as a secure server secret in your hosting settings." };
    }

    try {
      const response = await fetch("https://api.openai.com/v1/audio/speech", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4o-mini-tts",
          input: data.text,
          voice: "onyx",
          response_format: "mp3",
          instructions:
            "Speak the supplied words exactly as BACY-10, a private British gentleman's assistant. " +
            "Use natural modern British English pronunciation, poised and warm, with gentle authority. " +
            "Deep masculine timbre, measured rhythm, restrained expression, not mechanical. " +
            "Do not add or remove words.",
        }),
        signal: AbortSignal.timeout(25000),
      });

      if (!response.ok) {
        // Do not include upstream response bodies: they can expose sensitive details.
        if (response.status === 401) return { error: "OpenAI rejected the voice key (401). Please check that the new server secret is valid." };
        if (response.status === 403) return { error: "OpenAI voice access was denied (403). Check API project permissions." };
        if (response.status === 429) return { error: "The OpenAI voice service is rate limited or has reached its usage allowance (429)." };
        if (response.status === 400 || response.status === 404) return { error: "The OpenAI speech model or voice is unavailable for this project." };
        return { error: "The OpenAI speech service returned an error (" + response.status + ")." };
      }

      const bytes = new Uint8Array(await response.arrayBuffer());
      if (!bytes.byteLength) return { error: "The speech service returned an empty audio file." };
      if (bytes.byteLength > 3_500_000) return { error: "The audio reply was too large to play safely." };
      return { audio: Buffer.from(bytes).toString("base64"), mediaType: "audio/mpeg" };
    } catch (error) {
      console.error("BACY-10 voice service request failed", error instanceof Error ? error.name : "unknown");
      return { error: "Could not reach OpenAI's voice service. Please check the network and try again." };
    }
  });
