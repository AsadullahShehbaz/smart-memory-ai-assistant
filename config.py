# config.py
import os
from dotenv import load_dotenv
from mem0 import Memory
from google import genai
from qdrant_client import QdrantClient

load_dotenv()

# -----------------------------
# Secrets helper
# -----------------------------
def get_secret(key, default=None):
    import streamlit as st
    return st.secrets[key] if key in st.secrets else os.getenv(key, default)

# -----------------------------
# API Keys / DB Config
# -----------------------------
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
# Qdrant Client
# -----------------------------
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=30.0,
    prefer_grpc=False
)

# -----------------------------
# Gemini Client
# -----------------------------
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    raise ValueError("Missing GEMINI_API_KEY")

# -----------------------------
# Mem0 Client
# -----------------------------
mem_config = {
    "version": "v1.1",
    "embedder": {"provider": "gemini", "config": {"model": "models/text-embedding-004"}},
    "llm": {"provider": "gemini", "config": {"api_key": GEMINI_API_KEY, "model": "models/gemini-2.5-flash"}},
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": NEO4J_URI, "username": NEO4J_USERNAME, "password": NEO4J_PASSWORD},
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {"url": QDRANT_URL, "api_key": QDRANT_API_KEY, "collection_name": "memory_agent", "embedding_model_dims": 768},
    },
}

try:
    mem_client = Memory.from_config(mem_config)
except Exception:
    mem_client = None
