#!/usr/bin/env python3
"""Opt-in trigger gate for scheduled autonomous agent runs.

Exit codes are part of the contract:
- 0: no trigger; skip this scheduled run
- 1: at least one trigger fired; run the agent
- 2: gate error
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SKIP = 0
RUN = 1
ERROR = 2
UTC = timezone.utc


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid gate state JSON at {path}: {exc}") from exc


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def split_paths(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def iter_inbox_files(workspace: Path, inbox_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in inbox_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = workspace / path
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                item
                for item in path.rglob("*")
                if item.is_file() and not item.name.startswith(".")
            )
    return files


def inbox_triggers(workspace: Path, inbox_paths: list[str]) -> list[str]:
    reasons: list[str] = []
    for path in iter_inbox_files(workspace, inbox_paths):
        try:
            text = path.read_text(errors="replace")[:8192].lower()
        except OSError:
            continue
        if (
            "needs_reply: true" in text
            or "needs-reply: true" in text
            or "replied: false" in text
            or "unread: true" in text
        ):
            reasons.append(f"inbox:{path.relative_to(workspace)}")
    return reasons


def github_triggers(command: str | None, timeout_seconds: int) -> list[str]:
    if not command:
        return []
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0 and output and output not in {"0", "[]", "null"}:
        return ["github-command"]
    return []


def newest_mtime(path: Path) -> datetime | None:
    if not path.exists():
        return None
    if path.is_file():
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    newest: datetime | None = None
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=UTC)
        if newest is None or mtime > newest:
            newest = mtime
    return newest


def stale_work_triggers(
    workspace: Path, paths: list[str], now: datetime, threshold: timedelta
) -> list[str]:
    reasons: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = workspace / path
        mtime = newest_mtime(path)
        if mtime is not None and now - mtime >= threshold:
            try:
                label = str(path.relative_to(workspace))
            except ValueError:
                label = str(path)
            reasons.append(f"stale-work:{label}")
    return reasons


def decide(args: argparse.Namespace) -> tuple[int, list[str], dict[str, Any]]:
    workspace = Path(args.workspace).resolve()
    state_file = Path(args.state_file)
    if not state_file.is_absolute():
        state_file = workspace / state_file

    state = read_state(state_file)
    now = datetime.now(UTC)
    reasons: list[str] = []

    last_allowed_at = parse_dt(state.get("last_allowed_at"))
    blocked_until = parse_dt(state.get("blocked_until"))

    reasons.extend(inbox_triggers(workspace, split_paths(args.inbox_paths)))
    reasons.extend(github_triggers(args.github_command, args.github_timeout_seconds))
    reasons.extend(
        stale_work_triggers(
            workspace,
            split_paths(args.stale_work_paths),
            now,
            timedelta(minutes=args.stale_work_minutes),
        )
    )

    if last_allowed_at is None:
        reasons.append("first-run")
    elif now - last_allowed_at >= timedelta(hours=args.max_interval_hours):
        reasons.append("max-interval")

    if blocked_until and now < blocked_until and not reasons:
        state["last_checked_at"] = now.isoformat()
        state["last_decision"] = "skip"
        state["last_reasons"] = ["blocked-until"]
        return SKIP, ["blocked-until"], state

    if reasons:
        state["last_allowed_at"] = now.isoformat()
        state["last_checked_at"] = now.isoformat()
        state["last_decision"] = "run"
        state["last_reasons"] = reasons
        return RUN, reasons, state

    if last_allowed_at and now - last_allowed_at < timedelta(
        minutes=args.min_interval_minutes
    ):
        reasons.append("usage-pacing")

    state["last_checked_at"] = now.isoformat()
    state["last_decision"] = "skip"
    state["last_reasons"] = reasons
    return SKIP, reasons, state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.getcwd())
    parser.add_argument(
        "--state-file",
        default=os.environ.get("SESSION_GATE_STATE_FILE", "state/session-gate.json"),
    )
    parser.add_argument(
        "--inbox-paths",
        default=os.environ.get(
            "SESSION_GATE_INBOX_PATHS", "messages/inbox,email/inbox"
        ),
        help="Comma-separated inbox files or directories to scan for reply markers.",
    )
    parser.add_argument(
        "--github-command",
        default=os.environ.get("SESSION_GATE_GITHUB_COMMAND"),
        help="Optional local command; non-empty successful output triggers a run.",
    )
    parser.add_argument(
        "--github-timeout-seconds",
        type=int,
        default=int(os.environ.get("SESSION_GATE_GITHUB_TIMEOUT_SECONDS", "20")),
    )
    parser.add_argument(
        "--stale-work-paths",
        default=os.environ.get("SESSION_GATE_STALE_WORK_PATHS", ""),
        help="Comma-separated files/directories whose age should wake a maintenance run.",
    )
    parser.add_argument(
        "--stale-work-minutes",
        type=int,
        default=int(os.environ.get("SESSION_GATE_STALE_WORK_MINUTES", "1440")),
    )
    parser.add_argument(
        "--min-interval-minutes",
        type=int,
        default=int(os.environ.get("SESSION_GATE_MIN_INTERVAL_MINUTES", "30")),
    )
    parser.add_argument(
        "--max-interval-hours",
        type=int,
        default=int(os.environ.get("SESSION_GATE_MAX_INTERVAL_HOURS", "24")),
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code, reasons, state = decide(args)
        state_file = Path(args.state_file)
        if not state_file.is_absolute():
            state_file = Path(args.workspace).resolve() / state_file
        write_state(state_file, state)
    except (OSError, subprocess.TimeoutExpired, SystemExit) as exc:
        print(f"session-gate: {exc}", file=sys.stderr)
        return ERROR

    if args.verbose:
        decision = "run" if exit_code == RUN else "skip"
        reason_text = ", ".join(reasons) if reasons else "no triggers"
        print(f"session-gate: {decision} ({reason_text})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
