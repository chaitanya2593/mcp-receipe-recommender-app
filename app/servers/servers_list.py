from pathlib import Path
from mcp import StdioServerParameters

# List of available MCP servers for the Streamlit app
PROJECT_ROOT = Path(__file__).resolve().parents[2]

server_list = {
    "weather": StdioServerParameters(
        command="python",
        args=["app/servers/weather_server.py"],
        env=None
    ),
    "mcp_server_fetch": StdioServerParameters(
        command="python",
        args=["-m", "mcp_server_fetch"],
        env=None,
    ),
    "osm-mcp-server": StdioServerParameters(
        command="uvx",
        args=["osm-mcp-server"],
        env=None,
    ),
}
