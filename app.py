# app.py
# 🚀 Smart Memory AI Agent
# Streamlit + Gemini + Mem0 + Qdrant + MySQL Auth + Persistent Memory
# Fixed version — uses genai.Client(...) and safe session handling

import os
import json
import warnings
import streamlit as st
from dotenv import load_dotenv
from mem0 import Memory
from google import genai
from qdrant_client import QdrantClient
import mysql.connector
import bcrypt

# -----------------------------
# Basic Config
# -----------------------------
warnings.filterwarnings("ignore", category=ImportWarning)
load_dotenv()

# -----------------------------
# Helpers for secrets
# -----------------------------
def get_secret(key, default=None):
    # Prefer Streamlit secrets, fall back to environment
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
QDRANT_API_KEY = get_secret("QDRANT_API_KEY")
QDRANT_URL = get_secret("QDRANT_URL", "http://localhost:6333")
NEO4J_URI = get_secret("NEO4J_URI")
NEO4J_USERNAME = get_secret("NEO4J_USERNAME")
NEO4J_PASSWORD = get_secret("NEO4J_PASSWORD")

MYSQL_HOST = get_secret("MYSQL_HOST", "localhost")
MYSQL_PORT = int(get_secret("MYSQL_PORT", 3306))
MYSQL_USER = get_secret("MYSQL_USER", "root")
MYSQL_PASSWORD = get_secret("MYSQL_PASSWORD", "")
MYSQL_DB = get_secret("MYSQL_DB", "smart_ai_db")

# -----------------------------
# MySQL Setup (safe)
# -----------------------------
try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
except Exception as e:
    st.error(f"MySQL connection error: {e}")
    st.stop()

# -----------------------------
# Qdrant Client
# -----------------------------
try:
    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30.0,
        prefer_grpc=False
    )
except Exception as e:
    st.error(f"Qdrant client init error: {e}")
    st.stop()

# -----------------------------
# Gemini (Google GenAI) Client
# -----------------------------
if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY (set in Streamlit secrets or .env).")
    st.stop()

try:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Error initializing genai client: {e}")
    st.stop()

# -----------------------------
# Mem0 Config
# -----------------------------
config = {
    "version": "v1.1",
    "embedder": {"provider": "gemini", "config": {"model": "models/text-embedding-004"}},
    "llm": {"provider": "gemini", "config": {"api_key": GEMINI_API_KEY, "model": "models/gemini-2.5-flash"}},
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": NEO4J_URI,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD,
        },
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": QDRANT_URL,
            "api_key": QDRANT_API_KEY,
            "collection_name": "memory_agent",
            "embedding_model_dims": 768,
        },
    },
}
try:
    mem_client = Memory.from_config(config)
except Exception as e:
    st.warning(f"Warning: Mem0 initialization failed (memory features may not work): {e}")
    mem_client = None

# -----------------------------
# Auth helper functions
# -----------------------------
def register_user(email, password):
    try:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            (email, hashed_password.decode()),
        )
        conn.commit()
        return True
    except mysql.connector.Error as err:
        st.sidebar.error(f"MySQL Error: {err}")
        return False

def authenticate_user(email, password):
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user["email"]
    return None

# -----------------------------
# Streamlit UI config
# -----------------------------
st.set_page_config(page_title="Smart Memory AI Agent", page_icon="🧠", layout="wide")

st.title("🧠 Smart Memory AI Agent")
st.markdown("""
**Powered by Gemini + Mem0 + Qdrant + MySQL + Neo4j**  
💬 Personalized Memory | ⚡ Persistent AI | ☁️ Cloud-Ready
""")

# -----------------------------
# Sidebar - Authentication
# -----------------------------
st.sidebar.markdown("### 🔐 Authentication")

if "user_email" not in st.session_state:
    option = st.sidebar.radio("Choose an option:", ["Login", "Register"])

    if option == "Register":
        email = st.sidebar.text_input("Email", key="reg_email")
        password = st.sidebar.text_input("Password", type="password", key="reg_pass")
        if st.sidebar.button("Register"):
            if email and password:
                ok = register_user(email, password)
                if ok:
                    st.sidebar.success("✅ Registered successfully! Please login.")
                else:
                    st.sidebar.error("❌ Email already exists or DB error.")
            else:
                st.sidebar.warning("Please enter both fields.")

    elif option == "Login":
        email = st.sidebar.text_input("Email", key="login_email")
        password = st.sidebar.text_input("Password", type="password", key="login_pass")
        if st.sidebar.button("Login"):
            user_email = authenticate_user(email, password)
            if user_email:
                st.session_state.user_email = user_email
                st.sidebar.success(f"🎉 Welcome back, {user_email}!")
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid email or password")
else:
    st.sidebar.markdown(f"👋 **Logged in as:** `{st.session_state.user_email}`")
    st.sidebar.success("✅ Session Active")
    if st.sidebar.button("Logout"):
        for key in ["user_email", "chat_history"]:
            st.session_state.pop(key, None)
        st.sidebar.info("Logged out successfully.")
        st.experimental_rerun()

# -----------------------------
# After-login: Chat UI
# -----------------------------
if "user_email" in st.session_state:
    user_id = st.session_state.user_email

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("💬 Chat History")
    for chat in st.session_state.chat_history:
        st.markdown(f"**🧑 You:** {chat['user']}")
        st.markdown(f"**🤖 AI:** {chat['ai']}")
        st.markdown("---")

    # Use a distinct key for the text input to avoid past widget-key issues
    user_input = st.text_input("✏️ Your message:", key="message_input")

    def submit_message(user_query: str):
        user_query = user_query.strip()
        if not user_query:
            return

        # Get memories (if mem_client available)
        context_text = ""
        try:
            if mem_client:
                search_memory = mem_client.search(query=user_query, user_id=user_id)
                results = search_memory.get("results", []) if isinstance(search_memory, dict) else search_memory.get('results', [])
                memories = [f"Memory: {m.get('memory', '')}" for m in results]
                context_text = "\n".join(memories)
        except Exception as e:
            # non-fatal: continue without memory
            context_text = ""

        system_prompt = f"""
You are a helpful AI Assistant.
User context (from memory):
{context_text}
User message: {user_query}
"""

        # Call Gemini via genai_client
        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=system_prompt
            )
            # response.text is expected, otherwise try to pull from .output or repr
            ai_response = getattr(response, "text", None) or (response.output if hasattr(response, "output") else str(response))
        except Exception as e:
            ai_response = f"⚠️ Error generating response: {e}"

        # Store to mem0 if available
        try:
            if mem_client:
                mem_client.add(user_id=user_id, messages=[
                    {"role": "user", "content": user_query},
                    {"role": "assistant", "content": ai_response},
                ])
        except Exception:
            pass  # non-fatal

        # Append to chat history (safe)
        st.session_state.chat_history.append({"user": user_query, "ai": ai_response})

        # Clear the text input value safely by setting same widget key
        try:
            st.session
