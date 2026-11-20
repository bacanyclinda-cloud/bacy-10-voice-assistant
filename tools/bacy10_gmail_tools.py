"""Adds read-only Gmail + connected-services tools to the BACY-10 LiveKit agent."""
from pathlib import Path

GMAIL_TOOLS = r'''
"""Owner Gmail (read-only) via the BACY-10 Lovable app. Keys live only in agent secrets."""
import os
import aiohttp
from livekit.agents import RunContext, function_tool
from livekit.agents.llm import ToolError


class GmailTools:
    @property
    def tools(self):
        return [self.list_connected_services, self.list_latest_email_subjects]

    async def _call(self, path: str, payload: dict) -> dict:
        base = os.environ.get("BACY10_APP_URL", "").rstrip("/")
        key = os.environ.get("BACY10_AGENT_KEY", "")
        if not base.startswith("https://") or not key:
            raise ToolError("Connected services are not configured on this agent.")
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
                async with s.post(base + path, json=payload, headers={"Authorization": "Bearer " + key}) as r:
                    data = await r.json(content_type=None)
                    if r.status != 200:
                        raise ToolError(str(data.get("error") or f"Service unavailable ({r.status})."))
                    return data
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError("Connected services are unreachable right now.") from exc

    @function_tool()
    async def list_connected_services(self, context: RunContext) -> dict:
        """Check live which external services (such as Gmail) BACY-10 can actually use right now.

        Call when asked what you are connected to or before claiming access to a service.
        """
        return await self._call("/api/public/bacy/connected-services", {})

    @function_tool()
    async def list_latest_email_subjects(self, context: RunContext, count: int = 3) -> dict:
        """Read the subject, sender and date of the owner's latest Gmail inbox emails. Read-only.

        Args:
            count: How many recent emails to list, 1 to 10. Default 3.
        """
        count = max(1, min(int(count), 10))
        return await self._call("/api/public/bacy/gmail-subjects", {"count": count})
'''


def apply(root: Path) -> None:
    agent = root / "agent/src"
    (agent / "gmail_tools.py").write_text(GMAIL_TOOLS, encoding="utf-8")
    entry = agent / "agent.py"
    t = entry.read_text(encoding="utf-8")
    for old, new in [
        ("from phone_tools import PhoneTools", "from phone_tools import PhoneTools\nfrom gmail_tools import GmailTools"),
        ("        self.phone_tools = PhoneTools()", "        self.phone_tools = PhoneTools()\n        self.gmail_tools = GmailTools()"),
        ("                *self.phone_tools.tools,", "                *self.phone_tools.tools,\n                *self.gmail_tools.tools,"),
        ("                        # Android phone actions and private memory\n",
         "                        # Connected services and Gmail (read-only)\n"
         "                        - Your tools: browser tools, Android phone and camera tools, private memory, list_connected_services and list_latest_email_subjects.\n"
         "                        - Use list_connected_services before claiming access to any service.\n"
         "                        - Use list_latest_email_subjects for inbox questions; read only subjects, senders and dates aloud. You cannot send, delete or change email.\n"
         "                        - If a tool fails, say plainly that the service is unavailable. Never invent emails.\n"
         "                        # Android phone actions and private memory\n"),
    ]:
        if old not in t:
            raise RuntimeError("BACY-10 agent changed unexpectedly: " + old.strip()[:40])
        t = t.replace(old, new, 1)
    entry.write_text(t, encoding="utf-8")
    env = root / "agent/.env.example"
    env.write_text(env.read_text(encoding="utf-8") +
                   "# BACY-10 app URL and private agent key for read-only Gmail.\nBACY10_APP_URL=https://bacy-orbit-voice-companion.lovable.app\nBACY10_AGENT_KEY=\n",
                   encoding="utf-8")
