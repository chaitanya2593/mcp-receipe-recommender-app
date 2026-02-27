import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

# Azure OpenAI client setup
if os.getenv("AZURE_OPENAI_API_KEY"):
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )



API_BASE = "http://localhost:8080"  # your FastAPI server.py

st.set_page_config(page_title="Cuisine Recommender (LLM)", page_icon="🤖")
st.title("🤖 Chat: Weather‑Aware Dish Recommender")

SYSTEM = """You extract structured fields from the user's message.
Return ONLY a compact JSON object with the fields:
{ "cuisine": string, "city": string | null }

Rules:
- cuisine: from any common cuisine mentioned ("indian", "italian", ...). Capitalize first letter.
- city: if a city is present after words like 'in' or 'for', use it; else return null.
- No extra text. JSON only.
"""

def extract_fields(user_text: str, default_city="Munich"):
    prompt = f"User message: {user_text}\nReturn JSON as specified."
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt}
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0
    )
    out = resp.choices[0].message.content
    data = json.loads(out)
    cuisine = (data.get("cuisine") or "").strip()
    city = (data.get("city") or "") or default_city
    return cuisine, city

def call_recommend(cuisine: str, city: str):
    payload = {"cuisine": cuisine, "city": city}
    r = requests.post(f"{API_BASE}/tools/recommend", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

# ---- Chat history ----
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content":
            "Hi! Try phrases like **recommend italian**, or **recommend thai in Barcelona**."}
    ]

# Render history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("Type your request…")

if user_text:
    st.session_state.messages.append({"role":"user","content":user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Let me parse that and check the weather…"):
            try:
                cuisine, city = extract_fields(user_text)

                if not cuisine:
                    st.markdown("I couldn't detect a cuisine. Please try **recommend italian** etc.")
                else:
                    data = call_recommend(cuisine, city)
                    recos = "\n".join([f"- {d}" for d in data["recommendations"]])
                    reply = (
                        f"**Cuisine:** {data['cuisine']}  \n"
                        f"**City:** {data['city']}  \n"
                        f"**Weather:** {data['temperature_c']} °C, {data['conditions']}\n\n"
                        f"**Top 3 dishes:**\n{recos}"
                    )
                    st.markdown(reply)
                    st.session_state.messages.append({"role":"assistant","content":reply})

            except Exception as e:
                st.error(f"Error: {e}")
