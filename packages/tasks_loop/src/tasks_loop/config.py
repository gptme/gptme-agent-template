"""Configuration management for task scheduler."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]


@dataclass
class SchedulerConfig:
    """Configuration for the task scheduler."""

    # Job configuration
    jobs_dir: Path = Path("jobs")
    poll_interval_seconds: int = 60  # How often to check for jobs to run

    # Execution configuration
    default_timeout_seconds: int = 300  # 5 minutes
    max_concurrent_jobs: int = 1  # Run jobs sequentially by default

    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "SchedulerConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to configuration file

        Returns:
            SchedulerConfig instance
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid config YAML: expected dict, got {type(data)}")

        # Convert string paths to Path objects
        if "jobs_dir" in data:
            data["jobs_dir"] = Path(data["jobs_dir"])
        if "log_file" in data and data["log_file"]:
            data["log_file"] = Path(data["log_file"])

        # Filter to only valid fields
        valid_fields = {
            k: v
            for k, v in data.items()
            if k
            in [
                "jobs_dir",
                "poll_interval_seconds",
                "default_timeout_seconds",
                "max_concurrent_jobs",
                "log_level",
                "log_file",
            ]
        }

        return cls(**valid_fields)

    @classmethod
    def default(cls) -> "SchedulerConfig":
        """Create configuration with default values.

        Returns:
            SchedulerConfig with defaults
        """
        return cls()
