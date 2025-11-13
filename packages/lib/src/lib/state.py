"""State tracking for input orchestrator.

Tracks which items have been processed to prevent duplicate work.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Set


class StateTracker:
    """Tracks processed items across sessions."""

    def __init__(self, state_file: Path):
        """Initialize state tracker.

        Args:
            state_file: Path to state persistence file
        """
        self.state_file = state_file
        self.processed: Dict[str, Set[str]] = {}  # source -> set of item_ids
        self.timestamps: Dict[
            str, Dict[str, str]
        ] = {}  # source -> {item_id: timestamp}
        self._load()

    def _load(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            # Convert lists back to sets
            self.processed = {
                source: set(items)
                for source, items in data.get("processed", {}).items()
            }
            self.timestamps = data.get("timestamps", {})
        except (json.JSONDecodeError, IOError):
            # Start fresh if state file is corrupted
            self.processed = {}
            self.timestamps = {}

    def _save(self) -> None:
        """Persist state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert sets to lists for JSON serialization
        data = {
            "processed": {
                source: list(items) for source, items in self.processed.items()
            },
            "timestamps": self.timestamps,
        }

        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def is_processed(self, source: str, item_id: str) -> bool:
        """Check if an item has been processed.

        Args:
            source: Source name
            item_id: Item identifier

        Returns:
            True if item was already processed
        """
        return item_id in self.processed.get(source, set())

    def mark_processed(self, source: str, item_id: str) -> None:
        """Mark an item as processed.

        Args:
            source: Source name
            item_id: Item identifier
        """
        if source not in self.processed:
            self.processed[source] = set()
        if source not in self.timestamps:
            self.timestamps[source] = {}

        self.processed[source].add(item_id)
        self.timestamps[source][item_id] = datetime.now().isoformat()
        self._save()

    def get_processed_count(self, source: str) -> int:
        """Get count of processed items for a source.

        Args:
            source: Source name

        Returns:
            Number of processed items
        """
        return len(self.processed.get(source, set()))
