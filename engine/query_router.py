"""
Query Router
=============
Central routing logic that implements the DETERMINISTIC-FIRST pipeline.

Routing Rules:
    1. High confidence (≥ threshold) + deterministic intent → Direct API/rule handler
    2. High confidence + complex_query intent → Gemini API
    3. Low confidence + known deterministic intent → Still try deterministic handler
    4. Low confidence + unknown intent → Template fallback (Gemini ONLY if explicitly complex)

The router NEVER calls Gemini for simple queries like stock prices or EMI calculations.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
from engine.response_generator import generate_response
from nlp.preprocessor import normalize_amount, normalize_rate, normalize_duration


# Intents that can be handled WITHOUT Gemini (deterministic handlers)
DETERMINISTIC_INTENTS = {
    "get_stock_price", "calculate_emi", "calculate_interest", "loan_query", "faq_general",
    "get_exchange_rate", "loan_eligibility", "greeting", "goodbye",
}


class QueryRouter:
    """
    Routes classified intents to their appropriate handler.
    
    Handler precedence:
        1. Direct API calls (stock_api, currency_api)
        2. Rule-based computation (EMI calculator)
        3. Knowledge base lookup (FAQ)
        4. Template responses (greetings, goodbyes)
        5. Template fallback for unknown intents
        6. Gemini (ONLY for explicit complex_query intent with high confidence)
    """

    # Keywords that indicate a conceptual/explanatory question — even if the
    # classifier mislabels them, they should go to FAQ/Gemini not slot-filling.
    CONCEPTUAL_KEYWORDS = (
        "explain", "what is", "what are", "difference", " vs ", " versus ",
        "compare", "how does", "how do", "tell me about", "definition of",
        "meaning of", "types of", "benefits of", "advantages of",
        "disadvantages of", "which is better", "should i",
    )

    def route(
        self,
        intent: str,
        entities: dict,
        confidence: float,
        user_message: str,
        use_gemini: bool = True,
        user_context: dict = None,
        history: str = ""
    ) -> str:
        """
        Route a classified query to the appropriate handler.

        Args:
            intent: Predicted intent string
            entities: Dict of extracted entities
            confidence: Intent classification confidence [0, 1]
            user_message: Original user message (for fallback/FAQ)

        Returns:
            Formatted response string
        """
        # ---- KEYWORD PRE-CHECK ----
        # If the message is clearly conceptual/explanatory, skip slot-filling
        # handlers and go directly to FAQ lookup or Gemini.
        msg_lower = user_message.lower()
        is_conceptual = any(kw in msg_lower for kw in self.CONCEPTUAL_KEYWORDS)
        
        # Exemption: If it's a calculate_emi intent and ALL required entities are present, it is definitely a math calculation!
        has_all_emi_entities = intent == "calculate_emi" and all(
            k in entities for k in ["AMOUNT", "RATE", "DURATION", "CURRENCY"]
        )
        has_all_interest_entities = intent == "calculate_interest" and all(
            k in entities for k in ["AMOUNT", "RATE", "DURATION"]
        )

        if is_conceptual and intent in ("calculate_emi", "calculate_interest", "loan_query", "loan_eligibility", "faq_general") and not (has_all_emi_entities or has_all_interest_entities):
            print(f"[Router] Conceptual override -> FAQ/Gemini (original intent: {intent})")
            return self._handle_faq_or_gemini(user_message, use_gemini, history)

        # ---- DETERMINISTIC HANDLERS (used for BOTH high and low confidence) ----
        # Try deterministic handler first regardless of confidence.
        # This prevents unnecessary Gemini calls for queries that can be
        # answered without AI.

        if intent == "get_stock_price":
            return self._handle_stock_price(entities)

        elif intent == "calculate_emi":
            return self._handle_emi(entities)

        elif intent == "calculate_interest":
            return self._handle_interest(entities)

        elif intent in ("loan_query", "faq_general"):
            return self._handle_faq(user_message)

        elif intent == "get_exchange_rate":
            return self._handle_exchange_rate(entities)

        elif intent == "loan_eligibility":
            return self._handle_loan_eligibility(entities)

        elif intent == "greeting":
            return generate_response("greeting", {})

        elif intent == "goodbye":
            return generate_response("goodbye", {})

        # ---- GEMINI / FAQ: complex_query at any confidence ----
        elif intent == "complex_query":
            if user_context:
                print(f"[Router] User context provided -> Forcing Gemini (RAG mode)")
                return self._handle_complex(user_message, use_gemini, user_context, history)
            print(f"[Router] -> FAQ+Gemini (complex_query, confidence={confidence:.4f})")
            return self._handle_faq_or_gemini(user_message, use_gemini, history)

        # ---- FALLBACK: Try FAQ then Gemini for unknown intents ----
        if user_context:
            print(f"[Router] User context provided -> Forcing Gemini (RAG mode) for fallback")
            return self._handle_complex(user_message, use_gemini, user_context, history)
            
        print(f"[Router] -> FAQ+Gemini fallback (intent={intent}, confidence={confidence:.4f})")
        return self._handle_faq_or_gemini(user_message, use_gemini, history)


    # ---- Handler Methods ----

    def _handle_stock_price(self, entities: dict) -> str:
        """Fetch stock price via yfinance/Finnhub and format response."""
        from integrations.stock_api import get_stock_price

        ticker = entities.get("TICKER", "").strip().upper()
        if not ticker:
            return "Please provide a stock ticker symbol (e.g., AAPL, TSLA, RELIANCE.NS)."

        data = get_stock_price(ticker)

        if data.get("success"):
            return generate_response("stock_price", data)
        else:
            return generate_response("stock_price_error", {
                "ticker": ticker,
                "error": data.get("error", "Unknown error")
            })

    def _handle_emi(self, entities: dict) -> str:
        """Calculate EMI using the calculator module."""
        from integrations.calculator import calculate_emi

        amount_raw = entities.get("AMOUNT", "")
        rate_raw = entities.get("RATE", "")
        duration_raw = entities.get("DURATION", "")
        currency = entities.get("CURRENCY", "")

        result = calculate_emi(amount_raw, rate_raw, duration_raw, currency)

        if not result.get("success"):
            return result.get("error", "Error calculating EMI.")

        return generate_response("emi_result", result)

    def _handle_interest(self, entities: dict) -> str:
        """Calculate interest using the calculator module."""
        from integrations.calculator import calculate_interest

        amount_raw = entities.get("AMOUNT", "")
        rate_raw = entities.get("RATE", "")
        duration_raw = entities.get("DURATION", "")
        currency = entities.get("CURRENCY", "")

        # Default to compound interest unless user specifically asked for simple
        # In a more advanced version, we'd extract 'INTEREST_TYPE' entity.
        is_compound = True 
        
        result = calculate_interest(amount_raw, rate_raw, duration_raw, currency, is_compound)

        if not result.get("success"):
            return result.get("error", "Error calculating interest.")

        return generate_response("interest_result", result)

    def _handle_faq(self, user_message: str) -> str:
        """Look up the best matching FAQ. Falls back to template, NOT Gemini."""
        from knowledge.faq_lookup import find_best_faq_detailed

        result = find_best_faq_detailed(user_message)

        if result["matched"]:
            return generate_response("faq_answer", {"answer": result["answer"]})
        else:
            # No good FAQ match — return helpful template (NOT Gemini)
            # This prevents accidental Gemini calls for every unmatched FAQ
            return generate_response("gemini_unavailable", {})

    def _handle_exchange_rate(self, entities: dict) -> str:
        """Fetch exchange rate and format response."""
        from integrations.currency_api import get_exchange_rate

        data = get_exchange_rate(entities)

        if data.get("success"):
            return generate_response("exchange_rate", data)
        else:
            return generate_response("exchange_rate_error", {
                "error": data.get("error", "Unknown error")
            })

    def _handle_loan_eligibility(self, entities: dict) -> str:
        """Provide rule-based loan eligibility assessment."""
        amount = entities.get("AMOUNT", "Not specified")
        duration = entities.get("DURATION", "Not specified")

        return generate_response("loan_eligibility", {
            "amount": amount,
            "duration": duration
        })

    def _handle_complex(self, user_message: str, use_gemini: bool = True, user_context: dict = None, history: str = "") -> str:
        """
        Handle complex/uncertain queries or RAG queries.
        Uses Gemini if enabled, otherwise returns a helpful fallback.
        """
        if use_gemini and settings.USE_GEMINI and settings.GEMINI_API_KEY:
            from integrations.gemini_client import ask_gemini
            return ask_gemini(user_message, context=history, use_gemini=use_gemini, user_context=user_context)
        else:
            return generate_response("gemini_unavailable", {})

    def _handle_faq_or_gemini(self, user_message: str, use_gemini: bool = True, history: str = "") -> str:
        """
        Handle conceptual/explanatory questions.
        First tries the FAQ knowledge base; if no match, escalates to Gemini.
        This is used when a conceptual question is misclassified as a
        slot-filling intent (e.g. 'Explain SIP vs lump sum' classified as EMI).
        """
        from knowledge.faq_lookup import find_best_faq_detailed

        result = find_best_faq_detailed(user_message)
        if result["matched"]:
            return generate_response("faq_answer", {"answer": result["answer"]})

        # Escalate to Gemini for explanatory financial questions
        if use_gemini and settings.USE_GEMINI and settings.GEMINI_API_KEY:
            from integrations.gemini_client import ask_gemini
            return ask_gemini(user_message, context=history, use_gemini=use_gemini)

        return generate_response("gemini_unavailable", {})

