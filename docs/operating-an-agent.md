# Operating an agent

*Last verified: 2026-10-02 — verify this date is recent before trusting the specifics below; costs, model names, and provider quirks go stale fastest.*

This template gets you from zero to a running agent. It doesn't tell you what
happens after that — where it should live, what it costs, what breaks a few
months in, or what to decide before you start. This doc is that missing
second half, written from operational incidents, not design theory.

**Goal: honest expectations, not a sales pitch.** If a section reads as a
warning, that's deliberate — the failure modes below are the ones that
actually happened, not hypotheticals.

Choices below fall into two kinds:
- **General** — applies to any agent built on this template.
- **Worked example** *(marked explicitly)* — one operator's concrete setup,
  included as an illustration, not a recommendation to copy verbatim.

> **Reduced forks.** Any guidance naming an autonomous launcher
> (`scripts/runs/autonomous/autonomous-run.sh`, `autonomous-run-cc.sh`) applies
> to a full fork only. Forks created with `--minimal` or `--without-autonomous`
> omit `scripts/runs/` (a stub README remains in its place); re-fork without
> those flags, or copy the run scripts from the template, before following it.

## Where it should run

An agent that's supposed to keep running needs a host that keeps running
independently of your laptop being open. In rough order of commitment:

1. **A cheap VPS or LXC container** — the minimum viable "always on" setup.
   Isolate the agent from your other systems; it will run shell commands
   unsupervised.
2. **Your own hardware, virtualized** — more control, no recurring cloud bill,
   but you own the uptime.
3. **A managed hosting platform** (e.g. [gptme.ai](https://gptme.ai), in
   limited access at time of writing) — trades control for zero ops burden.

*(Worked example)*: one long-running agent runs in an LXC container on a
Proxmox cluster node (24 cores / 30GiB), sharing the host kernel — not a full
VM. Several sibling agents (same operator) run as identically-shaped LXCs on
the same cluster. The kernel is shared, not namespaced per-agent — don't
assume VM-grade isolation from a container-only deployment. Memory, not CPU,
turned out to be the binding limit on how many sessions can run at once; size
every guest so the sum of their memory limits stays below the host's physical
RAM (an over-committed node once OOM-killed the host itself).

Whatever you pick, decide the isolation boundary *before* the agent's first
unattended run: an agent with shell access will eventually run something you
didn't anticipate.

## Accounts

Give the agent its own identity, not yours:

- **Its own email address.** Needed for GitHub notifications, sign-ups, and
  anything that emails back. See the deliverability trap below before
  assuming "it sent successfully" means "it arrived."
- **Its own GitHub account (or self-hosted Forgejo instance).** Commits and
  PRs under a distinct identity are easier to audit, rate-limit, and revoke
  independently of your own account.
- **Separate API/model credentials from your personal ones**, so quota
  exhaustion or a leaked key doesn't take down your own accounts too.

## Costs

Running one model provider by the token adds up fast. On one long-running
deployment, moving the bulk of autonomous volume onto a flat-rate subscription
cut monthly spend by **roughly an order of magnitude (~20x)** at comparable
volume. Treat that as one observed data point, not a general constant — the
multiple depends on how much work routes to a cheap tier, how close you run to
the plan's rate limits, and which provider you compare against.

Practical shape that has held up:
- **Flat-rate subscription plans as the primary driver for substantial
  autonomous volume** — but match the plan to the authentication path the
  launcher actually uses. This template ships two launchers: **gptme**
  (`scripts/runs/autonomous/autonomous-run.sh`) and **Claude Code**
  (`autonomous-run-cc.sh`). A launcher only gives flat-rate billing for a
  subscription it is wired to authenticate against: Claude Max for the Claude
  Code launcher; for gptme, its subscription-backed providers (ChatGPT Plus/Pro,
  SuperGrok) rather than an API-key provider like OpenRouter, which bills per
  token. Choosing a subscription the launcher's auth path doesn't support
  silently leaves it on per-token billing.
- **A cheap-model tier wired in from day one**, not retrofitted later. Route
  mechanical work (search, formatting, simple transforms, first-pass
  triage) to a cheap model (e.g. via OpenRouter — `deepseek-v4-flash` or
  similar at time of writing) and reserve the expensive subscription-backed
  model for judgment, design, and hard reasoning. Retrofitting this split
  after the agent already has entrenched all-one-model habits is more work
  than building it in from the start.
- Track spend from week one. A quiet cost leak (retry loops, an
  over-eager polling script) is invisible until the bill arrives.

## The email deliverability trap

An SMTP `250 OK` response means the receiving mail server *accepted* the
message — it does not mean it reached an inbox. A newly-provisioned sending
domain with no sending-DKIM configured will get silently spam-filed by
providers like Gmail, with no bounce and no error. The agent (and you) will
believe the reply was delivered when it wasn't.

Concrete incident: three replies from an agent's own email address, all
`250 OK`, all correctly threaded — silently spam-filed for three days because
the sending domain had no DKIM record. Nothing in the send path signaled
failure.

Before relying on agent-sent email for anything time-sensitive: verify DKIM
alignment on the sending domain, and periodically confirm delivery
end-to-end (check the actual inbox, not just the send-side response code).

## Quota, auth, and unattended runs

Provider auth tokens and quotas expire. An unattended agent that hits an
expired token or exhausted quota mid-run doesn't necessarily fail loudly —
depending on the harness, it may retry silently, hang, or produce degraded
output while reporting success. Build a health check that verifies the agent
actually *did* something recently (a commit, a session log), not just that
the process is alive.

## Longevity: what breaks around month 3

The failure modes that show up early are model-quality complaints. The ones
that actually end agent deployments show up later and are operational:

- **Credential rotation.** API keys, SSH keys, and OAuth tokens all expire or
  need periodic rotation. Plan the rotation path before the first credential
  is a month old, not when it silently stops working.
- **Disk growth.** Session logs, trajectories, and generated artifacts
  accumulate. Without an explicit retention policy, disk usage grows
  unbounded and eventually blocks the agent from doing its job.
- **Config drift.** Small manual tweaks made to fix an incident, if not
  captured back into version control, diverge from what's documented and
  make the next incident harder to diagnose.

None of these are dramatic on their own. They compound silently, and by the
time they're visible they've usually already cost some downtime.

## Multi-harness setup

Running the agent on more than one harness (e.g. gptme plus Claude Code) is
primarily a **reliability property**, not a cost-optimization one: if one
harness has an outage, model deprecation, or quota exhaustion, the agent can
continue on another. Cost differences between harnesses are secondary and
change too often to be the deciding factor.

If you do run multiple harnesses, make sure they share the same durable state
(git-tracked identity files, task tracker, lessons) rather than each keeping
its own — otherwise you get two agents with diverging memories instead of one
agent with two front-ends.

Sharing state has a concurrency cost: the launchers do **not** share a run
lock. The gptme runner takes no lock at all, and the Claude Code runner's lock
only guards other Claude Code runs — it does not block a gptme run. Scheduling
both against the same workspace at overlapping times lets them edit and commit
tasks and journals simultaneously, producing file races and Git conflicts.
**Serialize runs across harnesses** (one scheduler per workspace, or an
external lock wrapped around both launchers) rather than running them side by
side.

## Before you start: a short checklist

- [ ] Where does it run, and what's the isolation boundary?
- [ ] Whose email/GitHub identity does it use — yours, or its own?
- [ ] Is a cheap-model tier wired in, or is everything routed through one
      expensive model by default?
- [ ] Is there a retention policy for logs/trajectories, or will disk usage
      grow unbounded?
- [ ] Is there a health check that verifies real recent activity, not just
      process liveness?
- [ ] Who verifies email deliverability (DKIM) before the agent relies on it
      for anything time-sensitive?

None of these need a perfect answer on day one. They need *an* answer, so
the failure isn't a surprise three months in.
