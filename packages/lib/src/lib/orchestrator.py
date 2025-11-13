"""Input sources orchestrator.

Coordinates polling of all configured input sources and creates tasks
from external sources like GitHub issues, emails, webhooks, and scheduled triggers.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

from .input_sources import InputItem, InputSource
from .state import StateTracker


class InputSourceOrchestrator:
    """Orchestrates polling and processing of all input sources."""

    def __init__(
        self,
        sources: Dict[str, InputSource],
        state_file: Path,
        poll_intervals: Dict[str, int] | None = None,
    ):
        """Initialize orchestrator with configuration.

        Args:
            sources: Dictionary of source_name -> InputSource instances
            state_file: Path to state persistence file
            poll_intervals: Optional dict of source_name -> interval_seconds
        """
        self.sources = sources
        self.state = StateTracker(state_file)
        self.poll_intervals = poll_intervals or {}
        self.last_poll: Dict[str, datetime] = {}
        self.running = False

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # Initialize last poll times
        for source_name in self.sources:
            self.last_poll[source_name] = datetime.min

    def _should_poll(self, source_name: str) -> bool:
        """Check if a source should be polled now.

        Args:
            source_name: Name of the source

        Returns:
            True if enough time has passed since last poll
        """
        interval = self.poll_intervals.get(source_name, 300)  # Default 5 min
        time_since_poll = datetime.now() - self.last_poll[source_name]
        return time_since_poll >= timedelta(seconds=interval)

    async def poll_source(
        self, source_name: str, source: InputSource
    ) -> List[InputItem]:
        """Poll a single source for new items.

        Args:
            source_name: Name of the source
            source: InputSource instance

        Returns:
            List of new (unprocessed) items
        """
        try:
            self.logger.info(f"Polling {source_name}")
            items = await source.poll()

            # Filter out already-processed items
            new_items = [
                item
                for item in items
                if not self.state.is_processed(source_name, item.item_id)
            ]

            if new_items:
                self.logger.info(
                    f"Found {len(new_items)} new items from {source_name} "
                    f"({len(items) - len(new_items)} already processed)"
                )

            self.last_poll[source_name] = datetime.now()
            return new_items

        except Exception as e:
            self.logger.error(f"Error polling {source_name}: {e}")
            return []

    async def process_item(self, item: InputItem) -> bool:
        """Process a single input item.

        Args:
            item: Input item to process

        Returns:
            True if processing succeeded
        """
        try:
            self.logger.info(
                f"Processing {item.source} item: {item.item_id} - {item.title}"
            )

            # TODO: Implement actual processing logic
            # This is where you would:
            # 1. Create task file
            # 2. Add to work queue
            # 3. Trigger autonomous run (optional)

            # Mark as processed
            self.state.mark_processed(item.source, item.item_id)

            # Acknowledge with source
            source = self.sources[item.source]
            await source.acknowledge(item.item_id)

            return True

        except Exception as e:
            self.logger.error(f"Error processing item {item.item_id}: {e}")
            return False

    async def poll_cycle(self) -> None:
        """Execute one polling cycle across all sources."""
        all_items: List[InputItem] = []

        # Poll all sources that are due
        for source_name, source in self.sources.items():
            if self._should_poll(source_name):
                items = await self.poll_source(source_name, source)
                all_items.extend(items)

        # Process items by priority
        all_items.sort(
            key=lambda x: {
                "urgent": 0,
                "high": 1,
                "medium": 2,
                "low": 3,
            }.get(x.priority, 4)
        )

        for item in all_items:
            await self.process_item(item)

    async def run(self, interval: int = 60) -> None:
        """Run orchestrator continuously.

        Args:
            interval: Sleep interval between poll cycles (seconds)
        """
        self.running = True
        self.logger.info("Input orchestrator started")

        while self.running:
            try:
                await self.poll_cycle()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                self.logger.info("Shutting down...")
                self.running = False
            except Exception as e:
                self.logger.error(f"Error in poll cycle: {e}")
                await asyncio.sleep(interval)
