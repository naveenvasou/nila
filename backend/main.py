import logging
import os
import datetime
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

# Internal modules
from database import get_db
from models import User, Message as DBMessage
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY, jwt
from prompts import build_system_instruction, ConversationContext
from safety import check_message, SafetyVerdict, reply_for_verdict
from nila_time import format_time_ampm_ist, format_timestamp_gemini_ist, split_model_bubbles

from admin_dashboard import router as admin_router

logger = logging.getLogger(__name__)

app = FastAPI()

# CORS: set CORS_ORIGINS (comma-separated) in production, e.g. "https://app.example.com,http://localhost:5173"
_default_origins = [
    "https://nila-ashy.vercel.app",
    "https://frontend-naveens-projects-31cb48a9.vercel.app",
    "https://frontend-mocha-nu-33.vercel.app",
    "https://naveen.superblue.team",
    "http://localhost:5173",
    "http://localhost:3000",
]
_cors_env = os.getenv("CORS_ORIGINS", "").strip()
allow_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else _default_origins

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_private_no_store_cache_headers(request: Request, call_next):
    """Tell caches (including Vercel external rewrite CDN) not to store authenticated API payloads."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "private, no-store, must-revalidate"
    return response


app.include_router(admin_router)

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # We will just print for now, so app doesn't crash on start if user hasn't set it yet
    print("WARNING: GEMINI_API_KEY not found.")

if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Pydantic Models ---
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageHistoryItem(BaseModel):
    id: int
    text: str
    sender: str
    time: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    messages: List[str]

# --- Auth Helpers ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- Routes ---

@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("register failed (database)")
        raise HTTPException(
            status_code=503,
            detail="Could not reach or write to the database. Check DATABASE_URL (Supabase needs sslmode=require) and table schema.",
        )

    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/history", response_model=List[MessageHistoryItem])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch messages ordered by time
    messages = db.query(DBMessage).filter(DBMessage.user_id == current_user.id).order_by(DBMessage.timestamp).all()
    
    history_items = []
    for msg in messages:
        sender = "nila" if msg.role == "model" else "user"
        time_str = format_time_ampm_ist(msg.timestamp)
        history_items.append(
            MessageHistoryItem(
                id=msg.id,
                text=msg.content if msg.content is not None else "",
                sender=sender,
                time=time_str,
            )
        )
    return history_items


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")

    try:
        # 1. Safety check — runs before the message is saved or sent to Gemini.
        verdict = check_message(request.message)
        if verdict != SafetyVerdict.ALLOW:
            # Return Nila's safety response as a bubble directly — no LLM call.
            safe_reply = reply_for_verdict(verdict)
            user_msg_db = DBMessage(content=request.message, role="user", user_id=current_user.id)
            db.add(user_msg_db)
            ai_msg_db = DBMessage(content=safe_reply, role="model", user_id=current_user.id)
            db.add(ai_msg_db)
            db.commit()
            return ChatResponse(messages=[safe_reply])

        # 2. Save user message.
        user_msg_db = DBMessage(content=request.message, role="user", user_id=current_user.id)
        db.add(user_msg_db)
        db.commit()

        # 3. Build context for this user.
        # age_confirmed defaults False until we build the onboarding flow (week 2).
        ctx = ConversationContext(
            user_display_name=getattr(current_user, "display_name", None),
            age_confirmed=getattr(current_user, "age_confirmed", False),
        )
        system_instruction = build_system_instruction(ctx)

        # 4. Construct history (last 20 messages) for Gemini context.
        existing_msgs = (
            db.query(DBMessage)
            .filter(DBMessage.user_id == current_user.id)
            .order_by(desc(DBMessage.timestamp))
            .limit(20)
            .all()
        )
        existing_msgs.reverse()

        gemini_history = []
        for msg in existing_msgs:
            role = "user" if msg.role == "user" else "model"
            ts = format_timestamp_gemini_ist(msg.timestamp)
            line = (msg.content or "").replace("\x00", "")
            timestamped_text = f"[{ts}] {line}"
            gemini_history.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=timestamped_text)]
            ))

        # 5. Generate.
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.9,
            )
        )

        try:
            raw_text = (response.text or "") if response is not None else ""
        except Exception as ex:
            logger.warning("Reading Gemini response.text failed (user_id=%s): %s", current_user.id, ex)
            raw_text = ""
        raw_text = raw_text.strip()
        if not raw_text:
            logger.warning("Gemini returned no text (user_id=%s)", current_user.id)
            raw_text = "oru sec da something bugged — try again?"
        split_messages = split_model_bubbles(raw_text)
        if not split_messages:
            split_messages = [raw_text]

        # 6. Save AI responses.
        for msg_text in split_messages:
            ai_msg_db = DBMessage(content=msg_text, role="model", user_id=current_user.id)
            db.add(ai_msg_db)
        db.commit()

        return ChatResponse(messages=split_messages)

    except Exception as e:
        logger.exception("chat_endpoint failed user_id=%s", current_user.id)
        try:
            from incident_log import record_incident

            note = f"message (truncated):\n{(request.message or '')[:1200]}"
            record_incident(source="http_chat", exc=e, user_id=current_user.id, extra_note=note)
        except Exception:
            logger.exception("record_incident after http_chat failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"status": "Nila Backend is running (Auth Enabled)"}


# ---------------------------------------------------------------------------
# Telegram webhook
# ---------------------------------------------------------------------------

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive updates from Telegram and route them through the bot handler."""
    from telegram_bot import handle_update
    try:
        update = await request.json()
        await handle_update(update, db)
    except Exception as e:
        # Never return non-200 to Telegram — it retries aggressively.
        logger.exception("Telegram webhook error: %s", e)
        try:
            from incident_log import record_incident

            record_incident(source="telegram_webhook", exc=e)
        except Exception:
            logger.exception("record_incident after telegram_webhook failed")
    return {"ok": True}
