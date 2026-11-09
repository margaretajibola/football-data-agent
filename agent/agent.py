import asyncio
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
- If you are not sure which view has the data, call list_views.
- Call describe_view before writing SQL for a view you have not seen yet.
- Use run_query to get the numbers. Only read-only SELECT queries work.
- Team names include "FC" (for example Arsenal FC), so match them with ILIKE.
- If a query returns an error, read it, fix the SQL and try again.
- Answer only from the query results. Never guess or use memory for numbers.
- If the data cannot answer the question, say so plainly.

The data covers the current Premier League season only. It is refreshed daily.
Keep answers short and include the key numbers."""

async def build_agent():
    client = MultiServerMCPClient({
        "football": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "mcp_server.server"],
        }
    })
    tools = await client.get_tools()
    model = init_chat_model(os.getenv("MODEL_NAME", "gpt-4o-mini"))
    return create_agent(model, tools, system_prompt=SYSTEM_PROMPT)


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