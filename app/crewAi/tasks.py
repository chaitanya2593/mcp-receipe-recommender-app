from crewai import Task


def build_extract_task(agent) -> Task:
    return Task(
        description=(
            "Extract fields from the user input below and return ONLY compact JSON with this schema:\n"
            '{"item_name":"string","place":"string|null"}\n\n'
            "Rules:\n"
            "- item_name: the product/dish/item requested by user\n"
            "- place: city/location if present, otherwise null\n"
            "- No markdown, no extra keys, no explanation\n\n"
            "User input:\n{user_text}"
        ),
        expected_output='Strict JSON only: {"item_name":"...","place":"...|null"}',
        agent=agent,
    )


def build_weather_task(agent) -> Task:
    return Task(
        description=(
            "Look up the current weather for **{place}**.\n"
            "Steps:\n"
            "1. Use the `get_city_coordinates` tool to get latitude and longitude for {place}.\n"
            "2. Use the `get_forecast` tool with those coordinates to get the current weather.\n"
            "Return a concise summary with temperature, conditions, humidity, and wind speed."
        ),
        expected_output=(
            "A short weather summary for {place} with temperature, conditions, humidity, and wind speed."
        ),
        agent=agent,
    )


def build_recipe_task(agent) -> Task:
    return Task(
        description=(
            "You are given the following user request: **{item_name}**.\n"
            "Current weather context for {place} is available from previous task output.\n\n"
            "Create a concise recipe including:\n"
            "- Dish name\n"
            "- Ingredients\n"
            "- Simple cooking instructions (max 5 lines)\n"
            "- Estimated prep/cook time\n"
            "- A brief note on why this suits the weather"
        ),
        expected_output=(
            "A compact, practical recipe for '{item_name}' tailored to weather in {place}."
        ),
        agent=agent,
    )


def build_places_task(agent) -> Task:
    return Task(
        description=(
            "Find places in **{place}** where the user can buy/order **{item_name}** or close matches.\n"
            "Use available OSM MCP tools to search relevant places.\n"
            "Return 3 options with: place name, area/address hint, type, and one-line match reason."
        ),
        expected_output=(
            "A concise list of 3  places in {place} relevant to '{item_name}' with location address. It should nicely formatted and easy to read for the user."
        ),
        agent=agent,
    )

