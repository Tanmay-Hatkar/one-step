"""Share a kitchen as a short link, and open one."""

import json
import logging

from pydantic import ValidationError

from app.models.api import SharedKitchenResponse
from app.models.dish import UserDish
from app.repositories.share_repository import ShareRepository

logger = logging.getLogger(__name__)


class ShareService:
    """Snapshots are stored as JSON and re-validated when read."""

    def __init__(self, repo: ShareRepository) -> None:
        """Args: repo: share storage."""
        self._repo = repo

    def create(self, dishes: list[UserDish]) -> str:
        """Store a snapshot of the kitchen and return its id.

        Raises:
            ShareStoreError: If it can't be saved.
        """
        payload = json.dumps({"dishes": [d.model_dump() for d in dishes]})
        return self._repo.create(payload)

    def get(self, share_id: str) -> SharedKitchenResponse | None:
        """Return a shared kitchen, or None if the id is unknown or the snapshot is unusable.

        Raises:
            ShareStoreError: If storage can't be read.
        """
        row = self._repo.get(share_id)
        if row is None:
            return None
        try:
            dishes = [UserDish.model_validate(d) for d in json.loads(row.payload_json)["dishes"]]
        except (json.JSONDecodeError, KeyError, ValidationError):
            logger.exception("Unreadable share %s", share_id)
            return None
        return SharedKitchenResponse(dishes=dishes, created_at=row.created_at.isoformat())
