import requests
import sys

# Set stdout to handle utf-8 safely
sys.stdout.reconfigure(encoding='utf-8')

API = "http://127.0.0.1:8000/api"

def test_chat(msg, sid="test_edge", use_bert=True, use_gemini=False):
    r = requests.post(f"{API}/chat", json={
        "message": msg,
        "session_id": sid,
        "use_bert": use_bert,
        "use_gemini": use_gemini
    })
    return r.json()

def p(label, res):
    print(f"{label}:")
    if "response" in res:
        print(f"  [{res.get('intent', 'none')}] {res['response'][:100]}")
    else:
        print("  Error:", res)

print("=== Edge Cases: EMI Calculator ===")
# Edge 4: Garbage entities
p("Garbage amounts", test_chat("calculate EMI for xyz lakh at abc% for def years", sid="e4"))

print("\n=== Edge Cases: Local Fallbacks (Gemini OFF) ===")
# Stock
p("Stock (AAPL)", test_chat("What is the price of AAPL?"))
p("Stock (garbage ticker)", test_chat("What is the price of xyzabc?"))
# FX
p("FX (USD to INR)", test_chat("Convert 100 USD to INR"))
p("FX (garbage currencies)", test_chat("Convert XYZ to ABC"))
# Interest
p("Compound Interest", test_chat("Calculate interest on 50000 at 5% for 3 years", sid="e5"))
p("Interest fill curr", test_chat("INR", sid="e5"))
p("0 Interest", test_chat("Calculate interest on 50000 at 0% for 3 years", sid="e7"))
p("0 Interest fill curr", test_chat("INR", sid="e7"))
p("0 Duration Interest", test_chat("Calculate interest on 50000 at 5% for 0 years", sid="e8"))
p("0 Duration Interest fill curr", test_chat("INR", sid="e8"))

# Loan Eligibility
p("Loan eligibility", test_chat("Am I eligible for a loan of 50000 for 5 years?", sid="e6"))
# Greeting
p("Greeting", test_chat("hello"))
# Complex conceptual fallback
p("Conceptual", test_chat("Explain how EMI is calculated", use_gemini=False))
