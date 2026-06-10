"""LangGraph orchestration for the weather-aware cuisine recommender.

Graph shape:

    START ──(has user_text?)──> extract ──> END
          └──(else)───────────> weather ──(action?)──> clarify ──> END
                                          ├──"prepare"─> recipe ──> END
                                          └──"order"───> places ──> END

The CrewAI supervisor agent is replaced by the conditional edges: routing
between clarification, recipe, and place finding is a deterministic decision,
so it lives in the graph instead of an LLM agent.
"""

import json
from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import (
    get_chef_chain,
    get_extractor_chain,
    get_place_finder_agent,
    get_weather_agent,
)
from .prompts import extract_task, places_task, recipe_task, weather_task


class RecipeState(TypedDict, total=False):
    # extraction inputs
    user_text: str
    default_city: str
    # core request
    item_name: str
    place: str
    action: Optional[str]
    # results
    weather_summary: Optional[str]
    clarification_needed: bool
    supervisor_prompt: Optional[str]
    recipe: Optional[str]
    places: Optional[str]


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -len("```")]
    return text.strip()


async def extract_node(state: RecipeState) -> RecipeState:
    user_text = state.get("user_text", "")
    raw = await get_extractor_chain().ainvoke({"input": extract_task(user_text)})

    try:
        data = json.loads(_strip_code_fences(str(raw)))
        item_name = str(data.get("item_name") or "").strip()
        place_val = data.get("place")
        place = str(place_val).strip() if place_val is not None else ""
    except Exception:
        item_name = user_text.strip()
        place = ""

    return {
        "item_name": item_name or user_text.strip(),
        "place": place or state.get("default_city", "Munich"),
    }


async def weather_node(state: RecipeState) -> RecipeState:
    agent = await get_weather_agent()
    result = await agent.ainvoke({"input": weather_task(state["place"])})
    return {"weather_summary": result.get("output")}


def clarify_node(state: RecipeState) -> RecipeState:
    supervisor_prompt = (
        f"Got it - you want '{state['item_name']}' in {state['place']}. "
        "Would you like to **order** it nearby or **prepare** it at home? "
        "Please reply with exactly one option: order or prepare. "
    )
    return {
        "action": None,
        "clarification_needed": True,
        "supervisor_prompt": supervisor_prompt,
    }


async def recipe_node(state: RecipeState) -> RecipeState:
    raw = await get_chef_chain().ainvoke(
        {"input": recipe_task(state["item_name"], state["place"], state.get("weather_summary"))}
    )
    return {
        "action": "prepare",
        "clarification_needed": False,
        "recipe": str(raw).strip() or "No recipe generated.",
    }


async def places_node(state: RecipeState) -> RecipeState:
    agent = await get_place_finder_agent()
    result = await agent.ainvoke({"input": places_task(state["item_name"], state["place"])})
    return {
        "action": "order",
        "clarification_needed": False,
        "places": result.get("output") or "No place suggestions available.",
    }


def route_entry(state: RecipeState) -> str:
    return "extract" if state.get("user_text") else "weather"


def route_after_weather(state: RecipeState) -> str:
    action = (state.get("action") or "").strip().lower()
    if action == "prepare":
        return "recipe"
    if action == "order":
        return "places"
    return "clarify"


def build_graph():
    graph = StateGraph(RecipeState)

    graph.add_node("extract", extract_node)
    graph.add_node("weather", weather_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("recipe", recipe_node)
    graph.add_node("places", places_node)

    graph.add_conditional_edges(START, route_entry, {"extract": "extract", "weather": "weather"})
    graph.add_edge("extract", END)
    graph.add_conditional_edges(
        "weather",
        route_after_weather,
        {"clarify": "clarify", "recipe": "recipe", "places": "places"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("recipe", END)
    graph.add_edge("places", END)

    return graph.compile()
