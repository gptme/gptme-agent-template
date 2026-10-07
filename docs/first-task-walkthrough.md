# First-task walkthrough

*Last verified: 2026-10-07 against gptme 0.34.0. The fixture is disposable —
nothing in this exercise belongs in the agent workspace.*

The [README quick start](../README.md#quick-start) gets you to `gptme "hello"`.
This is the next step: a failing pytest, the commands that ask the agent to
fix it, and captured before/after results from a fresh-directory dry run.

This is not identity setup
([`tasks/templates/initial-agent-setup.md`](../tasks/templates/initial-agent-setup.md))
and not long-term operations
([`operating-an-agent.md`](./operating-an-agent.md)). Those are different
jobs. This one is: can the agent change code against a real test.

Keep the files **outside** the agent repo. A first task that writes into
`~/my-agent` trains the wrong habit — the brain is for identity, tasks, and
journal, not throwaway fixtures.

## 1. Create a throwaway fixture

```sh
mkdir -p /tmp/first-task
cd /tmp/first-task
```

`clamp.py`:

```python
def clamp(n: int, lo: int, hi: int) -> int:
    """Return n limited to the inclusive range [lo, hi]."""
    return n
```

`test_clamp.py`:

```python
from clamp import clamp


def test_clamp_below_range():
    assert clamp(-5, 0, 10) == 0


def test_clamp_inside_range():
    assert clamp(3, 0, 10) == 3


def test_clamp_above_range():
    assert clamp(99, 0, 10) == 10
```

The implementation is deliberately wrong. The tests are the spec.

## 2. Confirm it fails

Needs `pytest` (`pipx install pytest` or `uvx pytest` if you don't have it).

```sh
python3 -m pytest -q --tb=short
```

Dry-run output, 2026-10-07, fresh directory:

```text
F.F                                                                      [100%]
=================================== FAILURES ===================================
____________________________ test_clamp_below_range ____________________________
test_clamp.py:5: in test_clamp_below_range
    assert clamp(-5, 0, 10) == 0
E   assert -5 == 0
E    +  where -5 = clamp(-5, 0, 10)
____________________________ test_clamp_above_range ____________________________
test_clamp.py:13: in test_clamp_above_range
    assert clamp(99, 0, 10) == 10
E   assert 99 == 10
E    +  where 99 = clamp(99, 0, 10)
=========================== short test summary info ============================
FAILED test_clamp.py::test_clamp_below_range - assert -5 == 0
 +  where -5 = clamp(-5, 0, 10)
FAILED test_clamp.py::test_clamp_above_range - assert 99 == 10
 +  where 99 = clamp(99, 0, 10)
2 failed, 1 passed in 0.02s
```

The middle test passes because `3` is already in range. Two failures is the
signal the agent should see.

## 3. Have the agent fix it

From the fixture directory, using gptme's non-interactive flag:

```sh
gptme -n --no-workspace -t shell,read,save,patch \
  "The Python project in the current directory has a failing pytest suite.

Run: python3 -m pytest -q --tb=short

Read test_clamp.py and clamp.py. Fix clamp.py so all three tests pass. Do not
change the tests. When python3 -m pytest -q passes with 3 passed, stop. Do not
git commit. Do not create extra files."
```

Flags that matter:

| Flag | Why |
|------|-----|
| `-n` / `--non-interactive` | One-shot run; implies `--no-confirm` |
| `--no-workspace` | Skip loading the agent brain. This exercise is two files, not a harness change |
| `-t shell,read,save,patch` | The tools this task actually needs |

Add `-m <provider/model>` to pin a model; omit it to use your default. The
dry-run below used `-m openai/gpt-5-mini`.

To run this **as the forked agent** (identity, lessons, tools loaded), `cd` to
the workspace from the quick start and put the fixture path in the prompt
instead of `--no-workspace`. That is slower and more expensive; use it when
you want the agent, not when you want a 2-minute proof.

## 4. Confirm it passes

After the dry-run session:

```text
...                                                                      [100%]
3 passed in 0.00s
```

`clamp.py` as the agent left it:

```python
def clamp(n: int, lo: int, hi: int) -> int:
    """Return n limited to the inclusive range [lo, hi].

    If n is less than lo return lo. If n is greater than hi return hi.
    Otherwise return n unchanged.
    """
    # Use builtin min/max to clamp the value.
    return min(max(n, lo), hi)
```

The tests were not modified.

## Captured dry-run

Executed 2026-10-07 in a fresh directory against gptme 0.34.0,
`openai/gpt-5-mini`. Cost: $0.01. Six turns. No credentials in the log.

Abridged:

```text
User: The Python project in the current directory has a failing pytest suite.
      Run python3 -m pytest -q --tb=short, fix clamp.py, stop when 3 passed.

Assistant: shell  pwd; ls -la; python3 -m pytest -q --tb=short
           → 2 failed, 1 passed (exit 1)

Assistant: read  test_clamp.py
Assistant: read  clamp.py
           → return n

Assistant: patch clamp.py
           → return min(max(n, lo), hi)

Assistant: shell  python3 -m pytest -q --tb=short
           → 3 passed in 0.00s

Session: $0.01 | 6 turns | 5k context
```

Wall clock for the agent turn was well under five minutes. Creating the
fixture and reading this page is the rest of the session. Stay inside one
50-minute sitting; if the model is slow or the prompt is vague, stop and
tighten the prompt rather than expanding the fixture.

## What this proved

The agent can run the test, read the failure, patch the implementation, and
re-run until green. That is the loop every later coding task uses. The
fixture itself is throwaway — delete `/tmp/first-task` when you are done.

## Next

Give the agent a real task in a project you care about: a failing test, a
broken script, a doc gap. File it under `tasks/` if you use gptodo. Write a
journal entry for the session. Before you leave the agent unattended, read
[`operating-an-agent.md`](./operating-an-agent.md).

## Related

- [README Quick Start](../README.md#quick-start) — zero to `gptme "hello"`
- [Operating an agent](./operating-an-agent.md) — where it lives, what it costs
- [Initial agent setup](../tasks/templates/initial-agent-setup.md) — identity interview
- [Forking workspace](../knowledge/forking-workspace.md) — creating a new agent
