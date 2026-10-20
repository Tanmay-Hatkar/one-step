"""Run the live evals against the real model and write evals/results/latest.json.

Usage:
    uv run python -m evals.run            # all suites
    uv run python -m evals.run parse      # one suite: parse | diff | e2e | diet

Responses are cached in evals/.cache.db, keyed by prompt, so re-runs are free until a
prompt or model changes. Exits non-zero if the overall pass rate is below threshold.
"""

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.db import init_db, make_engine, make_session_factory
from app.llm.client import LLMError, OpenAILLMClient
from app.models.dish import UserDish
from app.repositories.dish_repository import DishRepository
from app.repositories.llm_repository import LLMCacheRepository, LLMUsageRepository
from app.services.cousin_service import CousinService
from app.services.diet import ALLERGEN_KEYWORDS, ingredient_allergens, is_meat_ingredient
from app.services.graph_service import DietRule, GraphService
from app.services.ingredients import pantry_of
from app.services.llm_gateway import LLMGateway
from app.services.repertoire_service import RepertoireService
from evals.cases import ANCHORS, DIFF_CASES, END_TO_END_CASES, PARSE_CASES
from evals.checks import Check, check_diff, check_parsed_dish

logger = logging.getLogger("evals")

EVALS_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EVALS_DIR / "results" / "latest.json"
PASS_THRESHOLD = 0.85


def build_services() -> tuple[RepertoireService, CousinService, GraphService, DishRepository]:
    """Real services with a dedicated eval cache and a generous cap."""
    engine = make_engine(f"sqlite:///{EVALS_DIR / '.cache.db'}")
    init_db(engine)
    sessions = make_session_factory(engine)
    client = OpenAILLMClient(
        settings.openai_api_key,
        settings.llm_model,
        settings.llm_reasoning_effort,
        settings.llm_timeout_seconds,
    )
    gateway = LLMGateway(
        client, LLMCacheRepository(sessions), LLMUsageRepository(sessions), daily_cap=10_000
    )
    dishes = DishRepository(settings.dishes_path)
    graph = GraphService(dishes.all(), settings)
    return (
        RepertoireService(gateway, dishes, settings.max_repertoire_dishes),
        CousinService(graph, gateway),
        graph,
        dishes,
    )


async def run_parse(repertoire: RepertoireService) -> list[dict]:
    """Parse suite: one result per case."""

    async def one(case: dict) -> dict:
        try:
            dishes = await repertoire.parse(case["text"])
        except LLMError as exc:
            return {"id": case["id"], "checks": [("llm_call", False, str(exc))]}
        lo, hi = case["n_dishes"]
        checks: list[Check] = [("dish_count", lo <= len(dishes) <= hi, str(len(dishes)))]
        for i, expected in enumerate(case["dishes"]):
            if i < len(dishes):
                checks += [
                    (f"dish{i}.{n}", ok, d) for n, ok, d in check_parsed_dish(dishes[i], expected)
                ]
        return {"id": case["id"], "checks": checks}

    return await asyncio.gather(*(one(c) for c in PARSE_CASES))


async def run_diff(
    cousins: CousinService, graph: GraphService, dishes: DishRepository
) -> list[dict]:
    """Diff suite: write a diff for a fixed (anchor, dish) pair and check it."""

    async def one(case: dict) -> dict:
        anchor = UserDish.model_validate(ANCHORS[case["anchor"]])
        dish = dishes.get(case["dish"])
        if dish is None:
            return {"id": case["id"], "checks": [("dish_exists", False, case["dish"])]}
        delta = graph.compute_delta(
            anchor, dish, pantry_of([anchor.key_ingredients]), set(anchor.equipment)
        )
        diff = await cousins.write_diff(anchor, dish, delta)
        return {
            "id": case["id"],
            "checks": check_diff(diff, anchor, dish, delta),
            "sample": diff.model_dump(),
        }

    return await asyncio.gather(*(one(c) for c in DIFF_CASES))


async def run_e2e(repertoire: RepertoireService, graph: GraphService) -> list[dict]:
    """End-to-end suite: text → parse → cousins (graph only; diffs are covered above)."""

    async def one(case: dict) -> dict:
        try:
            user_dishes = await repertoire.parse(case["text"])
        except LLMError as exc:
            return {"id": case["id"], "checks": [("llm_call", False, str(exc))]}
        found = graph.find_cousins(user_dishes, settings.default_cousin_count)
        hits = sum(d.family == case["expect_family"] for d, _ in found)
        regions = len({d.region for d, _ in found})
        names = [d.name for d, _ in found]
        return {
            "id": case["id"],
            "cousins": names,
            "checks": [
                ("cousin_count", len(found) == settings.default_cousin_count, str(len(found))),
                ("family_hits", hits >= case["min_family_hits"], f"{hits} {case['expect_family']}"),
                ("region_spread", regions >= case["min_regions"], f"{regions} regions"),
            ],
        }

    return await asyncio.gather(*(one(c) for c in END_TO_END_CASES))


def run_diet(graph: GraphService, dishes: DishRepository) -> list[dict]:
    """Diet suite (code only, no LLM): each rule, swept over many kitchens, no violations.

    Kitchens are the fixed anchors plus every catalog dish cooked as a one-dish kitchen.
    For each, cousins, tonight's picks and the map are checked against both the dish's
    allergen tags and its ingredients.
    """
    kitchens = [[UserDish.model_validate(a)] for a in ANCHORS.values()]
    kitchens += [
        [UserDish.model_validate({**d.model_dump(), "notes": "", "matched_dish_id": d.id})]
        for d in dishes.all()
    ]
    rules: list[tuple[str, DietRule]] = [("vegetarian", DietRule(vegetarian=True))]
    rules += [(f"no_{a}", DietRule(avoid=frozenset({a}))) for a in ALLERGEN_KEYWORDS]
    results = []
    for rule_id, rule in rules:
        checked = 0
        bad: set[str] = set()
        for kitchen in kitchens:
            tonight = graph.pick_tonight(kitchen, rule)
            mapped, _ = graph.neighbourhood(kitchen, rule)
            shown = {d.id: d for d, _ in graph.find_cousins(kitchen, 8, rule)}
            shown.update({d.id: d for d, _ in mapped})
            shown.update({p[0].id: p[0] for p in (tonight.one_step, tonight.stretch) if p})
            checked += len(shown)
            bad |= {d.name for d in shown.values() if _violates(d, rule)}
        detail = f"{checked} suggestions over {len(kitchens)} kitchens; violations: {sorted(bad)}"
        results.append({"id": rule_id, "checks": [("no_violations", not bad, detail)]})
    return results


def _violates(dish, rule: DietRule) -> bool:
    """True if a shown dish breaks the rule by its tags or by any ingredient."""
    if rule.vegetarian and (
        not dish.vegetarian or any(is_meat_ingredient(i) for i in dish.key_ingredients)
    ):
        return True
    found = set(dish.allergens)
    for ingredient in dish.key_ingredients:
        found |= ingredient_allergens(ingredient)
    return bool(found & rule.avoid)


def summarize(suites: dict[str, list[dict]]) -> dict:
    """Print a readable report and return the JSON summary."""
    total = passed = 0
    report: dict = {
        "model": settings.llm_model,
        "run_at": datetime.now(UTC).isoformat(),
        "suites": {},
    }
    for name, results in suites.items():
        suite_total = suite_passed = 0
        for result in results:
            ok = sum(1 for _, p, _ in result["checks"] if p)
            suite_total += len(result["checks"])
            suite_passed += ok
            mark = "PASS" if ok == len(result["checks"]) else "FAIL"
            logger.info(
                "[%s] %-4s %-22s %d/%d", name, mark, result["id"], ok, len(result["checks"])
            )
            for check, p, detail in result["checks"]:
                if not p:
                    logger.info("        ✗ %s — %s", check, detail)
            result["checks"] = [
                {"name": c, "passed": p, "detail": d} for c, p, d in result["checks"]
            ]
        total += suite_total
        passed += suite_passed
        report["suites"][name] = {"passed": suite_passed, "total": suite_total, "results": results}
    report["passed"], report["total"] = passed, total
    report["pass_rate"] = round(passed / total, 3) if total else 0.0
    logger.info("Overall: %d/%d checks (%.0f%%)", passed, total, 100 * report["pass_rate"])
    return report


async def main() -> int:
    """Run the requested suites, write results, return the exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    wanted = set(sys.argv[1:]) or {"parse", "diff", "e2e", "diet"}
    repertoire, cousins, graph, dishes = build_services()
    suites: dict[str, list[dict]] = {}
    if "parse" in wanted:
        suites["parse"] = await run_parse(repertoire)
    if "diff" in wanted:
        suites["diff"] = await run_diff(cousins, graph, dishes)
    if "e2e" in wanted:
        suites["e2e"] = await run_e2e(repertoire, graph)
    if "diet" in wanted:
        suites["diet"] = run_diet(graph, dishes)
    report = summarize(suites)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return 0 if report["pass_rate"] >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
