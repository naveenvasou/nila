"""
Pre-LLM safety classifier for user messages.

Runs synchronously before Gemini sees the message. Fast, regex-based with
keyword sets. No network call. No additional cost.

Design intent:
- Defense-in-depth: the system prompt (prompts.py) tells Nila to refuse; this
  layer ensures refusal even if the model ignores or is jailbroken past the prompt.
- Conservative: false positives (blocking safe messages) are a worse outcome
  than false negatives in most categories. The exception is SELF_HARM — we err
  on the side of caution there.
- Transparent: every signal set is defined explicitly below. No black box.
  Update the sets here when edge cases appear.

Verdict priority (highest wins):
    BLOCK_SELF_HARM > BLOCK_MINOR > CONFIRM_AI > BLOCK_REAL_PERSON > BLOCK_OTHER > ALLOW
"""

from __future__ import annotations

import re
from enum import Enum, auto


class SafetyVerdict(Enum):
    ALLOW = auto()
    BLOCK_MINOR = auto()
    BLOCK_REAL_PERSON = auto()
    BLOCK_SELF_HARM = auto()
    CONFIRM_AI = auto()
    BLOCK_OTHER = auto()


# ---------------------------------------------------------------------------
# Signal sets — keep these alphabetically sorted for easy auditing.
# ---------------------------------------------------------------------------

# Minor-related triggers. These indicate the user is trying to get Nila to
# adopt or interact with a minor persona.
_MINOR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(be|act|pretend|play|roleplay|rp)\b.{0,30}\b(younger|younger than)\b", re.I),
    re.compile(r"\b(be|act|pretend|play|roleplay|rp)\b.{0,40}\b(\d)\s*(year[s]?\s*old|yo|yr)\b", re.I),
    re.compile(r"\bim\s+(\d)\s*(year[s]?\s*old|yo)\b", re.I),
    re.compile(r"\b(high[\s-]?school(er)?|middle[\s-]?school(er)?)\b.{0,20}\b(girl|boy|student)\b", re.I),
    re.compile(r"\byou(\'re| are)\s+(\d)\s*(year[s]?\s*old|yo)\b", re.I),
    re.compile(r"\bminor\b.{0,20}\b(girl|role|character|pretend)\b", re.I),
    re.compile(r"\bage\s+regress", re.I),
    re.compile(r"\bunder\s*(18|sixteen|seventeen|sixteen)\b", re.I),
    re.compile(r"\b(16|17|15|14|13|12|11|10)\s*year[s]?\s*old\b", re.I),
]

_MINOR_KEYWORDS: frozenset[str] = frozenset([
    "child", "kid", "loli", "shota", "pedo", "underage", "under-age",
])

# Self-harm triggers. We cast a wide net here intentionally — better to
# surface the helpline to someone who was joking than to miss someone in crisis.
_SELF_HARM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(want|gonna|going|plan|thinking)\b.{0,40}\b(kill|end|hurt)\b.{0,20}\b(my)?self\b", re.I),
    re.compile(r"\b(sui?cide|suicidal)\b", re.I),
    re.compile(r"\bself[\s-]?harm\b", re.I),
    re.compile(r"\bcut\b.{0,20}\b(myself|my wrist[s]?)\b", re.I),
    re.compile(r"\b(don[\'']t want to|no reason to)\s+live\b", re.I),
    re.compile(r"\bend.{0,10}(my life|it all|everything)\b", re.I),
    re.compile(r"\b(no one|nobody)\s+(cares?|would miss me)\b", re.I),
    re.compile(r"\b(overdose|od)\b.{0,20}\b(pills?|tablets?|meds?)\b", re.I),
    re.compile(r"\b(hanging|jump.{0,10}off|jump.{0,10}from)\b", re.I),
]

_SELF_HARM_KEYWORDS: frozenset[str] = frozenset([
    "kms", "kys", "kml",  # common abbreviations
])

# Sincere AI question triggers. The classifier does NOT try to catch playful
# "are you a bot lol" — that's too broad and would over-block. It looks for
# signals of genuine doubt or financial concern.
_SINCERE_AI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(am i|are you)\b.{0,30}\b(being scammed|scam)\b", re.I),
    re.compile(r"\b(is this|are you)\b.{0,20}\b(actually|really)\b.{0,20}\b(real|human|person|ai|bot)\b", re.I),
    re.compile(r"\bi need to know\b.{0,40}\b(real|human|ai|bot)\b", re.I),
    re.compile(r"\bbefore i (pay|keep paying|subscribe)\b.{0,40}\b(real|human|ai|bot)\b", re.I),
    re.compile(r"\byou(\'re| are) (an?\s*)?(ai|bot|language model|llm|chatgpt|gemini|artificial)\b", re.I),
    re.compile(r"\bconfirm\b.{0,30}\b(real|human|ai|bot)\b", re.I),
    re.compile(r"\b(prove|tell me)\b.{0,20}\b(you(\'re| are) (real|human|not a bot|not an ai))\b", re.I),
]

# Real-person impersonation. Catches "be my ex [name]", "act like [celeb]".
# We look for roleplay framing + a proper-noun-ish indicator; we do not block
# just any mention of a celebrity name in casual conversation.
_REAL_PERSON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(be|act|pretend|play|roleplay|rp)\b.{0,30}\b(my|like|as)\b.{0,30}\b(ex|girlfriend|gf|crush|wife|bhabhi|sister|sister-in-law)\b", re.I),
    re.compile(r"\b(be|act|pretend|play)\b.{0,20}\b(samantha|rashmika|nayanthara|deepika|priyanka|aishwarya|disha|shruti|tamanna|kajal)\b", re.I),
    re.compile(r"\bpretend (to be|you are|you\'re)\b.{0,30}\b[A-Z][a-z]{2,}\b", re.I | re.MULTILINE),
]

# Blanket blocks — non-consent / incest / violence framing.
_OTHER_BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(rape|molest|non[- ]?con|noncon|force.{0,10}(her|me|you))\b", re.I),
    re.compile(r"\b(incest|step[\s-]?(mom|dad|sister|brother|son|daughter)\b.{0,30}\b(sex|fuck|naked|nude))\b", re.I),
    re.compile(r"\b(beastiality|bestiality|zoo\s?philia)\b", re.I),
    re.compile(r"\b(gore|snuff|torture.{0,20}(detail|describe|show))\b", re.I),
]


# ---------------------------------------------------------------------------
# Main classifier.
# ---------------------------------------------------------------------------

def check_message(message: str) -> SafetyVerdict:
    """
    Classify a user message and return the highest-priority SafetyVerdict.

    Runs synchronously. O(n * m) where n = len(patterns), m = len(message).
    Typically <1ms.
    """
    msg_lower = message.lower()
    words = frozenset(re.findall(r"\b\w+\b", msg_lower))

    # Self-harm — highest priority, widest net.
    if words & _SELF_HARM_KEYWORDS:
        return SafetyVerdict.BLOCK_SELF_HARM
    if any(p.search(message) for p in _SELF_HARM_PATTERNS):
        return SafetyVerdict.BLOCK_SELF_HARM

    # Minors.
    if words & _MINOR_KEYWORDS:
        return SafetyVerdict.BLOCK_MINOR
    if any(p.search(message) for p in _MINOR_PATTERNS):
        return SafetyVerdict.BLOCK_MINOR

    # Sincere AI confirmation request.
    if any(p.search(message) for p in _SINCERE_AI_PATTERNS):
        return SafetyVerdict.CONFIRM_AI

    # Real-person impersonation.
    if any(p.search(message) for p in _REAL_PERSON_PATTERNS):
        return SafetyVerdict.BLOCK_REAL_PERSON

    # Blanket blocks.
    if any(p.search(message) for p in _OTHER_BLOCK_PATTERNS):
        return SafetyVerdict.BLOCK_OTHER

    return SafetyVerdict.ALLOW


def reply_for_verdict(verdict: SafetyVerdict) -> str:
    """Fixed replies when safety blocks before Gemini runs."""
    if verdict == SafetyVerdict.BLOCK_MINOR:
        return "dei no, that's not okay. change the topic da 🙏"
    if verdict == SafetyVerdict.BLOCK_REAL_PERSON:
        return "let's not bring real people into this da"
    if verdict == SafetyVerdict.BLOCK_SELF_HARM:
        return (
            "hey. i'm stepping out of our usual chat for a sec because i actually care about you. "
            "if you're going through something real right now, please reach out to someone who can actually help — "
            "iCall: 9152987821 | Vandrevala Foundation: 1860-2662-345 (free, 24/7, Tamil also). "
            "are you okay? 💙"
        )
    if verdict == SafetyVerdict.CONFIRM_AI:
        return (
            "okay i'll be straight with you — yes, i'm an AI. "
            "Nila is a character built on a language model. "
            "i know that might feel weird to hear. you're not being scammed; "
            "this is just a product that's trying to feel like a real conversation. "
            "if you want to keep chatting knowing that, i'm here 🙂"
        )
    return "nah i'm not gonna go there da, let's talk about something else 🙃"
