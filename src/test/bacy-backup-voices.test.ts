import { describe, expect, it } from "vitest";
import { parseVoiceSwitch } from "@/lib/bacy-backup.voices";
import { backupVoiceStatus, speakVoiceThree } from "@/lib/bacy-backup.server";

describe("Backup voice controls", () => {
  it("understands natural voice switch commands", () => {
    expect(parseVoiceSwitch("Hey BACY-10, switch to voice two")).toBe("voice2");
    expect(parseVoiceSwitch("Hey Basic 10, use voice three")).toBe("voice3");
    expect(parseVoiceSwitch("use ElevenLabs")).toBe("voice3");
    expect(parseVoiceSwitch("go back to original voice")).toBe("voice1");
    expect(parseVoiceSwitch("voice one")).toBe("voice1");
  });
  it("doesn't intercept normal personal or philosophical conversation", () => {
    expect(parseVoiceSwitch("Do you believe science or God made humans?")).toBe(null);
    expect(parseVoiceSwitch("Explain how the voice works")).toBe(null);
  });
  it("shows absent ElevenLabs credentials rather than inventing success", async () => {
    expect(backupVoiceStatus({})).toEqual({ voice2: false, voice3: false });
    await expect(speakVoiceThree("Hello", {})).resolves.toMatchObject({ code: "needs_key" });
  });
  it("reports only availability, never exposes credentials", () => {
    expect(backupVoiceStatus({ ELEVENLABS_API_KEY: "test-secret-not-real" })).toEqual({ voice2: false, voice3: true });
  });
});
