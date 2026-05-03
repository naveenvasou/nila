import json
import logging
import os
import socket
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


def _load_dotenv_before_config() -> None:
    """`.env` must be loaded before DATABASE_URL is read (import order: database loads before main's load_dotenv)."""
    try:
        from pathlib import Path

        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve().parent
    root = here.parent
    load_dotenv(root / ".env")
    load_dotenv(here / ".env", override=True)


_load_dotenv_before_config()


def _normalize_postgres_url(url: str) -> str:
    """Supabase (and most hosted Postgres) requires TLS; missing sslmode breaks register/chat via psycopg2."""
    u = url.strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    parsed = urlparse(u)
    base_scheme = (parsed.scheme or "").split("+", 1)[0].lower()
    if base_scheme not in ("postgresql", "postgres"):
        return u
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if not any(k.lower() == "sslmode" for k in qs):
        qs["sslmode"] = ["require"]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _ipv4_via_google_public_dns(hostname: str) -> str | None:
    """Fetch A records via Google DNS JSON API when task resolver returns no IPv4.

    Some VPC DNS setups answer only AAAA for hosted Postgres; getaddrinfo(AF_INET) then
    fails and libpq would otherwise connect via IPv6 (broken without IPv6 egress).
    """
    q = urlencode({"name": hostname, "type": "A"})
    url = f"https://dns.google/resolve?{q}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if payload.get("Status") != 0:
        return None
    for item in payload.get("Answer") or []:
        if item.get("type") != 1:
            continue
        data = (item.get("data") or "").strip().split()[0]
        if not data:
            continue
        try:
            socket.inet_aton(data)
            return data
        except OSError:
            continue
    return None


def _postgres_ipv4_hostaddr(hostname: str) -> str | None:
    """Resolve hostname to an IPv4 address for libpq hostaddr.

    Supabase often publishes AAAA records; AWS Fargate/ECS tasks frequently have no IPv6
    egress, which yields psycopg2 'Network is unreachable' while IPv4 works fine.

    Keep the original hostname in the URL host component so TLS verification still matches.
    """
    if not hostname:
        return None
    try:
        socket.inet_aton(hostname)
        return None
    except OSError:
        pass
    flag = os.getenv("DATABASE_PREFER_IPV4", "true").strip().lower()
    if flag not in ("1", "true", "yes"):
        return None

    manual = os.getenv("DATABASE_HOSTADDR", "").strip()
    if manual:
        try:
            socket.inet_aton(manual)
            return manual
        except OSError:
            logger.warning("DATABASE_HOSTADDR is not a valid IPv4 address; ignoring")

    infos = []
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
    except socket.gaierror:
        pass
    if infos:
        return infos[0][4][0]

    fb = os.getenv("DATABASE_IPV4_DNS_FALLBACK", "true").strip().lower()
    if fb not in ("1", "true", "yes"):
        return None
    ip = _ipv4_via_google_public_dns(hostname)
    if ip:
        logger.info("database: IPv4 from public DNS fallback for host=%s", hostname)
    return ip


def _inject_ipv4_hostaddr_into_url(url: str) -> str:
    """Append hostaddr=<IPv4> to the URI query string so libpq connects over IPv4 (not via broken IPv6)."""
    parsed = urlparse(url.strip())
    base_scheme = (parsed.scheme or "").split("+", 1)[0].lower()
    if base_scheme not in ("postgresql", "postgres"):
        return url
    host = parsed.hostname
    if not host:
        return url
    ipv4 = _postgres_ipv4_hostaddr(host)
    if not ipv4:
        return url
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if any(k.lower() == "hostaddr" for k in qs):
        return url
    qs["hostaddr"] = [ipv4]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


_db_url = os.getenv("DATABASE_URL", "").strip()
if _db_url and not _db_url.startswith("sqlite"):
    _db_url = _normalize_postgres_url(_db_url)
    _db_url = _inject_ipv4_hostaddr_into_url(_db_url)

SQLALCHEMY_DATABASE_URL = _db_url if _db_url else "sqlite:///./nila.db"


def _hostaddr_query_value(url: str) -> str | None:
    qs = parse_qs(urlparse(url).query, keep_blank_values=True)
    for key in qs:
        if key.lower() == "hostaddr" and qs[key]:
            return qs[key][0]
    return None


_engine_kwargs: dict = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True
    # SQLAlchemy does not always forward URI query params to psycopg2; pass hostaddr explicitly too.
    _ha = _hostaddr_query_value(SQLALCHEMY_DATABASE_URL)
    if _ha:
        _engine_kwargs["connect_args"] = {"hostaddr": _ha}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)

_parsed_boot = urlparse(SQLALCHEMY_DATABASE_URL)
if _parsed_boot.scheme and _parsed_boot.scheme.split("+", 1)[0].lower() in ("postgresql", "postgres"):
    logger.info(
        "database engine: host=%s hostaddr_set=%s pool_pre_ping=%s",
        _parsed_boot.hostname or "?",
        bool(_engine_kwargs.get("connect_args", {}).get("hostaddr")),
        _engine_kwargs.get("pool_pre_ping", False),
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def _sqlite_column_names(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _sqlite_migrate_legacy_columns(engine) -> None:
    """SQLite: create_all() never ALTERs. Add columns missing from older nila.db files."""
    if "sqlite" not in str(engine.url).lower():
        return
    from sqlalchemy import inspect

    insp = inspect(engine)
    with engine.begin() as conn:
        if insp.has_table("users"):
            cols = _sqlite_column_names(conn, "users")
            alters: list[str] = []
            if "display_name" not in cols:
                alters.append("ALTER TABLE users ADD COLUMN display_name VARCHAR")
            if "age_confirmed" not in cols:
                alters.append(
                    "ALTER TABLE users ADD COLUMN age_confirmed BOOLEAN NOT NULL DEFAULT 0"
                )
            if "vibe" not in cols:
                alters.append("ALTER TABLE users ADD COLUMN vibe VARCHAR")
            if "telegram_id" not in cols:
                alters.append("ALTER TABLE users ADD COLUMN telegram_id INTEGER")
            if "subscription_tier" not in cols:
                alters.append(
                    "ALTER TABLE users ADD COLUMN subscription_tier VARCHAR NOT NULL DEFAULT 'free'"
                )
            for stmt in alters:
                conn.execute(text(stmt))

        if insp.has_table("telegram_sessions"):
            cols = _sqlite_column_names(conn, "telegram_sessions")
            alters = []
            if "pending_age_text" not in cols:
                alters.append(
                    "ALTER TABLE telegram_sessions ADD COLUMN pending_age_text VARCHAR(2000)"
                )
            if "created_at" not in cols:
                alters.append(
                    "ALTER TABLE telegram_sessions ADD COLUMN created_at DATETIME "
                    "DEFAULT CURRENT_TIMESTAMP"
                )
            if "updated_at" not in cols:
                alters.append(
                    "ALTER TABLE telegram_sessions ADD COLUMN updated_at DATETIME "
                    "DEFAULT CURRENT_TIMESTAMP"
                )
            for stmt in alters:
                conn.execute(text(stmt))


_schema_initialized = False


def ensure_schema() -> None:
    """Create tables on first DB use — avoids crashing process import when Postgres is slow/unreachable."""
    global _schema_initialized
    if _schema_initialized:
        return
    Base.metadata.create_all(bind=engine)
    _sqlite_migrate_legacy_columns(engine)
    _schema_initialized = True


def get_db():
    ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
