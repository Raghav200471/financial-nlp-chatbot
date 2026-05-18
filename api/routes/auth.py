"""
Auth Routes
============
POST /auth/register — Create new user account
POST /auth/login    — Login and receive JWT token
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, field_validator
from api.database import get_db
from api.auth import hash_password, verify_password, create_access_token

router = APIRouter()


# ── Request/Response Schemas ─────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ── Routes ───────────────────────────────────────────────────

@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(request: RegisterRequest, db=Depends(get_db)):
    """Create a new user account."""
    # Check if email already registered
    existing = await db.users.find_one({"email": request.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Create user document
    user_doc = {
        "name": request.name,
        "email": request.email,
        "password_hash": hash_password(request.password),
        "rag_profile": {
            "monthly_income": None,
            "existing_emis": None,
            "savings": None,
            "goals": "",
            "risk_tolerance": "moderate",
        },
        "chats": [],
    }
    result = await db.users.insert_one(user_doc)

    token = create_access_token({"sub": request.email})
    return AuthResponse(
        access_token=token,
        user={"id": str(result.inserted_id), "name": request.name, "email": request.email},
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, db=Depends(get_db)):
    """Login with email + password, receive JWT."""
    user = await db.users.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token = create_access_token({"sub": request.email})
    return AuthResponse(
        access_token=token,
        user={"id": str(user["_id"]), "name": user["name"], "email": user["email"]},
    )
