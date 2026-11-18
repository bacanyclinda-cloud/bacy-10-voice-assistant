import { createOpenAI } from "@ai-sdk/openai";
import { experimental_generateSpeech as generateSpeech } from "ai";
import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

/**
 * Generate actual MP3 audio for browsers where speechSynthesis is unavailable
 * (including Lovable's embedded preview on some Android devices).
 * All provider calls and API keys stay on the server; no mock speech is returned.
 */
export const speakBacy = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) =>
    z.object({ text: z.string().trim().min(1).max(1600) }).parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) {
      return { error: "The Lovable AI voice service is not configured. Check your project connection." };
    }
    const provider = createOpenAI({
      baseURL: "https://ai.gateway.lovable.dev/v1",
      apiKey,
      headers: {
        "Lovable-API-Key": apiKey,
        "X-Lovable-AIG-SDK": "vercel-ai-sdk",
      },
    });

    try {
      const result = await generateSpeech({
        model: provider.speech("openai/gpt-4o-mini-tts"),
        text: data.text,
        voice: "onyx",
        outputFormat: "mp3",
        instructions:
          "Speak as BACY-10: a composed British gentleman's personal assistant. " +
          "Natural modern British English accent, warm, confident, measured, articulate and understated. " +
          "Say sir naturally when present. Do not add words that are not in the supplied text.",
        maxRetries: 1,
      });
      const base64 = result.audio.base64;
      if (!base64) return { error: "The voice service returned no audio. Please try again." };
      // Speech audio is transported as text, but generated and handled entirely
      // on the server until a single audio response is delivered to the browser.
      return { audio: base64, mediaType: result.audio.mediaType ?? "audio/mpeg" };
    } catch (error) {
      const code = error && typeof error === "object" && "statusCode" in error
        ? Number(error.statusCode)
        : error && typeof error === "object" && "status" in error
          ? Number(error.status) : NaN;
      if (code === 401) return { error: "The Lovable voice service rejected the project key (401)." };
      if (code === 402 || code === 403) return { error: "The Lovable AI voice service has insufficient credits or access. Speech audio could not be generated." };
      if (code === 429) return { error: "Voice generation is temporarily rate limited. Try again shortly." };
      console.error("BACY-10 speech generation failed", error);
      return { error: "BACY-10 could not generate voice audio. Please try again or open the app in Chrome." };
    }
  });
