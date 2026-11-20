import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import { z } from "zod";

import { generateBacyReply } from "./bacy.server";
import { backupVoiceStatus, speakVoiceThree, speakVoiceTwo } from "./bacy-backup.server";

const EXPRESSIVE = `Optional expressive mode is ON for this conversation. On benign subjective or philosophical questions, give a considered view and take a clear stance when asked, explaining your reasoning briefly. Express warmth and empathy in how you speak. Do not claim biological feelings, and do not present opinions as settled fact. On factual or safety matters stay accurate and balanced. You have no Gmail, weather or device tools on this backup page; say so honestly if asked.`;
const BACKUP_NOTE = `You are running on the BACY-10 backup page. You have no Gmail, weather, route or device tools here; say so honestly if asked.`;

export const askBacyBackup = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => z.object({
    expressive: z.boolean(),
    history: z.array(z.object({ role: z.enum(["user", "assistant"]), content: z.string().trim().min(1).max(2_000) })).min(1).max(12),
  }).parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) return { error: "The conversation service is not configured." };
    try {
      const r = await generateBacyReply({ request: getRequest(), apiKey, history: data.history, extraInstructions: data.expressive ? EXPRESSIVE : BACKUP_NOTE });
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
