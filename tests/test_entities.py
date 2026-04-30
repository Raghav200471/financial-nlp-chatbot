"""
Entity Extraction Tests
========================
Tests the entity extractor with various financial queries.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="module")
def entity_extractor():
    """Load the entity extractor once for all tests."""
    from nlp.entity_extractor import EntityExtractor
    return EntityExtractor()


class TestEntityExtraction:
    """Test suite for entity extraction accuracy."""

    def test_ticker_extraction(self, entity_extractor):
        """Test stock ticker extraction."""
        entities = entity_extractor.extract("What is the price of AAPL?")
        labels = [e["entity"] for e in entities]
        values = [e["value"] for e in entities]
        assert "TICKER" in labels, f"Expected TICKER entity, got: {entities}"

    def test_amount_extraction(self, entity_extractor):
        """Test monetary amount extraction."""
        entities = entity_extractor.extract("EMI for 10 lakh at 8% for 20 years")
        labels = [e["entity"] for e in entities]
        assert "AMOUNT" in labels, f"Expected AMOUNT entity, got: {entities}"

    def test_rate_extraction(self, entity_extractor):
        """Test interest rate extraction."""
        entities = entity_extractor.extract("EMI for 10 lakh at 8.5% for 20 years")
        labels = [e["entity"] for e in entities]
        assert "RATE" in labels, f"Expected RATE entity, got: {entities}"

    def test_duration_extraction(self, entity_extractor):
        """Test duration extraction."""
        entities = entity_extractor.extract("Loan for 20 years")
        labels = [e["entity"] for e in entities]
        assert "DURATION" in labels, f"Expected DURATION entity, got: {entities}"

    def test_currency_extraction(self, entity_extractor):
        """Test currency code extraction."""
        entities = entity_extractor.extract("Convert USD to INR")
        labels = [e["entity"] for e in entities]
        assert "CURRENCY" in labels, f"Expected CURRENCY entity, got: {entities}"

    def test_multi_entity_emi(self, entity_extractor):
        """Test multiple entities in EMI query."""
        entities = entity_extractor.extract("Calculate EMI for 50 lakh at 8% for 15 years")
        labels = [e["entity"] for e in entities]
        assert "AMOUNT" in labels, f"Missing AMOUNT in: {entities}"
        assert "RATE" in labels, f"Missing RATE in: {entities}"
        assert "DURATION" in labels, f"Missing DURATION in: {entities}"

    def test_multi_currency(self, entity_extractor):
        """Test extraction of two currency codes."""
        entities = entity_extractor.extract("Convert 100 USD to INR")
        currency_ents = [e for e in entities if e["entity"] == "CURRENCY"]
        assert len(currency_ents) >= 2, f"Expected 2 CURRENCY entities, got: {currency_ents}"

    def test_loan_type_extraction(self, entity_extractor):
        """Test loan type extraction."""
        entities = entity_extractor.extract("I want a home loan of 50 lakh")
        labels = [e["entity"] for e in entities]
        assert "LOAN_TYPE" in labels or "AMOUNT" in labels, (
            f"Expected LOAN_TYPE or AMOUNT, got: {entities}"
        )

    def test_empty_input(self, entity_extractor):
        """Test graceful handling of empty input."""
        entities = entity_extractor.extract("")
        assert isinstance(entities, list)

    def test_no_entities(self, entity_extractor):
        """Test text with no financial entities."""
        entities = entity_extractor.extract("Hello, how are you?")
        # Should not crash; may or may not find entities
        assert isinstance(entities, list)

    def test_extract_as_dict(self, entity_extractor):
        """Test the dict-based entity extraction."""
        result = entity_extractor.extract_as_dict("Convert 100 USD to INR")
        assert isinstance(result, dict)
        assert "CURRENCY" in result


class TestPreprocessor:
    """Test the text preprocessor utilities."""

    def test_clean_text(self):
        from nlp.preprocessor import clean_text
        assert clean_text("  Hello World!  ") == "hello world"
        assert "%" in clean_text("8.5% rate")
        assert "$" in clean_text("$500 price")

    def test_normalize_amount(self):
        from nlp.preprocessor import normalize_amount
        assert normalize_amount("10 lakh") == 1000000.0
        assert normalize_amount("2.5 crore") == 25000000.0
        assert normalize_amount("50000") == 50000.0

    def test_normalize_rate(self):
        from nlp.preprocessor import normalize_rate
        assert normalize_rate("8.5%") == 8.5
        assert normalize_rate("9 percent") == 9.0

    def test_normalize_duration(self):
        from nlp.preprocessor import normalize_duration
        assert normalize_duration("20 years") == 20.0
        assert normalize_duration("60 months") == 5.0
