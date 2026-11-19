/**
 * Web Speech API results can be interim-only when Android ends a recognition
 * session. Never discard audible speech merely because isFinal stayed false.
 */
export type BrowserSpeechResult = {
  isFinal: boolean;
  0: { transcript: string };
};

export function readSpeechResults(results: ArrayLike<BrowserSpeechResult>): {
  final: string;
  interim: string;
  best: string;
} {
  const final: string[] = [];
  const interim: string[] = [];
  for (let i = 0; i < results.length; i += 1) {
    const item = results[i];
    const phrase = item?.[0]?.transcript?.trim();
    if (!item || !phrase) continue;
    (item.isFinal ? final : interim).push(phrase);
  }
  const finalText = final.join(" ").trim();
  const interimText = interim.join(" ").trim();
  return {
    final: finalText,
    interim: interimText,
    best: [finalText, interimText].filter(Boolean).join(" ").trim(),
  };
}
