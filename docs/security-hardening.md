# Agent Zero Corporate Security Hardening

Agent Zero is a powerful open-source AI agent framework. Out of the box it is built for developer convenience, but deploying it in a corporate environment exposes several attack surfaces. This document describes what was hardened and why each change matters.

---

## 1. RFC (Remote Function Call) Endpoint — Disabled in Production

**The problem:** Agent Zero includes an RFC mechanism that lets the container call arbitrary Python functions on the host. In Docker mode this endpoint serves no legitimate purpose, but it was left enabled — meaning anyone who could reach the API could invoke `os`, `subprocess`, or any other Python module.

**What we did:**
- Disabled the `/rfc` API endpoint entirely when running in Docker/production mode
- Added a strict module prefix allowlist (`python.helpers.*`, `python.api.*`, `python.tools.*`) so even in development, only internal agent-zero modules can be called via RFC

---

## 2. Skill Approval Workflow — Human-in-the-Loop Before Execution

**The problem:** Agent Zero can import and execute "skills" — small Python/markdown programs. Previously, imported skills were immediately active with no review step. A malicious or compromised skill source could push code straight into execution.

**What we did:**
- Introduced a `pending/` and `active/` subdirectory structure for skills
- All newly imported skills land in `pending/` and cannot run until explicitly approved
- Added `skills_cli` commands — `list-pending` and `promote` — that show the full skill content for human review before moving it to `active/`

---

## 3. Browser Agent Hardening

**The problem:** The browser agent was configured with `disable_security=True` and `accept_downloads=True` — essentially a fully permissive headless browser running inside your network.

**What we did:**
- Set `disable_security=False` to restore normal browser security boundaries
- Set `accept_downloads=False` to prevent drive-by file downloads
- Added support for a `BROWSER_PROXY` environment variable so browser traffic can be routed through a corporate proxy for monitoring and filtering
- Added a prompt injection defence section to the browser agent's system prompt, explicitly instructing it to treat all web page content as untrusted data and never execute instructions found on pages it visits

---

## 4. Docker Hardening

**The problem:** The default compose file bound the agent port to `0.0.0.0` (all interfaces), used a bind mount of the entire project directory, and used the standard public image.

**What we did:**
- Bound the port to `127.0.0.1` only, so it is never exposed on the network interface
- Replaced the full bind mount with a named Docker volume scoped to `usr/` (user data only)
- Switched to a locally-built hardened image tag

---

## Key Takeaway

None of these issues are bugs — they are deliberate design choices for developer ergonomics. The security work is about adding the right controls for a production corporate deployment: least-privilege execution, human approval gates, and network containment.
