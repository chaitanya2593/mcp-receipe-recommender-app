# Weather-Aware Cuisine Recommender

A Streamlit + CrewAI + MCP application that routes a food request into one of two paths:
- `prepare`: generate a weather-aware recipe
- `order`: find nearby places via OSM tools

## Local Setup (with uv)

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install [uv](https://github.com/astral-sh/uv) if needed:
   ```bash
   pip install uv
   ```
3. Sync dependencies:
   ```bash
   uv sync
   ```

## Run Streamlit

From the repository root:

```bash
streamlit run app/streamlit/streamlit_app.py
```

## Architecture
- **Streamlit Frontend**: User interface for input and output.
- **RecipeCrew**: CrewAI agent that orchestrates the workflow.
- **MCP Servers**: Separate servers for weather data and place-finding.

## Agents and MCP Mapping

| Agent Name | Purpose | MCP Used | Input | Output |
|---|---|---|---|---|
| Weather Specialist | Fetch current weather context for the user-selected city (coordinates + forecast summary). | Weather MCP (`app/servers/weather_server.py`) | `place` (city/location) | Weather summary (temperature, conditions, humidity, wind) |
| World-Class Chef | Generate a concise, practical recipe tailored to the requested item and weather context. | None (LLM only) | `item_name`, `place`, weather context | Recipe with ingredients, steps, time, and weather-fit note |
| Local Place Finder | Find nearby places where the requested dish/item can be ordered or bought. | OSM MCP (`uvx osm-mcp-server`) | `item_name`, `place` | Top nearby place suggestions with short location hints |
| Supervisor | Route interaction flow and request clarification when action is not explicit (`order` vs `prepare`). | None (LLM only) | `item_name`, `place`, optional `action`, weather context | Clarification prompt or routing decision |
| Input Extractor | Parse free-text user request into strict structured fields. | None (LLM only) | Raw user text | JSON: `{"item_name":"...","place":"...|null"}` |

### MCP Servers (Used in Project)

| MCP Server | Command / Path | Used By | Purpose |
|---|---|---|---|
| Weather MCP | `app/servers/weather_server.py` | Weather Specialist | Coordinates lookup and current weather retrieval |
| Fetch MCP | `python -m mcp_server_fetch` | Configured (not in main route) | Generic fetch capability for extensible workflows |
| OSM MCP | `uvx osm-mcp-server` | Local Place Finder | Nearby places and map-based search |



## References

- https://streamlit.io/
- https://open-meteo.com/en/docs
- https://github.com/astral-sh/uv
- https://mcpservers.org/search
