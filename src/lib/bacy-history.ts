export type ConversationMessage = { role: "user" | "assistant"; content: string };

const MAX_STORED_MESSAGES = 40;
const MAX_PROMPT_MESSAGES = 12;
const MAX_MESSAGE_LENGTH = 2000;

/** Restore only well-formed conversation messages from untrusted browser storage. */
export function restoreConversation(raw: string | null): ConversationMessage[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is ConversationMessage =>
      item !== null && typeof item === "object" &&
      ((item as ConversationMessage).role === "user" || (item as ConversationMessage).role === "assistant") &&
      typeof (item as ConversationMessage).content === "string" &&
      (item as ConversationMessage).content.trim().length > 0 &&
      (item as ConversationMessage).content.length <= MAX_MESSAGE_LENGTH
    ).slice(-MAX_STORED_MESSAGES);
  } catch {
    return [];
  }
}

/** Keep local continuity bounded while retaining more context than the model prompt. */
export function appendConversation(
  history: ConversationMessage[],
  user: string,
  assistant: string,
): ConversationMessage[] {
  return [
    ...history,
    { role: "user" as const, content: user },
    { role: "assistant" as const, content: assistant },
  ].slice(-MAX_STORED_MESSAGES);
}

/** The AI request is deliberately smaller than the locally retained transcript. */
export function promptConversation(history: ConversationMessage[], user: string): ConversationMessage[] {
  return [...history.slice(-(MAX_PROMPT_MESSAGES - 1)), { role: "user", content: user }];
}

export function serializeConversation(history: ConversationMessage[]): string {
  return JSON.stringify(history.slice(-MAX_STORED_MESSAGES));
}
