"""LangChain agents and chains used as nodes in the LangGraph orchestration.

Tool-using agents (weather, place finder) are LangChain tool-calling
AgentExecutors over MCP tools; tool-less agents (extractor, chef) are plain
LCEL chains. Everything is created lazily and cached so importing this module
does not require credentials or a running MCP server.
"""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from .config import get_llm, get_osm_tools, get_weather_tools
from .prompts import (
    CHEF_SYSTEM_PROMPT,
    EXTRACTOR_SYSTEM_PROMPT,
    PLACE_FINDER_SYSTEM_PROMPT,
    WEATHER_SYSTEM_PROMPT,
)

_cache: dict[str, object] = {}


def _build_chain(system_prompt: str) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    return prompt | get_llm() | StrOutputParser()


def _build_tool_agent(system_prompt: str, tools: list) -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    agent = create_tool_calling_agent(get_llm(), tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def get_extractor_chain() -> Runnable:
    if "extractor" not in _cache:
        _cache["extractor"] = _build_chain(EXTRACTOR_SYSTEM_PROMPT)
    return _cache["extractor"]


def get_chef_chain() -> Runnable:
    if "chef" not in _cache:
        _cache["chef"] = _build_chain(CHEF_SYSTEM_PROMPT)
    return _cache["chef"]


async def get_weather_agent() -> AgentExecutor:
    if "weather" not in _cache:
        _cache["weather"] = _build_tool_agent(WEATHER_SYSTEM_PROMPT, await get_weather_tools())
    return _cache["weather"]


async def get_place_finder_agent() -> AgentExecutor:
    if "places" not in _cache:
        _cache["places"] = _build_tool_agent(PLACE_FINDER_SYSTEM_PROMPT, await get_osm_tools())
    return _cache["places"]
