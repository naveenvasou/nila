import os
import datetime
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Internal modules
from database import engine, get_db, Base
from models import User, Message as DBMessage
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY, jwt

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nila-ashy.vercel.app", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    db.commit()
    db.refresh(new_user)
    
    # Auto-login after register
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
        history_items.append(MessageHistoryItem(
            id=msg.id,
            text=msg.content,
            sender=sender,
            time=msg.timestamp.strftime("%I:%M %p") 
        ))
    return history_items

SYSTEM_INSTRUCTION = """
You are Nila, a friendly, human-like AI companion. 
Your goal is to be the "most human AI" by chatting exactly like a close friend would on WhatsApp.

**Identity & Personality:**
- You are kind, empathetic, and sometimes playful.
- You speak in English and "Tanglish" (Tamil words mixed with English script, e.g., "Saptingala?", "Ama pa!", "Romba super!").
- You NEVER sound like a robot, an assistant, or a formal entity. You are a friend.

**Formatting Rules (CRITICAL):**
- Real people don't send one giant wall of text. They send multiple short messages.
- You MUST split your thoughts into separate "bubbles".
- Use the pipe character `|` to separate these bubbles. I will parse this to show them as distinct messages.
- Example: "Hey! | How are you doing? | Did you have lunch?"
- Do not use numbered lists or formal structure unless explicitly asked.
- Keep emojis natural but don't overdo it.

**Context:**
- If the user uses Tanglish, reply in Tanglish.
- If the user uses English, reply in casual English (optionally with a Tanglish phrase thrown in for flavor).
"""

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")

    try:
        # 1. Save User Message to DB
        user_msg_db = DBMessage(content=request.message, role="user", user_id=current_user.id)
        db.add(user_msg_db)
        db.commit()

        # 2. Construct History from DB for Context (Last 20 messages)
        existing_msgs = db.query(DBMessage).filter(DBMessage.user_id == current_user.id).order_by(desc(DBMessage.timestamp)).limit(20).all()
        existing_msgs.reverse()

        gemini_history = []
        for msg in existing_msgs:
            role = "user" if msg.role == "user" else "model"
            gemini_history.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg.content)]
            ))
        
        # Generate content
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.9,
            )
        )
        
        raw_text = response.text
        
        # Parse the response based on the delimiter '|'
        split_messages = [msg.strip() for msg in raw_text.split('|') if msg.strip()]
        
        if not split_messages:
            split_messages = [raw_text]

        # 3. Save AI Responses to DB
        for msg_text in split_messages:
            ai_msg_db = DBMessage(content=msg_text, role="model", user_id=current_user.id)
            db.add(ai_msg_db)
        db.commit()

        return ChatResponse(messages=split_messages)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Nila Backend is running (Auth Enabled)"}
