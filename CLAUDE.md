# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **Weather-Aware Cuisine Recommender** that uses the **Claude Agent SDK** with **Skills** and **MCP (Model Context Protocol)** servers to suggest recipes or find nearby places based on local weather conditions.

**Required env vars** (see `.env.example`):
- `ANTHROPIC_API_KEY`

No test suite — the app is validated via the Streamlit UI.

## Architecture

```
Streamlit UI (app/streamlit/streamlit_app.py)
    └── RecipeAgent (app/agent/recipe_agent.py)
            └── Claude Agent SDK (model: claude-opus-4-7)
                    ├── Skills at .claude/skills/*
                    │     ├── input-extractor   → parses free-text into item + city
                    │     ├── weather-lookup    → Weather MCP → Open-Meteo
                    │     ├── recipe-chef       → weather-aware recipe (no MCP)
                    │     └── place-finder      → OSM MCP → nearby stores/restaurants
                    └── MCP servers from .mcp.json (weather, osm, fetch)
```

Routing is no longer hardcoded — Claude picks the right skill from each skill's `description` frontmatter.

### Two-step conversation flow

1. User provides food item + city → system fetches weather, asks "order or prepare?"
2. User picks action → system invokes the appropriate skill and returns the result.

### Key files

| File | Purpose |
|------|---------|
| `app/agent/recipe_agent.py` | Orchestrator — `extract_item_place()` and `run()` wrap Claude Agent SDK `query()` |
| `.claude/skills/*/SKILL.md` | Skill definitions — frontmatter (`name`, `description`) + markdown body |
| `.mcp.json` | MCP server registry loaded by the SDK |
| `app/servers/weather_server.py` | Custom MCP server wrapping Open-Meteo geocoding + forecast APIs |
| `app/streamlit/streamlit_app.py` | Chat UI, drives the two-step flow |

### MCP Servers

| Server | Launch command | Purpose |
|--------|---------------|---------|
| Weather | `python app/servers/weather_server.py` | Custom — geocoding + weather via Open-Meteo |
| OSM | `uvx osm-mcp-server` | External — map-based place search |
| Fetch | `python -m mcp_server_fetch` | External — generic HTTP fetching |

Configured in `.mcp.json` at the project root; the Agent SDK loads them automatically.

### Adding a new skill

1. Create `.claude/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`) and a markdown body of instructions.
2. If the skill needs tools, declare them in `.mcp.json`.
3. No orchestrator change required — Claude discovers and routes based on the skill's `description`.
