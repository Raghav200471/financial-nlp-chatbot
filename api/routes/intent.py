"""
Debug Routes
==============
Diagnostic endpoints for testing and monitoring:
    - GET  /api/health         — Health check
    - POST /api/predict-intent — Test intent detection in isolation
"""

from fastapi import APIRouter, HTTPException

from api.schemas import IntentRequest, IntentResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint. Returns model status and configuration."""
    from api.main import intent_detector
    from config import settings

    return HealthResponse(
        status="healthy" if intent_detector else "loading",
        models_loaded=intent_detector is not None,
        mode="bert" if settings.USE_BERT else "baseline",
        gemini_enabled=settings.USE_GEMINI,
    )


@router.post("/predict-intent", response_model=IntentResponse)
async def predict_intent(request: IntentRequest):
    """
    Test intent detection and entity extraction in isolation.
    Useful for debugging and evaluating model performance.
    """
    from api.main import intent_detector, entity_extractor
    from nlp.preprocessor import clean_text

    if not intent_detector:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    try:
        cleaned = clean_text(request.text)
        intent_result = intent_detector.predict(cleaned)
        entities = entity_extractor.extract(request.text)

        return IntentResponse(
            intent=intent_result["intent"],
            confidence=round(intent_result["confidence"], 4),
            entities=entities,
            all_intents=intent_result.get("all_intents"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")
