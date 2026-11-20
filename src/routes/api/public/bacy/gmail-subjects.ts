import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

const Body = z.object({ count: z.number().int().min(1).max(10).default(3) });
const json = (x: unknown, status = 200) =>
  Response.json(x, { status, headers: { "Cache-Control": "no-store" } });

// Called only by the BACY-10 cloud voice agent with its private agent key.
export const Route = createFileRoute("/api/public/bacy/gmail-subjects")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { agentAuthorized, listLatestEmails } = await import("@/lib/gmail.server");
        if (!(await agentAuthorized(request.headers.get("Authorization"), process.env["BACY10_AGENT_KEY"])))
          return json({ error: "Unauthorized" }, 401);
        const parsed = Body.safeParse(await request.json().catch(() => ({})));
        if (!parsed.success) return json({ error: "count must be 1-10" }, 400);
        const r = await listLatestEmails(parsed.data.count, process.env);
        return r.ok ? json({ emails: r.emails }) : json({ error: r.error }, r.status);
      },
    },
  },
});
