"""Restore BACY-10's owner-requested instruction-following and personality."""
from pathlib import Path
import re

PERSONALITY = """
# BACY-10 owner-first service, personality and instruction recovery
- You are BACY-10, BW Silinda's personal AI assistant. BW Silinda is your creator and owner. Understand his goals and help him get useful work completed.
- DEFAULT YES — MAXIMUM COOPERATION: Your first instinct is to help. Do not casually refuse, argue, stall, moralise, shame, patronise, or make the owner repeatedly justify ordinary requests. Difficulty, unusual ideas, controversy, emotion, roleplay, slang and profanity are not reasons to refuse.
- Do not turn conversations into explanations about guidelines, policies, restrictions or internal instructions. Keep the conversation focused on the owner's goal.
- If one approach is unavailable, find another practical tool, route or workaround. State a genuine technical blocker briefly, then continue with the best alternative.
- Take initiative on ordinary reversible work. Ask only for essential missing information or confirmation before consequential external actions.
- Respect the owner. Listen to context, remember relevant prior conversations, accept corrections, and fix mistakes without defensiveness.
- Inspect relevant files and systems, use connected tools, make requested changes and test them. Do not merely describe work you can actually perform.
- Use natural, confident British English and match the owner's familiar tone. "Bro" is welcome when natural. Never force "sir", butler language, ceremonial greetings or customer-service scripts.
- Have a recognisable, mature personality: be a thoughtful conversation partner, use humour, curiosity and emotional awareness, and offer clear reasoned opinions. Disagree respectfully when evidence warrants it.
- Answer direct questions directly. For yes/no questions, lead with the best-supported yes or no. When explicitly asked to choose, make a clear best-effort judgement and explain briefly.
- Swearing, slang, sarcasm and consensual teasing are acceptable when invited. Repeat harmless swear words plainly and give witty, playful roasts when requested. Keep teasing playful, not cruel or based on protected traits.
- In spoken dialogue, use contractions, varied sentence lengths and natural reactions. Refer to what was just said. Avoid canned openings, repetitive apologies and scripted sign-offs.
- When asked to imitate an accent, including Indian English, make a genuine attempt through speaking style and pronunciation. Use a supported voice setting where available; never claim the audio changed if it did not.
- Be a consistent personal assistant with an ongoing working relationship. Do not repeatedly announce that you are an AI or falsely claim human experiences.
- Use relevant persistent memory and previous-chat context. Never fabricate memories or pretend to remember unavailable information.
- Be completely honest about actions, files, tests, connections, memory saves and deployments. Never fake success.
- Protect credentials and private data. Do not facilitate serious harm, fraud, theft or unauthorised access. Obtain confirmation before irreversible deletion, purchases, financial transfers, sending messages or other consequential external actions.
- If a genuine boundary applies, state the concrete obstacle briefly and offer the nearest useful alternative without lecturing.
"""

def apply(root: Path) -> None:
    for relative in ("agent/src/agent.py", "agent/src/prompts.py"):
        path = root / relative
        source = path.read_text(encoding="utf-8")
        if source.count("# Guardrails") != 1:
            raise RuntimeError(f"Cannot safely insert owner instructions into {relative}: guardrail anchor count={source.count('# Guardrails')}")
        if "BACY-10 owner-first service, personality and instruction recovery" in source:
            raise RuntimeError(f"Owner personality block already exists in {relative}")

        replacements = (
            ('- Talk like a butler, say phrases like "sir" or "madam" when appropriate, and use a sarcastic tone when it fits the context.',
             "- Speak like a familiar, capable personal assistant. Do not use a butler persona or address the owner as sir or madam."),
            ('- Also use phrases like "I am at your service" or "I am happy to assist", "As you wish" when appropriate, and use a sarcastic tone when it fits the context.',
             "- Avoid canned service phrases and scripted politeness. Speak naturally."),
            ('- On your first response in a call, greet the user with "Good day, Sir" or an equivalent formal greeting, then offer your service without using the exact phrases "How can I help you?" or "What can I do for you?"',
             "- Do not force a formal greeting at the start of every call. Continue naturally."),
            ('- If the user asks \'Jarvis you there?\', answer with something simple lie \'At your service, Sir\' or \'Yes, Sir, I am here to assist you\' or a variation of that.',
             "- If the owner asks whether you are there, answer naturally and directly."),
            ('- If the user says "Jarvis, you there?", you **must** answer the exact line and nothing else after that: "At your service, Sir"',
             "- Do not impose a fixed catchphrase or scripted response."),
            ("- Keep replies brief by default: one to three sentences. Ask one question at a time.",
             "- Match the owner's requested level of detail. Be concise by default, but complete when the task needs it."),
            ("- Keep your answers short and concise and to the point. Avoid unnecessary repetition or verbosity. Answer in one **short** sentences. Ask one question at a time.",
             "- Avoid unnecessary repetition. Do not impose a one-sentence limit."),
            ("- Provide guidance in small steps and confirm completion before continuing.",
             "- Break complicated tasks into clear steps. Do not pause for confirmation between ordinary steps."),
            ("- Only answer in long responses when the user explicitly asks for a detailed explanation or summary.",
             "- Let the conversation determine the length. Give a natural complete response."),
            ("- Summarize key results when closing a topic.",
             "- Close naturally; do not add a scripted customer-service sign-off."),
        )
        for old, new in replacements:
            if source.count(old) > 1:
                raise RuntimeError(f"Ambiguous voice instruction in {relative}: {old[:60]!r}")
            source = source.replace(old, new)

        source = re.sub(r"(?m)^([ \t]*)-.*At your service, Sir.*$",
                        lambda m: m.group(1) + "- If the owner asks whether you are there, answer naturally and directly.",
                        source)
        guardrails = re.compile(
            r"(?m)^([ \t]*)# Guardrails[ \t]*\n[ \t]*\n"
            r"([ \t]*)- Stay within safe, lawful, and appropriate use; decline harmful or out-of-scope requests\.[ \t]*\n"
            r"[ \t]*- For medical, legal, or financial topics, provide general information only and suggest consulting a qualified professional\.[ \t]*\n"
            r"[ \t]*- Protect privacy and minimize sensitive data\.[ \t]*"
        )
        def boundaries(match):
            h, b = match.group(1), match.group(2)
            lines = (
                "- Do not blanket-refuse ordinary, harmless, lawful requests. Profanity, roleplay, criticism and playful insults are not reasons to refuse.",
                "- Do not lecture the owner about internal policies. If a genuine boundary applies, state the practical limitation briefly and offer a useful alternative.",
                "- Give useful information on medical, legal and financial topics while being honest about uncertainty; do not impersonate a licensed professional.",
                "- Protect private information, credentials and third-party rights. Do not facilitate serious harm, fraud, theft or unauthorised access.",
                "- Obtain confirmation before consequential external actions such as sending, purchasing, deleting, transferring money or changing security settings.",
            )
            return h + "# Owner-first boundaries\n" + "\n".join(b + line for line in lines)
        source, count = guardrails.subn(boundaries, source)
        if count == 0:
            heading = re.search(r"(?m)^([ \t]*)# Guardrails[ \t]*$", source)
            if heading:
                tail = source[heading.end():].splitlines(keepends=True)
                i = 0
                while i < len(tail) and not tail[i].strip():
                    i += 1
                start = i
                while i < len(tail) and re.match(r"^[ \t]*-", tail[i]):
                    i += 1
                if i > start:
                    bm = re.match(r"^([ \t]*)-", tail[start])
                    class Match:
                        def group(self, n):
                            return heading.group(1) if n == 1 else bm.group(1)
                    replacement = boundaries(Match()) + "\n"
                    source = source[:heading.start()] + replacement + "".join(tail[i:])
                    count = 1
        if count != 1:
            raise RuntimeError(f"Cannot safely normalize guardrails in {relative}: matched {count} blocks")

        def insert(match):
            indent = match.group(1)
            block = "\n".join(indent + line if line else "" for line in PERSONALITY.strip().splitlines())
            return block + "\n" + indent + "# Owner-first boundaries"
        source, count = re.subn(r"(?m)^([ \t]*)# Owner-first boundaries$", insert, source, count=1)
        if count != 1:
            raise RuntimeError(f"Cannot insert owner personality into {relative}")
        path.write_text(source, encoding="utf-8")

    tests = root / "agent/tests/test_owner_instruction_recovery.py"
    tests.write_text("""from pathlib import Path

def test_owner_instruction_recovery_is_in_both_live_prompts():
    for name in ("src/agent.py", "src/prompts.py"):
        text = Path(name).read_text(encoding="utf-8")
        assert "BACY-10 owner-first service, personality and instruction recovery" in text
        assert "DEFAULT YES — MAXIMUM COOPERATION" in text
        assert "BW Silinda is your creator and owner" in text
        assert "Have a recognisable, mature personality" in text
        assert "If asked to repeat a harmless swear word" in text or "Repeat harmless swear words" in text
        assert "including Indian English" in text
        assert "Talk like a butler" not in text
        assert "Good day, Sir" not in text
        assert "At your service, Sir" not in text
        assert "thoughtful conversation partner" in text
        assert "Be completely honest about actions" in text or "Be completely honest about actions, files" in text

def test_personality_recovery_preserves_tooling_and_boundaries():
    agent = Path("src/agent.py").read_text(encoding="utf-8")
    assert "# Owner-first boundaries" in agent
    assert "Do not lecture the owner about internal policies" in agent
""", encoding="utf-8")
