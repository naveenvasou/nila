"""
Telegram bot — webhook handler wired into the FastAPI app.

Architecture: single-service. The Telegram bot is not a separate process.
FastAPI receives POST /telegram/webhook, this module handles it, calls the
same Gemini brain + safety layer that the web frontend uses.

Onboarding via /start:
    name → free-text age (LLM classifies 18+) → optional one clarify if unclear
    → free-text "what brings you here?" → Gemini opening bubbles.

State is stored in `telegram_sessions` (and `pending_age_text` when clarifying age).

Once onboarding is complete, every message goes through:
    safety.check_message → Gemini (via _generate_nila_reply) → Telegram sendMessage

Daily message / paywall caps are disabled for now (``subscription_tier`` remains on the model for later).

Post-onboarding DM replies are debounced (``TELEGRAM_REPLY_DEBOUNCE_SECONDS``): rapid
user texts merge into one user turn. In-memory only — if you run **multiple ECS
tasks** without shared state, the same user could rarely get split behavior; keep
**min task = 1** for stricter batching, or add a distributed debounce later.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
import random
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models import User, Message as DBMessage, TelegramSession
from prompts import build_system_instruction, ConversationContext
from safety import check_message, SafetyVerdict, reply_for_verdict
from nila_time import format_timestamp_gemini_ist, split_model_bubbles

logger = logging.getLogger(__name__)

# Post-onboarding: batch consecutive user messages into one reply (Telegram typing bursts).
_pending_parts: dict[int, list[str]] = {}
_pending_tasks: dict[int, asyncio.Task] = {}
_chat_locks: dict[int, asyncio.Lock] = {}


def _debounce_seconds() -> float:
    return float(os.getenv("TELEGRAM_REPLY_DEBOUNCE_SECONDS", "2.5"))


def _chat_lock(chat_id: int) -> asyncio.Lock:
    lock = _chat_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[chat_id] = lock
    return lock


async def _enqueue_debounced_reply(chat_id: int, tg_user_id: int, text_fragment: str) -> None:
    """Stack rapid user texts; call Gemini once after a quiet window."""
    lock = _chat_lock(chat_id)
    async with lock:
        _pending_parts.setdefault(chat_id, []).append(text_fragment)
        old = _pending_tasks.pop(chat_id, None)
        if old is not None and not old.done():
            old.cancel()
        _pending_tasks[chat_id] = asyncio.create_task(
            _debounced_reply_after_idle(chat_id, tg_user_id),
            name=f"tg-debounce-{chat_id}",
        )


async def _debounced_reply_after_idle(chat_id: int, tg_user_id: int) -> None:
    try:
        await asyncio.sleep(_debounce_seconds())
    except asyncio.CancelledError:
        return
    lock = _chat_lock(chat_id)
    async with lock:
        parts = _pending_parts.pop(chat_id, [])
        _pending_tasks.pop(chat_id, None)
    combined = "\n".join(p.strip() for p in parts if p.strip())
    if not combined:
        return

    from database import SessionLocal, ensure_schema

    ensure_schema()
    db = SessionLocal()
    user: User | None = None
    try:
        session = (
            db.query(TelegramSession).filter(TelegramSession.telegram_id == tg_user_id).first()
        )
        if session is None or session.onboarding_step != OnboardingStep.DONE:
            return

        user = _get_or_create_user(tg_user_id, session, db)

        verdict = check_message(combined)
        if verdict != SafetyVerdict.ALLOW:
            safe_reply = reply_for_verdict(verdict)
            db.add(DBMessage(content=combined, role="user", user_id=user.id))
            db.add(DBMessage(content=safe_reply, role="model", user_id=user.id))
            db.commit()
            await _tg_send(chat_id, safe_reply)
            return

        bubbles = await _generate_nila_reply(user, combined, db, telegram_style=True)
        await _tg_send_bubbles(chat_id, bubbles)
    except Exception as exc:
        logger.exception("debounced Telegram reply failed: %s", exc)
        try:
            from incident_log import record_incident

            record_incident(
                source="telegram_debounce",
                exc=exc,
                user_id=user.id if user is not None else None,
                telegram_user_id=tg_user_id,
                telegram_chat_id=int(chat_id),
                extra_note=f"User text (truncated):\n{combined[:1500]}",
            )
        except Exception:
            logger.exception("record_incident after telegram debounce failed")
        await _tg_send(chat_id, "ugh something went wrong on my end da 😅 try again in a sec?")
    finally:
        db.close()


def _telegram_api_base() -> str:
    """Read token at call time so ECS env injection is visible (not import-time empty)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return f"https://api.telegram.org/bot{token}"


# ---------------------------------------------------------------------------
# Low-level Telegram API helpers.
# ---------------------------------------------------------------------------

async def _tg_send(chat_id: int | str, text: str, parse_mode: str = "") -> None:
    """Send a message to a Telegram chat. Fire-and-forget errors are logged."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is empty — cannot send Telegram messages")
        return
    base = _telegram_api_base()
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(f"{base}/sendMessage", json=payload)
            if r.status_code >= 400:
                logger.error(
                    "Telegram sendMessage HTTP %s: %s",
                    r.status_code,
                    r.text[:500],
                )
            r.raise_for_status()
        except Exception as exc:
            logger.exception("Telegram sendMessage failed: %s", exc)


async def _tg_send_bubbles(chat_id: int | str, bubbles: list[str]) -> None:
    """Send bubbles as separate Telegram messages with human-ish gaps (not one burst)."""
    clean = [b.strip() for b in bubbles if b and b.strip()]
    if not clean:
        return
    gap_min = float(os.getenv("TELEGRAM_BUBBLE_GAP_MIN", "0.35"))
    gap_max = float(os.getenv("TELEGRAM_BUBBLE_GAP_MAX", "2.0"))
    await asyncio.sleep(random.uniform(0.2, 1.05))
    for i, bubble in enumerate(clean):
        await _tg_send(chat_id, bubble)
        if i < len(clean) - 1:
            await asyncio.sleep(random.uniform(gap_min, gap_max))


async def set_webhook(base_url: str) -> None:
    """Call Telegram to point the webhook at our /telegram/webhook endpoint."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is empty — cannot setWebhook")
        return
    base = _telegram_api_base()
    webhook_url = f"{base_url.rstrip('/')}/telegram/webhook"
    async with httpx.AsyncClient(timeout=15) as client:
        # Keep the in-chat surface human: no visible command menu.
        await client.post(f"{base}/deleteMyCommands", json={})
        r = await client.post(
            f"{base}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message"]},
        )
        data = r.json()
        if data.get("ok"):
            logger.info("Webhook set to %s", webhook_url)
        else:
            logger.error("setWebhook failed: %s", data)


# ---------------------------------------------------------------------------
# Onboarding state machine.
# ---------------------------------------------------------------------------

class OnboardingStep:
    NONE = "none"
    AWAIT_NAME = "await_name"
    AWAIT_DOB = "await_dob"
    AWAIT_DOB_CLARIFY = "await_dob_clarify"
    AWAIT_VIBE = "await_vibe"  # free-text "why here"
    BLOCKED_AGE = "blocked_age"  # could not confirm 18+; only /start resets
    DONE = "done"


# Copy-only; age step is free-text (LLM gate), not date parsing.
TG_ASK_NAME = "hi 👋 i'm Nila — before we get started, what should i call you?"
TG_ASK_DOB_AFTER_NAME = (
    "nice to meet you {name} 😊\n\n"
    "how old are you? say it however is easy — your age, birth year, whatever 🙂\n\n"
    "(need to know you're 18+ — it's required for this app)"
)
TG_ASK_WHY = (
    "okay ✅\n\n"
    "last thing — what are you mostly here for? "
    "doesn't have to be deep; even a short line is fine 🙂"
)
TG_AGE_CLARIFY = (
    "hmm i couldn't tell for sure 😅 can you say your age as a number, "
    "or which year you were born? need to know you're 18+"
)
TG_AGE_TOO_SHORT = "say something quick — even \"i'm 24\" or \"born 2001\" works 🙂"
TG_AGE_BLOCKED = "sorry da, you need to be 18 or older to use this 🙏 it's a requirement we can't get around"
TG_AGE_FAIL_CLOSED = (
    "sorry da, still can't confirm you're 18+ 🙏 send /start if you want to try again from the top"
)
TG_WHY_TOO_SHORT = "even a few words is fine — what's pulling you here? 🙂"
TG_BLOCKED_HINT = "need 18+ confirmation to chat here 🙏 tap /start to try again from the top"


def _normalize_age_verdict(raw: str | None) -> str:
    """Map model output to pass | fail | unclear."""
    if not raw:
        return "unclear"
    first = raw.strip().upper().split()[0] if raw.strip() else ""
    first = first.strip(".,!?")
    if first.startswith("PASS") or first in ("ADULT", "YES", "OK", "OKAY"):
        return "pass"
    if first.startswith("FAIL") or first in ("MINOR", "NO", "UNDER"):
        return "fail"
    return "unclear"


async def _llm_classify_age_gate(user_text: str) -> str:
    """
    Classify free-text age reply. Returns pass | fail | unclear.
    On API/model errors, returns unclear (caller may clarify or fail closed).
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "unclear"
    year = datetime.date.today().year
    from google import genai
    from google.genai import types

    body = user_text.strip()[:1200]
    system = f"""You are a strict classifier for an 18+ only chat app (current calendar year: {year}).

The user was asked how old they are, in their own words (may be informal, Tanglish, messy, or multiple lines joined with ---).

Decide exactly one:
- PASS — They clearly are 18+ today (explicit age, birth year that implies 18+, unambiguous adult life stage).
- FAIL — They are clearly under 18, OR birth year implies under 18 in {year}, OR school context clearly implies minor.
- UNCLEAR — Genuinely impossible to tell after reading; jokes only; contradictory.

Rules: If likely under 18, FAIL (not UNCLEAR). If clearly 18+, PASS. If hopeless ambiguity, UNCLEAR.

Reply with exactly one word on the first line: PASS, FAIL, or UNCLEAR. Nothing else."""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"User said:\n{body}")],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.1,
            ),
        )
        verdict = _normalize_age_verdict(getattr(response, "text", None) or "")
        if verdict in ("pass", "fail", "unclear"):
            return verdict
    except Exception as exc:
        logger.warning("age gate LLM failed: %s", exc)
    return "unclear"


async def _handle_onboarding(
    tg_user_id: int,
    chat_id: int,
    text: str,
    session: TelegramSession,
    db: Session,
) -> bool:
    """
    Drive the onboarding state machine. Returns True if message was consumed
    by onboarding (caller should not process it further), False otherwise.
    """
    step = session.onboarding_step

    if step == OnboardingStep.AWAIT_NAME:
        name = text.strip()[:50]
        session.display_name = name
        session.onboarding_step = OnboardingStep.AWAIT_DOB
        db.commit()
        await _tg_send(
            chat_id,
            TG_ASK_DOB_AFTER_NAME.format(name=name),
        )
        return True

    if step == OnboardingStep.AWAIT_DOB:
        raw = text.strip()[:800]
        if len(raw) < 2:
            await _tg_send(chat_id, TG_AGE_TOO_SHORT)
            return True
        verdict = await _llm_classify_age_gate(raw)
        if verdict == "fail":
            session.onboarding_step = OnboardingStep.BLOCKED_AGE
            db.commit()
            await _tg_send(chat_id, TG_AGE_BLOCKED)
            return True
        if verdict == "unclear":
            session.pending_age_text = raw[:2000]
            session.onboarding_step = OnboardingStep.AWAIT_DOB_CLARIFY
            db.commit()
            await _tg_send(chat_id, TG_AGE_CLARIFY)
            return True
        session.age_confirmed = True
        session.pending_age_text = None
        session.onboarding_step = OnboardingStep.AWAIT_VIBE
        db.commit()
        await _tg_send(chat_id, TG_ASK_WHY)
        return True

    if step == OnboardingStep.AWAIT_DOB_CLARIFY:
        follow = text.strip()[:800]
        if len(follow) < 2:
            await _tg_send(chat_id, TG_AGE_TOO_SHORT)
            return True
        first = (session.pending_age_text or "").strip()[:1200]
        combined = f"{first}\n---\n{follow}" if first else follow
        verdict = await _llm_classify_age_gate(combined)
        session.pending_age_text = None
        if verdict == "pass":
            session.age_confirmed = True
            session.onboarding_step = OnboardingStep.AWAIT_VIBE
            db.commit()
            await _tg_send(chat_id, TG_ASK_WHY)
            return True
        if verdict == "fail":
            session.onboarding_step = OnboardingStep.BLOCKED_AGE
            db.commit()
            await _tg_send(chat_id, TG_AGE_BLOCKED)
            return True
        session.onboarding_step = OnboardingStep.BLOCKED_AGE
        db.commit()
        await _tg_send(chat_id, TG_AGE_FAIL_CLOSED)
        return True

    if step == OnboardingStep.AWAIT_VIBE:
        why = text.strip()[:500]
        if len(why) < 3:
            await _tg_send(chat_id, TG_WHY_TOO_SHORT)
            return True
        session.vibe = why
        session.onboarding_step = OnboardingStep.DONE
        db.commit()

        user = _get_or_create_user(tg_user_id, session, db)

        name = session.display_name or "you"
        bubbles = await _gemini_telegram_opening(name, why)
        clean = [b.strip() for b in bubbles if b and b.strip()]
        if clean:
            db.add(DBMessage(content=why, role="user", user_id=user.id))
            for b in clean:
                db.add(DBMessage(content=b, role="model", user_id=user.id))
            db.commit()
        await _tg_send_bubbles(chat_id, clean or bubbles)
        return True

    return False


# ---------------------------------------------------------------------------
# User resolution.
# ---------------------------------------------------------------------------

def _get_or_create_user(tg_user_id: int, session: TelegramSession, db: Session) -> User:
    """Get or create a User row linked to this Telegram user id."""
    username = f"tg_{tg_user_id}"
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            hashed_password="!telegram",  # Not used — TG users never hit /token
            display_name=session.display_name,
            age_confirmed=session.age_confirmed or False,
            vibe=session.vibe,
            telegram_id=tg_user_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif session.onboarding_step == OnboardingStep.DONE:
        # Re-/start can refresh session; keep users row aligned with canonical session.
        changed = False
        if user.display_name != session.display_name:
            user.display_name = session.display_name
            changed = True
        if bool(user.age_confirmed) != bool(session.age_confirmed):
            user.age_confirmed = bool(session.age_confirmed or False)
            changed = True
        if user.vibe != session.vibe:
            user.vibe = session.vibe
            changed = True
        if getattr(user, "telegram_id", None) != tg_user_id:
            user.telegram_id = tg_user_id
            changed = True
        if changed:
            db.commit()
    return user


# ---------------------------------------------------------------------------
# First reply after Telegram onboarding (LLM — not a fixed script).
# ---------------------------------------------------------------------------


def _opening_fallback_bubbles(display_name: str) -> list[str]:
    safe = (display_name or "there").strip() or "there"
    return [
        f"hey {safe} 🙂 i'm here",
        "so — what's going on with you today?",
    ]


async def _gemini_telegram_opening(display_name: str, why_here: str) -> list[str]:
    """Warm multi-bubble opener; matches Nila's voice via same model as /chat."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _opening_fallback_bubbles(display_name)
    from google import genai
    from google.genai import types

    safe_name = (display_name or "there").replace('"', "'")[:80]
    safe_why = why_here.replace('"', "'")[:400]
    system = (
        "You are Nila: 22, Chennai, texting casually (Tanglish ok). "
        "The user just finished signup on Telegram.\n"
        f"Their name: {safe_name}.\n"
        f"They said why they're here: \"{safe_why}\".\n"
        "Reply with ONLY 1–3 short chat bubbles, separated by | — "
        "often just ONE bubble is enough. No numbered lists or menus. "
        "Warm, natural; invite them to talk about their day."
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="say hi and draw them into chatting")],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.95,
            ),
        )
        raw = (response.text or "").strip()
        parts = split_model_bubbles(raw)
        if parts:
            return _cap_telegram_bubbles(parts)
    except Exception as exc:
        logger.warning("telegram opening Gemini failed: %s", exc)
    return _opening_fallback_bubbles(display_name)


# ---------------------------------------------------------------------------
# Nila's reply generation — shared core with web frontend.
# ---------------------------------------------------------------------------

def _cap_telegram_bubbles(parts: list[str]) -> list[str]:
    """Hard ceiling so Telegram never fires 5–6 rapid pings."""
    b = [p.strip() for p in parts if p.strip()]
    if len(b) <= 4:
        return b
    return b[:3] + [" ".join(b[3:])]


async def _generate_nila_reply(
    user: User, user_text: str, db: Session, *, telegram_style: bool = False
) -> list[str]:
    """
    Run user_text through safety → Gemini → return list of bubble strings.
    Saves both the user message and Nila's replies to DB.
    """
    from google import genai
    from google.genai import types
    from sqlalchemy import desc

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ["oru second da, konjam issue iruku... try again?"]

    client = genai.Client(api_key=api_key)

    ctx = ConversationContext(
        user_display_name=user.display_name,
        age_confirmed=user.age_confirmed or False,
        vibe=user.vibe,
        telegram_style=telegram_style,
    )
    system_instruction = build_system_instruction(ctx)

    # Persist the user turn BEFORE building Gemini history (matches web /chat in main.py).
    # Otherwise the current message is missing from context and the first-ever reply has empty contents.
    user_msg_db = DBMessage(content=user_text, role="user", user_id=user.id)
    db.add(user_msg_db)
    db.commit()

    history = (
        db.query(DBMessage)
        .filter(DBMessage.user_id == user.id)
        .order_by(desc(DBMessage.timestamp))
        .limit(20)
        .all()
    )
    history.reverse()

    gemini_history = []
    for msg in history:
        role = "user" if msg.role == "user" else "model"
        ts = format_timestamp_gemini_ist(msg.timestamp)
        line = (msg.content or "").replace("\x00", "")
        gemini_history.append(
            types.Content(role=role, parts=[types.Part.from_text(text=f"[{ts}] {line}")])
        )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=gemini_history,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.9,
        ),
    )

    try:
        raw = (response.text or "") if response is not None else ""
    except Exception as ex:
        logger.warning("Reading Gemini response.text failed (user_id=%s): %s", user.id, ex)
        raw = ""
    raw_stripped = raw.strip()
    if not raw_stripped:
        fb = getattr(response, "prompt_feedback", None)
        fr = None
        try:
            cands = getattr(response, "candidates", None) or []
            if cands:
                fr = getattr(cands[0], "finish_reason", None)
        except Exception:
            pass
        logger.warning(
            "Gemini returned no text (user_id=%s) prompt_feedback=%s finish_reason=%s",
            user.id,
            fb,
            fr,
        )
        raw_stripped = "oru sec da my reply got eaten 😅 can you send that again?"

    bubbles = split_model_bubbles(raw_stripped) or [raw_stripped]
    if telegram_style:
        bubbles = _cap_telegram_bubbles(bubbles)

    for bubble in bubbles:
        db.add(DBMessage(content=bubble, role="model", user_id=user.id))
    db.commit()

    return bubbles


# ---------------------------------------------------------------------------
# Main webhook handler — called from main.py.
# ---------------------------------------------------------------------------

async def handle_update(update: dict[str, Any], db: Session) -> None:
    """Process a single Telegram update dict."""
    message = update.get("message")
    if not message:
        return

    chat_id: int = message["chat"]["id"]
    tg_user_id: int = message["from"]["id"]
    text: str = message.get("text", "").strip()

    if not text:
        return

    # Get or create TelegramSession (tracks onboarding state).
    session = db.query(TelegramSession).filter(TelegramSession.telegram_id == tg_user_id).first()
    if not session:
        session = TelegramSession(telegram_id=tg_user_id, onboarding_step=OnboardingStep.NONE)
        db.add(session)
        db.commit()
        db.refresh(session)

    # /start command — reset and begin onboarding.
    if text.startswith("/start"):
        session.onboarding_step = OnboardingStep.AWAIT_NAME
        session.display_name = None
        session.age_confirmed = False
        session.vibe = None
        session.pending_age_text = None
        db.commit()
        await _tg_send(chat_id, TG_ASK_NAME)
        return

    if session.onboarding_step == OnboardingStep.BLOCKED_AGE:
        await _tg_send(chat_id, TG_BLOCKED_HINT)
        return

    # If onboarding isn't done, drive the state machine.
    if session.onboarding_step != OnboardingStep.DONE:
        consumed = await _handle_onboarding(tg_user_id, chat_id, text, session, db)
        if consumed:
            return
        # Fall through if somehow NONE state and not /start — restart onboarding.
        session.onboarding_step = OnboardingStep.AWAIT_NAME
        db.commit()
        await _tg_send(chat_id, TG_ASK_NAME)
        return

    # Onboarding done — resolve user (creates row + keeps profile in sync with session).
    _get_or_create_user(tg_user_id, session, db)

    # Batch consecutive user texts; one Gemini turn after a quiet window.
    await _enqueue_debounced_reply(chat_id, tg_user_id, text)
