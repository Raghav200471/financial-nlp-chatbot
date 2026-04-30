import requests
import json

API = "http://127.0.0.1:8000/api"
sid = "bug_test_gemini"

print("--- TURN 1 ---")
r1 = requests.post(f"{API}/chat", json={
    "message": "Calculate EMI for 10 lakh at 8.5% for 20 years",
    "session_id": sid,
    "use_bert": True,
    "use_gemini": True
}).json()
print(json.dumps(r1, indent=2))

print("\n--- TURN 2 ---")
r2 = requests.post(f"{API}/chat", json={
    "message": "inr",
    "session_id": sid,
    "use_bert": True,
    "use_gemini": True
}).json()
print(json.dumps(r2, indent=2))
