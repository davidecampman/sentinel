# Agent Zero — Corporate Edition

A hardened, self-hosted fork of [Agent Zero](https://github.com/frdel/agent-zero) built for corporate/on-prem deployment.

---

## Changes & Features

### Bug Fixes
- **Fix JSON parse error on message send** — syntax error in `update_check.py` (stray comma in `httpx.AsyncClient(,...)`) caused a 500 response on every prompt submission

### Docker & Deployment
- **Date-tagged builds** — `./build.sh` tags images as `agent-zero-hardened:YYYYMMDD` instead of overwriting `:latest`
- **Explicit `:latest` promotion** — use `./build.sh --latest` to update the local `:latest` tag when you're ready
- **Docker Hub push** — `./build.sh --push <dockerhub-user>` pushes only the date tag, never overwrites `:latest` on the registry
- **External named volume** — `docker-compose.yml` references existing volume `run_agent-zero-usr` instead of creating a new one
- **No `.env` required** — credentials optional at startup; configure LLM keys and auth via the UI after first login

### Scripts
- **`./start.sh`** — interactive prompt to launch prod (port 50080) or test (port 50081) instance
- **`./test.sh`** — run a test instance alongside prod without touching it; auto-selects latest date-tagged image
- **`./test.sh --stop`** — tear down the test instance
- **Consistent stack names** — `COMPOSE_PROJECT_NAME` set explicitly so Docker Desktop shows `agent-zero` and `agent-zero-test`

### TLS
- Single config point for corporate TLS inspection — set `TLS_CA_BUNDLE` and `TLS_VERIFY` via UI or environment

---

## Quick Start

```sh
# Build
./build.sh

# Start (interactive)
./start.sh

# Test a new build alongside prod
./build.sh
./test.sh
./test.sh --stop
```
