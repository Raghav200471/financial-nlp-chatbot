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

        # Step 2.5: Entity-Based Intent Correction
        # If BERT misclassified "AAPL price" as get_exchange_rate, but we extracted a TICKER
        if intent_result["intent"] == "get_exchange_rate" and "TICKER" in extracted_labels:
            intent_result["intent"] = "get_stock_price"
        elif intent_result["intent"] == "get_stock_price" and "TICKER" not in extracted_labels and ("CURRENCY" in extracted_labels or "CURRENCY_TO" in extracted_labels):
            intent_result["intent"] = "get_exchange_rate"

        # Step 3: Conversation manager (handles multi-turn slot filling)
        turn_result = conversation_manager.process_turn(
            session_id=session_id,
            user_message=user_message,
            intent=intent_result,
            entities=entities_list,
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
