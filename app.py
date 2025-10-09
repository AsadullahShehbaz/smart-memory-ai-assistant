# app.py
import streamlit as st
import mysql.connector
from config import GEMINI_API_KEY, mem_client, genai_client, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
from auth import register_user, authenticate_user

# -----------------------------
# MySQL Setup
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
# Streamlit Setup
# -----------------------------
st.set_page_config(page_title="Smart Memory AI Agent", page_icon="🧠", layout="wide")
st.title("🧠 Smart Memory AI Agent")
st.markdown("**Powered by Gemini + Mem0 + Qdrant + MySQL + Neo4j**")

# -----------------------------
# Sidebar Auth
# -----------------------------
st.sidebar.markdown("### 🔐 Authentication")

if "user_email" not in st.session_state:
    option = st.sidebar.radio("Choose:", ["Login", "Register"])

    if option == "Register":
        email = st.sidebar.text_input("Email", key="reg_email")
        password = st.sidebar.text_input("Password", type="password", key="reg_pass")
        if st.sidebar.button("Register"):
            if email and password:
                register_user(cursor, conn, email, password)
            else:
                st.sidebar.warning("Enter both fields.")

    elif option == "Login":
        email = st.sidebar.text_input("Email", key="login_email")
        password = st.sidebar.text_input("Password", type="password", key="login_pass")
        if st.sidebar.button("Login"):
            user_email = authenticate_user(cursor, email, password)
            if user_email:
                st.session_state.user_email = user_email
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid email or password")

else:
    st.sidebar.markdown(f"👋 Logged in as `{st.session_state.user_email}`")
    if st.sidebar.button("Logout"):
        for k in ["user_email", "chat_history"]:
            st.session_state.pop(k, None)
        st.experimental_rerun()

# -----------------------------
# Chat Section
# -----------------------------
if "user_email" in st.session_state:
    user_id = st.session_state.user_email

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("💬 Chat")
    user_query = st.text_area("Your message:", key="message_input", height=100)

    def submit_message(query):
        query = query.strip()
        if not query:
            return

        context_text = ""
        if mem_client:
            try:
                search_memory = mem_client.search(query=query, user_id=user_id)
                results = search_memory.get("results", []) if isinstance(search_memory, dict) else []
                context_text = "\n".join([f"Memory: {m.get('memory', '')}" for m in results])
            except Exception:
                pass

        prompt = f"You are a helpful AI assistant.\nPrevious context:\n{context_text}\nUser: {query}"

        try:
            response = genai_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            ai_response = getattr(response, "text", str(response))
        except Exception as e:
            ai_response = f"⚠️ Gemini Error: {e}"

        if mem_client:
            try:
                mem_client.add(user_id=user_id, messages=[
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": ai_response},
                ])
            except Exception:
                pass

        st.session_state.chat_history.append({"user": query, "ai": ai_response})
        st.session_state["message_input"] = ""

    if st.button("Send ✈️"):
        if user_query.strip():
            submit_message(user_query)
            st.experimental_rerun()
        else:
            st.warning("Please type a message.")
            
    if st.sidebar.button("🧹 Clear Chat"):
        st.session_state.chat_history = []
        st.sidebar.success("Chat cleared.")

    if st.sidebar.button("🧠 Reset Memory"):
        if mem_client and hasattr(mem_client, "delete_all"):
            mem_client.delete_all(user_id=user_id)
            st.sidebar.warning("Memory cleared.")
