# 💰 Financial NLP Chatbot

A modular, **deterministic-first** financial chatbot built with FastAPI, Streamlit, SpaCy, and Hugging Face Transformers. Uses direct API calls and rule-based logic for standard queries, with Gemini API as an intelligent fallback for complex financial questions.

## Architecture

```
User → Streamlit UI → FastAPI Backend → NLP Pipeline → Query Router
                                                           │
                                    ┌──────────────────────┼──────────────────────┐
                                    │                      │                      │
                              Deterministic APIs     Rule-Based Engine     Gemini Fallback
                              (Stooq, FMP, CSV)      (EMI calc, FAQs)     (Complex queries)
```

## Features

- 📈 **Real-time stock prices** via firewall-safe fallback (Stooq → FMP → CSV)
- 🏦 **EMI calculation** with rule-based math formulas
- 💱 **Currency exchange rates** via free API
- 📋 **FAQ knowledge base** with TF-IDF similarity matching
- 🤖 **Intent detection** (Scikit-learn baseline / BERT advanced)
- 🏷️ **Named Entity Recognition** with custom SpaCy model
- 🔄 **Multi-turn conversations** with slot-filling dialogue
- 🧠 **Gemini API fallback** for complex/open-ended queries

## Quick Start

### 1. Setup
```bash
# Clone the repo
git clone <repo-url>
cd financialchatbot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure
```bash
# Copy env template and fill in your keys
copy .env.example .env
# Edit .env with your API keys
```

### 3. Train Models
```bash
python models/intent_classifier/baseline/train_baseline.py
python models/ner/train_ner.py
```

### 4. Run
```bash
# Terminal 1: Start backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start frontend
streamlit run frontend/streamlit_app.py
```

## Project Structure

```
financialchatbot/
├── config.py              # Central configuration
├── api/                   # FastAPI backend
├── nlp/                   # NLP models (intent + NER)
├── engine/                # Conversation manager + router
├── integrations/          # External API wrappers
├── knowledge/             # FAQ knowledge base
├── frontend/              # Streamlit chat UI
├── models/                # Trained model artifacts
├── data/                  # Training datasets
└── tests/                 # Test suite
```

## Configuration

All settings are managed via `.env` file — **no hardcoded keys**.

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `FMP_API_KEY` | Financial Modeling Prep API key (optional) |
| `USE_BERT` | `true` to use BERT, `false` for baseline |
| `USE_GEMINI` | `true` to enable Gemini fallback |
| `INTENT_CONFIDENCE_THRESHOLD` | Min confidence for deterministic routing (default: 0.85) |

## License

MIT
