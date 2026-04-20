# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **Weather-Aware Cuisine Recommender** that uses CrewAI multi-agent orchestration and MCP (Model Context Protocol) servers to suggest recipes or find nearby places based on local weather conditions.


**Required env vars** (see `.env.example`):
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`

No test suite — the app is validated via the Streamlit UI.

## Architecture

```
Streamlit UI (app/streamlit/streamlit_app.py)
    └── RecipeCrew (app/crewAi/recipe_crew.py)
            ├── Input Extractor Agent  → parses free-text into item + location
            ├── Weather Specialist     → calls Weather MCP → Open-Meteo API
            └── Routes by user action:
                 ├── "prepare" → Chef Agent → weather-aware recipe (no MCP)
                 └── "order"   → Place Finder Agent → OSM MCP → nearby stores/restaurants
```

### Two-step conversation flow

1. User provides food item + city → system fetches weather, asks "order or prepare?"
2. User picks action → system executes targeted workflow and returns result

### Key files

| File | Purpose |
|------|---------|
| `app/crewAi/recipe_crew.py` | Main orchestrator — `extract_item_place()` and `run()` |
| `app/crewAi/agents.py` | 5 CrewAI agent definitions |
| `app/crewAi/tasks.py` | Task builders for each agent |
| `app/crewAi/config.py` | Azure OpenAI LLM + MCP server initialization |
| `app/servers/weather_server.py` | Custom MCP server wrapping Open-Meteo geocoding + forecast APIs |
| `app/servers/servers_list.py` | MCP server registry (Weather, OSM, Fetch) |

### MCP Servers

| Server | Launch command | Purpose |
|--------|---------------|---------|
| Weather | `python app/servers/weather_server.py` | Custom — geocoding + weather via Open-Meteo |
| OSM | `uvx osm-mcp-server` | External package — map-based place search |
| Fetch | `python -m mcp_server_fetch` | External package — generic HTTP fetching |

MCP servers are configured and initialized in `app/crewAi/config.py` and consumed by agents that need them.