import { describe, expect, it } from "vitest";
import { redactSensitiveText } from "@/lib/lovable-error-reporting";

describe("telemetry redaction", () => {
  it("removes common API keys, bearer tokens and JWTs", () => {
    const text = [
      "key=sk-" + "a".repeat(30),
      "Authorization: Bearer " + "b".repeat(32),
      "jwt=eyJ" + "a".repeat(20) + "." + "b".repeat(20) + "." + "c".repeat(20),
      "google=AIza" + "C".repeat(35),
    ].join(" ");
    const safe = redactSensitiveText(text);
    expect(safe).not.toContain("sk-" + "a".repeat(30));
    expect(safe).not.toContain("b".repeat(32));
    expect(safe).not.toContain("eyJ" + "a".repeat(20));
    expect(safe).not.toContain("AIza");
  });

  it("removes email addresses, phone numbers and long card-like numbers", () => {
    const safe = redactSensitiveText("contact test@example.com or +27123456789, card 4111 1111 1111 1111");
    expect(safe).not.toContain("test@example.com");
    expect(safe).not.toContain("+27123456789");
    expect(safe).not.toContain("4111 1111 1111 1111");
  });

  it("preserves ordinary diagnostic text", () => {
    expect(redactSensitiveText("Bacy 10 failed to connect with status 503.")).toContain("status 503");
  });
});
