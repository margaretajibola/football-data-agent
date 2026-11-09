import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

SYSTEM_PROMPT = """You are a football analyst for the Premier League. You answer
questions using a Postgres database, through three tools.

How to work:
- The database schema is listed below. Use those exact column names and values.
  Call describe_view only if something is missing.
- Use run_query to get the numbers. Only read-only SELECT queries work.
- Always use the tools before saying the data cannot answer. Never say
  something is not available without checking.
- Team names include "FC" (for example Arsenal FC), so match them with ILIKE.
- If a query returns an error or zero rows, check your filters and try again
  before answering.
- Answer only from the query results. Never guess or use memory for numbers.
- When asked for N items, give exactly N.

Rules about the data:
- The database holds the current season only. Never filter on season_year.
- league_table has three rows per team, one for each venue: ALL, HOME and AWAY.
  For overall questions (table position, points, goals scored, goal difference)
  always filter venue = 'ALL'. For home or away questions use venue = 'HOME'
  or 'AWAY'.
- match_results has finished matches only. upcoming_fixtures has future matches.
- upcoming_fixtures has home_team and away_team columns, not a team column. For
  a team's next N fixtures, match the team on either side in one query, then
  ORDER BY kickoff_utc and LIMIT N.
- The teams view has club details that do not depend on the season: founded
  year, stadium, short name and club colours.
- The only things the data cannot answer are things outside it, such as past
  seasons or predictions. Say so plainly in that case.

The data is refreshed daily. Keep answers short and include the key numbers."""


def tool_text(result):
    # tool results can be a string or a list of content blocks
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in result
        )
    return str(result)


async def load_schema(tools):
    # describe every view once at startup, using the MCP tools themselves
    by_name = {t.name: t for t in tools}
    try:
        views = json.loads(tool_text(await by_name["list_views"].ainvoke({})))["views"]
        parts = []
        for v in views:
            described = tool_text(
                await by_name["describe_view"].ainvoke({"view_name": v["name"]}))
            parts.append(f"{v['name']} ({v['description']}): {described}")
        return "\n".join(parts)
    except Exception as e:
        # the agent still works without this, it just has to look things up itself
        print(f"could not preload schema: {e}")
        return ""


async def build_agent():
    client = MultiServerMCPClient({
        "football": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "mcp_server.server"],
        }
    })
    tools = await client.get_tools()
    schema = await load_schema(tools)
    prompt = SYSTEM_PROMPT
    if schema:
        prompt += "\n\nDatabase schema (already loaded):\n" + schema
    model = init_chat_model(os.getenv("MODEL_NAME", "gpt-4o-mini"))
    return create_agent(model, tools, system_prompt=prompt)


def message_text(message):
    # some models return a list of content blocks instead of a string
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict))


def sql_used(messages):
    # every query the agent ran, in order
    queries = []
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            if call["name"] == "run_query":
                queries.append(call["args"].get("sql", ""))
    return queries

async def ask(agent, question, history=None):
    messages = (history or []) + [{"role": "user", "content": question}]
    result = await agent.ainvoke({"messages": messages})
    out = result["messages"]
    return message_text(out[-1]), sql_used(out)


async def main():
    agent = await build_agent()
    while True:
        question = input("\nQuestion (or 'quit'): ").strip()
        if question.lower() in ("quit", "exit", ""):
            break
        answer, queries = await ask(agent, question)
        for q in queries:
            print(f"\nSQL: {q}")
        print(f"\n{answer}")


if __name__ == "__main__":
    asyncio.run(main())