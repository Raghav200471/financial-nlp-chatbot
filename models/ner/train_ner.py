"""
SpaCy Custom NER — Training Script
===================================
Trains a custom SpaCy NER pipeline with financial entity types:
TICKER, AMOUNT, RATE, DURATION, CURRENCY, LOAN_TYPE

Uses data/entities.json as training data.
Outputs: saved_model/ in models/ner/

Usage:
    python models/ner/train_ner.py
"""

import json
import os
import sys
import random
import warnings

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)


def load_training_data(filepath: str) -> list[tuple]:
    """
    Load entity annotations and convert to SpaCy training format.
    
    Returns list of (text, {"entities": [(start, end, label), ...]})
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = []
    for item in data:
        text = item['text']
        entities = [tuple(e) for e in item['entities']]
        training_data.append((text, {"entities": entities}))
    
    return training_data


def train_ner_model(training_data: list[tuple], output_dir: str, n_iter: int = 40):
    """Train a SpaCy NER model with custom financial entities."""
    import spacy
    from spacy.training import Example
    from spacy.util import minibatch, compounding
    
    # Custom entity labels
    ENTITY_LABELS = ["TICKER", "AMOUNT", "RATE", "DURATION", "CURRENCY", "LOAN_TYPE"]
    
    print("=" * 60)
    print("SPACY CUSTOM NER — TRAINING")
    print("=" * 60)
    print(f"Training samples: {len(training_data)}")
    print(f"Entity labels: {ENTITY_LABELS}")
    print(f"Iterations: {n_iter}")
    
    # Filter out samples with no entities for NER training
    ner_data = [d for d in training_data if d[1]["entities"]]
    print(f"Samples with entities: {len(ner_data)}")
    
    # Create blank model or load base model
    try:
        nlp = spacy.load("en_core_web_sm")
        print("Base model: en_core_web_sm")
    except OSError:
        print("en_core_web_sm not found, creating blank model")
        nlp = spacy.blank("en")
    
    # Add NER pipe if not present, or get existing
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")
    
    # Add custom entity labels
    for label in ENTITY_LABELS:
        ner.add_label(label)
    
    # Prepare training examples
    examples = []
    for text, annotations in ner_data:
        try:
            doc = nlp.make_doc(text)
            example = Example.from_dict(doc, annotations)
            examples.append(example)
        except Exception as e:
            print(f"  ⚠ Skipping: '{text[:50]}...' — {e}")
    
    print(f"Valid training examples: {len(examples)}")
    
    # Only train NER pipe (disable others)
    pipe_exceptions = ["ner"]
    unaffected_pipes = [pipe for pipe in nlp.pipe_names if pipe not in pipe_exceptions]
    
    # Training loop
    with nlp.disable_pipes(*unaffected_pipes):
        optimizer = nlp.resume_training()
        
        best_loss = float('inf')
        
        for epoch in range(n_iter):
            random.shuffle(examples)
            losses = {}
            
            # Create minibatches
            batches = minibatch(examples, size=compounding(4.0, 32.0, 1.001))
            
            for batch in batches:
                nlp.update(batch, drop=0.35, sgd=optimizer, losses=losses)
            
            current_loss = losses.get("ner", 0)
            
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"  Epoch {epoch + 1:3d}/{n_iter} — Loss: {current_loss:.4f}")
            
            if current_loss < best_loss:
                best_loss = current_loss
    
    print(f"\nBest loss: {best_loss:.4f}")
    
    # Save model
    os.makedirs(output_dir, exist_ok=True)
    nlp.to_disk(output_dir)
    print(f"\n[OK] NER model saved to: {output_dir}")
    
    return nlp


def evaluate_model(nlp, test_data: list[tuple]):
    """Run quick evaluation on test samples."""
    print("\n" + "=" * 60)
    print("SANITY TEST — Entity Extraction")
    print("=" * 60)
    
    test_sentences = [
        "What is the price of AAPL?",
        "Calculate EMI for 10 lakh at 8.5% for 20 years",
        "Convert 100 USD to INR",
        "Am I eligible for a 50 lakh home loan?",
        "Show me TSLA stock",
        "Car loan of 8 lakh at 10% for 5 years",
        "What is the exchange rate from GBP to INR?",
        "EMI for education loan of 10 lakh at 10% for 5 years",
    ]
    
    for sent in test_sentences:
        doc = nlp(sent)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        if entities:
            ent_str = ", ".join([f"{text}({label})" for text, label in entities])
        else:
            ent_str = "No entities found"
        print(f"  '{sent}'\n    → {ent_str}")
    

def main():
    data_path = os.path.join(PROJECT_ROOT, 'data', 'entities.json')
    output_dir = os.path.join(PROJECT_ROOT, 'models', 'ner', 'saved_model')
    
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        print("   Please create data/entities.json first (Phase 2).")
        sys.exit(1)
    
    # Suppress warnings during training
    warnings.filterwarnings("ignore", category=UserWarning)
    
    # Load data
    training_data = load_training_data(data_path)
    
    # Train
    nlp = train_ner_model(training_data, output_dir, n_iter=40)
    
    # Evaluate
    evaluate_model(nlp, training_data)
    
    print("\n✅ NER training complete!")


if __name__ == '__main__':
    main()
