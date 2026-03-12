import os
from typing import Any, Dict

from crewai import Agent, Task, Crew
from crewai.mcp import MCPServerStdio
from crewai import LLM


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def gpt_client() -> LLM:
    """Construct a CrewAI-compatible LLM client for Azure OpenAI."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise ValueError("Missing environment variable: AZURE_OPENAI_DEPLOYMENT")
    return LLM(
        model="azure/" + deployment,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )


llm = gpt_client()


# ---------------------------------------------------------------------------
# MCP server configs (Stdio — local processes)
# ---------------------------------------------------------------------------

weather_mcp = MCPServerStdio(
    command="python",
    args=["app/servers/weather_server.py"],
)

fetch_mcp = MCPServerStdio(
    command="python",
    args=["-m", "mcp_server_fetch"],
)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

weather_agent = Agent(
    role="Weather Specialist",
    goal=(
        "Retrieve accurate, up-to-date weather information for a given city "
        "using the available MCP weather tools."
    ),
    backstory=(
        "You are a meteorology expert with direct access to real-time weather APIs. "
        "You always look up the city coordinates first, then fetch the current forecast."
    ),
    llm=llm,
    verbose=True,
    mcps=[weather_mcp],
)

recipe_agent = Agent(
    role="World-Class Chef",
    goal=(
        "Generate detailed, practical recipes tailored to the user's request "
        "and, when available, the current local weather conditions."
    ),
    backstory=(
        "You are a culinary expert with encyclopaedic knowledge of global cuisines. "
        "You craft recipes that are delicious, clearly explained, and appropriate "
        "for the season and weather."
    ),
    llm=llm,
    verbose=True,
)


# ---------------------------------------------------------------------------
# RecipeCrew — builds and runs the full pipeline via Crew.kickoff()
# ---------------------------------------------------------------------------

class RecipeCrew:
    """
    Orchestrates the weather-lookup + recipe-generation pipeline using
    CrewAI Agents, Tasks, and Crew.kickoff().  No bare LLM calls are made.
    """

    def run(self, dish_query: str, place: str = "Munich") -> Dict[str, Any]:
        # ------------------------------------------------------------------
        # Task 1 – fetch weather for the requested city
        # ------------------------------------------------------------------
        weather_task = Task(
            description=(
                "Look up the current weather for **{place}**.\n"
                "Steps:\n"
                "1. Use the `get_city_coordinates` tool to get latitude and longitude for {place}.\n"
                "2. Use the `get_forecast` tool with those coordinates to get the current weather.\n"
                "Return a concise summary that includes: temperature (°C), weather conditions, "
                "humidity (%), and wind speed (km/h)."
            ),
            expected_output=(
                "A short weather summary for {place} covering temperature, conditions, "
                "humidity, and wind speed."
            ),
            agent=weather_agent,
        )

        # ------------------------------------------------------------------
        # Task 2 – generate the recipe, informed by the weather summary
        # ------------------------------------------------------------------
        recipe_task = Task(
            description=(
                "You are given the following user request: **{dish_query}**.\n"
                "The current weather context for {place} has been fetched and is available "
                "as the output of the previous task.\n\n"
                "Using that weather context, craft a detailed recipe that includes:\n"
                "- Dish name\n"
                "- Simple cooking instructions not more than 5 lines \n"
                "- Estimated preparation and cooking time\n"
                "- Serving suggestions or chef's tips\n"
                "- A brief note on why this recipe suits the current weather."
            ),
            expected_output=(
                "A complete, well-formatted recipe for '{dish_query}' tailored to "
                "the weather in {place}. Keep it as short as possible while including all requested details."
            ),
            agent=recipe_agent,
            context=[weather_task],   # receives weather_task output automatically
        )

        # ------------------------------------------------------------------
        # Crew — sequential pipeline
        # ------------------------------------------------------------------
        crew = Crew(
            agents=[weather_agent, recipe_agent],
            tasks=[weather_task, recipe_task],
            verbose=True,
        )

        crew_output = crew.kickoff(inputs={"dish_query": dish_query, "place": place})

        # Extract individual task outputs
        weather_summary = (
            weather_task.output.raw if weather_task.output else None
        )
        recipe_text = (
            recipe_task.output.raw if recipe_task.output else str(crew_output)
        )

        return {
            "dish_query": dish_query,
            "place": place,
            "weather": {"conditions": weather_summary},
            "recipe": recipe_text,
        }
