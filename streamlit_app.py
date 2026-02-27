import os
import json
import asyncio
import re
import ast
import streamlit as st
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path
import httpx

load_dotenv()

# Azure OpenAI client setup
if os.getenv("AZURE_OPENAI_API_KEY"):
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
    )

st.set_page_config(page_title="Cuisine Recommender (LLM)", page_icon="🤖")
st.title("🤖 Weather based Dish Recommender")

SYSTEM = """You extract structured fields from the user's message.
Return ONLY a compact JSON object with the fields:
{ "cuisine": string, "city": string | null }

Rules:
- cuisine: from any common cuisine mentioned ("indian", "italian", ...). Capitalize first letter. Also the cusine can include specifactions like "spicy indian", "vegan italian" etc. In that case return the full specification as cuisine.
- city: if a city is present after words like 'in' or 'for', use it; else return null.
- No extra text. JSON only.
"""

async def extract_fields(user_text: str, default_city="Munich"):
    prompt = f"User message: {user_text}\nReturn JSON as specified."
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt}
    ]
    resp = await client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=messages
    )
    out = resp.choices[0].message.content
    data = json.loads(out)
    cuisine = (data.get("cuisine") or "").strip()
    if data.get("city") is None:
        st.info("No city detected in the message, defaulting to Munich.")
        city = default_city
    else:
        city = (data.get("city") or "")
    return cuisine, city

async def get_weather_from_mcp(city: str):
    """Fetch weather data using MCP weather server with Open-Meteo API"""
    project_root = Path(__file__).resolve().parent

    server_params = StdioServerParameters(
        command="python",
        args=[str(project_root / "app/servers/weather_server.py")],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # First, get city coordinates using MCP tool
                coords_result = await session.call_tool(
                    "get_city_coordinates",
                    arguments={"city": city}
                )

                # Parse coordinates from result
                coords_text = coords_result.content[0].text if coords_result.content else "{}"
                coords = ast.literal_eval(coords_text)
                latitude = coords.get("latitude", 48.1351)
                longitude = coords.get("longitude", 11.5820)

                # Then get forecast with those coordinates
                forecast_result = await session.call_tool(
                    "get_forecast",
                    arguments={"latitude": latitude, "longitude": longitude}
                )

                # Parse forecast from result
                forecast_text = forecast_result.content[0].text if forecast_result.content else "{}"
                weather_info = ast.literal_eval(forecast_text)

                return weather_info
    except Exception as e:
        # Fallback to mock data
        return {
            "current_temperature_c": 20,
            "conditions": "Partly cloudy",
            "humidity_percent": 60
        }

async def get_recommendations_with_gpt(cuisine: str, weather_info: dict, city: str):
    """Use GPT to recommend dishes based on cuisine type and weather conditions"""
    # Extract weather info with fallback values
    temp = weather_info.get('current_temperature_c', weather_info.get('temperature_c', 20))
    conditions = weather_info.get('conditions', 'Unknown')
    humidity = weather_info.get('humidity_percent', weather_info.get('humidity', 60))

    prompt = f"""Based on the following information, recommend 3 specific dishes from {cuisine} cuisine 
that would be perfect for the current weather conditions in {city}.

Weather conditions:
- Temperature: {temp}°C
- Conditions: {conditions}
- Humidity: {humidity}%

Consider:
- If it's cold, suggest warming, hearty dishes
- If it's hot, suggest lighter, refreshing options
- Match the dishes to the weather mood
- Suggest the best places/restaurants in {city} to eat each dish. Remember the resaurant should be in the city mentioned in the user query. 

Return ONLY a JSON array in this exact format - no explanations, just the array:
[
  "Dish 1 - Restaurant 1 & Restaurant 2 & Restaurant 3",
  "Dish 2 - Restaurant 1 & Restaurant 2 & Restaurant 3",
  "Dish 3 - Restaurant 1 & Restaurant 2 & Restaurant 3"
]"""

    messages = [{"role": "user", "content": prompt}]
    resp = await client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=messages
    )
    content = resp.choices[0].message.content.strip()
    recommendations = json.loads(content)
    return recommendations

async def process_recommendation(user_text: str):
    """Process user request and generate recommendations"""
    cuisine, city = await extract_fields(user_text)
    st.info(f"Extracted cuisine: {cuisine}, city: {city}")
    if not cuisine:
        return None, None, None, None

    # Get weather for the city using MCP weather server
    weather_info = await get_weather_from_mcp(city)

    # Get dish recommendations using GPT based on cuisine and weather
    recommendations = await get_recommendations_with_gpt(cuisine, weather_info, city)

    return cuisine, city, weather_info, recommendations


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
                cuisine, city, weather_info, recommendations = asyncio.run(process_recommendation(user_text))

                if not cuisine:
                    st.markdown("I couldn't detect a cuisine. Please try **recommend italian** etc.")
                else:
                    # Format the recommendations
                    recos = "\n".join([f"- {d}" for d in recommendations])

                    # Extract weather info with fallback values
                    temp = weather_info.get('current_temperature_c', weather_info.get('temperature_c', 'N/A'))
                    conditions = weather_info.get('conditions', 'Unknown')
                    humidity = weather_info.get('humidity_percent', weather_info.get('humidity', 'N/A'))

                    reply = (
                        f"**Cuisine:** {cuisine}  \n"
                        f"**City:** {city}  \n"
                        f"**Weather:** {temp}°C, {conditions} (Humidity: {humidity}%)\n\n"
                        f"**Weather-matched dish recommendations:**\n{recos}"
                    )
                    st.markdown(reply)
                    st.session_state.messages.append({"role":"assistant","content":reply})

            except Exception as e:
                st.error(f"Error: {e}")
