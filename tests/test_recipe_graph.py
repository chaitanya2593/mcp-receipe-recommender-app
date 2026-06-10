"""Tests for app/langGraph — LLM chains and MCP agents are fully mocked."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.langGraph import RecipeGraph


def _mock_chain(return_value: str) -> MagicMock:
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=return_value)
    return chain


def _mock_agent(output: str) -> AsyncMock:
    """Mock for the async agent getters: awaiting the getter yields an
    AgentExecutor-like object whose ainvoke returns {"output": ...}."""
    executor = MagicMock()
    executor.ainvoke = AsyncMock(return_value={"output": output})
    return AsyncMock(return_value=executor)


# ---------------------------------------------------------------------------
# extract_item_place
# ---------------------------------------------------------------------------

class TestExtractItemPlace:
    def _extract(self, llm_raw: str, user_text: str, default_city: str = "Munich"):
        with patch(
            "app.langGraph.graph.get_extractor_chain",
            return_value=_mock_chain(llm_raw),
        ):
            return RecipeGraph().extract_item_place(user_text, default_city=default_city)

    def test_parses_valid_json(self):
        raw = json.dumps({"item_name": "pasta", "place": "Rome"})
        result = self._extract(raw, "I want pasta in Rome")
        assert result["item_name"] == "pasta"
        assert result["place"] == "Rome"

    def test_parses_json_wrapped_in_code_fences(self):
        raw = '```json\n{"item_name": "pasta", "place": "Rome"}\n```'
        result = self._extract(raw, "I want pasta in Rome")
        assert result["item_name"] == "pasta"
        assert result["place"] == "Rome"

    def test_falls_back_to_default_city_when_place_missing(self):
        raw = json.dumps({"item_name": "sushi", "place": None})
        result = self._extract(raw, "I want sushi", default_city="Berlin")
        assert result["item_name"] == "sushi"
        assert result["place"] == "Berlin"

    def test_falls_back_on_invalid_json(self):
        result = self._extract("not json at all", "pizza", default_city="Munich")
        assert result["item_name"] == "pizza"
        assert result["place"] == "Munich"


# ---------------------------------------------------------------------------
# run — clarification / recipe / places paths
# ---------------------------------------------------------------------------

class TestRecipeGraphRun:
    def _run_with_mocks(self, action, weather_raw="Sunny 20°C", extra_raw="result text"):
        with patch("app.langGraph.graph.get_weather_agent", _mock_agent(weather_raw)), \
             patch("app.langGraph.graph.get_place_finder_agent", _mock_agent(extra_raw)), \
             patch("app.langGraph.graph.get_chef_chain", return_value=_mock_chain(extra_raw)):
            return RecipeGraph().run("pizza", place="Munich", action=action)

    def test_no_action_returns_clarification(self):
        result = self._run_with_mocks(action=None)
        assert result["clarification_needed"] is True
        assert result["action"] is None
        assert "supervisor_prompt" in result

    def test_prepare_action_returns_recipe(self):
        result = self._run_with_mocks(action="prepare", extra_raw="Recipe: ...")
        assert result["action"] == "prepare"
        assert result["clarification_needed"] is False
        assert result["recipe"] == "Recipe: ..."

    def test_order_action_returns_places(self):
        result = self._run_with_mocks(action="order", extra_raw="Place 1, Place 2")
        assert result["action"] == "order"
        assert result["clarification_needed"] is False
        assert result["places"] == "Place 1, Place 2"

    def test_weather_always_included(self):
        result = self._run_with_mocks(action="prepare", weather_raw="Rainy 10°C")
        assert result["weather"]["conditions"] == "Rainy 10°C"

    def test_action_case_insensitive(self):
        result = self._run_with_mocks(action="PREPARE")
        assert result["action"] == "prepare"
