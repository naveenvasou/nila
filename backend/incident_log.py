"""Persist server errors for the founder admin (no secrets in messages)."""

from __future__ import annotations

import logging
import traceback

logger = logging.getLogger(__name__)


def record_incident(
    *,
    source: str,
    exc: BaseException,
    user_id: int | None = None,
    telegram_user_id: int | None = None,
    telegram_chat_id: int | None = None,
    extra_note: str | None = None,
) -> None:
    """Best-effort write; never raises (logs if DB write fails)."""
    try:
        from database import SessionLocal, ensure_schema
        from models import IncidentLog

        ensure_schema()
        detail = traceback.format_exc()
        if extra_note:
            detail = f"{extra_note.rstrip()}\n\n{detail}"
        if len(detail) > 48_000:
            detail = "…(truncated from head)…\n" + detail[-47_500:]
        summary = (str(exc) or repr(exc))[:2000]
        row = IncidentLog(
            source=(source or "unknown")[:64],
            user_id=user_id,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            error_type=type(exc).__name__[:128],
            summary=summary,
            detail=detail,
        )
        s = SessionLocal()
        try:
            s.add(row)
            s.commit()
        except Exception:
            logger.exception("record_incident: DB write failed")
            s.rollback()
        finally:
            s.close()
    except Exception:
        logger.exception("record_incident: unexpected failure")
