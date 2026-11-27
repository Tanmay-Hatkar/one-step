"""Feedback and anonymous usage stats: what the owner needs to see if the app is working."""

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.models.api import UsageEvents, UsageStats
from app.repositories.insight_repository import InsightRepository
from app.repositories.llm_repository import LLMUsageRepository

logger = logging.getLogger(__name__)

TOP_DISHES = 10
FEEDBACK_SHOWN = 50
TOKENS_PER_MILLION = 1_000_000

# The path a visitor takes, as (label, events that count). A device reaches a step if it
# sent any of those events in the window. "came back" is computed from active days.
FUNNEL_STEPS: list[tuple[str, frozenset[str]]] = [
    ("visited", frozenset({"landed"})),
    ("built a kitchen", frozenset({"kitchen_built"})),
    ("saw results", frozenset({"results_shown"})),
    ("opened a dish", frozenset({"dish_opened", "cook_mode"})),
    ("saved or cooked", frozenset({"saved", "cooked"})),
]
CAME_BACK = "came back"


def funnel_of(rows: list[tuple[str, str, str | None, datetime]]) -> list[tuple[str, int]]:
    """Count devices at each funnel step.

    Args:
        rows: (device, event name, dish id, time) for the window.

    Returns:
        (step label, devices) in funnel order, ending with devices active on 2+ days.
    """
    by_event: dict[str, set[str]] = {}
    days: dict[str, set] = {}
    for device, name, _, at in rows:
        by_event.setdefault(name, set()).add(device)
        days.setdefault(device, set()).add(at.date())
    steps = [
        (label, len(set().union(*(by_event.get(n, set()) for n in names))))
        for label, names in FUNNEL_STEPS
    ]
    steps.append((CAME_BACK, sum(1 for d in days.values() if len(d) > 1)))
    return steps


class InsightService:
    """Records feedback and events, and sums them up."""

    def __init__(
        self,
        repo: InsightRepository,
        usage: LLMUsageRepository | None = None,
        input_usd_per_million: float = 0.0,
        output_usd_per_million: float = 0.0,
    ) -> None:
        """Create the service.

        Args:
            repo: Feedback and event storage.
            usage: LLM call and token totals; None leaves cost out of the stats.
            input_usd_per_million: Price of input tokens.
            output_usd_per_million: Price of output tokens.
        """
        self._repo = repo
        self._usage = usage
        self._input_price = input_usd_per_million
        self._output_price = output_usd_per_million

    def feedback(self, message: str, page: str) -> None:
        """Store a feedback message (trimmed).

        Raises:
            InsightStoreError: If it can't be saved.
        """
        self._repo.add_feedback(message.strip(), page.strip())

    def record(self, batch: UsageEvents) -> None:
        """Store a batch of events from one device.

        Raises:
            InsightStoreError: If they can't be saved.
        """
        self._repo.add_events(batch.device, [(e.name, e.dish_id) for e in batch.events])

    def stats(self, days: int) -> UsageStats:
        """Devices, returning devices, event counts, top dishes and feedback for the last days.

        Raises:
            InsightStoreError: If storage can't be read.
        """
        since = datetime.now(UTC) - timedelta(days=days)
        rows = self._repo.events_since(since)
        active_days: dict[str, set] = {}
        for device, _, _, at in rows:
            active_days.setdefault(device, set()).add(at.date())
        opened = Counter(dish for _, name, dish, _ in rows if name == "dish_opened" and dish)
        calls, tokens_in, tokens_out = self._llm_totals(since)
        cost = (
            tokens_in * self._input_price + tokens_out * self._output_price
        ) / TOKENS_PER_MILLION
        devices = len(active_days)
        return UsageStats(
            days=days,
            devices=devices,
            returning_devices=sum(1 for d in active_days.values() if len(d) > 1),
            events=dict(Counter(name for _, name, _, _ in rows)),
            top_dishes=opened.most_common(TOP_DISHES),
            feedback=self._repo.recent_feedback(since, FEEDBACK_SHOWN),
            funnel=funnel_of(rows),
            llm_calls=calls,
            llm_input_tokens=tokens_in,
            llm_output_tokens=tokens_out,
            llm_cost_usd=round(cost, 4),
            llm_cost_per_device_usd=round(cost / devices, 5) if devices else 0.0,
        )

    def _llm_totals(self, since: datetime) -> tuple[int, int, int]:
        """Calls and tokens since a moment; zeros if not wired or unreadable (cost is optional)."""
        if self._usage is None:
            return 0, 0, 0
        try:
            return self._usage.totals_since(since.date())
        except SQLAlchemyError:
            logger.exception("LLM usage read failed; leaving cost out of the stats")
            return 0, 0, 0
