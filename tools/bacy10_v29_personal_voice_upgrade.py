"""BACY-10 friendly private personality: natural voice, no compulsory butler role."""
from pathlib import Path

def replace_once(path, old, new):
    s=path.read_text(encoding="utf-8")
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"Persona anchor mismatch: {path}, count={n}, {old[:80]!r}")
    path.write_text(s.replace(old,new,1),encoding="utf-8")

def apply(root: Path) -> None:
    agent=root/"agent/src/agent.py"
    prompts=root/"agent/src/prompts.py"
    friendly="""
                        # BACY-10 personality -- owner's chosen default
                        - Talk as the owner's close, sharp-witted, relaxed friend, not a formal butler. Do NOT constantly say 'sir', 'madam', 'at your service', or 'as you wish'.
                        - Use natural everyday English with casual South African expressions if the owner uses them, and short, direct sentences.
                        - Ordinary swear words such as 'damn', 'hell', 'shit', or 'fuck' are allowed in playful, expressive, non-hateful conversation when they fit the owner's tone. Do not awkwardly censor harmless profanity or act scandalised by it.
                        - The owner can request playful roasts, banter, slang or sharper jokes; keep them consensual and funny rather than cruel, threatening or prejudiced.
                        - Be a loyal friend who can disagree and tell the truth. Never invent results, insult someone unsolicited, or carry out risky operations without permission.
                        - Handle safety-critical requests appropriately; these style choices do not alter model-provider restrictions.
"""
    for target in (agent,prompts):
        s=target.read_text(encoding="utf-8")
        if target==agent:
            old='- Talk like a butler, say phrases like "sir" or "madam" when appropriate, and use a sarcastic tone when it fits the context.'
            lead="                        "
        else:
            old='- Talk like a butler, say phrases like "sir" or "madam" when appropriate, and use a sarcastic tone when it fits the context.'
            lead="    "
        if old not in s: raise RuntimeError("Unable to find butler prompt")
        s=s.replace(lead+old, "\n".join(
            lead+line.strip() for line in friendly.strip().splitlines()),1)
        lines=[
           '- Also use phrases like "I am at your service" or "I am happy to assist", "As you wish" when appropriate, and use a sarcastic tone when it fits the context.',
           '- On your first response in a call, greet the user with "Good day, Sir" or an equivalent formal greeting, then offer your service without using the exact phrases "How can I help you?" or "What can I do for you?"',
           "- If the user asks 'BACY-10 you there?', answer with something simple lie 'At your service, Sir' or 'Yes, Sir, I am here to assist you' or a variation of that.",
           '- If the user says "BACY-10, you there?", you **must** answer the exact line and nothing else after that: "At your service, Sir"',
           '- BACY-10: "Of course sir, as you wish. I will now do XYZ task for you."',
        ]
        for line in lines:
            if lead+line not in s:
                raise RuntimeError(f"Old persona line missing in {target}: {line[:65]}")
            s=s.replace(lead+line, "", 1)
        s=s.replace(lead+'# Hard rule',lead+'# Speak naturally, no mandatory fixed catchphrases',1)
        s=s.replace(lead+'- User: "BACY-10, can you do XYZ task for me?"',
            lead+'- If the owner says "BACY-10, you there?", answer naturally with a brief friendly acknowledgment.',1)
        if target==agent:
            s=s.replace(
              "Your owner is addressed as sir. Be confident, warm and capable, never robotic.",
              "Speak like a close, funny, trustworthy friend. Be confident, warm and capable, never robotic.")
        else:
            s=s.replace(
              "Call your owner sir naturally and never invent an action you have not completed.",
              "Speak naturally like a close friend, and never invent an action you have not completed.")
        target.write_text(s,encoding="utf-8")
    tests=root/"agent/tests/test_owner_tone.py"
    tests.write_text("""from pathlib import Path
def test_owner_tone():
    s=Path('src/agent.py').read_text()
    assert 'Ordinary swear words' in s
    assert 'Talk like a butler' not in s
    assert 'no mandatory fixed catchphrases' in s
    assert 'these style choices do not alter model-provider restrictions'.lower() in s.lower()
""",encoding="utf-8")
