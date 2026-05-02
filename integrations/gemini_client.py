"""
Gemini API Client (Phase 10 — Optimized)
==========================================
Wrapper for Google Gemini API for complex query handling and data summarization.
Only active when USE_GEMINI=true in .env.

Optimizations to reduce API quota usage:
    1. Singleton client (created once, reused across calls)
    2. In-memory LRU cache for repeated questions (5-min TTL)
    3. Rate limiter (max 5 calls per minute for free tier)
    4. Token-efficient system prompt
    5. maxOutputTokens cap to prevent runaway responses

Usage:
    from integrations.gemini_client import ask_gemini, summarize_financial_data
    response = ask_gemini("Explain the impact of RBI policy on housing loans")
"""

import os
import sys
import time
import hashlib
from collections import OrderedDict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings


# ---- Token-efficient system prompt (shorter = fewer tokens per request) ----
SYSTEM_PROMPT = """You are a concise financial assistant. Topics: banking, loans, investments, tax, markets.
Rules: Be brief (3-5 sentences max). Use bullet points. Use Indian context (₹, lakh, crore) when relevant.
If unsure about specific numbers, say so. Recommend consulting a certified advisor for major decisions."""


# ---- Singleton Gemini Client ----
_gemini_client = None


def _get_client():
    """Return a reusable Gemini client (created once)."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


# ---- Simple LRU Cache with TTL ----
_cache: OrderedDict = OrderedDict()
_CACHE_MAX_SIZE = 50
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(text: str) -> str:
    """Generate a short hash key for a prompt string."""
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    """Get a cached response if it exists and hasn't expired."""
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            _cache.move_to_end(key)  # Keep recently used items fresh
            return value
        else:
            del _cache[key]  # Expired
    return None


def _cache_set(key: str, value: str):
    """Store a response in the cache."""
    _cache[key] = (value, time.time())
    if len(_cache) > _CACHE_MAX_SIZE:
        _cache.popitem(last=False)  # Remove oldest


# ---- Rate Limiter ----
_call_timestamps: list[float] = []
_RATE_LIMIT_MAX_CALLS = 5
_RATE_LIMIT_WINDOW_SECONDS = 60


def _check_rate_limit() -> bool:
    """
    Returns True if we are within the rate limit, False if we've exceeded it.
    Cleans up old timestamps automatically.
    """
    global _call_timestamps
    now = time.time()
    # Remove timestamps older than the window
    _call_timestamps = [t for t in _call_timestamps if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    return len(_call_timestamps) < _RATE_LIMIT_MAX_CALLS


def _record_call():
    """Record a Gemini API call timestamp."""
    _call_timestamps.append(time.time())


# ---- Public API ----

def ask_gemini(user_message: str, context: str = "", use_gemini: bool = True, user_context: dict = None) -> str:
    """
    Send a query to Gemini API with financial system prompt.

    Includes caching, rate limiting, and singleton client for efficiency.

    Args:
        user_message: The user's question
        context: Optional conversation context
        use_gemini: Boolean indicating if client explicitly disabled Gemini
        user_context: Dictionary containing personal finance context (RAG)

    Returns:
        Gemini's response text, or fallback message if unavailable
    """
    if not use_gemini or not settings.USE_GEMINI or not settings.GEMINI_API_KEY:
        return (
            "Gemini integration is disabled. "
            "Please enable it from the sidebar or provide your GEMINI_API_KEY."
        )

    # Check cache first (avoids API call entirely for repeated questions)
    # Include user_context in key so RAG vs non-RAG queries don't collide
    context_str = str(user_context) if user_context else ""
    cache_k = _cache_key(user_message + context + context_str)
    cached = _cache_get(cache_k)
    if cached:
        print(f"[Gemini] Cache HIT for: {user_message[:50]}...")
        return cached

    # Check rate limit
    if not _check_rate_limit():
        return "ERROR_QUOTA_EXCEEDED"

    try:
        client = _get_client()

        prompt = SYSTEM_PROMPT
        if user_context:
            prompt += f"\n\n[USER FINANCIAL PROFILE (Use this context for personalized advice)]:\n"
            for k, v in user_context.items():
                if v:
                    prompt += f"- {k}: {v}\n"

        prompt += "\n\n"
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        prompt += f"User: {user_message}"

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'max_output_tokens': 300,  # Cap output length to save quota
                'temperature': 0.3,        # Lower temp = more focused, fewer tokens
            },
        )

        _record_call()
        result_text = response.text

        # Cache the response
        _cache_set(cache_k, result_text)
        print(f"[Gemini] API call made. Remaining this minute: "
              f"{_RATE_LIMIT_MAX_CALLS - len(_call_timestamps)}")

        return result_text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            return "ERROR_QUOTA_EXCEEDED"

        # Truncate to prevent massive UI spills
        short_err = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
        return (
            f"I encountered an error while processing your request with the AI engine.\n"
            f"Error: {short_err}\n\n"
            f"Please try asking about stock prices, EMI, loans, or currency exchange!"
        )


def summarize_financial_data(data: dict, query: str, use_gemini: bool = True) -> str:
    """
    Use Gemini to summarize a large API payload into natural language.

    Args:
        data: Raw financial data dictionary
        query: The user's original question for context
        use_gemini: Boolean indicating if client explicitly disabled Gemini

    Returns:
        Natural language summary of the data
    """
    if not use_gemini or not settings.USE_GEMINI or not settings.GEMINI_API_KEY:
        return str(data)

    # Check rate limit before summarization too
    if not _check_rate_limit():
        return str(data)

    try:
        client = _get_client()

        prompt = (
            f"Summarize this financial data in 2-3 sentences.\n"
            f"Question: {query}\n"
            f"Data: {data}\n"
            f"Use Indian number formatting (lakh, crore) when appropriate."
        )
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'max_output_tokens': 150,  # Summaries should be short
                'temperature': 0.2,
            },
        )

        _record_call()
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            # Graceful fallback: return raw data on quota limit without error dump
            return str(data)
        return str(data)
