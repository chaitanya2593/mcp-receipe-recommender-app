# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **Weather-Aware Cuisine Recommender** that uses LangChain agents + LangGraph orchestration and MCP (Model Context Protocol) servers to suggest recipes or find nearby places based on local weather conditions. A legacy CrewAI implementation is kept in `app/crewAi/` for comparison; the Streamlit UI uses the LangGraph implementation in `app/langGraph/`.


**Required env vars** (see `.env.example`):
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`

Tests live in `tests/` (`make test` / `uv run pytest`); LLM and MCP calls are mocked.

## Architecture

```
Streamlit UI (app/streamlit/streamlit_app.py)
    └── RecipeGraph (app/langGraph/recipe_graph.py) — wraps a LangGraph StateGraph
            ├── extract node  → LCEL extractor chain → parses free-text into item + location
            ├── weather node  → LangChain tool-calling agent → Weather MCP → Open-Meteo API
            └── conditional edges route by user action:
                 ├── no action  → clarify node → asks "order or prepare?"
                 ├── "prepare"  → recipe node → chef LCEL chain (no MCP)
                 └── "order"    → places node → place finder agent → OSM MCP
```

### Two-step conversation flow

1. User provides food item + city → system fetches weather, asks "order or prepare?"
2. User picks action → system executes targeted workflow and returns result

### Key files

| File | Purpose |
|------|---------|
| `app/langGraph/recipe_graph.py` | Main orchestrator — `RecipeGraph` with `extract_item_place()` and `run()` |
| `app/langGraph/graph.py` | LangGraph `StateGraph` — nodes, conditional routing, `build_graph()` |
| `app/langGraph/agents.py` | LangChain tool-calling agents (MCP tools) + LCEL chains |
| `app/langGraph/prompts.py` | System prompts and task builders |
| `app/langGraph/config.py` | Azure OpenAI LLM + MCP client (`langchain-mcp-adapters`) |
| `app/crewAi/` | Legacy CrewAI implementation (same public contract) |
| `app/servers/weather_server.py` | Custom MCP server wrapping Open-Meteo geocoding + forecast APIs |
| `app/servers/servers_list.py` | MCP server registry (Weather, OSM, Fetch) |

### MCP Servers

| Server | Launch command | Purpose |
|--------|---------------|---------|
| Weather | `python app/servers/weather_server.py` | Custom — geocoding + weather via Open-Meteo |
| OSM | `uvx osm-mcp-server` | External package — map-based place search |
| Fetch | `python -m mcp_server_fetch` | External package — generic HTTP fetching |

MCP servers are configured in `app/langGraph/config.py` (via `MultiServerMCPClient` from `langchain-mcp-adapters`) and their tools are bound to the LangChain agents that need them. Note: `langchain-mcp-adapters` is pinned to `<0.2` because 0.2.x requires `langchain-core>=1.0`, while the project is on the langchain 0.3 line (held there by the `openai==1.83` compatible range).