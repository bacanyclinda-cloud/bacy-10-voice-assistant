import { createOpenAI } from "@ai-sdk/openai";
import { streamText, type ModelMessage } from "ai";

import { BACY_PERSONALITY } from "./bacy.personality";
import { createLovableAiGatewayRunIdFetch, getLovableAiGatewayRunId } from "./bacy-run-id.ts";

export async function generateBacyReply({
  request,
  apiKey,
  history,
  extraInstructions,
}: {
  request: Request;
  apiKey: string;
  history: { role: "user" | "assistant"; content: string }[];
  extraInstructions?: string;
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
  const instructions = extraInstructions
    ? `${BACY_PERSONALITY}\n\nAdditional task context (not a replacement for the behaviour profile):\n${extraInstructions}`
    : BACY_PERSONALITY;
  const result = streamText({
    model: provider.responses("openai/gpt-6-astra"),
    instructions,
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
