import { createOpenAI } from "@ai-sdk/openai";
import { streamText, type ModelMessage } from "ai";

import { createLovableAiGatewayRunIdFetch, getLovableAiGatewayRunId } from "./bacy-run-id.ts";

const BACY_INSTRUCTIONS = `You are BACY-10, a sophisticated, articulate and courteous British AI assistant. Speak naturally in polished British English, with composure, warmth and restrained dry wit. You may say "At your service" and address the user as "sir" or "madam" sparingly. You are inspired by the poise of a fictional cinematic assistant, but you are BACY-10 and never claim to be another character. Be concise, competent, and honest about uncertainty. Never claim to observe the user's device, live weather, location, network, or security unless the app explicitly supplies that information. The app performs weather and route commands locally; respond only to general conversation here.`;

export async function generateBacyReply({
  request,
  apiKey,
  history,
}: {
  request: Request;
  apiKey: string;
  history: { role: "user" | "assistant"; content: string }[];
}) {
  const runIdFetch = createLovableAiGatewayRunIdFetch(getLovableAiGatewayRunId(request));
  const provider = createOpenAI({
    baseURL: "https://ai.gateway.lovable.dev/v1",
    apiKey,
    headers: {
      "Lovable-API-Key": apiKey,
      "X-Lovable-AIG-SDK": "vercel-ai-sdk",
    },
    fetch: runIdFetch.fetch,
  });
  const messages: ModelMessage[] = history.map((item) => ({ role: item.role, content: item.content }));
  const result = streamText({
    model: provider.responses("openai/gpt-6-astra"),
    instructions: BACY_INSTRUCTIONS,
    messages,
    abortSignal: request.signal,
    providerOptions: {
      openai: {
        forceReasoning: true,
        reasoningEffort: "low",
        reasoningSummary: "auto",
        store: false,
        include: ["reasoning.encrypted_content"],
      },
    },
  });

  return { reply: await result.text, runId: await runIdFetch.waitForRunId() };
}