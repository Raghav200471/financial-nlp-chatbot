"""
BERT Intent Classifier — Transformers v5.6.2 Compatible
=======================================================
Trains on intents.json and evaluates on test_intents.json

Usage:
    python train_bert.py
"""

import json
import os
import sys
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# ------------------------------------------------
# Paths — computed relative to this script's location
# ------------------------------------------------
# This script lives at: models/intent_classifier/bert/train_bert.py
# PROJECT_ROOT is three levels up: bert/ → intent_classifier/ → models/ → project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

TRAIN_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "intents.json")
TEST_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "test_intents.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "models", "intent_classifier", "bert", "saved_model")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------
# Load dataset
# ------------------------------------------------
def load_training_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = []
    labels = []

    for intent_group in data["intents"]:
        intent = intent_group["intent"]
        for example in intent_group["examples"]:
            texts.append(example)
            labels.append(intent)

    return texts, labels


def load_test_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = []
    labels = []

    for item in data["tests"]:
        texts.append(item["text"])
        labels.append(item["intent"])

    return texts, labels


def create_label_mappings(labels):
    unique = sorted(set(labels))
    label2id = {label: i for i, label in enumerate(unique)}
    id2label = {i: label for label, i in label2id.items()}
    return label2id, id2label


# ------------------------------------------------
# MAIN
# ------------------------------------------------
def main():
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
    )
    from torch.utils.data import Dataset

    class IntentDataset(Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {k: v[idx] for k, v in self.encodings.items()}
            item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
            return item

        def __len__(self):
            return len(self.labels)


    # ------------------------------------------------
    # Load TRAIN data
    # ------------------------------------------------
    if not os.path.exists(TRAIN_DATA_PATH):
        print(f"❌ intents.json not found at {TRAIN_DATA_PATH}")
        sys.exit(1)

    train_texts, train_labels_raw = load_training_data(TRAIN_DATA_PATH)

    # ------------------------------------------------
    # Load TEST data
    # ------------------------------------------------
    if not os.path.exists(TEST_DATA_PATH):
        print(f"❌ test_intents.json not found at {TEST_DATA_PATH}")
        sys.exit(1)

    test_texts, test_labels_raw = load_test_data(TEST_DATA_PATH)

    # ------------------------------------------------
    # Label mappings from TRAINING labels ONLY
    # ------------------------------------------------
    label2id, id2label = create_label_mappings(train_labels_raw)

    y_train = [label2id[l] for l in train_labels_raw]
    y_test = [label2id[l] for l in test_labels_raw]

    print("=" * 60)
    print("BERT INTENT CLASSIFIER (Transformers 5.6.2)")
    print("=" * 60)
    print(f"Training Samples: {len(train_texts)}")
    print(f"Testing Samples:  {len(test_texts)}")
    print(f"Intents: {list(label2id.keys())}")
    print("Device:", "cuda" if torch.cuda.is_available() else "cpu")


    # ------------------------------------------------
    # Split TRAIN into train/val for evaluation
    # ------------------------------------------------
    X_train, X_val, y_train_split, y_val = train_test_split(
        train_texts, y_train, test_size=0.2, random_state=42, stratify=y_train
    )

    model_name = "bert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    train_enc = tokenizer(X_train, truncation=True, padding=True, max_length=64)
    val_enc = tokenizer(X_val, truncation=True, padding=True, max_length=64)
    test_enc = tokenizer(test_texts, truncation=True, padding=True, max_length=64)

    train_ds = IntentDataset(train_enc, y_train_split)
    val_ds = IntentDataset(val_enc, y_val)
    test_ds = IntentDataset(test_enc, y_test)

    # ------------------------------------------------
    # Load BERT model
    # ------------------------------------------------
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(label2id),
        label2id=label2id,
        id2label=id2label
    )

    # ------------------------------------------------
    # TrainingArguments (Transformers 5.x)
    # ------------------------------------------------
    training_args = TrainingArguments(
        output_dir=os.path.join(OUTPUT_DIR, "checkpoints"),
        num_train_epochs=10,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        warmup_steps=50,
        weight_decay=0.01,
        learning_rate=2e-5,

        logging_dir=os.path.join(OUTPUT_DIR, "logs"),
        logging_steps=10,

        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",

        report_to="none",
    )


    # ------------------------------------------------
    # Metrics
    # ------------------------------------------------
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {"accuracy": accuracy_score(labels, preds)}


    # ------------------------------------------------
    # Trainer
    # ------------------------------------------------
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
    )


    # TRAIN
    print("\nTraining started...")
    trainer.train()

    # VALIDATION ACCURACY
    print("\nValidation Accuracy:")
    print(trainer.evaluate())


    # ------------------------------------------------
    # TEST ACCURACY (from test_intents.json)
    # ------------------------------------------------
    print("\nTEST ACCURACY (from test_intents.json):")
    test_logits = trainer.predict(test_ds).predictions
    test_preds = np.argmax(test_logits, axis=-1)

    print(classification_report(test_labels_raw, [id2label[p] for p in test_preds]))
    print("Test Accuracy:", accuracy_score(test_labels_raw, [id2label[p] for p in test_preds]))


    # ------------------------------------------------
    # Save final model
    # ------------------------------------------------
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    with open(os.path.join(OUTPUT_DIR, "label_mappings.json"), "w") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, indent=4)

    print(f"\nModel saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
