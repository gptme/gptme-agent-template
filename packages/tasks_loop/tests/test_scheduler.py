"""Tests for task scheduler."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import pytest

from tasks_loop import (
    Job,
    JobResult,
    JobState,
    Priority,
    SchedulerConfig,
    TaskScheduler,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_job_yaml(temp_dir):
    """Create sample job YAML file."""
    jobs_dir = temp_dir / "jobs"
    jobs_dir.mkdir()

    job_file = jobs_dir / "test-job.yaml"
    job_file.write_text("""
id: test-job
name: Test Job
description: A test job
command: echo "test"
schedule: "*/5 * * * *"
priority: high
enabled: true
max_retries: 2
timeout_seconds: 60
""")

    return job_file


class TestJob:
    """Tests for Job class."""

    def test_create_job(self):
        """Test creating a job."""
        job = Job(
            id="test",
            name="Test Job",
            command="echo test",
            schedule="*/5 * * * *",
        )

        assert job.id == "test"
        assert job.name == "Test Job"
        assert job.command == "echo test"
        assert job.schedule == "*/5 * * * *"
        assert job.priority == Priority.MEDIUM
        assert job.state == JobState.PENDING

    def test_load_from_yaml(self, sample_job_yaml):
        """Test loading job from YAML."""
        job = Job.from_yaml(sample_job_yaml)

        assert job.id == "test-job"
        assert job.name == "Test Job"
        assert job.command == 'echo "test"'
        assert job.schedule == "*/5 * * * *"
        assert job.priority == Priority.HIGH
        assert job.max_retries == 2

    def test_invalid_yaml_missing_fields(self, temp_dir):
        """Test loading invalid YAML with missing fields."""
        jobs_dir = temp_dir / "jobs"
        jobs_dir.mkdir()

        invalid_file = jobs_dir / "invalid.yaml"
        invalid_file.write_text("""
id: invalid-job
name: Invalid Job
""")

        with pytest.raises(ValueError, match="Missing required fields"):
            Job.from_yaml(invalid_file)

    def test_invalid_priority(self, temp_dir):
        """Test loading job with invalid priority."""
        jobs_dir = temp_dir / "jobs"
        jobs_dir.mkdir()

        invalid_file = jobs_dir / "invalid.yaml"
        invalid_file.write_text("""
id: test-job
name: Test Job
command: echo test
schedule: "* * * * *"
priority: invalid_priority
""")

        with pytest.raises(ValueError, match="Invalid priority"):
            Job.from_yaml(invalid_file)

    def test_record_result_success(self):
        """Test recording successful job result."""
        job = Job(id="test", name="Test", command="echo test", schedule="* * * * *")

        result = JobResult(
            success=True,
            timestamp=datetime.now(),
            message="Success",
            duration_seconds=1.5,
        )

        job.record_result(result)

        assert job.state == JobState.COMPLETED
        assert job.last_result == result
        assert job.retry_count == 0

    def test_record_result_failure(self):
        """Test recording failed job result."""
        job = Job(id="test", name="Test", command="echo test", schedule="* * * * *")

        result = JobResult(
            success=False,
            timestamp=datetime.now(),
            message="Failed",
            duration_seconds=1.0,
        )

        job.record_result(result)

        assert job.state == JobState.FAILED
        assert job.retry_count == 1

    def test_can_retry(self):
        """Test retry logic."""
        job = Job(
            id="test",
            name="Test",
            command="echo test",
            schedule="* * * * *",
            max_retries=2,
        )

        # Initially no retries
        assert not job.can_retry()

        # After first failure
        job.state = JobState.FAILED
        job.retry_count = 1
        assert job.can_retry()

        # After max retries
        job.retry_count = 2
        assert not job.can_retry()


class TestSchedulerConfig:
    """Tests for SchedulerConfig class."""

    def test_default_config(self):
        """Test creating config with defaults."""
        config = SchedulerConfig.default()

        assert config.jobs_dir == Path("jobs")
        assert config.poll_interval_seconds == 60
        assert config.max_concurrent_jobs == 1

    def test_load_from_yaml(self, temp_dir):
        """Test loading config from YAML."""
        config_file = temp_dir / "config.yaml"
        config_file.write_text("""
jobs_dir: custom/jobs
poll_interval_seconds: 30
max_concurrent_jobs: 2
log_level: DEBUG
""")

        config = SchedulerConfig.from_yaml(config_file)

        assert config.jobs_dir == Path("custom/jobs")
        assert config.poll_interval_seconds == 30
        assert config.max_concurrent_jobs == 2
        assert config.log_level == "DEBUG"


class TestTaskScheduler:
    """Tests for TaskScheduler class."""

    def test_create_scheduler(self):
        """Test creating scheduler with default config."""
        scheduler = TaskScheduler()

        assert isinstance(scheduler.config, SchedulerConfig)
        assert scheduler.jobs == {}
        assert not scheduler._running

    def test_load_jobs(self, temp_dir, sample_job_yaml):
        """Test loading jobs from directory."""
        config = SchedulerConfig(jobs_dir=temp_dir / "jobs")
        scheduler = TaskScheduler(config)

        count = scheduler.load_jobs()

        assert count == 1
        assert "test-job" in scheduler.jobs
        assert scheduler.jobs["test-job"].name == "Test Job"

    def test_load_jobs_empty_directory(self, temp_dir):
        """Test loading from empty jobs directory."""
        jobs_dir = temp_dir / "jobs"
        jobs_dir.mkdir()

        config = SchedulerConfig(jobs_dir=jobs_dir)
        scheduler = TaskScheduler(config)

        count = scheduler.load_jobs()
        assert count == 0

    def test_load_jobs_missing_directory(self, temp_dir):
        """Test loading from nonexistent directory."""
        config = SchedulerConfig(jobs_dir=temp_dir / "nonexistent")
        scheduler = TaskScheduler(config)

        count = scheduler.load_jobs()
        assert count == 0

    @patch("tasks_loop.scheduler.subprocess.run")
    def test_execute_job_success(self, mock_run):
        """Test successful job execution."""
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        job = Job(
            id="test",
            name="Test",
            command="echo test",
            schedule="* * * * *",
        )

        scheduler = TaskScheduler()
        result = scheduler.execute_job(job)

        assert result.success
        assert job.state == JobState.COMPLETED
        assert "Success" in result.message

    @patch("tasks_loop.scheduler.subprocess.run")
    def test_execute_job_failure(self, mock_run):
        """Test failed job execution."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error occurred")

        job = Job(
            id="test",
            name="Test",
            command="false",
            schedule="* * * * *",
        )

        scheduler = TaskScheduler()
        result = scheduler.execute_job(job)

        assert not result.success
        assert job.state == JobState.FAILED
        assert "Error occurred" in result.message

    def test_get_jobs_due_empty(self):
        """Test getting due jobs when none exist."""
        scheduler = TaskScheduler()
        due_jobs = scheduler.get_jobs_due()

        assert due_jobs == []

    def test_get_jobs_due_disabled(self):
        """Test that disabled jobs are not returned."""
        job = Job(
            id="test",
            name="Test",
            command="echo test",
            schedule="* * * * *",
            enabled=False,
        )

        scheduler = TaskScheduler()
        scheduler.jobs[job.id] = job

        due_jobs = scheduler.get_jobs_due()
        assert due_jobs == []

    def test_get_jobs_due_priority_order(self):
        """Test that due jobs are sorted by priority."""
        jobs = [
            Job(
                id="low",
                name="Low",
                command="echo",
                schedule="* * * * *",
                priority=Priority.LOW,
            ),
            Job(
                id="urgent",
                name="Urgent",
                command="echo",
                schedule="* * * * *",
                priority=Priority.URGENT,
            ),
            Job(
                id="medium",
                name="Medium",
                command="echo",
                schedule="* * * * *",
                priority=Priority.MEDIUM,
            ),
            Job(
                id="high",
                name="High",
                command="echo",
                schedule="* * * * *",
                priority=Priority.HIGH,
            ),
        ]

        scheduler = TaskScheduler()
        for job in jobs:
            scheduler.jobs[job.id] = job

        due_jobs = scheduler.get_jobs_due()

        # Should be sorted: urgent, high, medium, low
        assert [j.id for j in due_jobs] == ["urgent", "high", "medium", "low"]

    @patch("tasks_loop.scheduler.subprocess.run")
    def test_run_once(self, mock_run):
        """Test running one scheduler cycle."""
        mock_run.return_value = Mock(returncode=0, stdout="OK", stderr="")

        job = Job(
            id="test",
            name="Test",
            command="echo test",
            schedule="* * * * *",  # Every minute
        )

        scheduler = TaskScheduler()
        scheduler.jobs[job.id] = job

        executed = scheduler.run_once()

        assert executed == 1
        assert job.state == JobState.COMPLETED
