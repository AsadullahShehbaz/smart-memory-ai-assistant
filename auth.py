# auth.py
import bcrypt
import mysql.connector
import streamlit as st

def register_user(cursor, conn, email, password):
    try:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            (email, hashed_password.decode())
        )
        conn.commit()
        return True
    except mysql.connector.Error as err:
        st.sidebar.error(f"MySQL Error: {err}")
        return False

def authenticate_user(cursor, email, password):
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return user["email"]
    return None
