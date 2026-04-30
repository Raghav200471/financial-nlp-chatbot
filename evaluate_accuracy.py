"""
Evaluate Model Accuracy
=======================
Use this script to measure the accuracy of your trained models (Intent Classifier and NER) 
so you can populate your Final Report deliverables.

Usage:
    python evaluate_accuracy.py
"""

import json
import os
import sys
from sklearn.metrics import accuracy_score, classification_report

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the actual models used in the active project context!
from nlp.intent_detector import IntentDetector
from nlp.entity_extractor import EntityExtractor


def evaluate_intent_classifier():
    print("\n" + "=" * 60)
    print("1. EVALUATING INTENT CLASSIFIER (VIA PROJECT PIPELINE)")
    print("=" * 60)
    
    data_path = os.path.join(PROJECT_ROOT, 'data', 'test_intents.json')
    if not os.path.exists(data_path):
        print(f"File not found: {data_path}")
        return
        
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Check if --bert flag was passed
    use_bert = "--bert" in sys.argv
    mode_label = "BERT" if use_bert else "Baseline (LogReg)"

    # Instantiate the active project intent detector
    try:
        detector = IntentDetector()
    except Exception as e:
        print(f"Could not load the IntentDetector: {e}")
        return

    labels_true = []
    labels_pred = []
    
    for intent_group in data['intents']:
        expected_intent = intent_group['intent']
        for example in intent_group['examples']:
            labels_true.append(expected_intent)
            
            # Predict using the selected model
            prediction = detector.predict(example, use_bert=use_bert)
            labels_pred.append(prediction['intent'])
            
    print(f"\nEvaluated on Entire Test Dataset: {len(labels_true)} samples")
    print(f"Active Model Mode: {mode_label}")
    print(f"Testing Accuracy: {accuracy_score(labels_true, labels_pred) * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(labels_true, labels_pred, zero_division=0))


def evaluate_ner_model():
    print("\n" + "=" * 60)
    print("2. EVALUATING NER MODEL (SPACY + RULES)")
    print("=" * 60)
    
    # Instantiate the active project entity extractor
    try:
        extractor = EntityExtractor()
    except Exception as e:
        print(f"Could not load the EntityExtractor: {e}")
        return
        
    data_path = os.path.join(PROJECT_ROOT, 'data', 'test_entities.json')
    if not os.path.exists(data_path):
         print(f"File not found: {data_path}")
         return
    
    with open(data_path, 'r', encoding='utf-8') as f:
         examples = json.load(f)
    
    correct_entities = 0
    total_entities = 0
    missed_entities = 0
    false_positives = 0
    
    for item in examples:
        text = item.get("text", "")
        # Get expected generic entity sets (label, value_extracted_from_spans)
        expected_matches = set()
        for start, end, label in item.get("entities", []):
            expected_matches.add((label, text[start:end]))
            
        total_entities += len(expected_matches)
        
        # Predict precisely how the active project extracts (including safety regex Fallbacks)
        predicted_raw = extractor.extract(text)
        predicted_matches = set((ent["entity"], ent["value"]) for ent in predicted_raw)
        
        # Super simple strict evaluation: Value & Label must match
        for exp_ent in expected_matches:
            if exp_ent in predicted_matches:
                correct_entities += 1
            else:
                missed_entities += 1
                
        for pred_ent in predicted_matches:
            if pred_ent not in expected_matches:
                false_positives += 1
                
    if total_entities == 0:
        print("No entities found in test set to evaluate.")
        return
        
    precision = correct_entities / (correct_entities + false_positives) if (correct_entities + false_positives) > 0 else 0
    recall = correct_entities / total_entities
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\nTotal True Entities: {total_entities}")
    print(f"Correctly Predicted: {correct_entities}")
    print(f"Missed: {missed_entities}")
    print(f"False Positives: {false_positives}")
    print("-" * 30)
    print(f"Precision: {precision * 100:.2f}%")
    print(f"Recall:    {recall * 100:.2f}%")
    print(f"F1-Score:  {f1 * 100:.2f}%\n")


if __name__ == "__main__":
    evaluate_intent_classifier()
    evaluate_ner_model()
