"""Technique how-to cards, loaded once from api/data/techniques.json."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.models.technique import TechniqueGuide

logger = logging.getLogger(__name__)


class TechniqueRepository:
    """All technique guides. Read-only; a missing file means no guides."""

    def __init__(self, path: Path) -> None:
        """Args: path to techniques.json."""
        self._guides: list[TechniqueGuide] = []
        try:
            self._guides = [TechniqueGuide.model_validate(g) for g in json.loads(path.read_text())]
        except FileNotFoundError:
            logger.warning("No technique guides at %s", path)
        except (json.JSONDecodeError, ValidationError):
            logger.exception("Unreadable technique guides at %s", path)

    def all(self) -> list[TechniqueGuide]:
        """Every guide, in vocabulary order."""
        return list(self._guides)
