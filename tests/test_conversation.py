"""
Conversation Flow Tests
========================
Tests multi-turn dialogues and slot-filling mechanics.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from engine.conversation_manager import ConversationManager, SLOT_PROMPTS


@pytest.fixture
def manager():
    return ConversationManager()


class TestMultiTurnConversation:
    """Test multi-turn slot-filling dialogue flows."""

    def test_emi_full_info_single_turn(self, manager):
        """Test EMI with all info provided in one message."""
        result = manager.process_turn(
            session_id="test_1",
            user_message="Calculate EMI for 10 lakh at 8.5% for 20 years",
            intent={"intent": "calculate_emi", "confidence": 0.95},
            entities=[
                {"entity": "AMOUNT", "value": "10 lakh"},
                {"entity": "RATE", "value": "8.5%"},
                {"entity": "DURATION", "value": "20 years"},
            ]
        )
        assert result["action"] == "execute"
        assert result["intent"] == "calculate_emi"
        assert "AMOUNT" in result["entities"]
        assert "RATE" in result["entities"]
        assert "DURATION" in result["entities"]

    def test_emi_multi_turn_slot_filling(self, manager):
        """Test EMI where info is collected across turns."""
        # Turn 1: User says "Calculate EMI" with no entities
        result1 = manager.process_turn(
            session_id="test_2",
            user_message="Calculate EMI",
            intent={"intent": "calculate_emi", "confidence": 0.92},
            entities=[]
        )
        assert result1["action"] == "ask_slot"
        assert result1["slot"] in ["AMOUNT", "RATE", "DURATION"]

        # Turn 2: User provides amount
        result2 = manager.process_turn(
            session_id="test_2",
            user_message="10 lakh",
            intent={"intent": "calculate_emi", "confidence": 0.50},
            entities=[{"entity": "AMOUNT", "value": "10 lakh"}]
        )
        assert result2["action"] == "ask_slot"

        # Turn 3: User provides rate
        result3 = manager.process_turn(
            session_id="test_2",
            user_message="8.5%",
            intent={"intent": "calculate_emi", "confidence": 0.50},
            entities=[{"entity": "RATE", "value": "8.5%"}]
        )
        assert result3["action"] == "ask_slot"

        # Turn 4: User provides duration — should complete
        result4 = manager.process_turn(
            session_id="test_2",
            user_message="20 years",
            intent={"intent": "calculate_emi", "confidence": 0.50},
            entities=[{"entity": "DURATION", "value": "20 years"}]
        )
        assert result4["action"] == "execute"
        assert result4["intent"] == "calculate_emi"
        assert result4["entities"]["AMOUNT"] == "10 lakh"
        assert result4["entities"]["RATE"] == "8.5%"
        assert result4["entities"]["DURATION"] == "20 years"

    def test_stock_single_turn(self, manager):
        """Test stock query with ticker in first message."""
        result = manager.process_turn(
            session_id="test_3",
            user_message="Price of AAPL",
            intent={"intent": "get_stock_price", "confidence": 0.95},
            entities=[{"entity": "TICKER", "value": "AAPL"}]
        )
        assert result["action"] == "execute"
        assert result["entities"]["TICKER"] == "AAPL"

    def test_stock_multi_turn(self, manager):
        """Test stock query where ticker is provided in second turn."""
        # Turn 1: "Show me stock price"
        result1 = manager.process_turn(
            session_id="test_4",
            user_message="Show me stock price",
            intent={"intent": "get_stock_price", "confidence": 0.90},
            entities=[]
        )
        assert result1["action"] == "ask_slot"
        assert result1["slot"] == "TICKER"

        # Turn 2: "AAPL"
        result2 = manager.process_turn(
            session_id="test_4",
            user_message="AAPL",
            intent={"intent": "get_stock_price", "confidence": 0.50},
            entities=[{"entity": "TICKER", "value": "AAPL"}]
        )
        assert result2["action"] == "execute"
        assert result2["entities"]["TICKER"] == "AAPL"

    def test_greeting_no_slots(self, manager):
        """Test that greetings don't trigger slot filling."""
        result = manager.process_turn(
            session_id="test_5",
            user_message="Hello",
            intent={"intent": "greeting", "confidence": 0.98},
            entities=[]
        )
        assert result["action"] == "respond_direct"
        assert result["intent"] == "greeting"

    def test_session_isolation(self, manager):
        """Test that two sessions don't interfere with each other."""
        # Session A: start EMI flow
        result_a1 = manager.process_turn(
            session_id="session_a",
            user_message="Calculate EMI",
            intent={"intent": "calculate_emi", "confidence": 0.92},
            entities=[]
        )
        assert result_a1["action"] == "ask_slot"

        # Session B: independent greeting
        result_b1 = manager.process_turn(
            session_id="session_b",
            user_message="Hello",
            intent={"intent": "greeting", "confidence": 0.98},
            entities=[]
        )
        assert result_b1["action"] == "respond_direct"

        # Session A: continue EMI (should still be in slot-filling)
        result_a2 = manager.process_turn(
            session_id="session_a",
            user_message="10 lakh",
            intent={"intent": "calculate_emi", "confidence": 0.50},
            entities=[{"entity": "AMOUNT", "value": "10 lakh"}]
        )
        assert result_a2["action"] == "ask_slot"  # Still needs more slots

    def test_raw_text_slot_filling(self, manager):
        """Test that raw text is used as slot value when no entities detected."""
        # Start stock query
        manager.process_turn(
            session_id="test_6",
            user_message="Show me stock price",
            intent={"intent": "get_stock_price", "confidence": 0.90},
            entities=[]
        )

        # User just types the ticker without NER detecting it
        result = manager.process_turn(
            session_id="test_6",
            user_message="TSLA",
            intent={"intent": "get_stock_price", "confidence": 0.50},
            entities=[]  # NER didn't catch it
        )
        assert result["action"] == "execute"
        assert result["entities"]["TICKER"] == "TSLA"

    def test_slot_prompts_exist(self):
        """Test that all expected slot prompts are defined."""
        expected_slots = ["TICKER", "AMOUNT", "DURATION", "RATE", "CURRENCY"]
        for slot in expected_slots:
            assert slot in SLOT_PROMPTS, f"Missing SLOT_PROMPT for {slot}"
            assert len(SLOT_PROMPTS[slot]) > 10, f"SLOT_PROMPT for {slot} too short"

    def test_conversation_history(self, manager):
        """Test that conversation history is recorded."""
        manager.process_turn(
            session_id="test_history",
            user_message="Hello",
            intent={"intent": "greeting", "confidence": 0.98},
            entities=[]
        )
        manager.add_bot_response("test_history", "Hi there!")

        history = manager.get_history("test_history")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
