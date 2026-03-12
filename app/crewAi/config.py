import os

from crewai import LLM
from crewai.mcp import MCPServerStdio


def gpt_client() -> LLM:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise ValueError("Missing environment variable: AZURE_OPENAI_DEPLOYMENT")
    return LLM(
        model="azure/" + deployment,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )


llm = gpt_client()

weather_mcp = MCPServerStdio(
    command="python",
    args=["app/servers/weather_server.py"],
)

fetch_mcp = MCPServerStdio(
    command="python",
    args=["-m", "mcp_server_fetch"],
)

osm_mcp = MCPServerStdio(
    command="uvx",
    args=["osm-mcp-server"],
)

