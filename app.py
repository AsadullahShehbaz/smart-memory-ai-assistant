# app.py
# 🚀 Smart Memory AI Agent
# Streamlit + Gemini + Mem0 + Qdrant + MySQL Auth + Persistent Memory
# Clean Version (No Custom CSS for Input Section)

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
from pathlib import Path

# -----------------------------
# Basic Config
# -----------------------------
warnings.filterwarnings("ignore", category=ImportWarning)
load_dotenv()

# Get secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
QDRANT_API_KEY = st.secrets["QDRANT_API_KEY"]
QDRANT_URL = st.secrets["QDRANT_URL"]
NEO4J_URI = st.secrets["NEO4J_URI"]
NEO4J_USERNAME = st.secrets["NEO4J_USERNAME"]
NEO4J_PASSWORD = st.secrets["NEO4J_PASSWORD"]

# MySQL Connection
conn = mysql.connector.connect(
    host=st.secrets["MYSQL_HOST"],
    port=st.secrets["MYSQL_PORT"],
    user=st.secrets["MYSQL_USER"],
    password=st.secrets["MYSQL_PASSWORD"],
    database=st.secrets["MYSQL_DB"]
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

# -----------------------------
# Qdrant + Gemini Config
# -----------------------------
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30.0,
    prefer_grpc=False
)

genai_client = genai.Client(api_key=GEMINI_API_KEY)

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
st.set_page_config(page_title="Smart Memory AI Agent", page_icon="🤖", layout="wide")

# Basic Theme
st.markdown("""
<style>
body, .stApp {
    background-color: #0F111A;
    color: #E0E0E0;
}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.title("🧠 Smart Memory AI Agent")
st.markdown("""
**Powered by Gemini + Mem0 + Qdrant DB + MySQL + Neo4j Graph DB**  
💬 Personalized Memory | ⚡ Persistent AI | ☁️ Cloud-Ready
""")

# -----------------------------
# Sidebar Auth System
# -----------------------------
st.sidebar.markdown("🤖 **Welcome to Smart Memory AI Agent**")

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
    st.sidebar.markdown(f"👋 **Logged in as {st.session_state.user_email}**")
    st.sidebar.success("Session Active ✅")
    if st.sidebar.button("Logout"):
        for key in ["user_email", "chat_history"]:
            st.session_state.pop(key, None)
        st.sidebar.info("Logged out successfully!")
        st.rerun()

# -----------------------------
# Chat Section (After Login)
# -----------------------------
if "user_email" in st.session_state:
    user_id = st.session_state.user_email

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    st.write("### 💬 Chat History")
    for chat in st.session_state.chat_history:
        st.markdown(f"**You:** {chat['user']}")
        st.markdown(f"**AI:** {chat['ai']}")
        st.markdown("---")

    # Message handler
    def submit_message():
        user_query = st.session_state.user_input.strip()
        if not user_query:
            return

        search_memory = mem_client.search(query=user_query, user_id=user_id)
        memories = [f"Memory: {mem.get('memory')}" for mem in search_memory.get('results', [])]
        system_prompt = f"""
        You are a helpful AI Assistant.
        User context (from previous chats):
        {json.dumps(memories, indent=2)}
        User message: {user_query}
        """
        response = genai_client.models.generate_content(model="gemini-2.5-flash", contents=system_prompt)
        ai_response = response.text

        mem_client.add(user_id=user_id, messages=[
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": ai_response},
        ])

        st.session_state.chat_history.append({"user": user_query, "ai": ai_response})
        st.session_state.user_input = ""

    # -----------------------------
    # Simple Input + Send Button
    # -----------------------------
    st.write("### ✍️ Type your message")
    user_input = st.text_input("Your message:", key="user_input")

    if st.button("Send"):
        if user_input.strip():
            submit_message()
        else:
            st.warning("Please enter a message before sending.")

    # Sidebar utility
    if st.sidebar.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.sidebar.success("Chat cleared.")
