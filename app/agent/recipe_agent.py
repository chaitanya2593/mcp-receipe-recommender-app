"""
AnthropicFoundry-based orchestrator.

Uses SKILL.md files as system prompts and hand-rolls the MCP tool-use loop,
since Azure Foundry exposes the Anthropic Messages API but not the
CLI-driven skill/tool machinery of the Claude Agent SDK.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from anthropic import AnthropicFoundry
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"

MAX_TOOL_ITERATIONS = 8


# --------------------------- Client ---------------------------

def _client() -> Tuple[AnthropicFoundry, str]:
    endpoint = os.getenv("AZURE_FOUNDRY_ENDPOINT")
    api_key = os.getenv("AZURE_FOUNDRY_API_KEY")
    deployment = os.getenv("AZURE_FOUNDRY_DEPLOYMENT", "claude-opus-4-7")
    if not endpoint or not api_key:
        raise RuntimeError(
            "Missing AZURE_FOUNDRY_ENDPOINT or AZURE_FOUNDRY_API_KEY. "
            "See .env.example."
        )
    return AnthropicFoundry(api_key=api_key, base_url=endpoint), deployment


# --------------------------- Skills ---------------------------

def _load_skill(name: str) -> str:
    """Return the markdown body of a SKILL.md (frontmatter stripped)."""
    path = SKILLS_DIR / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        _, _, rest = text.partition("---")
        _, _, body = rest.partition("---")
        return body.strip()
    return text.strip()


# --------------------------- MCP bridging ---------------------------

MCP_SERVERS: Dict[str, StdioServerParameters] = {
    "weather": StdioServerParameters(
        command="python",
        args=["app/servers/weather_server.py"],
    ),
    "osm": StdioServerParameters(
        command="uvx",
        args=["osm-mcp-server"],
    ),
}


def _run_async(coro):
    """Execute a coroutine on a dedicated worker thread (isolated from host loops)."""
    future: Future = Future()

    def _worker() -> None:
        try:
            future.set_result(asyncio.run(coro))
        except BaseException as e:  # noqa: BLE001
            future.set_exception(e)

    threading.Thread(target=_worker, daemon=True).start()
    return future.result()


async def _list_tools(server: StdioServerParameters) -> List[Dict[str, Any]]:
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema or {"type": "object", "properties": {}},
                }
                for t in resp.tools
            ]


async def _call_tool(
    server: StdioServerParameters, tool_name: str, tool_input: Dict[str, Any]
) -> str:
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_input)
            parts: List[str] = []
            for block in result.content:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "\n".join(parts) if parts else json.dumps({"ok": True})


# --------------------------- Messages loop ---------------------------

def _call_claude(
    system: str,
    user_content: str,
    mcp_server: Optional[StdioServerParameters] = None,
) -> str:
    """Run a single user turn, looping for tool use until the model stops calling tools."""
    client, model = _client()

    tools: List[Dict[str, Any]] = []
    if mcp_server is not None:
        tools = _run_async(_list_tools(mcp_server))

    messages: List[Dict[str, Any]] = [{"role": "user", "content": user_content}]

    for _ in range(MAX_TOOL_ITERATIONS):
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": 2048,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = client.messages.create(**kwargs)

        if response.stop_reason != "tool_use":
            return "".join(
                b.text for b in response.content if getattr(b, "type", None) == "text"
            ).strip()

        # Append assistant turn verbatim, then run each tool call and send back results.
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            assert mcp_server is not None
            try:
                output = _run_async(
                    _call_tool(mcp_server, block.name, dict(block.input or {}))
                )
            except Exception as e:  # noqa: BLE001
                output = f"Tool error: {e}"
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return "Tool-use iteration limit reached."


# --------------------------- Public orchestrator ---------------------------

class RecipeAgent:
    """Two-step conversational flow backed by Claude (Azure Foundry) + SKILL.md + MCP."""

    def extract_item_place(self, user_text: str, default_city: str = "Munich") -> Dict[str, str]:
        raw = _call_claude(
            system=_load_skill("input-extractor"),
            user_content=f"User input: {user_text}",
        )
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            data = json.loads(raw[start : end + 1])
            item_name = str(data.get("item_name") or "").strip()
            place_val = data.get("place")
            place = str(place_val).strip() if place_val else ""
        except Exception:
            item_name = user_text.strip()
            place = ""

        return {
            "item_name": item_name or user_text.strip(),
            "place": place or default_city,
        }

    def _weather(self, place: str) -> str:
        return _call_claude(
            system=_load_skill("weather-lookup"),
            user_content=f"Get the current weather for {place}.",
            mcp_server=MCP_SERVERS["weather"],
        ) or "Unknown"

    def run(
        self,
        item_name: str,
        place: str = "Munich",
        action: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_action = (action or "").strip().lower()
        weather_summary = self._weather(place)

        if normalized_action not in {"order", "prepare"}:
            return {
                "item_name": item_name,
                "place": place,
                "action": None,
                "weather": {"conditions": weather_summary},
                "clarification_needed": True,
                "supervisor_prompt": (
                    f"Got it — you want '{item_name}' in {place}. "
                    "Would you like to **order** it nearby or **prepare** it at home? "
                    "Please reply with exactly one option: order or prepare."
                ),
            }

        if normalized_action == "prepare":
            recipe_text = _call_claude(
                system=_load_skill("recipe-chef"),
                user_content=(
                    f"Item: {item_name}\nCity: {place}\n"
                    f"Weather context: {weather_summary}\n\n"
                    "Produce a recipe."
                ),
            )
            return {
                "item_name": item_name,
                "place": place,
                "action": "prepare",
                "weather": {"conditions": weather_summary},
                "clarification_needed": False,
                "recipe": recipe_text or "No recipe generated.",
            }

        places_text = _call_claude(
            system=_load_skill("place-finder"),
            user_content=(
                f"Item: {item_name}\nCity: {place}\n\n"
                "Find 3 nearby places that sell or serve this."
            ),
            mcp_server=MCP_SERVERS["osm"],
        )
        return {
            "item_name": item_name,
            "place": place,
            "action": "order",
            "weather": {"conditions": weather_summary},
            "clarification_needed": False,
            "places": places_text or "No place suggestions available.",
        }
