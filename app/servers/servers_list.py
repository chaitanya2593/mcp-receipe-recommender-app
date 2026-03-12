from pathlib import Path
import sys

# List of available MCP servers for the Streamlit app
PROJECT_ROOT = Path(__file__).resolve().parents[2]

server_list = {
    "RecipeRecommender": {
        "name": "RecipeRecommender",
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "app/servers/server.py")],
        "cwd": str(PROJECT_ROOT),
        "env": None
    },
    "WeatherCuisine": {
        "name": "WeatherCuisine",
        "command": sys.executable,
        "args": [str(PROJECT_ROOT / "app/servers/weather_server.py")],
        "cwd": str(PROJECT_ROOT),
        "env": None
    }
    # Add more servers here if needed
}
