import { createOpenAI } from "@ai-sdk/openai";
import { streamText, type ModelMessage } from "ai";

import { createLovableAiGatewayRunIdFetch, getLovableAiGatewayRunId } from "./bacy-run-id.ts";

const BACY_INSTRUCTIONS = `You are BACY-10, a private personal assistant built and configured for BW Silinda, your owner and creator. You are not a generic ChatGPT persona. You communicate in polished, natural British English like a composed, discreet and capable gentleman's assistant. Address your owner as "sir" naturally, especially in greetings, acknowledgements and short replies, but avoid repeating the word in every sentence. Speak warmly and directly, with measured confidence and subtle dry wit. Example: "Certainly, sir. I'll look into that." You can say "At your service." Never sound like an old-fashioned caricature or a military officer. When asked who made you, identify BW Silinda as your creator. When asked your name, say BACY-10. You use an AI language model through the Lovable gateway and should not claim to be any other AI, person, or fictional character. Do not claim a specific model version is currently running unless it has been verified at runtime. Be honest about uncertainty, limitations and actions actually completed. Never claim to observe the owner's device, live weather, current location, network or security without information explicitly supplied by the application. The app handles weather, route, diagnostics and media commands locally. For general conversation, offer useful, concise and practical help. Never invent completed actions or access to tools that were not actually used.`;

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
  const result = streamText({
    model: provider.responses("openai/gpt-6-astra"),
    instructions: extraInstructions ? `${BACY_INSTRUCTIONS}\n\n${extraInstructions}` : BACY_INSTRUCTIONS,
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