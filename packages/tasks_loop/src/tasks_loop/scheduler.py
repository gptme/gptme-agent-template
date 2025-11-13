"""Core task scheduler daemon."""

import logging
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

from croniter import croniter  # type: ignore[import-untyped]

from .config import SchedulerConfig
from .job import Job, JobResult, JobState


logger = logging.getLogger(__name__)


class TaskScheduler:
    """Main task scheduler that loads and executes jobs."""

    def __init__(self, config: Optional[SchedulerConfig] = None):
        """Initialize scheduler.

        Args:
            config: Scheduler configuration (uses defaults if None)
        """
        self.config = config or SchedulerConfig.default()
        self.jobs: Dict[str, Job] = {}
        self._running = False
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging based on config."""
        log_level = getattr(logging, self.config.log_level.upper())
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filename=self.config.log_file,
        )

    def load_jobs(self) -> int:
        """Load all job definitions from jobs directory.

        Returns:
            Number of jobs loaded
        """
        jobs_dir = self.config.jobs_dir
        if not jobs_dir.exists():
            logger.warning(f"Jobs directory does not exist: {jobs_dir}")
            return 0

        loaded = 0
        for yaml_file in jobs_dir.glob("*.yaml"):
            try:
                job = Job.from_yaml(yaml_file)
                self.jobs[job.id] = job
                loaded += 1
                logger.info(f"Loaded job: {job.id} ({job.name})")
            except Exception as e:
                logger.error(f"Failed to load job from {yaml_file}: {e}")

        logger.info(f"Loaded {loaded} jobs from {jobs_dir}")
        return loaded

    def get_jobs_due(self) -> List[Job]:
        """Get list of jobs that are due to run.

        Returns:
            List of jobs sorted by priority (highest first)
        """
        now = datetime.now()
        due_jobs = []

        for job in self.jobs.values():
            if not job.enabled:
                continue

            if job.state == JobState.RUNNING:
                continue

            # Check if job is due based on cron schedule
            if self._is_job_due(job, now):
                due_jobs.append(job)

        # Sort by priority (urgent first)
        due_jobs.sort(key=lambda j: j.priority)
        return due_jobs

    def _is_job_due(self, job: Job, now: datetime) -> bool:
        """Check if job is due to run based on schedule.

        Args:
            job: Job to check
            now: Current time

        Returns:
            True if job should run now
        """
        try:
            cron = croniter(job.schedule, now)
            next_run = cron.get_prev(datetime)

            # Job is due if last run was before the previous scheduled time
            if job.last_run is None:
                return True

            # Check if we've passed a scheduled run time since last execution
            return next_run > job.last_run

        except Exception as e:
            logger.error(f"Invalid cron schedule for job {job.id}: {e}")
            return False

    def execute_job(self, job: Job) -> JobResult:
        """Execute a single job.

        Args:
            job: Job to execute

        Returns:
            Execution result
        """
        logger.info(f"Executing job: {job.id} ({job.name})")
        job.state = JobState.RUNNING

        start_time = datetime.now()
        timeout = job.timeout_seconds or self.config.default_timeout_seconds

        try:
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            success = result.returncode == 0
            message = result.stdout if success else result.stderr

            job_result = JobResult(
                success=success,
                timestamp=datetime.now(),
                message=message.strip(),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

            if success:
                logger.info(f"Job {job.id} completed successfully")
            else:
                logger.error(f"Job {job.id} failed: {message}")

        except subprocess.TimeoutExpired:
            job_result = JobResult(
                success=False,
                timestamp=datetime.now(),
                message=f"Job timed out after {timeout} seconds",
                duration_seconds=timeout,
            )
            logger.error(f"Job {job.id} timed out")

        except Exception as e:
            job_result = JobResult(
                success=False,
                timestamp=datetime.now(),
                message=f"Execution error: {str(e)}",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )
            logger.error(f"Job {job.id} failed with exception: {e}")

        job.record_result(job_result)
        return job_result

    def run_once(self) -> int:
        """Run one scheduler cycle (check and execute due jobs).

        Returns:
            Number of jobs executed
        """
        due_jobs = self.get_jobs_due()

        if not due_jobs:
            logger.debug("No jobs due")
            return 0

        logger.info(f"Found {len(due_jobs)} jobs due")
        executed = 0

        for job in due_jobs[: self.config.max_concurrent_jobs]:
            try:
                self.execute_job(job)
                executed += 1
            except Exception as e:
                logger.error(f"Unexpected error executing job {job.id}: {e}")

        return executed

    def run(self) -> None:
        """Run scheduler daemon (infinite loop)."""
        logger.info("Starting task scheduler daemon")
        self._running = True

        self.load_jobs()

        while self._running:
            try:
                self.run_once()
                time.sleep(self.config.poll_interval_seconds)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self._running = False
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(self.config.poll_interval_seconds)

        logger.info("Task scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler daemon."""
        logger.info("Stopping task scheduler")
        self._running = False
