"""Read-only access to the latest eval results (written by `python -m evals.run`)."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EvalResultsRepository:
    """Loads evals/results/latest.json once; serves it from memory."""

    def __init__(self, path: Path) -> None:
        """Load the results file if it exists.

        Args:
            path: Path to latest.json. A missing or broken file means 'no results'.
        """
        try:
            self._results: dict[str, Any] | None = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            logger.warning("No eval results at %s", path)
            self._results = None

    def latest(self) -> dict[str, Any] | None:
        """Return the latest results, or None."""
        return self._results
