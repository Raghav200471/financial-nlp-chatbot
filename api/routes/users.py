"""
User Routes
============
GET  /users/me              — Get current user info
GET  /users/me/chats        — Load all chat sessions
POST /users/me/chats        — Save / upsert a chat session
DEL  /users/me/chats/{id}  — Delete a chat session
GET  /users/me/profile      — Load RAG profile
PUT  /users/me/profile      — Save RAG profile
"""

import uuid
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import get_current_user
from api.database import get_db

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────

class Message(BaseModel):
    role: str           # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatSession(BaseModel):
    id: str
    title: str
    pinned: bool = False
    messages: List[Message] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class RAGProfile(BaseModel):
    monthly_income: Optional[float] = None
    existing_emis: Optional[float] = None
    savings: Optional[float] = None
    goals: Optional[str] = ""
    risk_tolerance: Optional[str] = "moderate"


# ── Helpers ──────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Routes ───────────────────────────────────────────────────

@router.get("/users/me")
async def get_me(current_email: str = Depends(get_current_user), db=Depends(get_db)):
    """Return basic info for the logged-in user."""
    user = await db.users.find_one({"email": current_email}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"name": user["name"], "email": user["email"]}


@router.get("/users/me/chats")
async def get_chats(current_email: str = Depends(get_current_user), db=Depends(get_db)):
    """Load all chat sessions for the current user."""
    user = await db.users.find_one({"email": current_email}, {"chats": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user.get("chats", [])


@router.post("/users/me/chats", status_code=200)
async def save_chat(
    session: ChatSession,
    current_email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """
    Upsert a chat session.
    - If a chat with this id already exists → replace it.
    - If not → append it.
    """
    session_dict = session.model_dump()
    session_dict["updated_at"] = now_iso()
    if not session_dict.get("created_at"):
        session_dict["created_at"] = now_iso()
    if not session_dict.get("id"):
        session_dict["id"] = str(uuid.uuid4())

    user = await db.users.find_one({"email": current_email}, {"chats": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    chats = user.get("chats", [])
    existing_ids = [c["id"] for c in chats]

    if session_dict["id"] in existing_ids:
        # Replace in place
        await db.users.update_one(
            {"email": current_email, "chats.id": session_dict["id"]},
            {"$set": {"chats.$": session_dict}},
        )
    else:
        # Append new session
        await db.users.update_one(
            {"email": current_email},
            {"$push": {"chats": session_dict}},
        )
    return {"status": "saved", "id": session_dict["id"]}


@router.delete("/users/me/chats/{chat_id}", status_code=200)
async def delete_chat(
    chat_id: str,
    current_email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a specific chat session by ID."""
    result = await db.users.update_one(
        {"email": current_email},
        {"$pull": {"chats": {"id": chat_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"status": "deleted", "id": chat_id}


@router.get("/users/me/profile", response_model=RAGProfile)
async def get_profile(current_email: str = Depends(get_current_user), db=Depends(get_db)):
    """Load the user's RAG financial profile."""
    user = await db.users.find_one({"email": current_email}, {"rag_profile": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user.get("rag_profile", RAGProfile().model_dump())


@router.put("/users/me/profile", response_model=RAGProfile)
async def save_profile(
    profile: RAGProfile,
    current_email: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Save the user's RAG financial profile."""
    await db.users.update_one(
        {"email": current_email},
        {"$set": {"rag_profile": profile.model_dump()}},
    )
    return profile
