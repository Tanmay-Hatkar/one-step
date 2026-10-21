"""Read-only access to the latest eval results (written by `python -m evals.run`)."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BAKEOFF_FILE = "bakeoff.json"


class EvalResultsRepository:
    """Loads evals/results/latest.json (and the model bake-off next to it) once."""

    def __init__(self, path: Path) -> None:
        """Load the results files if they exist.

        Args:
            path: Path to latest.json. A missing or broken file means 'no results'.
                bakeoff.json in the same folder is optional.
        """
        self._results = _load(path)
        if self._results is not None:
            self._results["bakeoff"] = _load(path.with_name(BAKEOFF_FILE))

    def latest(self) -> dict[str, Any] | None:
        """Return the latest results (with a `bakeoff` key, possibly None), or None."""
        return self._results


def _load(path: Path) -> dict[str, Any] | None:
    """Parse a JSON file, or None if it's missing or broken."""
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("No eval results at %s", path)
        return None
