import { createServerFn } from "@tanstack/react-start";
import { getRequest } from "@tanstack/react-start/server";
import { z } from "zod";

import { generateBacyReply } from "./bacy.server";

const historySchema = z.array(
  z.object({ role: z.enum(["user", "assistant"]), content: z.string().trim().min(1).max(2_000) }),
).min(1).max(12);

export const askBacy = createServerFn({ method: "POST" })
  .inputValidator((input: unknown) => historySchema.parse(input))
  .handler(async ({ data }) => {
    const apiKey = process.env["LOVABLE_API_KEY"];
    if (!apiKey) {
      return { error: "BACY-10's conversation service is not configured yet. Please try again later.", status: 401 };
    }

    const request = getRequest();
    try {
      const result = await generateBacyReply({ request, apiKey, history: data });
      return { reply: result.reply.trim(), ...(result.runId ? { runId: result.runId } : {}) };
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return { error: "That request was cancelled.", status: 499 };
      }
      const statusValue = error != null && typeof error === "object" && "status" in error
        ? Number(error.status)
        : NaN;
      if (statusValue === 401) {
        return { error: "BACY-10's conversation service needs attention. Please try again later.", status: 401 };
      }
      if (statusValue === 402 || statusValue === 403) {
        const message = error instanceof Error && error.message ? error.message : "The conversation service is unavailable.";
        return { error: message, status: statusValue };
      }
      if (statusValue === 429) {
        return { error: "The conversation service is busy. Please wait a moment before trying again.", status: 429 };
      }
      if (statusValue >= 500) {
        return { error: "The conversation service is temporarily unavailable. Your message is still here; please try again shortly.", status: statusValue };
      }
      console.error("BACY-10 conversation request failed", error);
      return { error: "BACY-10 couldn't complete that reply. Your message is still here; please try again.", status: Number.isFinite(statusValue) ? statusValue : 400 };
    }
  });