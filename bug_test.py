import requests
import json

API = "http://127.0.0.1:8000/api"
sid = "bug_test_1"

print("--- TURN 1 ---")
r1 = requests.post(f"{API}/chat", json={
    "message": "Calculate EMI for 10 lakh at 8.5% for 20 years",
    "session_id": sid,
    "use_bert": True,
    "use_gemini": False
}).json()
print(json.dumps(r1, indent=2))

print("\n--- TURN 2 ---")
r2 = requests.post(f"{API}/chat", json={
    "message": "inr",
    "session_id": sid,
    "use_bert": True,
    "use_gemini": False
}).json()
print(json.dumps(r2, indent=2))

print("\n--- TURN 3 ---")
sid2 = "bug_test_2"
r3 = requests.post(f"{API}/chat", json={
    "message": "calculate emi for 10000 dollars for 8.5% rate for 3 years",
    "session_id": sid2,
    "use_bert": True,
    "use_gemini": False
}).json()
print(json.dumps(r3, indent=2))

print("\n--- TURN 4 ---")
r4 = requests.post(f"{API}/chat", json={
    "message": "inr",
    "session_id": sid2,
    "use_bert": True,
    "use_gemini": False
}).json()
print(json.dumps(r4, indent=2))
