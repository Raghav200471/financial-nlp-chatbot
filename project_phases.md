# Financial NLP Chatbot: Phase-by-Phase File Breakdown

This document maps every file in the project to the specific development phase it belongs to. This gives you a clear mental model of how the system was built layer-by-layer.

---

## Phase 1: Foundation & Configuration
*Setting up the environment, dependencies, and centralized configuration.*

* `requirements.txt`: The definitive list of all required Python packages (FastAPI, Streamlit, Spacy, Transformers, Google GenAI, etc.).
* `.env.example`: A template showing the required environment variables (without exposing real keys).
* `.env` *(Hidden)*: Your local file containing the actual API keys (Gemini, FMP).
* `config.py`: The central configuration manager that loads variables from `.env` and makes them accessible to the rest of the application.
* `.gitignore`: Specifies which files Git should ignore (like `venv`, `.env`, and `__pycache__`).

---

## Phase 2: Data & Knowledge Base
*Creating the local data sources required for the system to run deterministically and offline.*

* `data/stock_data.csv`: The local, offline fallback dataset containing static stock prices.
* `knowledge/faq.json`: The local knowledge base containing financial definitions (e.g., "What is a savings account?") used by the RAG system.

---

## Phase 3: Natural Language Processing (NLP) Core
*The brain of the local chatbot responsible for understanding what the user wants.*

* `nlp/intent_detector.py`: The module that classifies the user's intent (e.g., `get_stock_price`, `calculate_emi`).
* `nlp/entity_extractor.py`: The Named Entity Recognition module, using SpaCy to extract specific parameters like company names, numbers, and currencies.
* `nlp/preprocessor.py`: Text cleaning and normalization before sending text to the models.
* `models/intent_classifier/baseline/train_baseline.py`: Script to train the Scikit-Learn intent baseline model.
* `models/ner/train_ner.py`: Script to train the custom SpaCy NER model.

---

## Phase 4: External Integrations (Firewall-Safe)
*The wrappers built to communicate with external APIs, using the cascading fallback strategy.*

* `integrations/stock_api.py`: Fetches stock data using a cascading strategy (Stooq -> FMP -> CSV fallback).
* `integrations/currency_api.py`: Fetches real-time currency conversion rates.
* `integrations/calculator.py`: Local deterministic formulas for calculating EMIs, etc.
* `integrations/gemini_client.py`: The module that securely calls the Google Gemini API for complex queries that the local engine cannot handle.

---

## Phase 5: The Routing Engine & Dialog Management
*The core logic that ties NLP and Integrations together.*

* `engine/query_router.py`: The central brain. It takes the output from the `intent_detector`, checks confidence, and routes the query.
* `engine/conversation_manager.py`: Handles multi-turn conversations (e.g., if the user asks for an EMI but forgets to provide the interest rate, this module asks for the missing information).
* `engine/response_generator.py`: Formats the final text output sent back to the user.

---

## Phase 6: FastAPI Backend Server
*Exposing the Engine and NLP modules as a REST API.*

* `api/main.py`: The FastAPI application entry point. Handles server startup and registers routes.
* `api/schemas.py`: Pydantic models that strictly define the data format expected in requests and responses (ensures data validation).
* `api/routes/chat.py` *(or similar route files)*: The specific endpoint (`POST /chat`) that receives messages from the frontend and passes them to the `engine/query_router.py`.

---

## Phase 7: High-Fidelity Frontend UI
*The user-facing Streamlit application with the Gemini-inspired dark mode aesthetic.*

* `frontend/streamlit_app.py`: The entire Streamlit application. Handles the chat interface, the sidebar, the settings page, session state, and sending requests to the backend API.
* `.streamlit/config.toml`: The configuration file that strictly enforces the system-wide Dark Mode and subtle blue UI accents.

---

## Phase 8: Testing, QA & Diagnostics
*Scripts built to verify the system works under pressure and edge cases.*

* `test_all_edge_cases.py` & `evaluate_accuracy.py`: Scripts used to test the NLP model's accuracy against various phrasings.
* `audit_test.py`, `bug_test.py`, `bug_test_gemini.py`: Specialized diagnostic scripts written to debug specific issues (like the infinite loop bug, Gemini prompt formatting, or firewall blocks).
* `test_ruppes.py`: Small unit test for currency formatting logic.
* `tests/` *(Directory)*: Contains standard `pytest` automated testing suites.

---

## Summary Document
* `README.md`: The final documentation tying everything together, explaining the architecture, and providing instructions on how to run the servers.
