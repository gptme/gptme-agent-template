---
match:
  session_categories: [code, infrastructure, monitoring]
  keywords:
    - "curl in script"
    - "curl -s http"
    - "curl -fsSL"
    - "silent curl failure"
    - "health check curl"
description: "Use curl -fsSL instead of bare curl in scripts and health checks so silent HTTP failures surface as errors"
status: active
---

# curl Script Flags

## Rule
In scripts and health checks, always use `curl -fsSL` instead of bare `curl`.

## Context
When using `curl` in shell scripts, automation, or health checks. The default `curl` behavior treats HTTP errors (4xx, 5xx) as success — it only fails on transport-level errors (DNS, connection refused, timeout).

## Detection
- `curl https://api.example.com | jq ...` without `-f`
- Health checks using `curl -s http://...` that pass on 404/500
- Scripts checking `$?` after curl and assuming HTTP 200
- `curl -I` or `curl -sI` for status checks without `-f`

## Pattern
```bash
# ❌ Wrong: HTTP 404 returns exit 0
response=$(curl -s "https://api.example.com/health")
# $response might be {"error": "not found"} but script continues

# ✅ Correct: fail on HTTP errors, silent output, follow redirects
response=$(curl -fsSL "https://api.example.com/health")
# HTTP 4xx/5xx → exit non-zero → script stops or enters error handler

# ✅ For header-only status checks
if curl -fsSLI "https://example.com" >/dev/null 2>&1; then
    echo "OK"
else
    echo "FAIL"
fi
```

Flag reference:
- `-f` / `--fail`: return non-zero on HTTP 4xx/5xx
- `-s` / `--silent`: suppress progress meter
- `-S` / `--show-error`: show error text even with `-s`
- `-L` / `--location`: follow redirects

## Outcome
- Scripts fail fast on HTTP errors instead of processing garbage data
- Health checks correctly detect degraded services
- CI pipelines catch API failures instead of silently passing

## Related
- [exit-code-127-use-uv-run.md](./exit-code-127-use-uv-run.md) — another silent failure class in scripts
