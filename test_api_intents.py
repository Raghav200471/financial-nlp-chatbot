"""
Test all intents through the live API with both BERT and Baseline modes.
"""
import requests
import json

BASE = "http://127.0.0.1:8000"

# First, login to get a token
login_resp = requests.post(f"{BASE}/auth/login", json={
    "email": "final_verify@test.com",
    "password": "Test@1234"
})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code} {login_resp.text}")
    exit(1)

token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

test_queries = [
    # Stock
    ("What is the price of Apple?",         "get_stock_price"),
    ("AAPL stock price",                    "get_stock_price"),
    ("What is the price of AAPL?",          "get_stock_price"),
    # EMI
    ("Calculate EMI for 10 lakh at 8.5%",   "calculate_emi"),
    ("Monthly EMI for 50 lakh home loan at 9% for 20 years", "calculate_emi"),
    # Interest
    ("Calculate interest on 5 lakh at 7% for 3 years", "calculate_interest"),
    # Exchange
    ("USD to INR rate",                     "get_exchange_rate"),
    ("Convert 100 euros to dollars",        "get_exchange_rate"),
    # FAQ
    ("What is a savings account?",          "faq_general"),
    ("What is mutual fund?",                "faq_general"),
    # Loan eligibility
    ("Am I eligible for a home loan?",      "loan_eligibility"),
    # Loan query
    ("What are the types of home loans?",   "loan_query/faq_general"),
    ("Tell me about personal loan options", "loan_query/faq_general"),
    # Complex queries (should go to Gemini)
    ("Compare HDFC and SBI fixed deposit rates and suggest which is better for a 5 year investment", "complex_query/faq_general/unknown"),
    ("What are the tax implications of selling stocks held for less than a year in India?", "complex_query/faq_general/unknown"),
    ("Should I invest in gold or equity mutual funds given the current market conditions?", "complex_query/faq_general/unknown"),
    ("How does inflation affect my savings and what strategies can I use to beat it?", "complex_query/faq_general/unknown"),
    # General
    ("Explain SIP vs lump sum",             "faq_general/complex_query/unknown"),
    ("Hello",                               "greeting"),
    ("Bye",                                 "goodbye"),
]

for mode_name, use_bert in [("BERT", True), ("BASELINE", False)]:
    print(f"\n{'='*70}")
    print(f"  {mode_name} MODE")
    print(f"{'='*70}")
    
    for query, expected in test_queries:
        try:
            resp = requests.post(f"{BASE}/api/chat", json={
                "message": query,
                "session_id": f"test_{mode_name.lower()}_{hash(query)}",
                "use_bert": use_bert,
                "use_gemini": True,
            }, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                intent = data.get("intent", "?")
                conf = data.get("confidence", 0)
                response_preview = data.get("response", "")[:80].replace("\n", " ")
                
                match = "OK" if intent in expected.split("/") else "WRONG"
                symbol = "+" if match == "OK" else "X"
                
                print(f"  [{symbol}] [{conf:.4f}] {intent:25s} (expected: {expected:25s}) | {query}")
                if match == "WRONG":
                    print(f"       Response: {response_preview}...")
            else:
                print(f"  [!] HTTP {resp.status_code} | {query}")
                print(f"       {resp.text[:100]}")
        except Exception as e:
            print(f"  [!] Error: {e} | {query}")

print(f"\n{'='*70}")
print("  DONE")
print(f"{'='*70}")
