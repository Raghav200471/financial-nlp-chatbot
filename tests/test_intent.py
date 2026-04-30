"""
Intent Detection Tests
=======================
Tests intent classifier accuracy with unseen examples.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)


# Test data: unseen examples for each intent
INTENT_TEST_CASES = [
    # get_stock_price
    ("What is Apple stock price?", "get_stock_price"),
    ("Show me the price of NIFTY", "get_stock_price"),
    ("How much is Google trading at now?", "get_stock_price"),
    ("Get me the share price of Wipro", "get_stock_price"),
    ("TSLA stock rate", "get_stock_price"),

    # calculate_emi
    ("What is the EMI for a 20 lakh loan at 9% for 15 years?", "calculate_emi"),
    ("Calculate my monthly installment for 40 lakh at 7.5%", "calculate_emi"),
    ("How much EMI will I pay for a 10 lakh loan?", "calculate_emi"),
    ("EMI for 65 lakh at 8.25% for 25 years", "calculate_emi"),

    # loan_query
    ("What is a housing loan?", "loan_query"),
    ("How do personal loans work?", "loan_query"),
    ("Explain the loan process", "loan_query"),
    ("What are the types of loans available?", "loan_query"),

    # loan_eligibility
    ("Can I get a loan with my income?", "loan_eligibility"),
    ("Am I qualified for a 40 lakh loan?", "loan_eligibility"),
    ("What do I need to be eligible for a loan?", "loan_eligibility"),

    # get_exchange_rate
    ("Dollar to rupee exchange rate", "get_exchange_rate"),
    ("Convert euros to dollars", "get_exchange_rate"),
    ("What is the GBP to INR rate?", "get_exchange_rate"),

    # faq_general
    ("What is a mutual fund?", "faq_general"),
    ("Tell me about fixed deposits", "faq_general"),
    ("How does SIP work?", "faq_general"),

    # greeting
    ("Hey", "greeting"),
    ("Good morning!", "greeting"),
    ("Hi there!", "greeting"),

    # goodbye
    ("Thanks, I'm done", "goodbye"),
    ("See you later", "goodbye"),
    ("Goodbye", "goodbye"),

    # complex_query
    ("What factors affect the stock market?", "complex_query"),
    ("How will inflation affect my investments?", "complex_query"),
]


@pytest.fixture(scope="module")
def intent_detector():
    """Load the intent detector once for all tests in this module."""
    from nlp.intent_detector import IntentDetector
    return IntentDetector()


class TestIntentDetection:
    """Test suite for intent classification accuracy."""

    @pytest.mark.parametrize("text,expected_intent", INTENT_TEST_CASES)
    def test_intent_classification(self, intent_detector, text, expected_intent):
        """Test that each example is classified to the correct intent."""
        result = intent_detector.predict(text)
        assert result["intent"] == expected_intent, (
            f"Expected '{expected_intent}' but got '{result['intent']}' "
            f"(confidence: {result['confidence']:.3f}) for: '{text}'"
        )

    @pytest.mark.parametrize("text,expected_intent", INTENT_TEST_CASES)
    def test_minimum_confidence(self, intent_detector, text, expected_intent):
        """Test that correctly classified intents have reasonable confidence."""
        result = intent_detector.predict(text)
        if result["intent"] == expected_intent:
            assert result["confidence"] >= 0.3, (
                f"Confidence too low ({result['confidence']:.3f}) for: '{text}'"
            )

    def test_prediction_returns_required_keys(self, intent_detector):
        """Test that prediction output has all required keys."""
        result = intent_detector.predict("Hello")
        assert "intent" in result
        assert "confidence" in result
        assert isinstance(result["intent"], str)
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_overall_accuracy(self, intent_detector):
        """Test overall accuracy across all test cases (target: >= 75%)."""
        correct = 0
        total = len(INTENT_TEST_CASES)

        for text, expected in INTENT_TEST_CASES:
            result = intent_detector.predict(text)
            if result["intent"] == expected:
                correct += 1

        accuracy = correct / total
        print(f"\nOverall accuracy: {accuracy:.2%} ({correct}/{total})")
        assert accuracy >= 0.75, f"Accuracy {accuracy:.2%} below 75% threshold"
