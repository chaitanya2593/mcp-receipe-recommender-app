
# client.py
from mcp.client import StdioClient
import asyncio
import json

async def main():
    # Launch MCP server as subprocess
    client = StdioClient(command=["python", "server.py"])
    await client.start()

    # List tools
    tools = await client.list_tools()
    print("Available tools:", [t.name for t in tools])

    # Call market_analysis tool
    params = {
        "ticker": "AAPL",
        "period": "1mo",
        "interval": "1d",
        "include_chart": True,
        "sma_windows": [7, 30]
    }
    result = await client.call_tool("market_analysis", params)
    print("Result:\n", json.dumps(result, indent=2))

    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
