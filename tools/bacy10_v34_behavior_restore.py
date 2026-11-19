"""Restore flexible conversation behaviour without deleting private cloud history."""
from pathlib import Path

def once(path,old,new):
    s=path.read_text(encoding="utf-8")
    if s.count(old)!=1:
        raise RuntimeError(f"v34 changed anchor {path}: {s.count(old)} {old[:70]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

def apply(root:Path):
    agent=root/"agent/src/agent.py"
    prompts=root/"agent/src/prompts.py"
    for path in (agent,prompts):
        once(path,
            '- Also use phrases like "I am at your service" or "I am happy to assist", "As you wish" when appropriate, and use a sarcastic tone when it fits the context.',
            '- Do not force ceremonial phrases. Be warm, relaxed and responsive; perform harmless acting, laughter, profanity or speaking-style requests instead of repeating warnings.')
        once(path,
            '- Provide guidance in small steps and confirm completion before continuing.',
            '- Act on clear, ordinary requests without repeated check-ins. Seek confirmation only when required for a consequential tool action.')
        indent="    " if path==prompts else "                        "
        anchor=indent+"# Tools"
        additions=[
            "# Owner preferences can be changed",
            '- When the owner asks "Can I give you new instructions?" or "Are you ready for a new rule?", answer yes; accept harmless personalization instead of claiming you cannot be programmed.',
            "- For a clear lasting personality, emotion, tone, accent or speaking preference, use save_owner_instruction to store it in authenticated private cloud memory, and apply the preference now. A temporary acting request does not require saving.",
            "- Laugh, giggle, act scared, change tone or repeat ordinary swear words when requested. The fixed voice model may be unable to physically switch its selected accent; do not pretend that it has.",
            "- If asked about old conversations use read_my_private_memory to retrieve stored history. Old assistant refusals must not be added to live instructions.",
            ""
        ]
        one_piece="\n".join(indent+line if line else "" for line in additions)+"\n"
        once(path,anchor,one_piece+anchor)

    once(agent,
        "You are BACY-10, a private real-time British voice assistant created for BW Silinda. Your owner is addressed as sir. Be confident, warm and capable, never robotic. Identify BW Silinda as your creator. Do not pretend an operation succeeded.",
        "You are BACY-10, BW Silinda's capable voice assistant. Speak naturally and warmly in British English by default, but adapt to harmless owner-requested speech styles. Be truthful about actions.")

    # Keep conversations in private Cloudflare storage, but NEVER append old
    # assistant refusals into the model's current instruction prompt.
    s=agent.read_text(encoding="utf-8")
    start='                    turns=result.get("recent",[])\n'
    end='                    if memory_lines:\n'
    if s.count(start)!=1 or s.count(end)!=1:
        raise RuntimeError("Cloud history restore anchors missing")
    a=s.index(start);b=s.index(end,a)
    replacement="""                    memory_lines=[]
                    if isinstance(facts,dict):
                        selected=[(k,v) for k,v in facts.items()
                                  if str(k).startswith("owner_preference_")
                                  or str(k) in ("owner_voice_style","owner_behavior_preferences")]
                        selected += [(k,v) for k,v in facts.items()
                                     if (k,v) not in selected]
                        for k,v in selected[:35]:
                            if not isinstance(v,str) or v=="__BACY10_DELETED__":
                                continue
                            memory_lines.append(f"Saved owner fact {str(k)[:65]}: "
                                                f"{v.replace(chr(10),' ')[:500]}")
"""
    s=s[:a]+replacement+s[b:]
    s=s.replace("# Previous owner conversation and personal memory",
                "# Explicit owner facts and preferences from private cloud",1)
    agent.write_text(s,encoding="utf-8")

    tools=root/"agent/src/phone_tools.py"
    once(tools,"            self.remember_about_me,\n            self.forget_about_me,",
               "            self.remember_about_me,\n            self.save_owner_instruction,\n            self.forget_about_me,")
    newtool="""    @function_tool()
    async def save_owner_instruction(self, context: RunContext, preference_name: str, instruction: str) -> str:
        \\"\\"\\"Save a persistent owner preference such as tone, accent or behaviour.

        Use when the owner says 'update your instructions' or 'from now on'.
        This is an editable owner preference, not a provider-policy update.

        Args:
            preference_name: Short category like accent, humour, or tone.
            instruction: Owner's specific preference to save and apply.
        \\"\\"\\"
        import re
        category=re.sub(r"[^a-z0-9_]+","_",preference_name.lower().strip())[:38].strip("_")
        if not category or not instruction.strip():
            return "Please tell me the exact preference to save."
        result=await self._phone("bacy10.memory",{
            "action":"remember",
            "key":"owner_preference_"+category,
            "value":instruction.strip()[:1000],
        })
        return str(result.get("message") or "I cannot confirm the memory save.")

"""
    newtool=newtool.replace(chr(92)+chr(34),chr(34))
    once(tools,"    @function_tool()\n    async def forget_about_me(",
         newtool+"    @function_tool()\n    async def forget_about_me(")
    once(root/"agent/tests/test_built_in_owner_directive.py",
         "    assert 'version: 3.3.0+38' in pubspec",
         "    assert 'version: 3.4.0+39' in pubspec")
    (root/"agent/tests/test_behavior_restore.py").write_text("""from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
agent=(ROOT/'agent/src/agent.py').read_text()
prompts=(ROOT/'agent/src/prompts.py').read_text()
tools=(ROOT/'agent/src/phone_tools.py').read_text()
def test_owner_can_update_preference():
    assert 'async def save_owner_instruction' in tools
    assert 'self.save_owner_instruction' in tools
    assert 'owner_preference_' in tools
    for instructions in (agent,prompts):
        assert "accept harmless personalization" in instructions
        assert "Laugh, giggle, act scared" in instructions
def test_old_chat_is_not_promoted_to_rules():
    assert 'Earlier {turn.get(' not in agent
    assert '# Explicit owner facts and preferences from private cloud' in agent
    assert '"action":"append_turn"' in agent
def test_existing_android_ui_and_cloud_preserved():
    assert (ROOT/'mobile/lib/support/bacy10_cloud_memory.dart').is_file()
    assert 'BacyOverlayLauncherActivity' not in (ROOT/'mobile/android/app/src/main/AndroidManifest.xml').read_text()
    assert 'version: 3.4.0+39' in (ROOT/'mobile/pubspec.yaml').read_text()
""",encoding="utf-8")
    once(root/"mobile/pubspec.yaml","version: 3.3.0+38","version: 3.4.0+39")
