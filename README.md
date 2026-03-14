# Sentinel
### Enterprise AI. Hardened by design.

Sentinel is a hardened, corporate-ready fork of [Agent Zero](https://github.com/agent0ai/agent-zero) — an open-source autonomous AI agent framework. This project extends the original codebase with a focus on making it suitable for self-hosted deployment in enterprise engineering environments.

> **Base project:** [agent0ai/agent-zero](https://github.com/agent0ai/agent-zero) (MIT License)
> **License:** MIT — see [LICENSE](LICENSE)

---

## Purpose

Agent Zero is a powerful tool, but its defaults are oriented toward individual developers and rapid prototyping. Sentinel adapts it for **corporate engineering teams** by adding:

- Security controls appropriate for self-hosted, internal deployment
- Hardened Docker configuration for production use
- Cost-optimized model defaults for daily engineering work
- Refined agent profiles tuned for software development workflows
- Cleaner UI with corporate-friendly branding

The goal is to layer production-readiness on top of the Agent Zero foundation.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- API credentials for your chosen LLM provider

### Setup

```bash
# Clone
git clone https://github.com/davidecampman/sentinel.git
cd sentinel

# Configure
cp .env.example .env

# Build & run
./build.sh
./run.sh
```

Open `http://localhost` and enter your LLM API key via **Settings → Model**.

To test a new build alongside a running prod instance:

```bash
./test.sh          # starts test instance on port 50081
./test.sh --stop   # tear it down when done
```

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `A0_AUTH_LOGIN` | UI login username | Recommended |
| `A0_AUTH_PASSWORD` | UI login password | Recommended |
| `PORT` | Host port mapping | Optional (default `80`) |
| `TLS_CA_BUNDLE` | Path to corporate CA bundle | If behind TLS proxy |
| `TLS_VERIFY` | Enable/disable TLS verification | Optional |

---

## What's Different from Agent Zero

### 🎨 Rebranding — Sentinel
Full UI rebrand from Agent Zero to Sentinel:
- New `sn.` monogram logo and favicon (dark charcoal + teal `#2DD4BF`)
- Redesigned login page with Sentinel splash screen
- All UI text, page titles, PWA manifest updated
- GitHub links point to this repository
- Update checker and version display removed (no phone-home)

---

### 🔒 Security Hardening

**Authentication & Sessions**
- SHA256 credential hashing with 1-second delay on failed login (brute force mitigation)
- Session cookies with `SameSite=Strict`
- CSRF dual-layer validation: session token + runtime-scoped cookie (`secrets.token_urlsafe(32)`)

**Network & API**
- WebSocket origin validation (RFC 6455 compliant); rejects cross-origin connections
- DNS rebinding prevention via origin allowlist (configurable via `ALLOWED_ORIGINS`)
- Sensitive endpoints restricted to loopback via `requires_loopback()` decorator
- API key authentication via `requires_api_key()` decorator (`X-API-KEY` header) for MCP/API endpoints
- Container port bound to `127.0.0.1` only — not exposed on all network interfaces
- nginx `server_tokens off` (version hidden)

**Code Execution**
- RFC endpoint (`/rfc` — arbitrary Python execution) disabled in Docker/production mode
- Strict module allowlist enforced even in dev mode (`python.helpers.*`, `python.api.*`, `python.tools.*`)

**Input & File Safety**
- Filename security: Unicode normalization, forbidden character blocking, Windows reserved name detection, path traversal prevention, 255-byte limit
- Skill approval workflow: imported skills land in `pending/` and require explicit human promotion before execution
- Browser agent hardening: downloads disabled, security constraints enabled, prompt injection defense, web content treated as untrusted

---

### 🔐 TLS / SSL Management
Centralized TLS configuration for corporate environments with TLS inspection proxies:
- Single config point: `TLS_CA_BUNDLE` and `TLS_VERIFY` via UI or environment variables
- Custom CA bundle upload via Settings → Network → TLS (supports `.pem`, `.crt`, `.cer`, `.ca-bundle`)
- TLS settings propagated to **all** HTTP clients: `aiohttp`, `httpx`, `requests`, Playwright, IMAPClient

---

### 💰 Cost Optimization
Defaults tuned to reduce LLM token costs without sacrificing quality:
- `ctx_history` reduced to `0.40` (sends 40% of history per turn vs 70% default)
- `ctx_length` reduced to `60,000` tokens (vs 100,000 default)
- Browser model set to Claude Haiku (4x cheaper than Sonnet for browsing tasks)

---

### 🤖 Agent Profiles — Tuned for Engineering
All four agent profiles have detailed, opinionated instructions for corporate engineering work:

| Profile | Role | What's Different |
|---------|------|-----------------|
| `agent0` (Sentinel) | Orchestrator | Delegation rules, output style guide, commit/push workflow |
| `developer` | Code worker | Coding conventions, pre-done checklist, test/commit workflow |
| `researcher` | Docs & info | Source priority order, stack-specific doc URLs |
| `hacker` | Security review | OWASP focus areas, severity framework, finding format |

---

### 🛠️ Deployment Scripts
Production-ready scripts for building and running the container:

**`build.sh`** — Build the Docker image
```bash
./build.sh                          # build sentinel:<YYYYMMDD>
./build.sh --latest                 # also tag sentinel:latest locally
./build.sh --no-cache               # force full rebuild (no Docker layer cache)
./build.sh --push <dockerhub-user>  # build + push date-tagged image to Docker Hub
```

**`run.sh`** — Start a Sentinel instance
```bash
./run.sh                            # start production instance (port 50080)
./run.sh --test                     # start test instance (port 50081, isolated volume)
AGENT_ZERO_IMAGE=myuser/sentinel:20250101 ./run.sh  # run a specific image
```

**`stop.sh`** — Stop a Sentinel instance
```bash
./stop.sh                           # stop production instance
./stop.sh --test                    # stop test instance
```

**`run_tests.sh`** — Run the security test suite
```bash
./run_tests.sh                      # run security tests
./run_tests.sh -v                   # verbose output
./run_tests.sh -k <test-name>       # run a specific test (any pytest flag accepted)
```

Multi-instance support via environment variables:
- `PORT` — override host port mapping
- `COMPOSE_PROJECT_NAME` — namespace Docker resources for isolated instances
- `AGENT_ZERO_IMAGE` — specify which image `run.sh` starts (default `sentinel:latest`)

---

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

### Removed
- **Update checker** — upstream `update_check.py` phones home to `api.agent-zero.ai` on every user message; removed entirely

---

## Roadmap

### Phase 1 — Security Hardening ✅ In Progress
- [x] RFC endpoint disabled in production
- [x] Auth hardening (hashing, brute force protection, CSRF)
- [x] WebSocket security (origin validation, DNS rebinding)
- [x] TLS management (centralized config, CA bundle support)
- [x] Browser agent hardening
- [x] Filename and path safety
- [x] Skill approval workflow
- [ ] Audit logging (who ran what, when)
- [ ] Full API authentication audit

### Phase 2 — Corporate Integrations (Planned)
- Slack integration
- Microsoft Teams integration
- Email (SMTP/Exchange)
- Notification routing with access controls

### Phase 3 — Governance (Planned)
- Role-based access control (RBAC)
- Approval workflows for sensitive actions
- Policy enforcement on tool usage
- Compliance-friendly audit trails

---

## License & Attribution

Sentinel is a fork of [Agent Zero](https://github.com/agent0ai/agent-zero), which is released under the **MIT License**.

The MIT License is one of the most permissive open-source licenses. It explicitly permits:

| Action | Permitted |
|--------|----------|
| Forking and modifying the codebase | ✅ Yes |
| Rebranding (Agent Zero → Sentinel) | ✅ Yes |
| Removing the original name from the UI | ✅ Yes |
| Commercial use and internal deployment | ✅ Yes |
| Redistribution (e.g. Docker Hub) | ✅ Yes |

The **only requirement** of the MIT License is that the original copyright notice and license text be preserved somewhere in the project. Our [`LICENSE`](LICENSE) file fulfills this requirement — it retains the original:

```
MIT License
Copyright (c) 2025 Agent Zero, s.r.o
Contact: pr@agent-zero.ai
```

We believe this fork is fully compliant with the upstream license. We also give credit to the Agent Zero team for building the excellent foundation that Sentinel is built upon.
