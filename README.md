# Sentinel — Enterprise AI. Hardened by design.

Sentinel is a hardened, self-hosted enterprise AI agent built on [Agent Zero](https://github.com/frdel/agent-zero) for corporate/on-prem deployment.

---

## Changes & Features

### Bug Fixes
- **Fix JSON parse error on message send** — syntax error in `update_check.py` (stray comma in `httpx.AsyncClient(,...)`) caused a 500 response on every prompt submission

### Docker & Deployment
- **Date-tagged builds** — `./build.sh` tags images as `agent-zero-hardened:YYYYMMDD` instead of overwriting `:latest`
- **Explicit `:latest` promotion** — use `./build.sh --latest` to update the local `:latest` tag when you're ready
- **Docker Hub push** — `./build.sh --push <dockerhub-user>` pushes only the date tag, never overwrites `:latest` on the registry
- **No `.env` required** — credentials optional at startup; configure LLM keys and auth via the UI after first login

### Scripts
- **`./start.sh`** — interactive prompt to launch prod (port 50080) or test (port 50081) instance
- **`./test.sh`** — run a test instance alongside prod without touching it; auto-selects latest date-tagged image
- **`./test.sh --stop`** — tear down the test instance
- **Consistent stack names** — `COMPOSE_PROJECT_NAME` set explicitly so Docker Desktop shows `agent-zero` and `agent-zero-test`

### TLS
- Single config point for corporate TLS inspection — set `TLS_CA_BUNDLE` and `TLS_VERIFY` via UI or environment
- Custom CA bundle upload via Settings → Network → TLS (supports `.pem`, `.crt`, `.cer`, `.ca-bundle`)
- TLS settings propagated to all HTTP clients: aiohttp, httpx, requests, Playwright, IMAPClient

### Security Hardening
- **RFC endpoint disabled in production** — `/rfc` (arbitrary Python execution) blocked outside development mode; strict module allowlist (`python.helpers.*`, `python.api.*`, `python.tools.*`) enforced even in dev
- **CSRF protection** — dual-layer validation: session token + runtime-scoped cookie using `secrets.token_urlsafe(32)`; scoped cookie names prevent session collision on shared hosts
- **WebSocket origin validation** — RFC 6455 compliant; rejects cross-origin connections; handles reverse proxy headers (`X-Forwarded-Host`, `X-Forwarded-Proto`)
- **DNS rebinding prevention** — origin allowlist defaulting to localhost/127.0.0.1; configurable via `ALLOWED_ORIGINS`
- **Auth hardening** — SHA256 credential hashing; 1-second delay on failed login (brute force mitigation); session cookies with `SameSite=Strict`
- **Loopback restriction** — sensitive endpoints restricted to loopback via `requires_loopback()` decorator
- **API key authentication** — `requires_api_key()` decorator with `X-API-KEY` header validation for MCP/API endpoints
- **Filename security** — Unicode normalization, forbidden character blocking, Windows reserved name detection, path traversal prevention, 255-byte limit
- **Skill approval workflow** — imported skills land in `pending/` and require explicit human promotion before execution
- **Browser agent hardening** — downloads disabled, security constraints enabled, prompt injection defense in system prompt, web content treated as untrusted
- **Port binding** — container port bound to `127.0.0.1` only, not exposed on network interfaces
- **nginx hardening** — `server_tokens off` (version hidden)

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
