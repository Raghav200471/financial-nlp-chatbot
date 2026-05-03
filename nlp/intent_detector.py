"""
Intent Detector
===============
Unified interface for intent classification.
Loads either the Scikit-learn baseline or BERT model based on config.USE_BERT flag.

Usage:
    from nlp.intent_detector import IntentDetector
    detector = IntentDetector()
    result = detector.predict("What is the price of AAPL?")
    # → {"intent": "get_stock_price", "confidence": 0.95}
"""

import os
import sys
import joblib

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import settings
from nlp.preprocessor import clean_text


class IntentDetector:
    """
    Detects user intent from text input.
    
    Supports two modes:
        - 'baseline': TF-IDF + Logistic Regression (fast, CPU-friendly)
        - 'bert': Fine-tuned BERT (higher accuracy, needs more resources)
    
    Mode is controlled by the USE_BERT environment variable.
    """

    def __init__(self):
        self.baseline_loaded = False
        self.bert_loaded = False
        self.baseline_model = None
        self.vectorizer = None
        self.bert_classifier = None

    def _load_baseline(self):
        """Load Scikit-learn TF-IDF + LogReg model."""
        if self.baseline_loaded:
            return
            
        model_path = os.path.join(PROJECT_ROOT, settings.INTENT_MODEL_PATH)
        vectorizer_path = os.path.join(PROJECT_ROOT, settings.INTENT_VECTORIZER_PATH)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Baseline model not found at {model_path}. "
                "Run `python models/intent_classifier/baseline/train_baseline.py` first."
            )

        self.baseline_model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)
        self.baseline_loaded = True
        print("[OK] Intent detector loaded: baseline (LogReg)")

    def _load_bert(self):
        """Load fine-tuned BERT model via HuggingFace pipeline."""
        if self.bert_loaded:
            return
        model_path = os.path.join(PROJECT_ROOT, settings.BERT_MODEL_PATH)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"BERT model not found at {model_path}. "
                "Run `python models/intent_classifier/bert/train_bert.py` first."
            )

        from transformers import pipeline
        import transformers
        
        # Disable tqdm progress bars to prevent OSError: [Errno 22] on Windows Streamlit/FastAPI stderr
        transformers.utils.logging.disable_progress_bar()
        
        self.bert_classifier = pipeline(
            "text-classification",
            model=model_path,
            tokenizer=model_path,
            top_k=None  # Return all label scores
        )
        self.bert_loaded = True
        print("[OK] Intent detector loaded: BERT")

    def predict(self, text: str, use_bert: bool = False) -> dict:
        """
        Predict intent from user text.

        Args:
            text: Raw user input string.
            use_bert: Boolean flag to switch between Baseline (TF-IDF) and BERT.

        Returns:
            dict with keys:
                - "intent" (str): Predicted intent label
                - "confidence" (float): Prediction confidence [0, 1]
                - "all_intents" (list): All intents with scores (optional)
        """
        if use_bert:
            self._load_bert()
            return self._predict_bert(text)
        else:
            self._load_baseline()
            return self._predict_baseline(text)

    def _predict_baseline(self, text: str) -> dict:
        """Predict using TF-IDF + Logistic Regression."""
        cleaned = clean_text(text)
        vec = self.vectorizer.transform([cleaned])
        proba = self.baseline_model.predict_proba(vec)[0]
        idx = proba.argmax()

        # Build all-intents list sorted by confidence
        all_intents = [
            {"intent": self.baseline_model.classes_[i], "confidence": float(proba[i])}
            for i in range(len(proba))
        ]
        all_intents.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "intent": self.baseline_model.classes_[idx],
            "confidence": float(proba[idx]),
            "all_intents": all_intents[:5]  # Top 5
        }

    def _predict_bert(self, text: str) -> dict:
        """Predict using fine-tuned BERT."""
        # Truncate text to avoid crashing on long "nonsense" inputs (max 512 tokens)
        results = self.bert_classifier(text, truncation=True, max_length=512)
        
        # HuggingFace pipeline with top_k=None returns list of dicts
        if isinstance(results[0], list):
            results = results[0]
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        top = results[0]

        all_intents = [
            {"intent": r["label"], "confidence": r["score"]}
            for r in results[:5]
        ]

        return {
            "intent": top["label"],
            "confidence": top["score"],
            "all_intents": all_intents
        }
