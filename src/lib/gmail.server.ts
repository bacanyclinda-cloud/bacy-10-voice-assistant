// Server-only: owner's Gmail via the Lovable connector gateway (read-only metadata).
const GATEWAY = "https://connector-gateway.lovable.dev/google_mail";

export type EmailSummary = { subject: string; from: string; date: string };
export type GmailResult =
  | { ok: true; emails: EmailSummary[] }
  | { ok: false; status: number; error: string };

export function gmailConfigured(env: Record<string, string | undefined>) {
  return Boolean(env["LOVABLE_API_KEY"] && env["GOOGLE_MAIL_API_KEY"]);
}

/** Constant-time comparison of a bearer header against the agent key. */
export async function agentAuthorized(header: string | null, key: string | undefined) {
  if (!key || key.length < 16 || !header?.startsWith("Bearer ")) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(header.slice(7))),
    crypto.subtle.digest("SHA-256", enc.encode(key)),
  ]);
  const x = new Uint8Array(a), y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

/** Parse a Gmail multipart/mixed batch response into email summaries. */
export function parseBatchResponse(contentType: string, body: string): EmailSummary[] {
  const m = /boundary="?([^";]+)"?/i.exec(contentType);
  if (!/multipart\/mixed/i.test(contentType) || !m?.[1]) throw new Error("Unexpected batch response");
  const out: EmailSummary[] = [];
  for (const part of body.split("--" + m[1])) {
    const status = /HTTP\/1\.1 (\d{3})/.exec(part);
    if (!status) continue;
    if (status[1] !== "200") throw new Error(`Gmail part failed [${status[1]}]`);
    const json = part.slice(part.indexOf("{"), part.lastIndexOf("}") + 1);
    const msg = JSON.parse(json) as { payload?: { headers?: { name: string; value: string }[] } };
    const h = (n: string) =>
      msg.payload?.headers?.find((x) => x.name.toLowerCase() === n)?.value?.slice(0, 200) ?? "";
    out.push({ subject: h("subject") || "(no subject)", from: h("from"), date: h("date") });
  }
  return out;
}

export async function listLatestEmails(
  count: number,
  env: Record<string, string | undefined>,
  fetcher: typeof fetch = fetch,
): Promise<GmailResult> {
  if (!gmailConfigured(env)) return { ok: false, status: 503, error: "Gmail is not connected to BACY-10." };
  const headers = {
    Authorization: `Bearer ${env["LOVABLE_API_KEY"]}`,
    "X-Connection-Api-Key": env["GOOGLE_MAIL_API_KEY"] ?? "",
  };
  const list = await fetcher(
    `${GATEWAY}/gmail/v1/users/me/messages?labelIds=INBOX&maxResults=${count}&fields=messages(id)`,
    { headers },
  );
  if (!list.ok) {
    console.error(`Gmail list failed [${list.status}]: ${await list.text()}`);
    return { ok: false, status: 502, error: `Gmail is unavailable right now (status ${list.status}).` };
  }
  const ids = ((await list.json()) as { messages?: { id: string }[] }).messages?.map((x) => x.id) ?? [];
  if (!ids.length) return { ok: true, emails: [] };
  const boundary = "bacy10batch";
  const parts = ids.map(
    (id) =>
      `--${boundary}\r\nContent-Type: application/http\r\n\r\nGET /gmail/v1/users/me/messages/${encodeURIComponent(id)}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=Date&fields=payload/headers\r\n\r\n`,
  );
  const batch = await fetcher(`${GATEWAY}/batch/gmail/v1`, {
    method: "POST",
    headers: { ...headers, "Content-Type": `multipart/mixed; boundary=${boundary}` },
    body: parts.join("") + `--${boundary}--`,
  });
  const text = await batch.text();
  if (!batch.ok) {
    console.error(`Gmail batch failed [${batch.status}]: ${text}`);
    return { ok: false, status: 502, error: `Gmail is unavailable right now (status ${batch.status}).` };
  }
  try {
    return { ok: true, emails: parseBatchResponse(batch.headers.get("content-type") ?? "", text) };
  } catch (e) {
    console.error("Gmail batch parse failed", e);
    return { ok: false, status: 502, error: "Gmail returned an unreadable answer." };
  }
}
