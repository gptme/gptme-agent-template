"""Base classes for input sources.

Input sources poll external systems (GitHub, Email, Webhooks, Scheduler)
and generate work items for autonomous processing.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List


class InputItem:
    """Represents an item of work from an input source."""

    def __init__(
        self,
        source: str,
        item_id: str,
        priority: str,
        title: str,
        description: str,
        metadata: Dict[str, Any] | None = None,
    ):
        """Initialize input item.

        Args:
            source: Source name (github, email, webhook, scheduler)
            item_id: Unique identifier for the item
            priority: Priority level (urgent, high, medium, low)
            title: Brief title/summary
            description: Full description or prompt
            metadata: Additional metadata (URLs, timestamps, etc.)
        """
        self.source = source
        self.item_id = item_id
        self.priority = priority
        self.title = title
        self.description = description
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source,
            "item_id": self.item_id,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class InputSource(ABC):
    """Base class for all input sources."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize input source with configuration.

        Args:
            config: Source-specific configuration dict
        """
        self.config = config
        self.name = self.__class__.__name__.replace("InputSource", "").lower()

    @abstractmethod
    async def poll(self) -> List[InputItem]:
        """Poll the input source for new items.

        Returns:
            List of new input items to process
        """
        pass

    @abstractmethod
    async def acknowledge(self, item_id: str) -> None:
        """Acknowledge that an item has been processed.

        Args:
            item_id: ID of the processed item
        """
        pass
