import sys, os
sys.path.insert(0, '.')
from nlp.intent_detector import IntentDetector

d = IntentDetector()

tests = [
    'What is the price of Apple?',
    'AAPL stock price',
    'What is the price of AAPL?',
    'Calculate EMI for 10 lakh at 8.5 percent',
    'USD to INR rate',
    'What is a savings account?',
    'Am I eligible for a home loan?',
    'Explain SIP vs lump sum',
    'Hello',
    'Bye',
]

print('=== BERT MODE ===')
for t in tests:
    r = d.predict(t, use_bert=True)
    conf = r["confidence"]
    intent = r["intent"]
    print(f"  [{conf:.4f}] {intent:25s} | {t}")

print()
print('=== BASELINE MODE ===')
for t in tests:
    r = d.predict(t, use_bert=False)
    conf = r["confidence"]
    intent = r["intent"]
    print(f"  [{conf:.4f}] {intent:25s} | {t}")
