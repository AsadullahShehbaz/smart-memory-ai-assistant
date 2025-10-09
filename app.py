# app.py
# 🚀 Smart Memory AI Agent
# Streamlit + Gemini + Mem0 + Qdrant + MySQL Auth + Persistent Memory
# Clean, working version (2025 update)

import streamlit as st
from dotenv import load_dotenv
from mem0 import Memory
from google import genai
from qdrant_client import QdrantClient
import mysql.connector
import bcrypt
import os
import json
import warnings

# -----------------------------
# Basic Config
# -----------------------------
warnings.filterwarnings("ignore", category=ImportWarning)
load_dotenv()

# ✅ Load Secrets Safely
def get_secret(key, default=None):
    return (
        st.secrets[key]
        if key in st.secrets
        else os.getenv(key, default)
    )

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

# ✅ MySQL Setup
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

# ✅ Qdrant Client
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30.0,
    prefer_grpc=False
)

# ✅ Gemini Config
if not GEMINI_API_KEY:
    st.error("❌ GOOGLE_API_KEY not found in secrets or .env")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ✅ Mem0 Config
config = {
    "version": "v1.1",
    "embedder": {"provider": "gemini", "config": {"model": "models/text-embedding-004"}},
    "llm": {"provider": "gemini", "config": {"api_key": GEMINI_API_KEY, "model": "models/gemini-1.5-flash"}},
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
mem_client = Memory.from_config(config)

# -----------------------------
# Auth Functions
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
# Streamlit Layout
# -----------------------------
st.set_page_config(page_title="Smart Memory AI Agent", page_icon="🧠", layout="wide")

# -----------------------------
# Header
# -----------------------------
st.title("🧠 Smart Memory AI Agent")
st.markdown("""
**Powered by Gemini + Mem0 + Qdrant + MySQL + Neo4j**  
💬 Personalized Memory | ⚡ Persistent AI | ☁️ Cloud-Ready
""")

# -----------------------------
# Sidebar Auth System
# -----------------------------
st.sidebar.markdown("### 🔐 Authentication")

if "user_email" not in st.session_state:
    option = st.sidebar.radio("Choose an option:", ["Login", "Register"])

    if option == "Register":
        email = st.sidebar.text_input("Email", key="reg_email")
        password = st.sidebar.text_input("Password", type="password", key="reg_pass")
        if st.sidebar.button("Register"):
            if email and password:
                if register_user(email, password):
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
                st.rerun()
            else:
                st.sidebar.error("Invalid email or password")

else:
    st.sidebar.markdown(f"👋 **Logged in as:** `{st.session_state.user_email}`")
    st.sidebar.success("✅ Session Active")
    if st.sidebar.button("Logout"):
        for key in ["user_email", "chat_history"]:
            st.session_state.pop(key, None)
        st.sidebar.info("Logged out successfully.")
        st.rerun()

# -----------------------------
# Chat Section (After Login)
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

    # -----------------------------
    # Chat Handler Function
    # -----------------------------
    def submit_message():
        user_query = st.session_state.user_input.strip()
        if not user_query:
            return

        # 🔍 Retrieve relevant memories
        search_memory = mem_client.search(query=user_query, user_id=user_id)
        memories = [
            f"Memory: {mem.get('memory', '')}"
            for mem in search_memory.get('results', [])
        ]
        context_text = "\n".join(memories)

        # 🧠 Combine prompt
        prompt = f"""
        You are a helpful AI assistant with memory.
        Previous context:
        {context_text}
        User says: {user_query}
        """

        # 🚀 Generate Gemini response
        try:
            response = model.generate_content(prompt)
            ai_response = response.text if hasattr(response, "text") else "I generated a reply but couldn't extract text."
        except Exception as e:
            ai_response = f"⚠️ Gemini Error: {e}"

        # 💾 Store in memory
        mem_client.add(user_id=user_id, messages=[
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": ai_response},
        ])

        # 🧠 Update chat
        st.session_state.chat_history.append({"user": user_query, "ai": ai_response})
        st.session_state.user_input = ""

    # -----------------------------
    # Input Box + Button
    # -----------------------------
    user_input = st.text_input("✏️ Your message:", key="user_input")

    if st.button("Send ✈️"):
        if user_input.strip():
            submit_message()
            st.rerun()
        else:
            st.warning("Please enter a message before sending.")

    # -----------------------------
    # Sidebar Utilities
    # -----------------------------
    if st.sidebar.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.sidebar.success("Chat cleared.")

    if st.sidebar.button("🧠 Reset Memory"):
        mem_client.delete_all(user_id=user_id)
        st.sidebar.warning("Memory cleared for this user.")
