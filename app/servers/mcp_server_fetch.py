import sys
import asyncio
import httpx
from mcp.server import MCPServer, Tool, ToolCall, ToolResponse

class FetchUrlTool(Tool):
    name = "fetch_url"
    description = "Fetches the content of a URL via HTTP GET."

    async def call(self, call: ToolCall) -> ToolResponse:
        url = call.arguments.get("url")
        if not url:
            return ToolResponse(content=[{"text": "{'error': 'No URL provided'}"}])
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10)
                resp.raise_for_status()
                # Return only first 1000 chars to avoid flooding
                text = resp.text[:1000]
                return ToolResponse(content=[{"text": repr(text)}])
        except Exception as e:
            return ToolResponse(content=[{"text": f"{{'error': '{str(e)}'}}"}])

async def main():
    server = MCPServer(tools=[FetchUrlTool()])
    await server.run_stdio()

if __name__ == "__main__":
    asyncio.run(main())

