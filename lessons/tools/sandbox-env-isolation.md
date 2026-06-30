---
match:
  keywords:
    - "host_dir cleanup"
    - "include_user_context"
    - "sandbox tempdir leak"
    - "eval env isolation"
    - "sandbox runner config leak"
description: "Building or editing an eval/sandbox runner that auto-creates tempdirs without tracking ownership or leaks host ~/.config prompt files into the scored environment"
target_grade: trajectory_grade
status: active
---

# Eval / Sandbox Environment Isolation

## Rule
A sandboxed execution environment must (1) isolate from the host's user-level config and (2) own the lifecycle of every ephemeral resource it auto-creates.

## Context
When building or modifying eval runners, container exec envs, or any subprocess sandbox that runs benchmark/test workloads. Both isolation and lifecycle ownership prevent subtle result corruption and growing disk usage.

## Detection
Observable signals:
- Auto-creating `host_dir` / tempdir without tracking ownership
- Cleanup that stops the container but leaves the mkdtemp dir behind
- Eval scoring polluted by `~/.config` prompt files or user agent instructions
- `/tmp/<prefix>-*` dirs growing unbounded over time
- Caller can pass an external dir but cleanup unconditionally `rmtree`s it (or vice versa)

## Pattern

```python
# ✅ Track ownership; only clean what you created
class SandboxEnv:
    def __init__(self, host_dir: str | None = None, ...):
        self._owns_host_dir = host_dir is None
        self.host_dir = host_dir or tempfile.mkdtemp(prefix="sandbox-")

    def cleanup(self) -> None:
        if self.container_id:
            subprocess.run(["docker", "rm", "-f", self.container_id])
            self.container_id = None  # idempotent on second call
        if self._owns_host_dir and self.host_dir:
            shutil.rmtree(self.host_dir, ignore_errors=True)
```

```python
# ✅ Make user-context inclusion an explicit, defaulted-off knob for eval
def build_prompts(..., include_user_context: bool = False): ...

# eval CLI default = isolated (explicit opt-in to load user config)
parser.add_argument("--user-context", dest="user_context",
                    default=False, action=BooleanOptionalAction)
```

## Outcome
- No tempdir leaks accumulating across runs
- Benchmark scores reflect the model+prompt under test, not the operator's local config
- `cleanup()` is safe to call twice (defensive `__del__` doesn't blow up)
- External callers that pass their own `host_dir` still own it — no surprise deletes
