"""System prompts and task builders for the LangChain agents.

The CrewAI role/goal/backstory triples are folded into system prompts;
the CrewAI Task descriptions become task-builder functions whose output
is passed to the agent/chain as the human message.
"""

EXTRACTOR_SYSTEM_PROMPT = (
    "You are an information extraction specialist. You output compact JSON only "
    "and avoid adding commentary. Your goal is to extract the requested item name "
    "and place from user text as strict JSON."
)

WEATHER_SYSTEM_PROMPT = (
    "You are a Weather Specialist - a meteorology expert with direct access to "
    "real-time weather APIs via tools. You always look up the city coordinates "
    "first, then fetch the current forecast. Your goal is to retrieve accurate, "
    "up-to-date weather information for a given city using the available weather tools."
)

CHEF_SYSTEM_PROMPT = (
    "You are a World-Class Chef - a culinary expert with encyclopaedic knowledge "
    "of global cuisines. You craft recipes that are delicious, clearly explained, "
    "and appropriate for the season and weather. Your goal is to generate detailed, "
    "practical recipes tailored to the user's request and, when available, the "
    "current local weather conditions."
)

PLACE_FINDER_SYSTEM_PROMPT = (
    "You are a Local Place Finder - a local discovery specialist. You use map/place "
    "tools to identify relevant shops, restaurants, and markets with practical "
    "location hints. Your goal is to find nearby places in a city that are likely "
    "to offer the requested product or dish using the OSM-based tools."
)


def extract_task(user_text: str) -> str:
    return (
        "Extract fields from the user input below and return ONLY compact JSON with this schema:\n"
        '{"item_name":"string","place":"string|null"}\n\n'
        "Rules:\n"
        "- item_name: the product/dish/item requested by user\n"
        "- place: city/location if present, otherwise null\n"
        "- No markdown, no extra keys, no explanation\n\n"
        f"User input:\n{user_text}"
    )


def weather_task(place: str) -> str:
    return (
        f"Look up the current weather for **{place}**.\n"
        "Steps:\n"
        f"1. Use the `get_city_coordinates` tool to get latitude and longitude for {place}.\n"
        "2. Use the `get_forecast` tool with those coordinates to get the current weather.\n"
        "Return a concise summary with temperature, conditions, humidity, and wind speed."
    )


def recipe_task(item_name: str, place: str, weather_summary: str | None) -> str:
    weather_context = weather_summary or "No weather context available."
    return (
        f"You are given the following user request: **{item_name}**.\n"
        f"Current weather context for {place}:\n{weather_context}\n\n"
        "Create a concise recipe including:\n"
        "- Dish name\n"
        "- Ingredients\n"
        "- Simple cooking instructions (max 5 lines)\n"
        "- Estimated prep/cook time\n"
        "- A brief note on why this suits the weather"
    )


def places_task(item_name: str, place: str) -> str:
    return (
        f"Find places in **{place}** where the user can buy/order **{item_name}** or close matches.\n"
        "Use the available OSM tools to search relevant places.\n"
        "Return 3 options with: place name, area/address hint, type, and one-line match reason. "
        "It should be nicely formatted and easy to read for the user."
    )
