"""
Central Configuration Module
============================
Loads all settings from .env file using python-dotenv.
All modules import `settings` from this file — never read os.environ directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application-wide configuration loaded from environment variables."""

    # --- API Keys ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")

    # --- Model Paths ---
    INTENT_MODEL_PATH: str = os.getenv(
        "INTENT_MODEL_PATH", "models/intent_classifier/baseline/model.pkl"
    )
    INTENT_VECTORIZER_PATH: str = os.getenv(
        "INTENT_VECTORIZER_PATH", "models/intent_classifier/baseline/vectorizer.pkl"
    )
    BERT_MODEL_PATH: str = os.getenv(
        "BERT_MODEL_PATH", "models/intent_classifier/bert/saved_model"
    )
    NER_MODEL_PATH: str = os.getenv("NER_MODEL_PATH", "models/ner/saved_model")

    # --- Thresholds ---
    INTENT_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.85")
    )

    # --- Feature Flags ---
    USE_BERT: bool = os.getenv("USE_BERT", "false").lower() == "true"
    USE_GEMINI: bool = os.getenv("USE_GEMINI", "false").lower() == "true"
    SAVE_CHAT_HISTORY: bool = os.getenv("SAVE_CHAT_HISTORY", "false").lower() == "true"

    # --- Server ---
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


settings = Settings()
