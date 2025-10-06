# app.py
# Streamlit AI Agentic Chat App with ChatGPT-style interface + MySQL Auth + Qdrant + Gemini + Persistent Memory

import streamlit as st
from dotenv import load_dotenv
from mem0 import Memory
from google import genai
from qdrant_client import QdrantClient
import mysql.connector
import bcrypt
import os
import uuid
import json
import warnings
from pathlib import Path

# -----------------------------
# Basic Config
# -----------------------------
warnings.filterwarnings("ignore", category=ImportWarning)
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

# MySQL (Railway)
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")

# -----------------------------
# MySQL Connection
# -----------------------------
conn = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB
)
cursor = conn.cursor(dictionary=True)

# Create users table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# -----------------------------
# Qdrant + Gemini Config
# -----------------------------
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
genai_client = genai.Client(api_key=GEMINI_API_KEY)

config = {
    "version": "v1.1",
    "embedder": {"provider": "gemini", "config": {"model": "models/text-embedding-004"}},
    "llm": {"provider": "gemini", "config": {"api_key": GEMINI_API_KEY, "model": "models/gemini-2.5-flash"}},
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "url": QDRANT_URL,
            "api_key": QDRANT_API_KEY,
            "collection_name": "memory_agent",
            "embedding_model_dims": 768
        }
    },
}
mem_client = Memory.from_config(config)

# -----------------------------
# User Auth Functions (MySQL)
# -----------------------------
def register_user(email, password):
    try:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        user_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO users (email, password_hash, user_id) VALUES (%s, %s, %s)",
                       (email, hashed_password.decode(), user_id))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print("Error:", err)
        return False


def authenticate_user(email, password):
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user["user_id"]
    return None

# -----------------------------
# Streamlit Layout
# -----------------------------
st.set_page_config(page_title="Memory AI Agent", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
    body, .stApp { background-color: #0F111A; color: #E0E0E0; }
    footer {visibility: hidden;}
    .chat-container { max-height: 70vh; overflow-y: auto; padding: 10px; }
    .user-msg { background: linear-gradient(135deg,#6EE7B7,#3B82F6); color:white; padding:12px; border-radius:15px; margin:5px 0; max-width:70%; float:right; clear:both;}
    .ai-msg { background: linear-gradient(135deg,#FDE68A,#F59E0B); color:black; padding:12px; border-radius:15px; margin:5px 0; max-width:70%; float:left; clear:both;}
    .input-container { position: fixed; bottom: 10px; width: 90%; left: 5%; display: flex; background-color: #1F2937; padding:10px; border-radius:10px; }
    .stTextInput>div>div>input { background-color:#374151; color:#E0E0E0; border-radius:10px; padding:10px; border:none; width:100%; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🚀 Smart Memory AI Agent")
st.markdown(
    """
    **Powered by Gemini + Mem0 + Qdrant DB + MySQL**  
    🧠 Personalized Memory | 🤖 Persistent Agent | ☁️ Cloud Database (Railway)
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Login / Register Section
# -----------------------------
st.sidebar.markdown("🤖 **Welcome to Smart Memory AI Agent — your personalized assistant that learns, remembers, and evolves with every chat!**")

if "user_id" not in st.session_state:
    option = st.sidebar.radio("Choose an option:", ["Login", "Register"])

    if option == "Register":
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Register"):
            if email and password:
                if register_user(email, password):
                    st.sidebar.success("✅ Registered successfully! Please login.")
                else:
                    st.sidebar.error("❌ Email already exists or DB error.")

    elif option == "Login":
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user_id = authenticate_user(email, password)
            if user_id:
                st.session_state.user_id = user_id
                st.sidebar.success("🎉 Login successful!")
            else:
                st.sidebar.error("Invalid email or password")

# -----------------------------
# Chat Section (After Login)
# -----------------------------
if "user_id" in st.session_state:
    user_id = st.session_state.user_id

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display Chat History
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for chat in st.session_state.chat_history:
            st.markdown(f'<div class="user-msg"><b>You:</b> {chat["user"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-msg"><b>AI:</b> {chat["ai"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Input Box
    def submit_message():
        user_query = st.session_state.user_input.strip()
        if not user_query:
            return

        # Memory search
        search_memory = mem_client.search(query=user_query, user_id=user_id)
        memories = [f"ID:{mem.get('id')} \nMemory:{mem.get('memory')}" for mem in search_memory.get('results')]

        system_prompt = f"""
        You are a helpful AI Assistant.
        Context about the user:
        {json.dumps(memories)}
        User question:
        {user_query}
        """
        response = genai_client.models.generate_content(model="gemini-2.5-flash", contents=system_prompt)
        ai_response = response.text

        # Save conversation
        mem_client.add(user_id=user_id, messages=[
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": ai_response}
        ])
        st.session_state.chat_history.append({"user": user_query, "ai": ai_response})
        st.session_state.user_input = ""

    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    st.text_input("", key="user_input", placeholder="Type your message and press Enter...", on_change=submit_message)
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar Buttons
    if st.sidebar.button("Logout"):
        st.session_state.pop("user_id", None)
        st.session_state.pop("chat_history", None)
        st.success("Logged out successfully!")

    if st.sidebar.button("Clear Chat History"):
        st.session_state.chat_history = []

    if st.sidebar.button("Clear Memory"):
        mem_client.clear(user_id=user_id)
        st.success("Memory cleared successfully!")
