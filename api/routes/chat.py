"""
Chat Route
===========
POST /api/chat — Main chat endpoint.
Processes user messages through the full NLP pipeline:
    Input → Preprocess → Intent Detection → Entity Extraction →
    Conversation Manager → Query Router → Response Generation → Output
"""

from fastapi import APIRouter, HTTPException

from api.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message and return the bot's response.
    
    Supports multi-turn conversations via session_id.
    """
    # Import global instances from main module
    from api.main import (
        intent_detector,
        entity_extractor,
        conversation_manager,
        query_router,
    )
    from engine.conversation_manager import SLOT_PROMPTS
    from engine.response_generator import generate_response
    from nlp.preprocessor import clean_text

    if not intent_detector:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    try:
        user_message = request.message.strip()
        session_id = request.session_id or "default"

        # Step 1: Detect intent
        cleaned = clean_text(user_message)
        intent_result = intent_detector.predict(cleaned, use_bert=request.use_bert)
        
        # Step 2: Extract entities (use original text to preserve case for tickers)
        entities_list = entity_extractor.extract(user_message)
        extracted_labels = {e["entity"] for e in entities_list}

        # Step 2.5: Entity-Based Intent Promotion (runs BEFORE threshold!)
        # When entities unambiguously reveal the true intent, trust entities over
        # the classifier — BERT frequently confuses "What is the price of Apple?"
        # as faq_general because of the "What is..." pattern.
        original_intent = intent_result["intent"]
        words = set(cleaned.split())
        stock_keywords = {"stock", "price", "share", "market", "cost", "ticker", "quote", "trade", "value"}
        currency_keywords = {"currency", "exchange", "rate", "convert", "forex"}
        # Common currency codes that the NER may tag as TICKER
        currency_codes = {"usd", "inr", "eur", "gbp", "jpy", "cny", "aud", "cad", "chf", "sgd", "aed", "sar"}

        # CURRENCY entities → exchange rate (check BEFORE ticker to avoid USD→stock)
        if ("CURRENCY" in extracted_labels or "CURRENCY_TO" in extracted_labels):
            if original_intent not in ("get_exchange_rate",):
                print(f"[Intent Fix] {original_intent} → get_exchange_rate (CURRENCY entity found)")
                intent_result["intent"] = "get_exchange_rate"
                intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        # Currency keywords in query → exchange rate
        elif words.intersection(currency_keywords) and words.intersection(currency_codes):
            if original_intent not in ("get_exchange_rate",):
                print(f"[Intent Fix] {original_intent} → get_exchange_rate (currency keywords found)")
                intent_result["intent"] = "get_exchange_rate"
                intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        # TICKER entity found → stock query (but NOT if currency words are present)
        elif "TICKER" in extracted_labels:
            # Guard: if the ticker value itself is a known currency code, skip
            ticker_values = {e["value"].lower() for e in entities_list if e["entity"] == "TICKER"}
            is_currency_ticker = bool(ticker_values.intersection(currency_codes))
            if not is_currency_ticker and original_intent not in ("get_stock_price",):
                print(f"[Intent Fix] {original_intent} → get_stock_price (TICKER entity found)")
                intent_result["intent"] = "get_stock_price"
                intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        # Stock keywords present but no ticker → still likely stock query
        elif words.intersection(stock_keywords) and original_intent in ("faq_general", "unknown", "complex_query"):
            print(f"[Intent Fix] {original_intent} → get_stock_price (stock keywords found)")
            intent_result["intent"] = "get_stock_price"
            intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        # AMOUNT + RATE → likely EMI/interest calculation
        elif "AMOUNT" in extracted_labels and "RATE" in extracted_labels:
            if original_intent in ("faq_general", "unknown", "complex_query"):
                emi_keywords = {"emi", "loan", "interest", "calculate", "monthly"}
                if words.intersection(emi_keywords):
                    print(f"[Intent Fix] {original_intent} → calculate_emi (AMOUNT+RATE+keywords)")
                    intent_result["intent"] = "calculate_emi"
                    intent_result["confidence"] = max(intent_result["confidence"], 0.90)

        # Step 2.6: Confidence boost — when BERT's intent already matches keyword evidence
        # (promotions above only fire when the intent is WRONG; this handles when intent
        # is RIGHT but confidence is borderline, e.g. get_exchange_rate at 0.83)
        if intent_result["intent"] == "get_exchange_rate" and (
            "CURRENCY" in extracted_labels or "CURRENCY_TO" in extracted_labels
            or (words.intersection(currency_keywords) and words.intersection(currency_codes))
        ):
            intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        elif intent_result["intent"] == "get_stock_price" and (
            "TICKER" in extracted_labels or words.intersection(stock_keywords)
        ):
            intent_result["confidence"] = max(intent_result["confidence"], 0.90)
        elif intent_result["intent"] == "loan_eligibility" and any(
            kw in cleaned for kw in ("loan", "eligible", "eligibility", "home loan")
        ):
            intent_result["confidence"] = max(intent_result["confidence"], 0.90)

        # Step 2.7: Confidence threshold — only AFTER all corrections and boosts
        from config import settings
        if intent_result["confidence"] < settings.INTENT_CONFIDENCE_THRESHOLD:
            intent_result["intent"] = "unknown"

        # Step 2.7: OOD (Out-Of-Domain) / Hallucination Rejection
        # Neural networks (BERT) can be overconfident on completely unrelated queries (e.g. "temperature of hyderabad").
        # If the intent is an action, it MUST have either extracted entities OR basic domain keywords.
        if intent_result["intent"] == "get_stock_price":
            if "TICKER" not in extracted_labels and not words.intersection(stock_keywords):
                intent_result["intent"] = "unknown"
                
        elif intent_result["intent"] == "get_exchange_rate":
            if "CURRENCY" not in extracted_labels and "CURRENCY_TO" not in extracted_labels and not words.intersection(currency_keywords):
                intent_result["intent"] = "unknown"
                
        elif intent_result["intent"] in ("calculate_emi", "calculate_interest"):
            loan_keywords = {"loan", "emi", "interest", "rate", "principal", "borrow", "mortgage", "calculate", "math"}
            if not extracted_labels and not words.intersection(loan_keywords):
                intent_result["intent"] = "unknown"


        # Step 3: Conversation manager (handles multi-turn slot filling)
        turn_result = conversation_manager.process_turn(
            session_id=session_id,
            user_message=user_message,
            intent=intent_result,
            entities=entities_list,
            user_context=request.user_context,
        )

        # Step 4: Generate response based on action
        if turn_result["action"] == "ask_slot":
            slot = turn_result["slot"]
            prompt = SLOT_PROMPTS.get(slot, f"Could you provide the {slot}?")
            response_text = generate_response("slot_ask", {"prompt": prompt})

        elif turn_result["action"] in ("execute", "respond_direct"):
            # Use the user_message carried in turn_result if present
            # (set by the conceptual escape hatch in conversation_manager)
            route_message = turn_result.get("user_message", user_message)
            history_list = conversation_manager.get_history(session_id)
            # Format history as a string, excluding the current turn to avoid duplication
            # Limit to last 6 turns (3 interactions) to save context length
            history_str = ""
            if len(history_list) > 1:
                recent_history = history_list[-7:-1]
                history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])
            
            response_text = query_router.route(
                intent=turn_result["intent"],
                entities=turn_result.get("entities", {}),
                confidence=intent_result["confidence"],
                user_message=route_message,
                use_gemini=request.use_gemini,
                user_context=request.user_context,
                history=history_str,
            )

        else:
            response_text = generate_response("fallback", {})

        quota_exceeded = False
        if response_text == "ERROR_QUOTA_EXCEEDED":
            quota_exceeded = True
            response_text = (
                "**Gemini API Quota Exceeded**\n\n"
                "The free-tier limit for the AI model has been reached. "
                "Please toggle off the Gemini Fallback module in the sidebar to switch "
                "offline to the Local Knowledge Base."
            )

        # Record bot response in session history
        conversation_manager.add_bot_response(session_id, response_text)

        return ChatResponse(
            response=response_text,
            intent=intent_result["intent"],
            confidence=round(intent_result["confidence"], 4),
            entities=entities_list,
            session_id=session_id,
            quota_exceeded=quota_exceeded,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
