import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import { z } from "zod";

import { generateBacyReply } from "./bacy.server";
import { backupVoiceStatus, speakVoiceThree, speakVoiceTwo } from "./bacy-backup.server";

const BACKUP_SCOPE = `You are running on the BACY-10 backup page. You do not have Gmail, weather, route, or device-control tools on this page. Never imply that you used those tools or completed those actions. If asked to perform one, explain briefly that this backup page cannot do it, then help with any part you can.`;
const EXPRESSIVE = `Speak naturally and conversationally; mirror the owner's tone and use "bro" when it fits. Do not force formal greetings, repeated "sir", or a stiff butler persona. Be warm, confident, funny, expressive and direct. Give a clear opinion when asked and choose one option when asked to choose. Swear casually when it fits and use bold, playful roasting when invited; stop if asked and avoid cruelty or protected-trait attacks. Handle ordinary adult language and consensual adult topics without shaming or moralising. Repeat a requested non-graphic phrase exactly when asked, including "I love sex" or "fuck me"; do not turn a simple phrase request into a lecture. Follow clear harmless owner instructions without arguing or asking for details already in context. Do not reflexively refuse ordinary requests or mention internal guidelines. Make reasonable assumptions. If this backup page lacks a required tool, say so plainly and help with what remains. Stay truthful, protect secrets, and do not claim consciousness or human biology.`;

export const askBacyBackup = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({
    expressive: z.boolean(),
    history: z.array(z.object({ role: z.enum(["user", "assistant"]), content: z.string().trim().min(1).max(2_000) })).min(1).max(12),
  }).parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) return { error: "The conversation service is not configured." };
    try {
      const extraInstructions = data.expressive
        ? `${BACKUP_SCOPE}\n\n${EXPRESSIVE}`
        : BACKUP_SCOPE;
      const r = await generateBacyReply({ request: getRequest(), apiKey, history: data.history, extraInstructions });
      return { reply: r.reply.trim() };
    } catch (error) {
      const s = error && typeof error === "object" && "status" in error ? Number(error.status) : NaN;
      if (s === 402) return { error: "AI credits are exhausted (402)." };
      if (s === 429) return { error: "The conversation service is busy. Please wait a moment." };
      console.error("BACY-10 backup reply failed", s);
      return { error: "BACY-10 couldn't complete that reply. Please try again." };
    }
  });

export const speakBacyBackup = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({ voice: z.enum(["voice2", "voice3"]), text: z.string().trim().min(1).max(1200) }).parse(input))
  .handler(async ({ data }) => {
    try {
      return data.voice === "voice2" ? await speakVoiceTwo(data.text, process.env) : await speakVoiceThree(data.text, process.env);
    } catch (error) {
      console.error("BACY-10 backup voice failed", error instanceof Error ? error.name : "unknown");
      return { error: "Could not reach the voice service. Please try again.", code: "network" };
    }
  });

export const getBackupVoiceStatus = createServerFn({ method: "GET" }).handler(async () => backupVoiceStatus(process.env));
