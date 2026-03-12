import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))


import re
import streamlit as st
from dotenv import load_dotenv
from app.crewai_agents import RecipeCrew

load_dotenv()

st.set_page_config(page_title="Cuisine Recommender (LLM)", page_icon="🤖")
st.title("🤖 Weather based Dish Recommender")

SYSTEM = """You extract structured fields from the user's message.\nReturn ONLY a compact JSON object with the fields:\n{ \"cuisine\": string, \"city\": string | null }\n\nRules:\n- cuisine: from any common cuisine mentioned (\"indian\", \"italian\", ...). Capitalize first letter. Also the cusine can include specifactions like \"spicy indian\", \"vegan italian\" etc. In that case return the full specification as cuisine.\n- city: if a city is present after words like 'in' or 'for', use it; else return null.\n- No extra text. JSON only.\n"""

# Utility: detect URL in text
def extract_url(text):
    url_pattern = r"https?://[\w.-]+(?:/[\w.-]*)*\??(?:[\w.-=&%]+)?"
    match = re.search(url_pattern, text)
    return match.group(0) if match else None

# Instantiate the CrewAI orchestrator
recipe_crew = RecipeCrew()

def extract_fields(user_text: str, default_city="Munich"):
    # This function should be replaced with a CrewAI-based extraction if desired
    # For now, keep as a placeholder for extracting cuisine and city from user input
    return user_text, default_city  # Now treat user_text as the dish query

async def process_user_input(user_text: str):
    url = extract_url(user_text)
    if url:
        st.info(f"Detected URL: {url}. Fetching content from the internet...")
        # You can implement CrewAI-based URL fetch if needed
        return {"mode": "url", "url": url, "content": "URL fetch not implemented in CrewAI version."}
    else:
        dish_query, place = extract_fields(user_text)
        result = recipe_crew.run(dish_query, place)
        if result.get("error"):
            return {"mode": "none"}
        return {
            "mode": "recipe",
            "dish_query": result["dish_query"],
            "city": result["place"],
            "weather_info": result["weather"],
            "recipe": result["recipe"]
        }

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
        with st.spinner("Processing your request…"):
            import asyncio
            result = asyncio.run(process_user_input(user_text))
            if result["mode"] == "url":
                url = result["url"]
                content = result["content"]
                st.markdown(f"**Fetched content from:** {url}")
                st.code(str(content)[:1000])
                st.session_state.messages.append({"role":"assistant","content":f"Fetched content from {url}:\n\n{str(content)[:1000]}"})
            elif result["mode"] == "recipe":
                dish_query = result["dish_query"]
                city = result["city"]
                weather_info = result["weather_info"]
                recipe = result["recipe"]
                if isinstance(weather_info, dict):
                    temp = weather_info.get('current_temperature_c', weather_info.get('temperature_c', 'N/A'))
                    conditions = weather_info.get('conditions', 'Unknown')
                    humidity = weather_info.get('humidity_percent', weather_info.get('humidity', 'N/A'))
                else:
                    temp = conditions = humidity = 'N/A'
                reply = (
                    f"**Dish Query:** {dish_query}  \n"
                    f"**City:** {city}  \n"
                    f"**Weather:** {temp}°C, {conditions} (Humidity: {humidity}%)\n\n"
                    f"**Recipe:**\n{recipe}"
                )
                st.markdown(reply)
                st.session_state.messages.append({"role":"assistant","content":reply})
            else:
                st.markdown("I couldn't detect a cuisine or a valid URL. Please try **recommend italian** or provide a link.")
