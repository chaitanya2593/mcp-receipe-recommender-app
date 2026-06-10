import asyncio
from typing import Any, Dict, Optional

from .graph import build_graph


class RecipeGraph:
    """
    LangGraph-backed orchestrator with the same public contract as the
    CrewAI ``RecipeCrew``:
    - Always fetch weather first
    - If action is missing: request clarification
    - prepare -> chef chain
    - order -> place finder agent
    """

    def __init__(self) -> None:
        self._graph = build_graph()

    def extract_item_place(self, user_text: str, default_city: str = "Munich") -> Dict[str, str]:
        final_state = asyncio.run(
            self._graph.ainvoke({"user_text": user_text, "default_city": default_city})
        )
        return {
            "item_name": final_state.get("item_name") or user_text.strip(),
            "place": final_state.get("place") or default_city,
        }

    def run(self, item_name: str, place: str = "Munich", action: Optional[str] = None) -> Dict[str, Any]:
        final_state = asyncio.run(
            self._graph.ainvoke({"item_name": item_name, "place": place, "action": action})
        )

        result: Dict[str, Any] = {
            "item_name": item_name,
            "place": place,
            "action": final_state.get("action"),
            "weather": {"conditions": final_state.get("weather_summary")},
            "clarification_needed": final_state.get("clarification_needed", False),
        }

        if result["clarification_needed"]:
            result["supervisor_prompt"] = final_state.get("supervisor_prompt")
        if final_state.get("recipe") is not None:
            result["recipe"] = final_state["recipe"]
        if final_state.get("places") is not None:
            result["places"] = final_state["places"]

        return result
