"""
FastAPI Application — Main Entry Point
========================================
Initializes the FastAPI app, loads all NLP models at startup,
and registers route modules.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.routes import chat, intent, auth, users
from api.database import connect_db, close_db
from config import settings

# ---- Global instances (populated at startup) ----
intent_detector = None
entity_extractor = None
conversation_manager = None
query_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads all models and initializes components at startup.
    """
    global intent_detector, entity_extractor, conversation_manager, query_router

    print("\n" + "=" * 60)
    print("[START] Financial NLP Chatbot -- Starting Up")
    print("=" * 60)

    # Connect to MongoDB
    await connect_db()

    # Load NLP models
    from nlp.intent_detector import IntentDetector
    from nlp.entity_extractor import EntityExtractor
    from engine.conversation_manager import ConversationManager
    from engine.query_router import QueryRouter

    intent_detector = IntentDetector()
    entity_extractor = EntityExtractor()
    conversation_manager = ConversationManager()
    query_router = QueryRouter()

    print(f"\n[INFO] Configuration:")
    print(f"   Mode: {'BERT' if settings.USE_BERT else 'Baseline (LogReg)'}")
    print(f"   Gemini: {'Enabled' if settings.USE_GEMINI else 'Disabled'}")
    print(f"   Confidence threshold: {settings.INTENT_CONFIDENCE_THRESHOLD}")
    print(f"\n{'=' * 60}")
    print(f"[OK] All systems ready! API running on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"{'=' * 60}\n")

    yield  # App runs here

    # Cleanup
    await close_db()
    print("\n[STOP] Shutting down Financial NLP Chatbot...")


# ---- Create FastAPI app ----
app = FastAPI(
    title="Financial NLP Chatbot API",
    description=(
        "A deterministic-first financial chatbot API with intent detection, "
        "entity extraction, multi-turn conversations, and real-time financial data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---- CORS Middleware ----
_default_origins = "http://localhost:5173,http://localhost:3000,http://localhost:8501"
_cors_origins = os.getenv("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Register Routes ----
app.include_router(chat.router,  prefix="/api", tags=["Chat"])
app.include_router(intent.router, prefix="/api", tags=["Intent"])
app.include_router(auth.router,  tags=["Auth"])
app.include_router(users.router, tags=["Users"])


# ---- Root endpoint ----
@app.get("/")
async def root():
    return {
        "message": "Financial NLP Chatbot API",
        "docs": "/docs",
        "health": "/api/health"
    }
