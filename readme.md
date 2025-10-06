# AgenticAI 🤖

**Tagline:** Personalized AI Chat Assistant with Memory and Context Awareness

---

## Project Overview

**AgenticAI** is a Gemini-powered AI chat assistant that remembers user interactions, delivering **personalized and context-aware conversations**.  
Built with **Streamlit**, **mem0ai**, and **Qdrant**, it provides a sleek ChatGPT-style interface with per-user persistent memory.

- **Persistent User Memory:** Each user has a unique ID and memory stored in Qdrant.
- **Context-Aware Responses:** AI recalls past conversations for smarter replies.
- **Gemini LLM Integration:** Uses Gemini 2.5-flash model for high-quality AI responses.
- **Beginner-Friendly Interface:** Chat at the bottom, conversation history on top.

---

## Demo

![Demo Screenshot](demo_screenshot.png)  
*(Replace with your own screenshot of the chat interface)*

---

## Features

- User Registration & Login for persistent sessions  
- Memory-powered conversation context  
- ChatGPT-style UI with scrolling chat history  
- Gemini LLM integration for AI responses  
- Easy to deploy with Streamlit  

---

## Tech Stack

- **Frontend:** Streamlit  
- **AI:** Gemini API (`genai` Python SDK)  
- **Memory:** mem0ai + Qdrant vector DB  
- **Environment Management:** Python 3.10+, dotenv for API keys  

---

## Installation

1. Clone the repo:

```bash
git clone https://github.com/<your-username>/AgenticAI.git
cd AgenticAI
```
2.Create virtual environment & install dependencies:

```python
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```
