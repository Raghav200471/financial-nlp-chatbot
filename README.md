# 💰 Financial NLP Chatbot

A modular, **deterministic-first** financial chatbot built with FastAPI, React, SpaCy, and Hugging Face Transformers. Uses direct API calls and rule-based logic for standard queries, with Gemini/Groq as an intelligent LLM fallback for complex financial questions.

## Architecture

```
User → React Frontend → FastAPI Backend → NLP Pipeline → Query Router
         (Vite)           (Uvicorn)            │
                                  ┌────────────┼────────────────┐
                                  │            │                │
                            Deterministic   Rule-Based      LLM Fallback
                            APIs            Engine          (Gemini / Groq)
                            (Stooq, FMP)    (EMI, FAQs)     (Complex queries)
```

## Features

- 📈 **Real-time stock prices** via firewall-safe fallback chain (Stooq → FMP → CSV)
- 🏦 **EMI & interest calculation** with rule-based math formulas
- 💱 **Currency exchange rates** via free API
- 📋 **FAQ knowledge base** with TF-IDF similarity matching
- 🤖 **Dual intent detection** — Scikit-learn baseline (fast) / BERT advanced (accurate)
- 🏷️ **Named Entity Recognition** with custom SpaCy NER model
- 🔄 **Multi-turn conversations** with intelligent slot-filling dialogue
- 🧠 **LLM fallback** — Gemini API + Groq for complex/open-ended queries
- 👤 **RAG Profile** — Auto-fills missing financial details (income, EMIs) from saved user profile
- 🔐 **JWT Authentication** — Secure login/register with MongoDB user storage
- 🌙 **Day/Night Theme** — Persistent dark/light mode toggle
- 💬 **Chat History** — MongoDB-backed conversation persistence per user

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19 + Vite |
| **Backend** | FastAPI + Uvicorn |
| **NLP** | SpaCy, HuggingFace Transformers, Scikit-learn |
| **Database** | MongoDB (via Motor async driver) |
| **Auth** | JWT (python-jose) + bcrypt |
| **LLM** | Google Gemini API, Groq API |
| **Financial Data** | Stooq, Financial Modeling Prep, CSV fallback |
| **Legacy Frontend** | Streamlit (still functional) |

---

## Quick Start

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/Raghav200471/financial-nlp-chatbot.git
cd financial-nlp-chatbot

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Download SpaCy language model
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
# Copy env template and fill in your keys
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

Open `.env` and set your API keys. See [Configuration](#configuration) for details.

### 3. Start MongoDB

Make sure MongoDB is running locally:

```bash
# Default connection: mongodb://localhost:27017
# Database name: finchat (auto-created on first run)
mongod
```

Or set `MONGODB_URI` in `.env` to point to a remote MongoDB Atlas instance.

### 4. Train Models

```bash
# Train baseline intent classifier (TF-IDF + Logistic Regression) — ~5 seconds
python models/intent_classifier/baseline/train_baseline.py

# Train BERT intent classifier (downloads HuggingFace weights) — ~5 minutes
python models/intent_classifier/bert/train_bert.py

# Train custom SpaCy NER model — ~2 minutes
python models/ner/train_ner.py
```

### 5. Run the Application

Open **two terminals** (activate venv in both):

```bash
# Terminal 1 — FastAPI Backend
python -m uvicorn api.main:app --reload --port 8000
```

```bash
# Terminal 2 — React Frontend
cd react-frontend
npm install        # first time only
npm run dev
```

Open your browser at **http://localhost:5173** → Register an account → Start chatting!

> **Legacy Streamlit UI:** You can also run `python -m streamlit run frontend/streamlit_app.py` for the original interface at `http://localhost:8501`.

---

## Configuration

All settings are managed via the `.env` file — **no hardcoded keys or secrets in code**.

### API Keys

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Optional | Google Gemini API key for AI fallback |
| `GROQ_API_KEY` | Optional | Groq API key (secondary LLM fallback) |
| `FMP_API_KEY` | Optional | Financial Modeling Prep key (stock data fallback) |

### Model Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `INTENT_MODEL_PATH` | `models/intent_classifier/baseline/model.pkl` | Baseline classifier path |
| `INTENT_VECTORIZER_PATH` | `models/intent_classifier/baseline/vectorizer.pkl` | TF-IDF vectorizer path |
| `BERT_MODEL_PATH` | `models/intent_classifier/bert/saved_model` | Fine-tuned BERT model path |
| `NER_MODEL_PATH` | `models/ner/saved_model` | Custom SpaCy NER model path |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_BERT` | `false` | `true` = BERT classifier, `false` = baseline LogReg |
| `USE_GEMINI` | `false` | `true` = enable LLM fallback for unknown queries |
| `SAVE_CHAT_HISTORY` | `false` | `true` = persist chat history to MongoDB |

### Database & Auth

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB` | `finchat` | Database name |
| `JWT_SECRET_KEY` | *(placeholder)* | **Change this!** Secret for JWT signing |
| `JWT_EXPIRE_MINUTES` | `10080` | Token expiry (default: 7 days) |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `127.0.0.1` | FastAPI bind host |
| `API_PORT` | `8000` | FastAPI bind port |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |
| `INTENT_CONFIDENCE_THRESHOLD` | `0.85` | Min confidence for deterministic routing |

---

## Project Structure

```
financial-nlp-chatbot/
│
├── .env.example               # Environment variable template
├── config.py                  # Central configuration (reads from .env)
├── requirements.txt           # Python dependencies
│
├── api/                       # FastAPI backend
│   ├── main.py                # App entry point, lifespan, CORS
│   ├── auth.py                # JWT + bcrypt utilities
│   ├── database.py            # MongoDB async connection (Motor)
│   ├── schemas.py             # Pydantic request/response models
│   └── routes/
│       ├── chat.py            # POST /api/chat — main NLP pipeline
│       ├── intent.py          # POST /api/intent — raw intent detection
│       ├── auth.py            # POST /auth/login, /auth/register
│       └── users.py           # GET/PUT /users/me — profile & chats
│
├── nlp/                       # NLP models
│   ├── preprocessor.py        # Text cleaning, normalization
│   ├── intent_detector.py     # Unified baseline/BERT classifier
│   └── entity_extractor.py    # SpaCy NER wrapper
│
├── engine/                    # Business logic
│   ├── conversation_manager.py # Multi-turn dialogue + slot filling
│   ├── query_router.py        # Deterministic-first routing logic
│   └── response_generator.py  # Template-based response formatting
│
├── integrations/              # External API wrappers
│   ├── stock_api.py           # Stock prices (Stooq → FMP → CSV)
│   ├── currency_api.py        # Exchange rates
│   ├── calculator.py          # EMI & interest math
│   └── gemini_client.py       # Gemini + Groq LLM clients
│
├── knowledge/                 # Knowledge base
│   └── faq_lookup.py          # TF-IDF FAQ similarity search
│
├── models/                    # ML model training & artifacts
│   ├── intent_classifier/
│   │   ├── baseline/          # TF-IDF + LogReg (model.pkl, vectorizer.pkl)
│   │   └── bert/              # Fine-tuned BERT (saved_model/)
│   └── ner/                   # Custom SpaCy NER (saved_model/)
│
├── data/                      # Training datasets
│   ├── intents.json           # Intent training data
│   ├── faq.json               # FAQ knowledge base
│   └── spacy_training/        # NER training data
│
├── react-frontend/            # React 19 + Vite frontend
│   ├── src/
│   │   ├── App.jsx            # Routes + providers
│   │   ├── index.css          # Design system + theme variables
│   │   ├── api/client.js      # API client with JWT handling
│   │   ├── context/
│   │   │   ├── AuthContext.jsx # Auth state + protected routes
│   │   │   └── ThemeContext.jsx # Dark/light theme persistence
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx  # Messages + suggestion bubbles
│   │   │   ├── Sidebar.jsx     # Chat list + model toggle
│   │   │   ├── TopBar.jsx      # Theme toggle + account menu
│   │   │   ├── MessageInput.jsx # Chat input bar
│   │   │   └── SettingsPanel.jsx # Gemini toggle + health
│   │   └── pages/
│   │       ├── ChatPage.jsx    # Main chat interface
│   │       ├── LoginPage.jsx   # Login form
│   │       ├── RegisterPage.jsx # Registration form
│   │       └── SettingsPage.jsx # User profile + RAG settings
│   ├── vite.config.js         # Dev server proxy to FastAPI
│   └── package.json
│
├── frontend/                  # Legacy Streamlit UI
│   └── streamlit_app.py
│
└── tests/                     # Test suite
    └── test_api_intents.py    # Intent classification tests
```

---

## Supported Intents

| Intent | Example Query | Handler |
|--------|---------------|---------|
| `get_stock_price` | "What is the price of Apple?" | Stooq/FMP API |
| `calculate_emi` | "Calculate EMI for 10 lakh at 8.5%" | Rule-based math |
| `calculate_interest` | "Interest on 5 lakh at 7% for 3 years" | Rule-based math |
| `get_exchange_rate` | "USD to INR rate" | Currency API |
| `loan_eligibility` | "Am I eligible for a home loan?" | Rule-based + RAG |
| `loan_query` | "What types of home loans are available?" | FAQ + Gemini |
| `faq_general` | "What is a savings account?" | TF-IDF FAQ lookup |
| `complex_query` | "Compare SBI vs HDFC FD rates" | Gemini/Groq LLM |
| `greeting` | "Hello" | Template response |
| `goodbye` | "Bye" | Template response |

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account (name, email, password) |
| POST | `/auth/login` | Login, returns JWT token |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message through NLP pipeline |
| POST | `/api/intent` | Raw intent detection (debug) |
| GET | `/api/health` | Backend health check |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current user profile |
| GET | `/users/me/profile` | Get RAG financial profile |
| PUT | `/users/me/profile` | Update RAG financial profile |
| GET | `/users/me/chats` | Get saved chat sessions |
| POST | `/users/me/chats` | Save a chat session |
| DELETE | `/users/me/chats/{id}` | Delete a chat session |

---

## License

MIT
