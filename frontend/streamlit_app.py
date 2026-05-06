"""
Financial NLP Chatbot — Streamlit Frontend
============================================
Gemini-inspired chat UI with clean sidebar, settings page,
and suggestion bubbles.

Run with:
    streamlit run frontend/streamlit_app.py
"""

import streamlit as st
import requests
import json
from uuid import uuid4
from datetime import datetime

# ---- Page Configuration ----
st.set_page_config(
    page_title="Financial NLP Chatbot",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Custom CSS (dark theme with bright text) ----
st.markdown("""
<style>
    /* ---- Global ---- */
    .block-container { max-width: 850px; margin: 0 auto; padding-top: 2rem; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* ---- Chat messages ---- */
    .stChatMessage { border-radius: 18px !important; }
    .stChatMessage p { font-size: 1.05rem; line-height: 1.6; }
    div[data-testid="stChatInput"] textarea {
        font-size: 1.1rem; padding: 1.2rem; border-radius: 24px !important;
    }
    div[data-testid="stChatInput"] {
        padding-bottom: 1.5rem;
    }
    div[data-testid="stChatInput"] > div {
        border-radius: 24px !important;
    }

    /* ---- All buttons: rounded, subtle colors ---- */
    .stButton > button {
        border-radius: 22px !important;
        padding: 0.45rem 1.1rem;
        font-size: 0.88rem;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }
    /* Suggestion & secondary buttons — bright readable text */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="stBaseButton-secondary"] {
        background-color: transparent !important;
        border: 1px solid rgba(138,180,248,0.25) !important;
        color: #c9d1d9 !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background-color: rgba(138,180,248,0.08) !important;
        border-color: rgba(138,180,248,0.5) !important;
        color: #8ab4f8 !important;
    }

    /* ---- Radio buttons: subtle ---- */
    .stRadio > div { gap: 0.3rem; }
    .stRadio label { font-size: 0.88rem !important; }

    /* ---- Inputs: rounded ---- */
    .stTextInput > div > div { border-radius: 14px !important; }
    .stTextArea > div > div { border-radius: 14px !important; }
    .stSelectbox > div > div { border-radius: 14px !important; }
    div[data-baseweb="select"] > div { border-radius: 14px !important; }

    /* ---- Alert boxes: rounded ---- */
    .stAlert { border-radius: 14px !important; }

    /* ---- Welcome screen ---- */
    .welcome-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 50vh; text-align: center;
    }
    .welcome-greeting {
        font-size: 1.8rem; font-weight: 300; color: #a8c7fa;
        margin-bottom: 0.3rem;
    }
    .welcome-tagline {
        font-size: 2.1rem; font-weight: 500; color: #e8eaed;
        margin-bottom: 2.5rem;
    }

    /* ---- Brand header ---- */
    .brand-header {
        font-size: 1.05rem; font-weight: 600; color: #8ab4f8;
        letter-spacing: 0.3px; padding: 0.3rem 0 0.8rem 0;
    }

    /* ---- Sidebar footer ---- */
    .sidebar-footer {
        font-size: 0.75rem; color: #666; padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: 1rem;
    }

    /* ---- Popover / Expander: rounded ---- */
    details { border-radius: 14px !important; }
    div[data-testid="stExpander"] { border-radius: 14px !important; }

</style>
""", unsafe_allow_html=True)

# ---- API & Configuration ----
API_BASE_URL = "http://127.0.0.1:8000/api"
import os
from dotenv import load_dotenv
load_dotenv()
SAVE_CHAT_HISTORY = os.getenv("SAVE_CHAT_HISTORY", "false").lower() == "true"
HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chat_history_log.json")

# ---- Session State Initialization ----
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
    st.session_state.session_order = []

# Global user profile — persists across all chat sessions
# Only cleared when Personal Info toggle is turned off
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "monthly_income": "",
        "existing_emis": "",
        "savings": "",
        "financial_goals": "",
        "risk_tolerance": "Moderate"
    }

if "active_session_id" not in st.session_state:
    new_id = str(uuid4())
    st.session_state.sessions[new_id] = {
        "title": "New Chat",
        "messages": [],
        "debug_data": [],
        "intent_locked": False,
    }
    st.session_state.session_order.append(new_id)
    st.session_state.active_session_id = new_id

if "current_page" not in st.session_state:
    st.session_state.current_page = "chat"

# Helper to save dropped sessions to disk
def persist_session_to_disk(session_id: str, session_data: dict):
    if not SAVE_CHAT_HISTORY or not session_data["messages"]:
        return
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []
        
        # Update existing session entry instead of appending duplicates
        entry = {
            "session_id": session_id,
            "title": session_data.get("title", "Unknown"),
            "timestamp": datetime.now().isoformat(),
            "messages": session_data.get("messages", [])
        }
        # Find and replace existing entry for this session_id
        found = False
        for i, item in enumerate(history):
            if item.get("session_id") == session_id:
                history[i] = entry
                found = True
                break
        if not found:
            history.append(entry)
        
        # Keep last 100 sessions on disk to avoid bloated files
        if len(history) > 100:
            history = history[-100:]
            
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Failed to save chat history: {e}")

# Helper to add a new session
def create_new_session():
    new_id = str(uuid4())
    st.session_state.sessions[new_id] = {
        "title": "New Chat",
        "messages": [],
        "debug_data": [],
        "intent_locked": False,
    }
    st.session_state.session_order.append(new_id)
    st.session_state.active_session_id = new_id
    
    # Enforce max 5 sessions in UI
    if len(st.session_state.session_order) > 5:
        oldest_id = st.session_state.session_order.pop(0)
        persist_session_to_disk(oldest_id, st.session_state.sessions[oldest_id])
        del st.session_state.sessions[oldest_id]

# Get current active session
active_session = st.session_state.sessions[st.session_state.active_session_id]


# ============================================================
# SIDEBAR — Clean, Gemini-inspired
# ============================================================
with st.sidebar:
    # ---- Brand + New Chat ----
    st.markdown("<div class='brand-header'>FinChat AI</div>", unsafe_allow_html=True)
    if st.button("+ New Chat", key="new_chat_btn", use_container_width=True):
        create_new_session()
        st.session_state.current_page = "chat"
        st.rerun()

    # ---- Model selector (radio, not editable) ----
    model_choice = st.radio(
        "Model",
        options=["BERT (Advanced)", "Baseline (Fast)"],
        index=0,
        key="model_selector",
        disabled=st.session_state.get("is_processing", False),
        label_visibility="collapsed",
        horizontal=True,
    )

    # ---- Personal Info toggle ----
    use_rag_toggle = st.toggle(
        "Personal Info",
        value=st.session_state.get("use_rag_toggle", False),
        key="use_rag_toggle",
        disabled=st.session_state.get("is_processing", False),
    )

    st.markdown("---")

    # ---- Chat History ----
    for s_id in reversed(st.session_state.session_order):
        s_data = st.session_state.sessions[s_id]
        is_active = (s_id == st.session_state.active_session_id)
        
        title_display = s_data["title"][:28]
        
        if st.button(
            title_display,
            key=f"sel_{s_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.active_session_id = s_id
            st.session_state.current_page = "chat"
            st.rerun()

    st.markdown("---")

    # ---- Settings button ----
    settings_icon = "Back to Chat" if st.session_state.current_page == "settings" else "Settings"
    if st.button(settings_icon, use_container_width=True, key="settings_btn"):
        if st.session_state.current_page == "settings":
            st.session_state.current_page = "chat"
        else:
            st.session_state.current_page = "settings"
        st.rerun()

    # ---- Sidebar footer ----
    st.markdown(
        "<div class='sidebar-footer'>"
        "FastAPI · SpaCy · HuggingFace<br>"
        "Deterministic-First Architecture"
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# HELPER: Send message to API
# ============================================================
def send_message(user_input: str, use_rag: bool = False) -> dict | None:
    """Send a message to the backend API and return the response."""
    try:
        payload = {
            "message": user_input,
            "session_id": st.session_state.active_session_id,
            "use_gemini": st.session_state.get("use_gemini_toggle", True),
            "use_bert": st.session_state.get("model_selector", "BERT (Advanced)") == "BERT (Advanced)",
        }
        if use_rag:
            payload["user_context"] = st.session_state.user_profile
            
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "response": (
                "Cannot connect to the backend API. "
                "Please make sure the FastAPI server is running:\n\n"
                "`uvicorn api.main:app --reload --port 8000`"
            ),
            "intent": None,
            "confidence": None,
            "entities": [],
            "session_id": st.session_state.active_session_id,
        }
    except Exception as e:
        return {
            "response": f"An error occurred: {str(e)}",
            "intent": None,
            "confidence": None,
            "entities": [],
            "session_id": st.session_state.active_session_id,
        }





# ============================================================
# PAGE: SETTINGS
# ============================================================
if st.session_state.current_page == "settings":
    st.markdown("## Settings")
    st.markdown("---")

    # API Health
    st.markdown("### API Status")
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=3).json()
        st.success(f"Connected — {health.get('mode', 'unknown')} mode")
        if health.get("gemini_enabled"):
            st.info("Gemini fallback: Enabled")
        else:
            st.warning("Gemini fallback: Disabled")
    except Exception:
        st.error("Backend not reachable. Start with:\n`uvicorn api.main:app --reload --port 8000`")

    st.markdown("---")

    # Model Engine
    st.markdown("### AI Model Engine")
    st.markdown(f"**Currently selected:** `{st.session_state.get('model_selector', 'BERT (Advanced)')}`")
    st.caption("Change this from the sidebar dropdown.")

    st.markdown("---")

    # Gemini Toggle
    st.markdown("### Gemini AI Fallback")
    temp_gemini = st.toggle(
        "Enable Gemini AI Fallback",
        value=st.session_state.get("use_gemini_toggle", True),
        disabled=st.session_state.get("is_processing", False),
    )
    if not temp_gemini:
        st.info("Strictly using local rules & knowledge base.")
    else:
        st.caption("When enabled, complex queries that can't be answered locally will be forwarded to Gemini.")

    st.markdown("---")

    # Personal Finance Profile (RAG)
    st.markdown("### Personal Finance Profile")
    rag_active = st.session_state.get("use_rag_toggle", False)
    
    temp_income = ""
    temp_emis = ""
    temp_savings = ""
    temp_goals = ""
    temp_risk = "Low"

    if rag_active:
        st.caption("This profile is used for personalized financial advice. Data is ephemeral and never saved to disk.")
        temp_income = st.text_input(
            "Monthly Income (₹)", value=st.session_state.user_profile["monthly_income"]
        )
        temp_emis = st.text_input(
            "Existing Monthly EMIs (₹)", value=st.session_state.user_profile["existing_emis"]
        )
        temp_savings = st.text_input(
            "Total Savings / Investments (₹)", value=st.session_state.user_profile["savings"]
        )
        temp_goals = st.text_area(
            "Financial Goals", value=st.session_state.user_profile["financial_goals"],
            placeholder="e.g. Buy a house in 5 years, retire early..."
        )
        temp_risk = st.selectbox(
            "Risk Tolerance",
            ["Low", "Moderate", "High"],
            index=["Low", "Moderate", "High"].index(st.session_state.user_profile["risk_tolerance"])
        )
    else:
        st.warning("Personal Info is turned off. Enable it from the sidebar toggle to fill your profile.")

    st.markdown("---")
    
    if st.button("Save Settings", type="primary", use_container_width=True):
        st.session_state.use_gemini_toggle = temp_gemini
        if rag_active:
            st.session_state.user_profile["monthly_income"] = temp_income
            st.session_state.user_profile["existing_emis"] = temp_emis
            st.session_state.user_profile["savings"] = temp_savings
            st.session_state.user_profile["financial_goals"] = temp_goals
            st.session_state.user_profile["risk_tolerance"] = temp_risk
        st.success("Settings saved successfully!")

    st.markdown("---")
    st.caption("Built with FastAPI + Streamlit + SpaCy + HuggingFace · Deterministic-First Architecture")


# ============================================================
# PAGE: CHAT
# ============================================================
else:
    # ---- Handle pending query (from suggestion bubbles or chat input) ----
    if "pending_query" in st.session_state:
        user_input = st.session_state.pending_query
        del st.session_state.pending_query

        # Add user message
        active_session["messages"].append({"role": "user", "content": user_input})
        active_session["debug_data"].append(None)

        # Display existing chat history FIRST (for multi-turn conversations)
        for idx, msg in enumerate(active_session["messages"][:-1]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Show the new user message
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Only count actual data fields, not the always-set risk_tolerance default
                profile = st.session_state.user_profile
                has_profile_data = any(profile.get(k, "") for k in ["monthly_income", "existing_emis", "savings", "financial_goals"])
                use_rag = st.session_state.get("use_rag_toggle", False) and has_profile_data
                data = send_message(user_input, use_rag=use_rag)
        
        if data and not active_session["intent_locked"] and data.get("intent"):
            active_session["title"] = data["intent"].replace("_", " ").title()
            active_session["intent_locked"] = True
            
        if data:
            active_session["messages"].append({"role": "assistant", "content": data["response"]})
            active_session["debug_data"].append({
                "intent": data.get("intent"),
                "confidence": data.get("confidence"),
                "entities": data.get("entities", []),
            })

        # Persist session to disk after every bot response
        persist_session_to_disk(
            st.session_state.active_session_id, active_session
        )

        # Unlock the UI
        st.session_state.is_processing = False
        st.rerun()

    # ---- Welcome screen (empty chat) ----
    elif not active_session["messages"]:
        st.markdown(
            """
            <div class="welcome-container">
                <div class="welcome-greeting">Hi, I'm your Financial Assistant</div>
                <div class="welcome-tagline">What would you like to know?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Suggestion bubbles
        examples = [
            "What is the price of Apple?",
            "Calculate EMI for 10 lakh at 8.5%",
            "USD to INR rate",
            "What is a savings account?",
            "Am I eligible for a home loan?",
            "Explain SIP vs lump sum",
        ]
        
        # Render as two rows of 3 columns
        row1 = examples[:3]
        row2 = examples[3:]

        cols1 = st.columns(len(row1))
        for i, ex in enumerate(row1):
            with cols1[i]:
                if st.button(ex, key=f"sug_{i}", use_container_width=True, disabled=st.session_state.get("is_processing", False)):
                    st.session_state.pending_query = ex
                    st.session_state.is_processing = True
                    st.rerun()

        cols2 = st.columns(len(row2))
        for i, ex in enumerate(row2):
            with cols2[i]:
                if st.button(ex, key=f"sug_{i+3}", use_container_width=True, disabled=st.session_state.get("is_processing", False)):
                    st.session_state.pending_query = ex
                    st.session_state.is_processing = True
                    st.rerun()

    else:
        # ---- Display Chat History ----
        for i, msg in enumerate(active_session["messages"]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                if msg["role"] == "assistant" and i < len(active_session["debug_data"]):
                    debug = active_session["debug_data"][i]
                    if debug:
                        try:
                            with st.popover("View Intent & Entities"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Intent:** `{debug.get('intent', 'N/A')}`")
                                    conf = debug.get('confidence')
                                    conf_str = f"{conf:.4f}" if conf is not None else "N/A"
                                    st.markdown(f"**Confidence:** `{conf_str}`")
                                with col2:
                                    entities = debug.get("entities", [])
                                    if entities:
                                        ent_strs = [f"`{e['value']}` ({e['entity']})" for e in entities]
                                        st.markdown(f"**Entities:** {', '.join(ent_strs)}")
                                    else:
                                        st.markdown("**Entities:** None detected")
                        except AttributeError:
                            with st.expander("View Intent & Entities", expanded=False):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Intent:** `{debug.get('intent', 'N/A')}`")
                                    conf = debug.get('confidence')
                                    conf_str = f"{conf:.4f}" if conf is not None else "N/A"
                                    st.markdown(f"**Confidence:** `{conf_str}`")
                                with col2:
                                    entities = debug.get("entities", [])
                                    if entities:
                                        ent_strs = [f"`{e['value']}` ({e['entity']})" for e in entities]
                                        st.markdown(f"**Entities:** {', '.join(ent_strs)}")
                                    else:
                                        st.markdown("**Entities:** None detected")

    # ---- Chat Input ----
    user_input = st.chat_input(
        "Ask me about stocks, loans, EMI, currency exchange...",
        disabled=st.session_state.get("is_processing", False),
    )
    if user_input:
        st.session_state.pending_query = user_input
        st.session_state.is_processing = True
        st.rerun()
