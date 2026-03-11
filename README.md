# Sentinel
### Enterprise AI. Hardened by design.

Sentinel is a hardened, corporate-ready fork of [Agent Zero](https://github.com/agent0ai/agent-zero) — an open-source autonomous AI agent framework. This project extends the upstream codebase with a focus on making it suitable for self-hosted deployment in enterprise engineering environments.

> **Base project:** [agent0ai/agent-zero](https://github.com/agent0ai/agent-zero) (MIT License)  
> **License:** MIT — see [LICENSE](LICENSE)

---

## Purpose

Agent Zero is a powerful tool, but its defaults are oriented toward individual developers and rapid prototyping. Sentinel adapts it for **corporate engineering teams** by adding:

- Security controls appropriate for self-hosted, internal deployment
- Hardened Docker configuration for production use
- AWS Bedrock as the primary LLM backend (on-prem/approved cloud)
- Cost-optimized model defaults for daily engineering work
- Refined agent profiles tuned for software development workflows
- Cleaner UI with corporate-friendly branding

The goal is not to diverge from upstream — it's to layer production-readiness on top of it, while staying mergeable with upstream improvements.

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

### ☁️ AWS Bedrock as Primary LLM Backend
Configured for AWS Bedrock — keeps all LLM traffic within approved cloud infrastructure:
- Default chat model: `us.anthropic.claude-sonnet-4-6`
- Default utility model: `us.amazon.nova-micro-v1:0`
- Default browser model: `us.anthropic.claude-haiku-3-5` (cost-optimized)
- Default embedding model: `amazon.titan-embed-text-v2:0`
- No external API calls required beyond AWS

---

### 💰 Cost Optimization
Defaults tuned to reduce Bedrock spend without sacrificing quality:
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

```bash
./build.sh                        # build Docker image
./build.sh --push <dockerhub-user> # build + push to Docker Hub
./run.sh                          # start production instance
./stop.sh                         # stop production instance
./test.sh                         # start test instance on port 50081
./test.sh --stop                  # stop test instance
./run_tests.sh                    # run security test suite
./run_tests.sh -v                 # verbose test output
```

Multi-instance support via environment variables:
- `PORT` — configure host port mapping (default `80`)
- `COMPOSE_PROJECT_NAME` — namespace Docker resources for isolated instances

---

### 🧪 Test Infrastructure
Security-focused test suite with pytest:
- `tests/test_tls_helper.py` — 16 tests covering all TLS configuration paths
- `tests/test_fasta2a_client.py` — A2A connectivity test
- `pytest.ini` with `asyncio_mode=auto` and security/integration markers
- `run_tests.sh` — one-command test runner

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- AWS credentials with Bedrock access

### Setup

```bash
# Clone
git clone https://github.com/davidecampman/agentzero.git sentinel
cd sentinel

# Configure
cp .env.example .env
# Edit .env — add AWS credentials at minimum

# Build & run
./build.sh
./run.sh
```

Open `http://localhost` and configure LLM settings via the UI.

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `AWS_ACCESS_KEY_ID` | Bedrock authentication | Yes |
| `AWS_SECRET_ACCESS_KEY` | Bedrock authentication | Yes |
| `AWS_DEFAULT_REGION` | Bedrock region | Yes |
| `A0_AUTH_LOGIN` | UI login username | Recommended |
| `A0_AUTH_PASSWORD` | UI login password | Recommended |
| `PORT` | Host port mapping | Optional (default `80`) |
| `TLS_CA_BUNDLE` | Path to corporate CA bundle | If behind TLS proxy |
| `TLS_VERIFY` | Enable/disable TLS verification | Optional |

---

## Upstream Compatibility

Sentinel is designed to stay mergeable with upstream Agent Zero. All Sentinel-specific changes are annotated with `# SENTINEL:` comments in the Python source.

To check for upstream updates:
```bash
git fetch upstream
git log upstream/main --oneline -10
```

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
