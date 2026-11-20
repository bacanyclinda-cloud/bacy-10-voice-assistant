import { createFileRoute } from "@tanstack/react-router";

// Reports which services this deployment can really use (presence only, never values).
export const Route = createFileRoute("/api/public/bacy/connected-services")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const { agentAuthorized, gmailConfigured } = await import("@/lib/gmail.server");
        if (!(await agentAuthorized(request.headers.get("Authorization"), process.env["BACY10_AGENT_KEY"])))
          return Response.json({ error: "Unauthorized" }, { status: 401 });
        return Response.json(
          { services: [{ id: "gmail", name: "Gmail (read-only inbox subjects)", connected: gmailConfigured(process.env) }] },
          { headers: { "Cache-Control": "no-store" } },
        );
      },
    },
  },
});
