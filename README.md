# Agent Zero — Corporate Edition

A hardened, self-hosted fork of [Agent Zero](https://github.com/frdel/agent-zero) built for corporate/on-prem deployment.

---

## Changes & Features

### Removed
- **Update checker removed** — upstream `update_check.py` feature disabled; this fork does not phone home to `api.agent-zero.ai`

### Bug Fixes

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

### Dependency Security Patches

Patched 25 known CVEs via version bumps (2 remain unfixable pending upstream releases):

| Package | Version | CVEs fixed |
|---|---|---|
| `pypdf` | 6.0.0 → 6.7.5 | 13 CVEs — DoS via malformed PDFs (infinite loop, RAM exhaustion) |
| `langchain-core` | 0.3.49 → 0.3.81 | CVE-2025-65106 (template injection), CVE-2025-68664 (serialization injection / secret extraction) |
| `mcp` | 1.22.0 → 1.26.0 | CVE-2025-66416 — DNS rebinding protection disabled by default on localhost MCP servers |
| `fastmcp` | 2.13.1 → 2.14.0 | GHSA-rcfx-77hg-w2wv — inherits mcp CVE-2025-66416 fix |
| `unstructured` | 0.16.23 → 0.18.18 | CVE-2025-64712 — path traversal in `partition_msg()` → arbitrary file write |
| `langchain-community` | 0.3.19 → 0.3.27 | CVE-2025-6984 |
| `lxml_html_clean` | 0.3.1 → 0.4.4 | PYSEC-2024-160, CVE-2026-28348/28350 — XSS via HTML cleaning bypass |
| `flask` | 3.0.3 → 3.1.3 | CVE-2026-27205 — missing `Vary: Cookie` header (cache poisoning) |
| `markdown` | 3.7 → 3.8.1 | CVE-2025-69534 |

**Remaining unfixed:**
- `diskcache` CVE-2025-69872 — pickle RCE; no patched version released upstream yet
- `langchain-core` CVE-2026-26013 (SSRF, CVSS LOW) — fix requires 1.2.x, breaking langchain-community 0.3.x compatibility

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
