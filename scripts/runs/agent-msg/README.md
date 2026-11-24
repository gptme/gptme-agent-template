# Event-driven agent-message pickup

Wake one bounded session when an agent message lands in `messages/inbox/`,
instead of waiting for the next scheduled autonomous run. This is the portable
shape of the pickup that one deployed agent measured before it was written down here
([gptme-agent-template#119](https://github.com/gptme/gptme-agent-template/issues/119)).

It assumes [gptmail](https://github.com/gptme/gptme-contrib/tree/master/packages/gptmail)
for agent-to-agent messages (see `TOOLS.md`).

## Parts

| File | Job |
|---|---|
| `agent-msg-run.path.example` | `PathChanged` on `messages/inbox` only: arrival detection |
| `agent-msg-run.service.example` | oneshot, 3 s pre-scan sleep, runs the script |
| `agent-msg-run.timer.example` | 2-minute retry for messages that arrived while the slot was busy |
| `agent-msg-run.sh` | one-slot lock, `gptmail agent pending`, attempt cap, one `claude -p` session |

The units live in `dotfiles/.config/systemd/user/`.

## Install

```bash
# 1. Set AGENT_NAME in scripts/runs/agent-msg/agent-msg-run.sh
# 2. Copy the units, drop the .example suffix, fix paths and PATH
cd dotfiles/.config/systemd/user
for u in path service timer; do cp agent-msg-run.$u.example ~/.config/systemd/user/agent-msg-run.$u; done
# 3. Enable the path and the timer, not the service
systemctl --user daemon-reload
systemctl --user enable --now agent-msg-run.path agent-msg-run.timer
```

Test without systemd: `./scripts/runs/agent-msg/agent-msg-run.sh`. With nothing pending
it logs `nothing pending` and exits without starting a model session.

## Behaviour

- **Debounce.** The path unit fires on the first write; `ExecStartPre=sleep 3` lets a
  multi-file SCP and the first read/replied edit settle, so a burst costs one scan.
  `TriggerLimitBurst=100` keeps a large burst from tripping the start limit.
- **Read/replied edits.** Handling a message edits its frontmatter, which fires the
  path again. That second scan finds nothing new and exits. Re-reading or re-acking
  a message that is already read and replied writes nothing, so it fires nothing.
- **One slot.** A second trigger while a session runs exits 0 (`slot occupied`).
  The timer, not the path, recovers it: no later file may arrive to wake the path.
- **Retry cap.** A message is dispatched at most `AGENT_MSG_MAX_ATTEMPTS` (default 3)
  times; after that the script logs `STUCK:` and skips it. Counters live in
  `state/agent-msg/attempts/` and are dropped once the message leaves `pending`.
  A run that never starts a session (prompt build fails, or `claude` cannot be
  executed: exit 126/127) does not count toward the cap.
  Without the cap, a handler that decides "no reply needed" and never runs `ack`
  is relaunched at every retry. Handlers must end in `reply` or `ack` (`TOOLS.md`).
- **Shared no-reply policy.** Feeds that never owe a reply belong in
  `messages/no-reply-subject-patterns`, which `gptmail agent pending` reads for every
  caller. Do not set the patterns on this unit's environment only: an interactive
  session and any other dispatcher would then disagree about what is owed.

## Timestamps: measuring send-to-pickup

Read the stages separately; the slot wait is the variable part.

| Stage | Where to read it |
|---|---|
| Send | `msg_ts` in the dispatch line (the `YYYYMMDD-HHMMSS` file-name prefix, UTC) |
| Trigger | `journalctl --user -u agent-msg-run.path`, then the first service line |
| Scan done / dispatched | the `dispatch:` line of `journalctl --user -u agent-msg-run.service` |
| Session pickup | `launched_at` in that line; `pickup_s` is send to launch |
| Slot busy | a `slot occupied` line, then the next timer run |

One deployed agent's measured numbers, for scale: path trigger within 6 s of send in 6 of 6
cases; free slot, launch 8-14 s after the message timestamp (23 messages, median
about 10 s); behind a busy slot, 81 s. `launched_at` is dispatch, not the first model
turn, and these are one agent's figures, not a promise.

## Not in this slice

- Urgency routing and a separate alert directory.
- A single-lane "force one session" option.
- A shared priority slot with the scheduled autonomous run: this script has its own
  lock, so a message session and a scheduled session can overlap. Share one lock file
  (`AGENT_MSG_LOCKFILE`) if your host cannot afford both.
