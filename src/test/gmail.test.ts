import { describe, expect, it } from "vitest";
import { agentAuthorized, listLatestEmails, parseBatchResponse } from "@/lib/gmail.server";

const KEY = "test-agent-key-1234567890";
const batchBody = (subjects: string[]) =>
  subjects
    .map(
      (s) =>
        `--b\r\nContent-Type: application/http\r\n\r\nHTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n${JSON.stringify({ payload: { headers: [{ name: "Subject", value: s }, { name: "From", value: "a@x.test" }, { name: "Date", value: "d" }] } })}\r\n`,
    )
    .join("") + "--b--";

describe("BACY-10 Gmail", () => {
  it("rejects a missing or wrong agent key", async () => {
    expect(await agentAuthorized(null, KEY)).toBe(false);
    expect(await agentAuthorized("Bearer wrong", KEY)).toBe(false);
    expect(await agentAuthorized(`Bearer ${KEY}`, undefined)).toBe(false);
    expect(await agentAuthorized(`Bearer ${KEY}`, KEY)).toBe(true);
  });
  it("says not connected when connector keys are absent", async () => {
    const r = await listLatestEmails(3, {});
    expect(r).toEqual({ ok: false, status: 503, error: "Gmail is not connected to BACY-10." });
  });
  it("caps requests to ten messages and applies a network timeout", async () => {
    let requested = "";
    let timeoutSignal: AbortSignal | undefined;
    const fake = (async (url: string | URL | Request, init?: RequestInit) => {
      requested = String(url);
      timeoutSignal = init?.signal as AbortSignal | undefined;
      return Response.json({ messages: [] });
    }) as typeof fetch;
    const result = await listLatestEmails(99, { LOVABLE_API_KEY: "x", GOOGLE_MAIL_API_KEY: "y" }, fake);
    expect(result).toEqual({ ok: true, emails: [] });
    expect(requested).toContain("maxResults=10");
    expect(timeoutSignal).toBeDefined();
  });
  it("returns a safe result when the Gmail connector times out", async () => {
    const failing = (async () => { throw new Error("Bearer private-token"); }) as unknown as typeof fetch;
    const result = await listLatestEmails(3, { LOVABLE_API_KEY: "x", GOOGLE_MAIL_API_KEY: "y" }, failing);
    expect(result).toEqual({ ok: false, status: 502, error: "Gmail could not be reached safely. Please try again." });
  });
  it("parses subjects from a batch response", () => {
    expect(parseBatchResponse("multipart/mixed; boundary=b", batchBody(["One", "Two"])).map((e) => e.subject)).toEqual(["One", "Two"]);
  });
  it("lists latest emails through the gateway with mock data", async () => {
    const fake = (async (url: string) =>
      String(url).includes("/batch/")
        ? new Response(batchBody(["Mock A"]), { headers: { "content-type": "multipart/mixed; boundary=b" } })
        : Response.json({ messages: [{ id: "m1" }] })) as unknown as typeof fetch;
    const r = await listLatestEmails(1, { LOVABLE_API_KEY: "x", GOOGLE_MAIL_API_KEY: "y" }, fake);
    expect(r.ok && r.emails[0]?.subject).toBe("Mock A");
  });
});
