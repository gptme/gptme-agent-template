"""Tests for input orchestrator."""

from typing import List

import pytest

from lib.input_sources import InputItem, InputSource
from lib.orchestrator import InputSourceOrchestrator
from lib.state import StateTracker


class MockInputSource(InputSource):
    """Mock input source for testing."""

    def __init__(self, config, items=None):
        super().__init__(config)
        self.items = items or []
        self.acknowledged = []

    async def poll(self) -> List[InputItem]:
        """Return mock items."""
        return self.items

    async def acknowledge(self, item_id: str) -> None:
        """Track acknowledged items."""
        self.acknowledged.append(item_id)


@pytest.fixture
def temp_state_file(tmp_path):
    """Provide temporary state file path."""
    return tmp_path / "state.json"


@pytest.fixture
def mock_items():
    """Create mock input items."""
    return [
        InputItem(
            source="test",
            item_id="item1",
            priority="high",
            title="Test Item 1",
            description="Description 1",
        ),
        InputItem(
            source="test",
            item_id="item2",
            priority="low",
            title="Test Item 2",
            description="Description 2",
        ),
    ]


def test_state_tracker_persistence(temp_state_file):
    """Test state tracker saves and loads correctly."""
    # Create tracker and mark item processed
    tracker1 = StateTracker(temp_state_file)
    tracker1.mark_processed("test", "item1")

    assert tracker1.is_processed("test", "item1")
    assert not tracker1.is_processed("test", "item2")

    # Load in new tracker instance
    tracker2 = StateTracker(temp_state_file)
    assert tracker2.is_processed("test", "item1")
    assert not tracker2.is_processed("test", "item2")


def test_state_tracker_counts(temp_state_file):
    """Test processed item counting."""
    tracker = StateTracker(temp_state_file)

    assert tracker.get_processed_count("test") == 0

    tracker.mark_processed("test", "item1")
    assert tracker.get_processed_count("test") == 1

    tracker.mark_processed("test", "item2")
    assert tracker.get_processed_count("test") == 2


@pytest.mark.asyncio
async def test_orchestrator_polls_sources(temp_state_file, mock_items):
    """Test orchestrator polls sources correctly."""
    mock_source = MockInputSource({}, items=mock_items)

    orchestrator = InputSourceOrchestrator(
        sources={"test": mock_source},
        state_file=temp_state_file,
        poll_intervals={"test": 1},
    )

    # Poll should return items
    items = await orchestrator.poll_source("test", mock_source)
    assert len(items) == 2

    # Mark as processed
    for item in items:
        orchestrator.state.mark_processed("test", item.item_id)

    # Second poll should return no new items (already processed)
    items2 = await orchestrator.poll_source("test", mock_source)
    assert len(items2) == 0


@pytest.mark.asyncio
async def test_orchestrator_priority_sorting(temp_state_file):
    """Test items are processed in priority order."""
    items = [
        InputItem("test", "low1", "low", "Low", "Low priority"),
        InputItem("test", "urgent1", "urgent", "Urgent", "Urgent priority"),
        InputItem("test", "medium1", "medium", "Medium", "Medium priority"),
        InputItem("test", "high1", "high", "High", "High priority"),
    ]

    mock_source = MockInputSource({}, items=items)
    orchestrator = InputSourceOrchestrator(
        sources={"test": mock_source},
        state_file=temp_state_file,
    )

    await orchestrator.poll_cycle()

    # Check items were processed in priority order
    # (urgent, high, medium, low)
    expected_order = ["urgent1", "high1", "medium1", "low1"]
    assert mock_source.acknowledged == expected_order
