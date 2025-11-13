"""Job definition and management for the task scheduler."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]


class Priority(Enum):
    """Job priority levels."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def __lt__(self, other):
        """Enable priority comparison for sorting."""
        priority_order = [Priority.URGENT, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        return priority_order.index(self) < priority_order.index(other)


class JobState(Enum):
    """Job execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobResult:
    """Result of a job execution."""

    success: bool
    timestamp: datetime
    message: str = ""
    duration_seconds: float = 0.0


@dataclass
class Job:
    """A scheduled job definition."""

    # Required fields
    id: str
    name: str
    command: str
    schedule: str  # Cron-like schedule string

    # Optional fields
    priority: Priority = Priority.MEDIUM
    description: str = ""
    enabled: bool = True
    max_retries: int = 0
    timeout_seconds: Optional[int] = None

    # Runtime state (not from YAML)
    state: JobState = field(default=JobState.PENDING, init=False)
    last_run: Optional[datetime] = field(default=None, init=False)
    last_result: Optional[JobResult] = field(default=None, init=False)
    retry_count: int = field(default=0, init=False)

    @classmethod
    def from_yaml(cls, path: Path) -> "Job":
        """Load job definition from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Job instance

        Raises:
            ValueError: If YAML is invalid or missing required fields
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML in {path}: expected dict, got {type(data)}")

        # Validate required fields
        required = ["id", "name", "command", "schedule"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields in {path}: {missing}")

        # Parse priority if present
        if "priority" in data:
            try:
                data["priority"] = Priority(data["priority"])
            except ValueError:
                valid = [p.value for p in Priority]
                raise ValueError(
                    f"Invalid priority '{data['priority']}' in {path}. "
                    f"Valid options: {valid}"
                )

        # Create job (extra fields will be ignored)
        valid_fields = {
            k: v
            for k, v in data.items()
            if k
            in [
                "id",
                "name",
                "command",
                "schedule",
                "priority",
                "description",
                "enabled",
                "max_retries",
                "timeout_seconds",
            ]
        }
        return cls(**valid_fields)

    def record_result(self, result: JobResult) -> None:
        """Record job execution result.

        Args:
            result: Execution result to record
        """
        self.last_run = result.timestamp
        self.last_result = result

        if result.success:
            self.state = JobState.COMPLETED
            self.retry_count = 0
        else:
            self.state = JobState.FAILED
            self.retry_count += 1

    def can_retry(self) -> bool:
        """Check if job can be retried after failure.

        Returns:
            True if retry is allowed, False otherwise
        """
        return self.state == JobState.FAILED and self.retry_count < self.max_retries

    def reset_state(self) -> None:
        """Reset job state for next execution."""
        self.state = JobState.PENDING
        self.retry_count = 0
