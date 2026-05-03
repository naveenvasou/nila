"""
Founder-only admin UI: users, Telegram sessions, per-user message history.

Auth: HTTP Basic — username `admin`, password from env ``ADMIN_DASHBOARD_KEY``.
If that env var is unset, all routes under ``/admin`` return 404 (dashboard disabled).

Do not expose ``ADMIN_DASHBOARD_KEY`` in client apps or git; set only on the server / .env.
"""

from __future__ import annotations

import html
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database import get_db
from models import User, Message as DBMessage, TelegramSession, IncidentLog
from nila_time import format_time_ampm_ist

router = APIRouter(prefix="/admin", tags=["admin"])
_basic = HTTPBasic(auto_error=False)

_ADMIN_NAV = (
    "<nav>"
    '<a href="/admin">Users</a>'
    '<a href="/admin/telegram">Telegram</a>'
    '<a href="/admin/incidents">Incidents</a>'
    "</nav>"
)


def _admin_secret() -> str | None:
    s = os.getenv("ADMIN_DASHBOARD_KEY", "").strip()
    return s or None


def require_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
) -> None:
    secret = _admin_secret()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Nila Admin"'},
        )
    ok_user = credentials.username == "admin"
    ok_pass = credentials.password == secret
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Nila Admin"'},
        )


def _shell(title: str, inner_html: str, *, extra_styles: str = "") -> str:
    t = html.escape(title)
    es = extra_styles or ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="robots" content="noindex,nofollow"/>
  <title>{t} — Nila Admin</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"/>
    <style>
    .muted {{ color: var(--pico-muted-color, #666); font-size: 0.9rem; }}
    pre.wrap {{ white-space: pre-wrap; word-break: break-word; margin: 0.25rem 0 0 0; }}
    nav a {{ margin-right: 1rem; }}
    {es}
  </style>
</head>
<body>
  <main class="container">
    {_ADMIN_NAV}
    <h1>{t}</h1>
    {inner_html}
  </main>
</body>
</html>"""


CHAT_EXTRA_STYLES = """
    .chat-header { margin-bottom: 0.75rem; }
    .chat-thread {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      padding: 1rem;
      max-height: calc(100vh - 13rem);
      overflow-y: auto;
      border-radius: 12px;
      background: color-mix(in srgb, var(--pico-muted-border-color, #ccc) 35%, var(--pico-background-color, #fff));
      border: 1px solid var(--pico-muted-border-color, #ddd);
    }
    .bubble-row { display: flex; width: 100%; }
    .bubble-row-user { justify-content: flex-end; }
    .bubble-row-model { justify-content: flex-start; }
    .bubble {
      max-width: min(88%, 28rem);
      padding: 0.5rem 0.85rem;
      border-radius: 16px;
      line-height: 1.45;
      box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }
    .bubble-user {
      background: var(--pico-primary, #1095c1);
      color: var(--pico-primary-inverse, #fff);
      border-bottom-right-radius: 5px;
    }
    .bubble-model {
      background: var(--pico-card-background-color, #fff);
      color: var(--pico-color, #1a1a1a);
      border: 1px solid var(--pico-muted-border-color, #e8e8e8);
      border-bottom-left-radius: 5px;
    }
    .bubble-meta { font-size: 0.7rem; opacity: 0.88; margin-bottom: 0.15rem; font-weight: 500; }
    .bubble-text { white-space: pre-wrap; word-break: break-word; font-size: 0.92rem; margin: 0; }
"""


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_home(
    _: Annotated[None, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    counts = dict(
        db.query(DBMessage.user_id, func.count(DBMessage.id))
        .group_by(DBMessage.user_id)
        .all()
    )
    users = db.query(User).order_by(User.id.desc()).limit(500).all()
    rows = []
    for u in users:
        c = counts.get(u.id, 0)
        dn = html.escape(u.display_name or "—")
        un = html.escape(u.username)
        tg = u.telegram_id if u.telegram_id is not None else "—"
        tier = html.escape(u.subscription_tier or "free")
        vibe = html.escape((u.vibe or "")[:80] + ("…" if u.vibe and len(u.vibe) > 80 else ""))
        rows.append(
            f"<tr><td>{u.id}</td><td>{un}</td><td>{dn}</td><td>{tg}</td>"
            f"<td>{tier}</td><td>{'yes' if u.age_confirmed else 'no'}</td>"
            f"<td class=\"muted\">{vibe or '—'}</td><td>{c}</td>"
            f"<td><a href=\"/admin/user/{u.id}\">Chat</a></td></tr>"
        )
    body = (
        "<p class=\"muted\">Basic auth: username <code>admin</code>, password = <code>ADMIN_DASHBOARD_KEY</code> "
        "on the server.</p>"
        "<figure class=\"overflow-auto\"><table><thead><tr>"
        "<th>ID</th><th>Username</th><th>Display name</th><th>Telegram ID</th>"
        "<th>Tier</th><th>18+</th><th>Vibe</th><th>Msgs</th><th></th>"
        "</tr></thead><tbody>"
        + ("".join(rows) if rows else "<tr><td colspan=\"9\">No users yet.</td></tr>")
        + "</tbody></table></figure>"
    )
    return _shell("Users", body)


@router.get("/telegram", response_class=HTMLResponse)
def admin_telegram_sessions(
    _: Annotated[None, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(TelegramSession).order_by(TelegramSession.updated_at.desc()).limit(300).all()
    )
    rows = []
    for s in sessions:
        dn = html.escape(s.display_name or "—")
        step = html.escape(s.onboarding_step or "")
        vibe = html.escape((s.vibe or "")[:60] + ("…" if s.vibe and len(s.vibe) > 60 else ""))
        ua = format_time_ampm_ist(s.updated_at) if s.updated_at else "—"
        rows.append(
            f"<tr><td>{s.id}</td><td>{s.telegram_id}</td><td>{step}</td><td>{dn}</td>"
            f"<td class=\"muted\">{vibe or '—'}</td><td class=\"muted\">{ua}</td></tr>"
        )
    body = (
        "<p class=\"muted\">Onboarding state only; same person also has a <code>users</code> row after signup.</p>"
        "<figure class=\"overflow-auto\"><table><thead><tr>"
        "<th>ID</th><th>Telegram ID</th><th>Step</th><th>Display name</th><th>Vibe</th><th>Updated (IST)</th>"
        "</tr></thead><tbody>"
        + ("".join(rows) if rows else "<tr><td colspan=\"6\">No sessions.</td></tr>")
        + "</tbody></table></figure>"
    )
    return _shell("Telegram sessions", body)


@router.get("/user/{user_id}", response_class=HTMLResponse)
def admin_user_chat(
    user_id: int,
    _: Annotated[None, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    limit = 800
    msgs = (
        db.query(DBMessage)
        .filter(DBMessage.user_id == user_id)
        .order_by(desc(DBMessage.timestamp))
        .limit(limit)
        .all()
    )
    msgs.reverse()
    total = db.query(func.count(DBMessage.id)).filter(DBMessage.user_id == user_id).scalar() or 0
    header = (
        '<div class="chat-header">'
        f'<p style="margin:0 0 0.35rem 0"><a href="/admin">← Users</a></p>'
        f'<p class="muted" style="margin:0">User <strong>{user.id}</strong> — <code>{html.escape(user.username)}</code> — '
        f"{html.escape(user.display_name or '—')} — telegram_id={user.telegram_id or '—'} — "
        f"showing latest <strong>{len(msgs)}</strong> of <strong>{total}</strong> messages (cap {limit}).</p>"
        "</div>"
    )
    bubbles_html: list[str] = []
    for m in msgs:
        role = (m.role or "?").strip().lower()
        ts = format_time_ampm_ist(m.timestamp) if m.timestamp else "—"
        body = html.escape(m.content or "")
        row_cls = "bubble-row-user" if role == "user" else "bubble-row-model"
        bubble_cls = "bubble-user" if role == "user" else "bubble-model"
        label = "User" if role == "user" else "Nila"
        meta = html.escape(f"{label} · {ts} · #{m.id}")
        bubbles_html.append(
            f'<div class="bubble-row {row_cls}">'
            f'<div class="bubble {bubble_cls}">'
            f'<div class="bubble-meta">{meta}</div>'
            f'<div class="bubble-text">{body}</div>'
            f"</div></div>"
        )
    thread = (
        '<div class="chat-thread">'
        + ("".join(bubbles_html) if bubbles_html else '<p class="muted" style="margin:0">No messages.</p>')
        + "</div>"
    )
    inner = header + thread
    return _shell(f"User {user_id} chat", inner, extra_styles=CHAT_EXTRA_STYLES)


@router.get("/incidents", response_class=HTMLResponse)
def admin_incidents(
    _: Annotated[None, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    rows_db = (
        db.query(IncidentLog).order_by(desc(IncidentLog.created_at)).limit(150).all()
    )
    rows = []
    for r in rows_db:
        ts = format_time_ampm_ist(r.created_at) if r.created_at else "—"
        src = html.escape(r.source or "")
        et = html.escape(r.error_type or "")
        sm = html.escape((r.summary or "")[:140] + ("…" if r.summary and len(r.summary) > 140 else ""))
        uid = r.user_id
        ucell = f'<a href="/admin/user/{uid}">{uid}</a>' if uid else "—"
        rows.append(
            f"<tr><td class=\"muted\">{html.escape(ts)}</td><td>{src}</td><td><code>{et}</code></td>"
            f"<td>{sm}</td><td>{ucell}</td><td>{r.telegram_user_id or '—'}</td>"
            f'<td><a href="/admin/incident/{r.id}">Detail</a></td></tr>'
        )
    body = (
        "<p class=\"muted\">Recent server errors (e.g. Gemini quota / rate limits, DB, Telegram). "
        "Open <strong>Detail</strong> for full traceback; Telegram debounce includes truncated user text.</p>"
        "<figure class=\"overflow-auto\"><table><thead><tr>"
        "<th>Time (IST)</th><th>Source</th><th>Error type</th><th>Summary</th>"
        "<th>User</th><th>TG user</th><th></th>"
        "</tr></thead><tbody>"
        + ("".join(rows) if rows else "<tr><td colspan=\"7\">No incidents logged yet.</td></tr>")
        + "</tbody></table></figure>"
    )
    return _shell("Incidents", body)


@router.get("/incident/{incident_id}", response_class=HTMLResponse)
def admin_incident_detail(
    incident_id: int,
    _: Annotated[None, Depends(require_admin)],
    db: Session = Depends(get_db),
):
    r = db.query(IncidentLog).filter(IncidentLog.id == incident_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    ts = format_time_ampm_ist(r.created_at) if r.created_at else "—"
    detail = html.escape(r.detail or "(no traceback)")
    summary = html.escape(r.summary or "")
    src = html.escape(r.source or "")
    et = html.escape(r.error_type or "")
    ulink = (
        f'<a href="/admin/user/{r.user_id}">user #{r.user_id}</a>' if r.user_id else "—"
    )
    inner = (
        '<p><a href="/admin/incidents">← Incidents</a></p>'
        f"<p><strong>{src}</strong> · <code>{et}</code> · {html.escape(ts)} IST<br/>"
        f"user: {ulink} · tg_user={r.telegram_user_id or '—'} · chat={r.telegram_chat_id or '—'}</p>"
        f"<h2>Summary</h2><pre class=\"wrap\">{summary}</pre>"
        f"<h2>Detail / traceback</h2><pre class=\"wrap\">{detail}</pre>"
    )
    return _shell(f"Incident #{incident_id}", inner)
