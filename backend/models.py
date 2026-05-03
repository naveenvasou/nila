from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # Onboarding fields (populated by Telegram /start or web registration).
    display_name = Column(String, nullable=True)
    age_confirmed = Column(Boolean, default=False, nullable=False)
    vibe = Column(String, nullable=True)

    # Telegram linkage (null for web-only users).
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)

    # Subscription tier: "free" | "close" | "closer"
    subscription_tier = Column(String, default="free", nullable=False)

    messages = relationship("Message", back_populates="owner")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    role = Column(String)  # 'user' or 'model'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="messages")


class IncidentLog(Base):
    """Founder-visible errors (Telegram debounce, /chat, etc.) — do not log secrets."""

    __tablename__ = "incident_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    source = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_user_id = Column(Integer, nullable=True)
    telegram_chat_id = Column(Integer, nullable=True)
    error_type = Column(String(128), nullable=False)
    summary = Column(String(2000), nullable=False)
    detail = Column(Text, nullable=True)


class TelegramSession(Base):
    """Tracks onboarding state for Telegram users before their User row is created."""
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    onboarding_step = Column(String, default="none", nullable=False)
    display_name = Column(String, nullable=True)
    age_confirmed = Column(Boolean, default=False, nullable=False)
    vibe = Column(String, nullable=True)
    # First free-text age reply when LLM said UNCLEAR; used with follow-up in await_dob_clarify.
    pending_age_text = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
