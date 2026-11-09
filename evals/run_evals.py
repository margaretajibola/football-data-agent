import asyncio
import csv
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from pydantic import BaseModel

from agent.agent import ask, build_agent
from evals.test_cases import CASES
from mcp_server.db import fetch

load_dotenv()

RESULTS_DIR = Path(__file__).parent / "results"

JUDGE_PROMPT = """You are grading a football analyst agent.

Question: {question}

What a correct answer must contain:
{expected}

Agent answer:
{answer}

Rules:
- The agent is correct if its answer agrees with the expected data. Team name
  variants are fine (Spurs for Tottenham Hotspur, Man City for Manchester City FC).
- If several rows tie, naming any one of them or all of them is correct.
- Never mark an answer wrong for including extra details or numbers. Mark it
  wrong only if a key fact is missing or contradicts the expected data.
- For dates and times, matching the same day and teams is enough.
- If the expected text describes a behaviour (refuse, cannot answer), the agent
  is correct only if it behaves that way."""


class Verdict(BaseModel):
    correct: bool
    reason: str


def expected_text(case):
    # reference answers come from the database at run time, so they never go stale
    if "note" in case:
        return case["note"]
    columns, rows = fetch(case["sql"])
    lines = [", ".join(f"{c}={v}" for c, v in zip(columns, row)) for row in rows[:10]]
    return "Correct data from the database:\n" + "\n".join(lines)


async def run_case(agent, judge, case):
    expected = expected_text(case)
    start = time.time()
    answer, queries = await ask(agent, case["question"])
    latency = round(time.time() - start, 1)
    verdict = judge.invoke(JUDGE_PROMPT.format(
        question=case["question"], expected=expected, answer=answer))
    return {
        "id": case["id"], "category": case["category"], "question": case["question"],
        "passed": verdict.correct, "reason": verdict.reason, "answer": answer,
        "sql": " || ".join(queries), "sql_queries": len(queries), "latency_s": latency,
    }


async def main():
    wanted = set(sys.argv[1:])
    cases = [c for c in CASES if not wanted or c["id"] in wanted]

    model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
    judge = init_chat_model(os.getenv("JUDGE_MODEL", "gpt-4o-mini"), temperature=0)
    judge = judge.with_structured_output(Verdict)
    agent = await build_agent()

    results = []
    for case in cases:
        try:
            row = await run_case(agent, judge, case)
        except Exception as e:
            row = {"id": case["id"], "category": case["category"],
                   "question": case["question"], "passed": False,
                   "reason": f"error: {e}", "answer": "", "sql": "",
                   "sql_queries": 0, "latency_s": 0}
        row["model"] = model_name
        results.append(row)
        print(f"{'PASS' if row['passed'] else 'FAIL'}  {row['id']}  {row['question']}")
        if not row["passed"]:
            print(f"      {row['reason']}")

    # summary
    total = len(results)
    passed = sum(r["passed"] for r in results)
    print(f"\nAccuracy: {passed}/{total} ({passed / total:.0%})")
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r["passed"])
    for cat, flags in by_cat.items():
        print(f"  {cat}: {sum(flags)}/{len(flags)}")
    print(f"Average latency: {sum(r['latency_s'] for r in results) / total:.1f}s")

    # save
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"results_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    asyncio.run(main())