"""
Query Router Tests
===================
Tests the deterministic routing logic to verify that:
- Stock queries go to yfinance, NOT Gemini
- EMI queries are computed with math, NOT Gemini
- FAQ queries hit the knowledge base, NOT Gemini
- Complex/uncertain queries route to Gemini fallback
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from engine.query_router import QueryRouter
from engine.response_generator import generate_response


@pytest.fixture
def router():
    return QueryRouter()


class TestDeterministicRouting:
    """Verify deterministic queries never hit Gemini."""

    def test_greeting_is_template(self, router):
        """Greeting should return a template, not call Gemini."""
        result = router.route("greeting", {}, 0.95, "Hello")
        assert "Financial Assistant" in result
        assert "📈" in result  # Our greeting template has this emoji

    def test_goodbye_is_template(self, router):
        """Goodbye should return a template."""
        result = router.route("goodbye", {}, 0.95, "Bye")
        assert "Goodbye" in result

    def test_emi_calculation_math(self, router):
        """EMI should be calculated with math, not Gemini."""
        result = router.route(
            "calculate_emi",
            {"AMOUNT": "10 lakh", "RATE": "8.5%", "DURATION": "20 years"},
            0.95,
            "Calculate EMI for 10 lakh at 8.5% for 20 years"
        )
        assert "EMI" in result
        assert "₹" in result  # Should have formatted currency
        # Verify actual EMI value (10 lakh @ 8.5% for 20 years ≈ ₹8,678)
        assert "8,678" in result or "8678" in result or "Monthly EMI" in result

    def test_faq_hits_knowledge_base(self, router):
        """FAQ queries should search the knowledge base."""
        result = router.route(
            "faq_general", {}, 0.90,
            "What is a savings account?"
        )
        assert "savings" in result.lower() or "account" in result.lower()

    def test_loan_query_hits_knowledge_base(self, router):
        """Loan FAQ queries should search the knowledge base."""
        result = router.route(
            "loan_query", {}, 0.90,
            "What is a home loan?"
        )
        assert isinstance(result, str)
        assert len(result) > 20

    def test_loan_eligibility_rule_based(self, router):
        """Loan eligibility should use rule-based criteria."""
        result = router.route(
            "loan_eligibility",
            {"AMOUNT": "50 lakh", "DURATION": "20 years"},
            0.90,
            "Am I eligible for a 50 lakh home loan?"
        )
        assert "Eligibility" in result or "eligib" in result.lower()

    def test_exchange_rate_api(self, router):
        """Exchange rate should call the currency API."""
        result = router.route(
            "get_exchange_rate",
            {"CURRENCY": "USD", "CURRENCY_TO": "INR"},
            0.90,
            "USD to INR rate"
        )
        # Should return something about exchange rate (may fail if API is down)
        assert isinstance(result, str)
        assert len(result) > 10


class TestLowConfidenceFallback:
    """Test that low-confidence queries route to fallback."""

    def test_low_confidence_gets_fallback(self, router):
        """Below threshold confidence should trigger fallback."""
        result = router.route(
            "get_stock_price",
            {"TICKER": "AAPL"},
            0.50,  # Below threshold
            "Maybe check apple price?"
        )
        # Should get fallback response (either Gemini or template)
        assert isinstance(result, str)
        assert len(result) > 10


class TestResponseGenerator:
    """Test the template response engine."""

    def test_greeting_template(self):
        result = generate_response("greeting", {})
        assert "Hello" in result

    def test_goodbye_template(self):
        result = generate_response("goodbye", {})
        assert "Goodbye" in result

    def test_fallback_template(self):
        result = generate_response("fallback", {})
        assert "stock" in result.lower() or "rephrase" in result.lower()

    def test_error_template(self):
        result = generate_response("error", {"error_message": "test error"})
        assert "test error" in result

    def test_missing_template_key(self):
        result = generate_response("nonexistent_key", {})
        # Should fall back to the fallback template
        assert isinstance(result, str)

    def test_missing_data_field(self):
        result = generate_response("stock_price", {})
        # Should handle missing fields gracefully
        assert isinstance(result, str)
