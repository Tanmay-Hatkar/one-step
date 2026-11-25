"""Feedback and anonymous usage stats: what the owner needs to see if the app is working."""

from collections import Counter
from datetime import UTC, datetime, timedelta

from app.models.api import UsageEvents, UsageStats
from app.repositories.insight_repository import InsightRepository

TOP_DISHES = 10
FEEDBACK_SHOWN = 50


class InsightService:
    """Records feedback and events, and sums them up."""

    def __init__(self, repo: InsightRepository) -> None:
        """Args: repo: feedback and event storage."""
        self._repo = repo

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
        return UsageStats(
            days=days,
            devices=len(active_days),
            returning_devices=sum(1 for d in active_days.values() if len(d) > 1),
            events=dict(Counter(name for _, name, _, _ in rows)),
            top_dishes=opened.most_common(TOP_DISHES),
            feedback=self._repo.recent_feedback(since, FEEDBACK_SHOWN),
        )
