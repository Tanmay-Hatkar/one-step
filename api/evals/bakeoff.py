"""Model bake-off: run the AI suites on several cheap models and compare quality, cost, speed.

OpenAI closed new fine-tuning jobs, so instead of training a smaller parser we measure
which off-the-shelf model is the cheapest one that's still as good. Writes
evals/results/bakeoff.json, which the public eval page shows.

Usage:
    uv run python -m evals.bakeoff
"""

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from tempfile import mkdtemp

from app.config import settings
from app.llm.client import OpenAILLMClient
from evals.run import EVALS_DIR, build_services, run_diff, run_e2e, run_parse

logger = logging.getLogger("bakeoff")

BAKEOFF_PATH = EVALS_DIR / "results" / "bakeoff.json"

# (model, reasoning effort, $ per 1M input tokens, $ per 1M output tokens).
# List prices from OpenAI's model pages when this was written; check before relying on them.
CANDIDATES: list[tuple[str, str, float, float]] = [
    ("gpt-5.4-mini", "low", 0.75, 4.50),
    ("gpt-5.4-nano", "low", 0.20, 1.25),
    ("gpt-5-mini", "low", 0.25, 2.00),
    ("gpt-5-nano", "low", 0.05, 0.40),
    ("gpt-4.1-mini", "", 0.40, 1.60),
    ("gpt-4o-mini", "", 0.15, 0.60),
]


def score(results: list[dict]) -> tuple[int, int]:
    """(passed, total) checks over one suite's results."""
    checks = [p for r in results for _, p, _ in r["checks"]]
    return sum(checks), len(checks)


async def evaluate(model: str, effort: str, price_in: float, price_out: float) -> dict:
    """Run parse, diff and e2e on one model; return its row for the report."""
    client = OpenAILLMClient(settings.openai_api_key, model, effort, settings.llm_timeout_seconds)
    # Fresh cache so every model pays for its own calls and the costs compare fairly.
    repertoire, cousins, graph, dishes = build_services(
        client, cache_url=f"sqlite:///{mkdtemp()}/cache.db"
    )
    suites = {
        "parse": await run_parse(repertoire),
        "diff": await run_diff(cousins, graph, dishes),
        "e2e": await run_e2e(repertoire, graph),
    }
    passed = total = 0
    row: dict = {"model": model, "reasoning": effort or "none", "suites": {}, "failed": []}
    for name, results in suites.items():
        p, t = score(results)
        passed, total = passed + p, total + t
        row["suites"][name] = {"passed": p, "total": t}
        row["failed"] += [
            f"{name} · {r['id']} · {check}"
            for r in results
            for check, ok, _ in r["checks"]
            if not ok
        ]
    usage = client.usage
    calls = max(usage.calls, 1)
    cost = (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000
    row.update(
        passed=passed,
        total=total,
        pass_rate=round(passed / total, 3) if total else 0.0,
        calls=usage.calls,
        usd_per_1k_calls=round(1000 * cost / calls, 3),
        seconds_per_call=round(usage.seconds / calls, 2),
        price_per_1m={"input": price_in, "output": price_out},
    )
    logger.info(
        "%-14s %3d/%d  $%.3f/1k calls  %.1fs/call",
        model,
        passed,
        total,
        row["usd_per_1k_calls"],
        row["seconds_per_call"],
    )
    return row


def pick(rows: list[dict]) -> dict:
    """The cheapest model that passes at least as many checks as the current one."""
    current = next(r for r in rows if r["model"] == settings.llm_model)
    good = [r for r in rows if r["passed"] >= current["passed"] and r["calls"]]
    return min(good or [current], key=lambda r: r["usd_per_1k_calls"])


async def main() -> int:
    """Evaluate every candidate one after another (keeps under rate limits)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("evals").setLevel(logging.WARNING)
    rows = [await evaluate(*c) for c in CANDIDATES]
    best = pick(rows)
    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "current": settings.llm_model,
        "pick": best["model"],
        "rule": "Cheapest model that passes at least as many checks as the current one.",
        "models": rows,
    }
    BAKEOFF_PATH.write_text(json.dumps(report, indent=2) + "\n")
    logger.info("Pick: %s (current: %s)", best["model"], settings.llm_model)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
