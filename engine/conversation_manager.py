"""
Conversation Manager
====================
Stateful session management for multi-turn dialogues.
Handles slot-filling workflows where the bot needs to collect
multiple pieces of information before executing (e.g., EMI calculation
needs AMOUNT, RATE, and DURATION).

Each session is identified by a session_id and tracks:
    - Current intent being processed
    - Collected entities (slots)
    - Missing required slots
    - Conversation history
    - Dialogue state (IDLE → SLOT_FILLING → PROCESSING → RESPONDED)
"""

from dataclasses import dataclass, field
from typing import Optional


# ---- Slot definitions per intent ----
REQUIRED_SLOTS = {
    "calculate_emi": ["AMOUNT", "RATE", "DURATION", "CURRENCY"],
    "calculate_interest": ["AMOUNT", "RATE", "DURATION", "CURRENCY"],
    "get_stock_price": ["TICKER"],
    "get_exchange_rate": ["CURRENCY"],
    "loan_eligibility": ["AMOUNT"],
}

# ---- Optional slots (collected if present, not prompted for) ----
OPTIONAL_SLOTS = {
    "loan_eligibility": ["DURATION", "LOAN_TYPE"],
    "calculate_emi": [],
}

# ---- Human-friendly prompts for each missing slot ----
SLOT_PROMPTS = {
    "TICKER": "Which stock ticker are you interested in? (e.g., AAPL, TSLA, RELIANCE.NS)",
    "AMOUNT": "What is the loan/investment amount? (e.g., 10 lakh, ₹50,000)",
    "DURATION": "What is the duration/tenure? (e.g., 20 years, 60 months)",
    "RATE": "What is the interest rate? (e.g., 8.5%)",
    "CURRENCY": "Which currency is this amount in? (e.g., INR, USD, EUR, GBP)",
    "CURRENCY_TO": "Which currency would you like to convert to? (e.g., INR, USD)",
    "LOAN_TYPE": "What type of loan? (e.g., home loan, personal loan, car loan)",
}


@dataclass
class ConversationState:
    """Represents the state of a single user session."""
    session_id: str
    current_intent: Optional[str] = None
    collected_entities: dict = field(default_factory=dict)
    required_slots: list = field(default_factory=list)
    missing_slots: list = field(default_factory=list)
    turn_count: int = 0
    history: list = field(default_factory=list)
    state: str = "IDLE"  # IDLE | SLOT_FILLING | PROCESSING | RESPONDED


class ConversationManager:
    """
    Manages conversation sessions and multi-turn slot-filling dialogues.
    
    Flow:
        1. User sends message → NLP extracts intent + entities
        2. Manager checks if all required slots are filled
        3. If slots missing → state = SLOT_FILLING, ask for missing slot
        4. User provides missing info → repeat until all slots filled
        5. All slots filled → state = PROCESSING, return execute action
    """

    def __init__(self):
        self.sessions: dict[str, ConversationState] = {}

    def get_or_create_session(self, session_id: str) -> ConversationState:
        """Get existing session or create a new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationState(session_id=session_id)
        return self.sessions[session_id]

    def process_turn(
        self,
        session_id: str,
        user_message: str,
        intent: dict,
        entities: list[dict]
    ) -> dict:
        """
        Process one turn of conversation.

        Args:
            session_id: Unique session identifier
            user_message: Raw user text
            intent: {"intent": str, "confidence": float}
            entities: [{"entity": str, "value": str, ...}]

        Returns:
            Action dict:
                {"action": "ask_slot", "slot": str}
                {"action": "execute", "intent": str, "entities": dict}
                {"action": "respond_direct", "intent": str}
        """
        session = self.get_or_create_session(session_id)
        session.turn_count += 1
        session.history.append({"role": "user", "content": user_message})

        # Convert entity list to dict for easier slot access
        entity_dict = {}
        for ent in entities:
            label = ent["entity"]
            if label not in entity_dict:
                entity_dict[label] = ent["value"]
            elif label + "_TO" not in entity_dict:
                entity_dict[label + "_TO"] = ent["value"]

        # ---- Branch 1: We're in SLOT_FILLING mode (continuing a multi-turn flow) ----
        if session.state == "SLOT_FILLING" and session.current_intent:

            # ---- Greeting/Goodbye escape hatch ----
            # If the user sends a greeting or goodbye while we're slot-filling,
            # they clearly want to change topic, not provide a slot value.
            GREETING_GOODBYE_TRIGGERS = {
                "hi", "hello", "hey", "greetings", "namaste", "hola", "yo",
                "bye", "goodbye", "exit", "quit", "stop", "end", "close",
                "thanks", "thank you", "done", "finished", "ciao",
                "good morning", "good afternoon", "good evening", "good night",
            }
            msg_lower = user_message.lower().strip()
            msg_words = set(msg_lower.split())
            # Check if the entire message is a greeting/goodbye (or very close)
            is_greeting_goodbye = (
                msg_lower in GREETING_GOODBYE_TRIGGERS
                or (len(msg_words) <= 3 and msg_words & GREETING_GOODBYE_TRIGGERS)
            )
            if is_greeting_goodbye:
                # Detect which intent to route to
                goodbye_words = {"bye", "goodbye", "exit", "quit", "stop", "end",
                                 "close", "done", "finished", "ciao", "thanks",
                                 "thank you", "good night"}
                detected_intent = "goodbye" if (msg_words & goodbye_words) else "greeting"
                self._reset_session(session)
                return {
                    "action": "respond_direct",
                    "intent": detected_intent,
                    "entities": {},
                    "user_message": user_message,
                }

            # ---- Conceptual escape hatch ----
            # If the user sends a clearly explanatory/conceptual question while
            # we're waiting for a slot value, break out of slot-filling and
            # route it as a direct respond_direct so the router handles it.
            CONCEPTUAL_TRIGGERS = (
                "explain", "what is", "what are", "difference", " vs ",
                " versus ", "compare", "how does", "how do", "tell me about",
                "definition of", "meaning of", "types of", "benefits of",
                "advantages of", "disadvantages of", "which is better",
                "should i", "why is", "why do",
            )
            is_conceptual = any(kw in msg_lower for kw in CONCEPTUAL_TRIGGERS)
            if is_conceptual:
                # Abandon current slot-filling, handle as a standalone question
                self._reset_session(session)
                return {
                    "action": "respond_direct",
                    "intent": "complex_query",
                    "entities": {},
                    "user_message": user_message,  # carry message for router
                }

            # Merge new entities into collected set, only for PENDING slots.
            # This prevents overwriting already-collected correct values.
            pending = set(session.missing_slots)
            optional = set(OPTIONAL_SLOTS.get(session.current_intent, []))
            all_expected = pending | optional

            for key, value in entity_dict.items():
                # Only accept entity if it matches a slot we still need
                if key in all_expected or key in pending:
                    session.collected_entities[key] = value
                elif key not in session.collected_entities:
                    # Accept unknown extras (e.g., LOAN_TYPE)
                    session.collected_entities[key] = value

            # Raw-message fallback: when exactly one slot is still missing
            # AND that slot was NOT filled by entity extraction
            # AND the message is short (≤ 4 words — likely a simple value)
            slot_still_needed = [
                s for s in session.missing_slots
                if s not in session.collected_entities
            ]
            if (
                len(slot_still_needed) == 1
                and len(user_message.strip().split()) <= 4
            ):
                slot_needed = slot_still_needed[0]
                
                # Special handling for CURRENCY slot: normalize common names/codes
                if slot_needed == "CURRENCY":
                    raw = user_message.strip().lower()
                    CURRENCY_ALIASES = {
                        "inr": "INR", "rupee": "INR", "rupees": "INR", "ruppees": "INR",
                        "ruppee": "INR", "ruppes": "INR", "rupe": "INR", "indian": "INR", "indian rupees": "INR",
                        "usd": "USD", "dollar": "USD", "dollars": "USD", "doller": "USD",
                        "dollers": "USD", "dolar": "USD", "dolars": "USD", "dollrs": "USD", "us dollar": "USD", "us dollars": "USD",
                        "eur": "EUR", "euro": "EUR", "euros": "EUR",
                        "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "british pound": "GBP",
                        "jpy": "JPY", "yen": "JPY",
                        "aed": "AED", "dirham": "AED", "dirhams": "AED",
                        "cad": "CAD", "aud": "AUD", "sgd": "SGD", "chf": "CHF",
                    }
                    resolved = CURRENCY_ALIASES.get(raw)
                    if resolved:
                        session.collected_entities[slot_needed] = resolved
                    else:
                        # Last resort: if it looks like a 3-letter code, use it uppercased
                        if len(raw) == 3 and raw.isalpha():
                            session.collected_entities[slot_needed] = raw.upper()
                        else:
                            # Don't blindly assign garbage — just re-ask
                            pass
                else:
                    session.collected_entities[slot_needed] = user_message.strip()

            # Recalculate missing slots
            session.missing_slots = [
                s for s in session.required_slots
                if s not in session.collected_entities
            ]

            if session.missing_slots:
                # Still need more info
                return {
                    "action": "ask_slot",
                    "slot": session.missing_slots[0],
                    "intent": session.current_intent
                }
            else:
                # All slots filled — execute
                session.state = "PROCESSING"
                result = {
                    "action": "execute",
                    "intent": session.current_intent,
                    "entities": session.collected_entities.copy()
                }
                self._reset_session(session)
                return result


        # ---- Branch 2: New intent processing ----
        session.current_intent = intent["intent"]
        session.collected_entities = entity_dict.copy()

        # ---- Conceptual override for new intents ----
        # If the user is asking a conceptual/explanatory question but it got
        # classified as a slot-filling intent (e.g., "should I choose floating or
        # fixed rate for home loan?" classified as loan_eligibility), bypass
        # slot-filling and route it directly.
        CONCEPTUAL_TRIGGERS = (
            "explain", "what is", "what are", "difference", " vs ",
            " versus ", "compare", "how does", "how do", "tell me about",
            "definition of", "meaning of", "types of", "benefits of",
            "advantages of", "disadvantages of", "which is better",
            "should i", "why is", "why do",
        )
        msg_lower = user_message.lower()
        is_conceptual = any(kw in msg_lower for kw in CONCEPTUAL_TRIGGERS)
        
        # If user explicitly provides mathematical entities, it's a calculation, not conceptual
        has_math_entities = any(
            k in entity_dict for k in ["AMOUNT", "RATE", "DURATION", "TICKER"]
        )
        
        if is_conceptual and not has_math_entities and intent["intent"] in ("loan_eligibility", "loan_query", "calculate_emi", "calculate_interest"):
            self._reset_session(session)
            return {
                "action": "respond_direct",
                "intent": "complex_query",
                "entities": {},
                "user_message": user_message,
            }

        # Check if this intent requires slots
        required = REQUIRED_SLOTS.get(intent["intent"], [])
        session.required_slots = required

        if not required:
            # No slots needed -- respond directly (greetings, FAQs, etc.)
            session.state = "RESPONDED"
            result = {
                "action": "respond_direct",
                "intent": intent["intent"],
                "entities": session.collected_entities.copy()
            }
            self._reset_session(session)
            return result

        # Check for missing slots
        missing = [s for s in required if s not in session.collected_entities]
        session.missing_slots = missing

        if missing:
            session.state = "SLOT_FILLING"
            return {
                "action": "ask_slot",
                "slot": missing[0],
                "intent": intent["intent"]
            }
        else:
            # All slots provided in one message
            session.state = "PROCESSING"
            result = {
                "action": "execute",
                "intent": intent["intent"],
                "entities": session.collected_entities.copy()
            }
            self._reset_session(session)
            return result

    def _reset_session(self, session: ConversationState):
        """Reset session state after completing a turn (keep history)."""
        session.current_intent = None
        session.collected_entities = {}
        session.required_slots = []
        session.missing_slots = []
        session.state = "IDLE"

    def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        session = self.get_or_create_session(session_id)
        return session.history

    def add_bot_response(self, session_id: str, response: str):
        """Record bot response in session history."""
        session = self.get_or_create_session(session_id)
        session.history.append({"role": "assistant", "content": response})
