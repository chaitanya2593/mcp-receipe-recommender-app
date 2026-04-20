"""Tests for app/crewAi/recipe_crew.py — CrewAI calls are fully mocked."""
import json
from unittest.mock import MagicMock, patch

import pytest

# Patch heavy imports before RecipeCrew is imported
_agent_patch = patch("app.crewAi.recipe_crew.extractor_agent", new=MagicMock())
_weather_agent_patch = patch("app.crewAi.recipe_crew.weather_agent", new=MagicMock())
_recipe_agent_patch = patch("app.crewAi.recipe_crew.recipe_agent", new=MagicMock())
_place_agent_patch = patch("app.crewAi.recipe_crew.place_finder_agent", new=MagicMock())
_supervisor_patch = patch("app.crewAi.recipe_crew.supervisor_agent", new=MagicMock())

_agent_patch.start()
_weather_agent_patch.start()
_recipe_agent_patch.start()
_place_agent_patch.start()
_supervisor_patch.start()

from app.crewAi.recipe_crew import RecipeCrew  # noqa: E402


def _make_task_output(raw: str) -> MagicMock:
    out = MagicMock()
    out.raw = raw
    return out


def _mock_crew(kickoff_return=None, task_output_raw="mock output"):
    """Return a mock Crew class whose kickoff sets task.output."""
    crew_instance = MagicMock()
    crew_instance.kickoff = MagicMock(return_value=kickoff_return)
    crew_cls = MagicMock(return_value=crew_instance)
    return crew_cls


# ---------------------------------------------------------------------------
# extract_item_place
# ---------------------------------------------------------------------------

class TestExtractItemPlace:
    def test_parses_valid_json(self):
        crew_cls = _mock_crew(kickoff_return=json.dumps({"item_name": "pasta", "place": "Rome"}))

        with patch("app.crewAi.recipe_crew.Crew", crew_cls), \
             patch("app.crewAi.recipe_crew.build_extract_task", return_value=MagicMock()):
            result = RecipeCrew().extract_item_place("I want pasta in Rome")

        assert result["item_name"] == "pasta"
        assert result["place"] == "Rome"

    def test_falls_back_to_default_city_when_place_missing(self):
        crew_cls = _mock_crew(kickoff_return=json.dumps({"item_name": "sushi", "place": None}))

        with patch("app.crewAi.recipe_crew.Crew", crew_cls), \
             patch("app.crewAi.recipe_crew.build_extract_task", return_value=MagicMock()):
            result = RecipeCrew().extract_item_place("I want sushi", default_city="Berlin")

        assert result["item_name"] == "sushi"
        assert result["place"] == "Berlin"

    def test_falls_back_on_invalid_json(self):
        crew_cls = _mock_crew(kickoff_return="not json at all")

        with patch("app.crewAi.recipe_crew.Crew", crew_cls), \
             patch("app.crewAi.recipe_crew.build_extract_task", return_value=MagicMock()):
            result = RecipeCrew().extract_item_place("pizza", default_city="Munich")

        assert result["item_name"] == "pizza"
        assert result["place"] == "Munich"


# ---------------------------------------------------------------------------
# run — clarification path
# ---------------------------------------------------------------------------

class TestRecipeCrewRun:
    def _run_with_mocks(self, action, weather_raw="Sunny 20°C", extra_task_raw="result text"):
        weather_task_mock = MagicMock()
        weather_task_mock.output = _make_task_output(weather_raw)

        other_task_mock = MagicMock()
        other_task_mock.output = _make_task_output(extra_task_raw)

        build_weather = MagicMock(return_value=weather_task_mock)
        build_recipe = MagicMock(return_value=other_task_mock)
        build_places = MagicMock(return_value=other_task_mock)

        crew_instance = MagicMock()
        crew_instance.kickoff = MagicMock()
        crew_cls = MagicMock(return_value=crew_instance)

        with patch("app.crewAi.recipe_crew.Crew", crew_cls), \
             patch("app.crewAi.recipe_crew.build_weather_task", build_weather), \
             patch("app.crewAi.recipe_crew.build_recipe_task", build_recipe), \
             patch("app.crewAi.recipe_crew.build_places_task", build_places):
            return RecipeCrew().run("pizza", place="Munich", action=action)

    def test_no_action_returns_clarification(self):
        result = self._run_with_mocks(action=None)
        assert result["clarification_needed"] is True
        assert result["action"] is None
        assert "supervisor_prompt" in result

    def test_prepare_action_returns_recipe(self):
        result = self._run_with_mocks(action="prepare", extra_task_raw="Recipe: ...")
        assert result["action"] == "prepare"
        assert result["clarification_needed"] is False
        assert "recipe" in result
        assert result["recipe"] == "Recipe: ..."

    def test_order_action_returns_places(self):
        result = self._run_with_mocks(action="order", extra_task_raw="Place 1, Place 2")
        assert result["action"] == "order"
        assert result["clarification_needed"] is False
        assert "places" in result
        assert result["places"] == "Place 1, Place 2"

    def test_weather_always_included(self):
        result = self._run_with_mocks(action="prepare", weather_raw="Rainy 10°C")
        assert result["weather"]["conditions"] == "Rainy 10°C"

    def test_action_case_insensitive(self):
        result = self._run_with_mocks(action="PREPARE")
        assert result["action"] == "prepare"
