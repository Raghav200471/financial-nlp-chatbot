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
            return self._handle_faq_or_gemini(user_message, use_gemini, history, user_context)

        # ---- DETERMINISTIC HANDLERS (used for BOTH high and low confidence) ----
        # Try deterministic handler first regardless of confidence.
        # This prevents unnecessary Gemini calls for queries that can be
        # answered without AI.
        # NOTE: When RAG is on, the conversation_manager has already auto-filled
        # missing slots (AMOUNT, CURRENCY) from the user's profile, so these
        # handlers receive complete entity sets.

        if intent == "get_stock_price":
            return self._handle_stock_price(entities)

        elif intent == "calculate_emi":
            return self._handle_emi(entities)

        elif intent == "calculate_interest":
            return self._handle_interest(entities)

        elif intent in ("loan_query", "faq_general"):
            # If user has profile data, try FAQ first then Gemini with context
            if user_context:
                return self._handle_faq_or_gemini(user_message, use_gemini, history, user_context)
            return self._handle_faq(user_message)

        elif intent == "get_exchange_rate":
            return self._handle_exchange_rate(entities)

        elif intent == "loan_eligibility":
            return self._handle_loan_eligibility(entities, user_context)

        elif intent == "greeting":
            return generate_response("greeting", {})

        elif intent == "goodbye":
            return generate_response("goodbye", {})

        # ---- GEMINI / FAQ: complex_query at any confidence ----
        elif intent == "complex_query":
            if user_context:
                print(f"[Router] complex_query + RAG -> Gemini with user profile")
                return self._handle_complex(user_message, use_gemini, user_context, history)
            print(f"[Router] -> FAQ+Gemini (complex_query, confidence={confidence:.4f})")
            return self._handle_faq_or_gemini(user_message, use_gemini, history)

        # ---- FALLBACK: Try FAQ then Gemini for unknown intents ----
        if user_context:
            print(f"[Router] Unknown intent + RAG -> Gemini with user profile")
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
            # Determine currency symbol based on exchange suffix
            upper_ticker = ticker.upper()
            if upper_ticker.endswith(".NS") or upper_ticker.endswith(".BO"):
                data["currency_symbol"] = "₹"
            else:
                data["currency_symbol"] = "$"
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

    def _handle_loan_eligibility(self, entities: dict, user_context: dict = None) -> str:
        """Provide rule-based loan eligibility assessment.
        When user_context (RAG) is available, calculate a personalized assessment
        using income, existing EMIs, and savings."""
        from nlp.preprocessor import normalize_amount

        if user_context:
            income_raw = user_context.get("monthly_income", "").strip()
            emi_raw = user_context.get("existing_emis", "").strip()
            savings_raw = user_context.get("savings", "").strip()

            income = normalize_amount(income_raw) if income_raw else None
            existing_emis = (normalize_amount(emi_raw) or 0) if emi_raw else 0
            savings = (normalize_amount(savings_raw) or 0) if savings_raw else 0

            if income and income > 0:
                # Standard banking rule: max EMI = 50% of (income - existing EMIs)
                disposable = max(0, income - existing_emis)
                
                if disposable == 0:
                    max_emi = 0
                    max_loan = 0
                else:
                    max_emi = disposable * 0.5
                    # Rough max loan estimate: max_emi * 12 * 20 years at ~8.5%
                    # Using simplified formula: max_loan ≈ max_emi * 12 * tenure_factor
                    # For 20yr @ 8.5%: factor ≈ 10.5
                    max_loan = max_emi * 12 * 10.5
                
                currency = "₹"
                lines = [
                    f"**Personalized Loan Eligibility Assessment**",
                    f"",
                    f"Based on your financial profile:",
                    f"- **Monthly Income:** {currency}{income:,.0f}",
                ]
                if existing_emis:
                    lines.append(f"- **Existing EMIs:** {currency}{existing_emis:,.0f}")
                if savings:
                    lines.append(f"- **Savings:** {currency}{savings:,.0f}")
                lines.append(f"- **Disposable Income:** {currency}{disposable:,.0f}")
                lines.append(f"- **Max Affordable EMI (50% rule):** {currency}{max_emi:,.0f}/month")
                lines.append(f"- **Estimated Max Loan (20yr @ ~8.5%):** {currency}{max_loan:,.0f}")
                lines.append(f"")
                
                if disposable == 0:
                    lines.append(f"❌ **Declined:** Your existing EMIs exceed or match your monthly income. You are not eligible for a new loan at this time.")
                elif max_emi > 5000:
                    lines.append(f"✅ You appear to have good loan eligibility.")
                else:
                    lines.append(f"⚠️ Your current disposable income may limit loan options. Consider reducing existing EMIs first.")
                
                lines.append(f"")
                lines.append(f"*Note: Actual eligibility depends on credit score, employment type, and lender policies. Consult a financial advisor.*")
                return "\n".join(lines)

        # Fallback: generic template when no profile data
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

    def _handle_faq_or_gemini(self, user_message: str, use_gemini: bool = True, history: str = "", user_context: dict = None) -> str:
        """
        Handle conceptual/explanatory questions.
        First tries the FAQ knowledge base; if no match, escalates to Gemini.
        When user_context is present, passes it to Gemini for personalized advice.
        """
        from knowledge.faq_lookup import find_best_faq_detailed

        result = find_best_faq_detailed(user_message)
        if result["matched"]:
            return generate_response("faq_answer", {"answer": result["answer"]})

        # Escalate to Gemini for explanatory financial questions
        if use_gemini and settings.USE_GEMINI and settings.GEMINI_API_KEY:
            from integrations.gemini_client import ask_gemini
            return ask_gemini(user_message, context=history, use_gemini=use_gemini, user_context=user_context)

        return generate_response("gemini_unavailable", {})

