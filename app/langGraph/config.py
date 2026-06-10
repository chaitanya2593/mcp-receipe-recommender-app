import os
from functools import lru_cache
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def get_llm() -> AzureChatOpenAI:
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if not deployment:
        raise ValueError("Missing environment variable: AZURE_OPENAI_DEPLOYMENT")
    return AzureChatOpenAI(
        azure_deployment=deployment,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature=1,
    )


@lru_cache(maxsize=1)
def get_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "weather": {
                "transport": "stdio",
                "command": "python",
                "args": [str(PROJECT_ROOT / "app" / "servers" / "weather_server.py")],
            },
            "osm": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["osm-mcp-server"],
            },
        }
    )


async def get_weather_tools():
    return await get_mcp_client().get_tools(server_name="weather")


async def get_osm_tools():
    return await get_mcp_client().get_tools(server_name="osm")
