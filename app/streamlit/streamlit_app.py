import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import re
import streamlit as st
from dotenv import load_dotenv
from app.agent import RecipeAgent

load_dotenv()

st.set_page_config(page_title="Cuisine Recommender (LLM)", page_icon="🍽️")
st.title("Weather based Dish Recommender")

# Utility: detect URL in text
def extract_url(text: str) -> str | None:
    url_pattern = r"https?://[\w.-]+(?:/[\w.-]*)*\??(?:[\w.=&%-]+)?"
    match = re.search(url_pattern, text)
    return match.group(0) if match else None


# Instantiate orchestrator
recipe_crew = RecipeAgent()


# ---- Session state ----
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! Tell me what you want and where (example: **pizza in Berlin**)."
        }
    ]

if "pending_request" not in st.session_state:
    st.session_state.pending_request = None


# ---- Sidebar: dietary preferences ----
DIET_OPTIONS = [
    "Vegetarian", "Vegan", "Pescatarian", "Halal", "Kosher",
    "Gluten-free", "Dairy-free", "Nut-free", "Low-carb",
]
with st.sidebar:
    st.header("Preferences")
    diet_selected = st.multiselect(
        "Dietary preferences",
        options=DIET_OPTIONS,
        default=st.session_state.get("diet_selected", []),
        key="diet_selected",
    )
    other_notes = st.text_input(
        "Other allergies / notes",
        value=st.session_state.get("other_notes", ""),
        key="other_notes",
        placeholder="e.g. no cilantro, mild spice",
    )

preferences = list(diet_selected)
if other_notes.strip():
    preferences.append(other_notes.strip())


# Render history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])


user_text = st.chat_input("Type your request...")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Processing your request..."):
            url = extract_url(user_text)
            if url:
                reply = f"Detected URL: {url}. URL flow is not implemented in this mode."
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            else:
                pending = st.session_state.pending_request

                # Step 1: collect item + place and ask action
                if not pending:
                    extracted = recipe_crew.extract_item_place(user_text, default_city="Munich")
                    item_name = extracted.get("item_name", "").strip()
                    place = extracted.get("place", "Munich").strip() or "Munich"
                    if not item_name:
                        reply = "Please tell me an item and city, for example: **ramen in Tokyo**."
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                    else:
                        st.session_state.pending_request = {"item_name": item_name, "place": place}
                        precheck = recipe_crew.run(item_name=item_name, place=place, action=None)
                        supervisor_prompt = precheck.get(
                            "supervisor_prompt",
                            f"Got it - you want '{item_name}' in {place}. Would you like to **order** or **prepare**?",
                        )
                        weather_info = precheck.get("weather", {})
                        conditions = weather_info.get("conditions", "Unknown") if isinstance(weather_info, dict) else "Unknown"
                        reply = (
                            f"**Item:** {item_name}  \n"
                            f"**City:** {place}  \n"
                            f"**Weather context:** {conditions}\n\n"
                            f"{supervisor_prompt}"
                        )
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})

                # Step 2: route by action
                else:
                    action = user_text.strip().lower()
                    if action not in {"order", "prepare"}:
                        reply = "Please reply with exactly one option: **order** or **prepare**."
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                    else:
                        item_name = pending["item_name"]
                        place = pending["place"]
                        result = recipe_crew.run(
                            item_name=item_name,
                            place=place,
                            action=action,
                            preferences=preferences,
                            stream=True,
                        )

                        weather_info = result.get("weather", {})
                        conditions = weather_info.get("conditions", "Unknown") if isinstance(weather_info, dict) else "Unknown"

                        header = (
                            f"**Item:** {item_name}  \n"
                            f"**City:** {place}  \n"
                            f"**Weather:** {conditions}\n\n"
                        )
                        if preferences:
                            header += f"**Preferences:** {', '.join(preferences)}\n\n"

                        if action == "prepare":
                            header += "**Recipe:**\n"
                            stream_iter = result.get("recipe_stream")
                        else:
                            header += "**Places to order/buy nearby:**\n"
                            stream_iter = result.get("places_stream")

                        st.markdown(header)
                        streamed_text = st.write_stream(stream_iter) if stream_iter else ""
                        full_reply = header + (streamed_text or "")
                        st.session_state.messages.append({"role": "assistant", "content": full_reply})
                        st.session_state.pending_request = None


st.markdown(
    """
    <style>
    .tiny-footer {
        position: fixed;
        bottom: 0.35rem;
        left: 0;
        right: 0;
        text-align: center;
        font-size: 0.70rem;
        color: #888;
        opacity: 0.9;
        z-index: 999;
        pointer-events: auto;
    }
    </style>
    <div class="tiny-footer">
      Built by <a href="https://www.linkedin.com/in/v-s-chaitanya-madduri-2886447a/" target="_blank">Chaitanya Madduri</a>.
      Powered by Python + Streamlit + Claude (Azure Foundry) + Skills + MCP. Streaming enabled.
    </div>
    """,
    unsafe_allow_html=True,
)