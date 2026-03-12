import json
from typing import Any, Dict, Optional

from crewai import Crew

from .agents import (
    extractor_agent,
    place_finder_agent,
    recipe_agent,
    supervisor_agent,
    weather_agent,
)
from .tasks import (
    build_extract_task,
    build_places_task,
    build_recipe_task,
    build_weather_task,
)


class RecipeCrew:
    """
    Orchestrates weather + intent-based routing:
    - Always fetch weather first
    - If action is missing: request clarification
    - prepare -> recipe agent
    - order -> place finder agent
    """

    def extract_item_place(self, user_text: str, default_city: str = "Munich") -> Dict[str, str]:
        extract_task = build_extract_task(extractor_agent)

        extract_crew = Crew(
            agents=[extractor_agent],
            tasks=[extract_task],
            verbose=True,
        )
        raw = str(extract_crew.kickoff(inputs={"user_text": user_text}))

        try:
            data = json.loads(raw)
            item_name = str(data.get("item_name") or "").strip()
            place_val = data.get("place")
            place = str(place_val).strip() if place_val is not None else ""
        except Exception:
            item_name = user_text.strip()
            place = ""

        return {
            "item_name": item_name or user_text.strip(),
            "place": place or default_city,
        }

    def run(self, item_name: str, place: str = "Munich", action: Optional[str] = None) -> Dict[str, Any]:
        normalized_action = (action or "").strip().lower()

        weather_task = build_weather_task(weather_agent)

        weather_crew = Crew(
            agents=[weather_agent],
            tasks=[weather_task],
            verbose=True,
        )
        weather_crew.kickoff(inputs={"place": place})

        weather_summary = weather_task.output.raw if weather_task.output else None

        if normalized_action not in {"order", "prepare"}:
            supervisor_prompt = (
                f"Got it - you want '{item_name}' in {place}. "
                "Would you like to **order** it nearby or **prepare** it at home? Please reply with exactly one option: order or prepare. "
            )
            return {
                "item_name": item_name,
                "place": place,
                "action": None,
                "weather": {"conditions": weather_summary},
                "clarification_needed": True,
                "supervisor_prompt": supervisor_prompt,
            }

        if normalized_action == "prepare":
            recipe_task = build_recipe_task(recipe_agent)

            route_crew = Crew(
                agents=[supervisor_agent, recipe_agent],
                tasks=[recipe_task],
                verbose=True,
            )
            route_crew.kickoff(inputs={"item_name": item_name, "place": place})

            recipe_text = recipe_task.output.raw if recipe_task.output else "No recipe generated."
            return {
                "item_name": item_name,
                "place": place,
                "action": "prepare",
                "weather": {"conditions": weather_summary},
                "clarification_needed": False,
                "recipe": recipe_text,
            }

        places_task = build_places_task(place_finder_agent)

        route_crew = Crew(
            agents=[supervisor_agent, place_finder_agent],
            tasks=[places_task],
            verbose=True,
        )
        route_crew.kickoff(inputs={"item_name": item_name, "place": place})

        places_text = places_task.output.raw if places_task.output else "No place suggestions available."
        return {
            "item_name": item_name,
            "place": place,
            "action": "order",
            "weather": {"conditions": weather_summary},
            "clarification_needed": False,
            "places": places_text,
        }

