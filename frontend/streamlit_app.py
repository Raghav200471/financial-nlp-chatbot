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

    /* ---- Sidebar section labels ---- */
    .sb-label { font-size:0.7rem; font-weight:600; color:#666; text-transform:uppercase; letter-spacing:0.08em; padding:0.5rem 0 0.2rem; }
    /* ---- Sidebar footer ---- */
    .sidebar-footer { font-size: 0.72rem; color: #555; padding-top: 0.5rem; }
    /* ---- Popover / Expander: rounded ---- */
    details { border-radius: 14px !important; }
    div[data-testid="stExpander"] { border-radius: 14px !important; }
    /* ---- Suggestion bubble container ---- */
    .suggestion-hidden { display: none !important; }
    /* ---- ⋮ menu button (last col in row) ---- */
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child .stButton > button {
        padding: 0 !important; min-height: unset !important;
        height: 26px !important; width: 26px !important; min-width: unset !important;
        border-radius: 6px !important; background: transparent !important;
        border: none !important; color: #9aa0a6 !important;
        font-size: 1rem !important; line-height: 1 !important;
        opacity: 0; transition: opacity 0.15s ease;
    }
    div[data-testid="stHorizontalBlock"]:hover div[data-testid="column"]:last-child .stButton > button { opacity: 1 !important; }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child .stButton > button:hover {
        color: #e8eaed !important; background: rgba(255,255,255,0.08) !important; opacity: 1 !important;
    }
    /* ---- Context menu dropdown ---- */
    .ctx-menu { background:#1e2124; border:1px solid rgba(255,255,255,0.1); border-radius:10px;
        padding:0.3rem 0; margin:0.1rem 0 0.4rem 0; box-shadow:0 4px 20px rgba(0,0,0,0.4); }
    .ctx-menu .stButton > button {
        background: transparent !important; border: none !important;
        color: #c9d1d9 !important; text-align: left !important;
        padding: 0.4rem 1rem !important; width: 100% !important;
        border-radius: 0 !important; font-size: 0.85rem !important;
        justify-content: flex-start !important;
    }
    .ctx-menu .stButton > button:hover { background: rgba(255,255,255,0.07) !important; }
    .ctx-menu-delete .stButton > button { color: #f28b82 !important; }

</style>
""", unsafe_allow_html=True)

# ---- JS: sticky sidebar + hide bubbles ----
st.markdown("""
<script>
(function(){
    // Hide suggestion bubbles when spinner shows
    function hideBubbles(){
        var el=document.getElementById('suggestion-bubbles');
        if(el) el.style.display='none';
    }
    new MutationObserver(function(){
        if(document.querySelector('[data-testid="stSpinner"]')) hideBubbles();
    }).observe(document.body,{childList:true,subtree:true});

    // Sticky sidebar: find real scroll container and apply flex
    var timer;
    function fixSidebar(){
        var sc=document.querySelector('[data-testid="stSidebarContent"]');
        if(!sc) return;
        var bc=sc.firstElementChild;
        if(!bc||bc.dataset.sbDone==='1') return;

        var topEl=bc.querySelector('.sb-top');
        var botEl=bc.querySelector('.sb-bot');
        if(!topEl||!botEl) return;

        // Walk up to find direct child of bc
        function dc(el){ while(el&&el.parentElement!==bc) el=el.parentElement; return el; }
        var topDC=dc(topEl), botDC=dc(botEl);
        if(!topDC||!botDC) return;

        var kids=Array.from(bc.children);
        var ti=kids.indexOf(topDC), bi=kids.indexOf(botDC);
        if(ti<0||bi<0||ti>=bi) return;

        // Create history scroll zone
        var hz=document.createElement('div');
        hz.style.cssText='flex:1 1 0;min-height:0;overflow-y:auto;overflow-x:hidden;padding:0 2px;scrollbar-width:thin;scrollbar-color:rgba(138,180,248,0.25) transparent;';

        // Insert hz after topDC, move history items in
        bc.insertBefore(hz, kids[ti+1]);
        var fresh=Array.from(bc.children);
        var hzi=fresh.indexOf(hz);
        var newBi=fresh.indexOf(botDC);
        fresh.slice(hzi+1,newBi).forEach(function(el){ hz.appendChild(el); });

        // Apply flex to block container
        bc.style.cssText='display:flex;flex-direction:column;height:100%;overflow:hidden;padding:0;margin:0;';
        sc.style.overflow='hidden';
        sc.style.height='100vh';
        topDC.style.flexShrink='0';
        botDC.style.flexShrink='0';
        bc.dataset.sbDone='1';
    }

    function debounce(){
        clearTimeout(timer);
        timer=setTimeout(function(){
            var bc=document.querySelector('[data-testid="stSidebarContent"]');
            if(bc&&bc.firstElementChild&&bc.firstElementChild.dataset.sbDone!=='1') fixSidebar();
        },120);
    }
    debounce();
    new MutationObserver(debounce).observe(document.body,{childList:true,subtree:true});
})();
</script>
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
        "title": "New Chat", "messages": [], "debug_data": [],
        "intent_locked": False, "pinned": False,
    }
    st.session_state.session_order.append(new_id)
    st.session_state.active_session_id = new_id

if "current_page" not in st.session_state:
    st.session_state.current_page = "chat"
if "editing_session_id" not in st.session_state:
    st.session_state.editing_session_id = None
if "menu_open_session_id" not in st.session_state:
    st.session_state.menu_open_session_id = None

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

def create_new_session():
    new_id = str(uuid4())
    st.session_state.sessions[new_id] = {
        "title": "New Chat", "messages": [], "debug_data": [],
        "intent_locked": False, "pinned": False,
    }
    st.session_state.session_order.append(new_id)
    st.session_state.active_session_id = new_id
    if len(st.session_state.session_order) > 50:
        oldest_id = st.session_state.session_order.pop(0)
        persist_session_to_disk(oldest_id, st.session_state.sessions[oldest_id])
        del st.session_state.sessions[oldest_id]

def delete_session(s_id):
    if len(st.session_state.session_order) <= 1:
        return  # don't delete last session
    st.session_state.session_order.remove(s_id)
    del st.session_state.sessions[s_id]
    if st.session_state.active_session_id == s_id:
        st.session_state.active_session_id = st.session_state.session_order[-1]
    st.session_state.menu_open_session_id = None

# Get current active session
active_session = st.session_state.sessions[st.session_state.active_session_id]


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:

    # ══ STICKY TOP marker (JS uses .sb-top to find boundary) ══
    st.markdown("<div class='sb-top'></div>", unsafe_allow_html=True)

    # Brand + New Chat
    st.markdown("<div class='brand-header'>FinChat AI</div>", unsafe_allow_html=True)
    if st.button("+ New Chat", key="new_chat_btn", use_container_width=True):
        create_new_session()
        st.session_state.current_page = "chat"
        st.session_state.menu_open_session_id = None
        st.rerun()

    model_choice = st.radio(
        "Model", options=["BERT (Advanced)", "Baseline (Fast)"],
        index=0, key="model_selector",
        disabled=st.session_state.get("is_processing", False),
        label_visibility="collapsed", horizontal=True,
    )
    use_rag_toggle = st.toggle(
        "Personal Info",
        value=st.session_state.get("use_rag_toggle", False),
        key="use_rag_toggle",
        disabled=st.session_state.get("is_processing", False),
    )

    # ══ HISTORY (between sb-top and sb-bot — JS makes this scroll) ══

    # Pinned sessions first
    pinned_ids   = [s for s in reversed(st.session_state.session_order)
                    if st.session_state.sessions[s].get("pinned")]
    unpinned_ids = [s for s in reversed(st.session_state.session_order)
                    if not st.session_state.sessions[s].get("pinned")]

    def render_session_row(s_id):
        s_data    = st.session_state.sessions[s_id]
        is_active = (s_id == st.session_state.active_session_id)
        title_display = s_data["title"][:26]

        if st.session_state.editing_session_id == s_id:
            new_title = st.text_input("", value=s_data["title"],
                key=f"ri_{s_id}", label_visibility="collapsed", max_chars=40)
            cs, cc = st.columns(2)
            with cs:
                if st.button("✓", key=f"sv_{s_id}", use_container_width=True):
                    if new_title.strip():
                        st.session_state.sessions[s_id]["title"] = new_title.strip()
                    st.session_state.editing_session_id = None
                    st.rerun()
            with cc:
                if st.button("✗", key=f"cc_{s_id}", use_container_width=True):
                    st.session_state.editing_session_id = None
                    st.rerun()
        else:
            ct, cm = st.columns([0.82, 0.18])
            with ct:
                if st.button(title_display, key=f"sel_{s_id}",
                             use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.active_session_id = s_id
                    st.session_state.current_page = "chat"
                    st.session_state.menu_open_session_id = None
                    st.rerun()
            with cm:
                if st.button("⋮", key=f"mn_{s_id}"):
                    st.session_state.menu_open_session_id = (
                        None if st.session_state.menu_open_session_id == s_id else s_id
                    )
                    st.session_state.editing_session_id = None
                    st.rerun()

        # Context menu dropdown
        if st.session_state.menu_open_session_id == s_id:
            with st.container():
                st.markdown("<div class='ctx-menu'>", unsafe_allow_html=True)
                if st.button("✏  Rename", key=f"do_rn_{s_id}", use_container_width=True):
                    st.session_state.editing_session_id = s_id
                    st.session_state.menu_open_session_id = None
                    st.rerun()
                pin_label = "📌  Unpin" if s_data.get("pinned") else "📌  Pin"
                if st.button(pin_label, key=f"do_pin_{s_id}", use_container_width=True):
                    st.session_state.sessions[s_id]["pinned"] = not s_data.get("pinned", False)
                    st.session_state.menu_open_session_id = None
                    st.rerun()
                st.markdown("<div class='ctx-menu-delete'>", unsafe_allow_html=True)
                if st.button("🗑  Delete", key=f"do_del_{s_id}", use_container_width=True):
                    delete_session(s_id)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    if pinned_ids:
        st.markdown("<div class='sb-label'>📌 Pinned</div>", unsafe_allow_html=True)
        for s_id in pinned_ids:
            render_session_row(s_id)

    st.markdown("<div class='sb-label'>Chats</div>", unsafe_allow_html=True)
    for s_id in unpinned_ids:
        render_session_row(s_id)

    # ══ STICKY BOTTOM marker ══
    st.markdown("<div class='sb-bot'></div>", unsafe_allow_html=True)

    settings_icon = "← Back to Chat" if st.session_state.current_page == "settings" else "⚙  Settings & Help"
    if st.button(settings_icon, use_container_width=True, key="settings_btn"):
        st.session_state.current_page = (
            "chat" if st.session_state.current_page == "settings" else "settings"
        )
        st.rerun()
    st.markdown(
        "<div class='sidebar-footer'>FastAPI · SpaCy · HuggingFace<br>Deterministic-First Architecture</div>",
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
    # Create a placeholder for the welcome screen that we can clear
    welcome_placeholder = st.empty()

    # ---- Handle pending query (from suggestion bubbles or chat input) ----
    if "pending_query" in st.session_state:
        user_input = st.session_state.pending_query
        del st.session_state.pending_query

        # CLEAR the welcome screen + bubbles immediately before doing anything
        welcome_placeholder.empty()

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

    # ---- Welcome screen (empty chat, NOT processing) ----
    elif not active_session["messages"] and not st.session_state.get("is_processing", False):
        with welcome_placeholder.container():
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
                    if st.button(ex, key=f"sug_{i}", use_container_width=True):
                        st.session_state.pending_query = ex
                        st.session_state.is_processing = True
                        st.rerun()

            cols2 = st.columns(len(row2))
            for i, ex in enumerate(row2):
                with cols2[i]:
                    if st.button(ex, key=f"sug_{i+3}", use_container_width=True):
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
