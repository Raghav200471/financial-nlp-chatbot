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
p("0 duration", test_chat("calculate EMI for 10 lakh at 8.5% for 0 years", sid="e1"))
p("0 duration fill curr", test_chat("INR", sid="e1"))
