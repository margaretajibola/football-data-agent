import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])


async def call(session, tool, args):
    result = await session.call_tool(tool, args)
    print(f"\n{tool} {args}\n{result.content[0].text}")


async def main():
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            await call(session, "list_views", {})
            await call(session, "describe_view", {"view_name": "league_table"})
            await call(session, "run_query", {"sql": "SELECT * FROM league_table LIMIT 3"})
            # these two should return errors
            await call(session, "run_query", {"sql": "DELETE FROM teams"})
            await call(session, "run_query", {"sql": "SELECT 1; DROP VIEW teams"})


asyncio.run(main())