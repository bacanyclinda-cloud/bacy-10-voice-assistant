import { describe, expect, it } from "vitest";
import { readSpeechResults, type BrowserSpeechResult } from "@/lib/speech-results";

const segment = (transcript: string, isFinal: boolean): BrowserSpeechResult =>
  ({ isFinal, 0: { transcript } });

describe("Android Web Speech transcript handling", () => {
  it("keeps recognised speech when the browser stops before finalising", () => {
    expect(readSpeechResults([segment("hello", false)])).toEqual({
      final: "", interim: "hello", best: "hello",
    });
  });

  it("uses the finalised result without duplicating interim words", () => {
    expect(readSpeechResults([segment("hello", true)])).toEqual({
      final: "hello", interim: "", best: "hello",
    });
  });

  it("combines partial final and interim speech into the sentence", () => {
    expect(readSpeechResults([segment("hello", true), segment("sir", false)]).best)
      .toBe("hello sir");
  });

  it("does not invent speech if the microphone detected no words", () => {
    expect(readSpeechResults([segment(" ", false)]).best).toBe("");
    expect(readSpeechResults([]).best).toBe("");
  });

  it("skips missing result entries safely", () => {
    const results: BrowserSpeechResult[] = [];
    results.length = 2;
    results[1] = segment("hello", true);
    expect(readSpeechResults(results).best).toBe("hello");
  });
});
