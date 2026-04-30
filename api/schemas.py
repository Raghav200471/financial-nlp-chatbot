"""
API Schemas
============
Pydantic models for request/response validation across all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """Request body for the /chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(default="default", description="Session ID for multi-turn")
    use_gemini: bool = Field(default=True, description="Whether Gemini AI fallback is allowed by client")
    use_bert: bool = Field(default=True, description="Whether BERT model is used for intent classification")
    user_context: Optional[dict] = Field(default=None, description="Personal finance RAG context")


class ChatResponse(BaseModel):
    """Response body for the /chat endpoint."""
    response: str = Field(..., description="Bot's response text")
    intent: Optional[str] = Field(None, description="Detected intent")
    confidence: Optional[float] = Field(None, description="Intent confidence score")
    entities: Optional[list] = Field(None, description="Extracted entities")
    session_id: str = Field(..., description="Session ID")
    quota_exceeded: bool = Field(default=False, description="True if Gemini API was skipped or failed due to quota limits")


class IntentRequest(BaseModel):
    """Request body for the /predict-intent debug endpoint."""
    text: str = Field(..., min_length=1, max_length=2000, description="Text to classify")


class IntentResponse(BaseModel):
    """Response body for the /predict-intent debug endpoint."""
    intent: str
    confidence: float
    entities: list
    all_intents: Optional[list] = None


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""
    status: str
    models_loaded: bool
    mode: str
    gemini_enabled: bool
