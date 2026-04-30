import requests
import json

API = "http://127.0.0.1:8000/api"

r = requests.post(f"{API}/chat", json={
    "message": "okay what is my emi for 2 years at 5% for 10 lakhs ruppes",
    "session_id": "test_ruppes",
    "use_bert": True,
    "use_gemini": True,
    "user_context": {"goal": "save money"}
}).json()
print(json.dumps(r, indent=2))
