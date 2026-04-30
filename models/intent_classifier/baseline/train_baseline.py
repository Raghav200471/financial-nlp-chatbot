"""
Baseline Intent Classifier — Training Script
=============================================
Trains a TF-IDF + Logistic Regression model on data/intents.json.
Outputs: model.pkl, vectorizer.pkl in models/intent_classifier/baseline/

Usage:
    python models/intent_classifier/baseline/train_baseline.py
"""

import json
import os
import sys
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from nlp.preprocessor import clean_text


def load_intent_data(filepath: str) -> tuple[list[str], list[str]]:
    """Load and flatten the intent dataset into (texts, labels)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    texts = []
    labels = []
    for intent_group in data['intents']:
        intent_name = intent_group['intent']
        for example in intent_group['examples']:
            texts.append(clean_text(example))
            labels.append(intent_name)
    
    return texts, labels


def train_model(texts: list[str], labels: list[str]) -> tuple:
    """Train TF-IDF + Logistic Regression and return model, vectorizer, metrics."""
    
    # TF-IDF Vectorizer with bigrams for better feature capture
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),        # Unigrams + bigrams
        min_df=1,
        max_df=0.95,
        sublinear_tf=True          # Apply log normalization
    )
    
    X = vectorizer.fit_transform(texts)
    y = np.array(labels)
    
    # Logistic Regression with multinomial classification
    model = LogisticRegression(
        max_iter=1000,
        solver='lbfgs',
        C=10.0,                    # Regularization (higher = less regularization)
        class_weight='balanced',   # Handle class imbalance
        random_state=42
    )
    
    # Cross-validation evaluation
    print("=" * 60)
    print("BASELINE INTENT CLASSIFIER -- TRAINING")
    print("=" * 60)
    print(f"\nDataset: {len(texts)} samples, {len(set(labels))} intents")
    print(f"Intents: {sorted(set(labels))}")
    
    # Stratified K-Fold cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
    print(f"\n5-Fold CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    print(f"Per-fold scores: {[f'{s:.4f}' for s in cv_scores]}")
    
    # Train final model on full dataset
    model.fit(X, y)
    
    # Full-dataset evaluation (for reference)
    y_pred = model.predict(X)
    print(f"\nFull-dataset accuracy: {accuracy_score(y, y_pred):.4f}")
    print("\nClassification Report (full dataset):")
    print(classification_report(y, y_pred))
    
    return model, vectorizer


def save_model(model, vectorizer, output_dir: str):
    """Save trained model and vectorizer to disk."""
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, 'model.pkl')
    vectorizer_path = os.path.join(output_dir, 'vectorizer.pkl')
    
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    
    print(f"\n[OK] Model saved to: {model_path}")
    print(f"[OK] Vectorizer saved to: {vectorizer_path}")


def main():
    # Paths
    data_path = os.path.join(PROJECT_ROOT, 'data', 'intents.json')
    output_dir = os.path.join(PROJECT_ROOT, 'models', 'intent_classifier', 'baseline')
    
    # Check data file exists
    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found: {data_path}")
        print("   Please create data/intents.json first (Phase 2).")
        sys.exit(1)
    
    # Load data
    texts, labels = load_intent_data(data_path)
    
    # Train
    model, vectorizer = train_model(texts, labels)
    
    # Save
    save_model(model, vectorizer, output_dir)
    
    # Quick sanity test
    print("\n" + "=" * 60)
    print("SANITY TEST -- Sample Predictions")
    print("=" * 60)
    test_queries = [
        "What is the price of AAPL?",
        "Calculate EMI for 10 lakh at 8% for 20 years",
        "Hello there",
        "What is a savings account?",
        "USD to INR rate",
        "Am I eligible for a home loan?",
        "Explain the impact of RBI policy on housing",
        "Bye, thank you"
    ]
    for query in test_queries:
        cleaned = clean_text(query)
        vec = vectorizer.transform([cleaned])
        proba = model.predict_proba(vec)[0]
        idx = proba.argmax()
        intent = model.classes_[idx]
        confidence = proba[idx]
        print(f"  '{query}' -> {intent} ({confidence:.3f})")
    
    print("\n[OK] Baseline training complete!")


if __name__ == '__main__':
    main()
