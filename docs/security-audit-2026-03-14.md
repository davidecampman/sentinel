# Security Audit Report — Sentinel

**Date:** 2026-03-14
**Branch:** `claude/security-audit-73SuN`
**Audited by:** Claude (automated code review)
**Scope:** Full codebase static analysis — authentication, authorisation, file operations, cryptography, network layer, WebSocket security, input validation.

---

## Executive Summary

The codebase demonstrates a mature security posture: CSRF double-submit, WebSocket origin validation, session isolation by runtime ID, HMAC-based cryptography, and explicit opt-in for sensitive endpoints are all well-implemented. However, **two critical vulnerabilities** allow an authenticated attacker to read, write, or delete any file on the host filesystem (not just the work directory), and **three timing-attack surfaces** allow an offline or online attacker to recover credentials more efficiently than intended.

---

## Findings

### CRITICAL

---

#### C-1 — FileBrowser `base_dir = "/"` makes all path-traversal guards ineffective

**File:** `python/helpers/file_browser.py:29`

```python
base_dir = "/"
self.base_dir = Path(base_dir)
```

Every path-containment check in `FileBrowser` follows this pattern:

```python
full_path = (self.base_dir / file_path).resolve()
if not str(full_path).startswith(str(self.base_dir)):
    raise ValueError("Invalid path")
```

When `base_dir` is `"/"`, `str(self.base_dir)` is `"/"` and `str(full_path).startswith("/")` is **always `True`** for any absolute path. The guard is therefore a no-op.

**Impact:**
Any authenticated user (or any session with auth disabled) can call `get_work_dir_files`, `edit_work_dir_file`, `download_work_dir_file`, `delete_work_dir_file`, or `rename_work_dir_file` with `path=../../etc/passwd` (or any absolute path), and the server will:
- Read arbitrary files (`/etc/shadow`, private keys, `.env`)
- Write or overwrite arbitrary files (cron jobs, SSH `authorized_keys`)
- Delete arbitrary files

**Recommended fix:**
Restrict `base_dir` to the configured work directory path and validate that the resolved path starts with the real, non-root base directory. Example:

```python
from python.helpers import settings, files

work_dir = settings.get_settings().get("workdir_path") or files.get_abs_path("work")
self.base_dir = Path(work_dir).resolve()
```

---

#### C-2 — `_is_allowed_file` unconditionally returns `True` — no file type restriction on uploads

**File:** `python/helpers/file_browser.py:185-195`

```python
def _is_allowed_file(self, filename: str, file) -> bool:
    # allow any file to be uploaded in file browser
    # ... extension check is commented out ...
    return True  # Allow the file if it passes the checks
```

All file-type enforcement is commented out. Combined with C-1, an authenticated user can upload a Python/shell script to `/etc/cron.daily/` or overwrite any existing binary.

**Impact:** Unrestricted file upload to any writable path on the filesystem.

**Recommended fix:**
If unrestricted uploads within the work directory are intentional, document that and ensure C-1 is fixed first (so uploads are at least contained). If extension filtering is desired, restore the commented-out extension check.

---

### HIGH

---

#### H-1 — Timing attack on login credential comparison

**File:** `run_ui.py:199`

```python
if request.form['username'] == user and request.form['password'] == password:
```

Python's `==` on strings is not constant-time. An attacker with a network timing oracle can recover the correct username or password character-by-character.

**Recommended fix:**

```python
import hmac

username_ok = hmac.compare_digest(request.form['username'], user or "")
password_ok = hmac.compare_digest(request.form['password'], password or "")
if username_ok and password_ok:
```

---

#### H-2 — Timing attack on API key validation

**File:** `run_ui.py:133-138`

```python
if api_key != valid_api_key:
    return Response("Invalid API key", 401)
```

Same issue as H-1. The API key comparison is non-constant-time.

**Recommended fix:**

```python
import hmac
if not hmac.compare_digest(api_key, valid_api_key):
    return Response("Invalid API key", 401)
```

---

#### H-3 — Timing attack on CSRF token comparison

**File:** `run_ui.py:185`

```python
if not token or not sent or token != sent:
    return Response("CSRF token missing or invalid", 403)
```

While CSRF timing attacks are lower severity than authentication timing attacks, the pattern is inconsistent with the rest of the security posture.

**Recommended fix:**

```python
import hmac
if not token or not sent or not hmac.compare_digest(token, sent):
    return Response("CSRF token missing or invalid", 403)
```

---

#### H-4 — RFC endpoint has no authentication or CSRF protection

**File:** `python/api/rfc.py`

```python
@classmethod
def requires_csrf(cls) -> bool:
    return False

@classmethod
def requires_auth(cls) -> bool:
    return False

async def process(self, input: dict, request: Request) -> dict | Response:
    if not runtime.is_development():
        raise Exception("RFC endpoint is disabled in Docker mode.")
    result = await runtime.handle_rfc(input)
    return result
```

The RFC endpoint executes arbitrary Python module functions. Its only protection is the `is_development()` flag, with no authentication and no CSRF guard. If the development mode flag is ever set incorrectly (misconfiguration, environment variable injection), this endpoint becomes a trivial remote code execution vector for any client that can reach the server.

**Recommended fix:**
Add at minimum `requires_loopback = True` and consider also requiring the auth session. The `requires_loopback` decorator is already available in `run_ui.py` and would prevent non-loopback clients from reaching this endpoint even when development mode is active.

---

### MEDIUM

---

#### M-1 — Health endpoint discloses git version and commit time without authentication

**File:** `python/api/health.py`

```python
@classmethod
def requires_auth(cls) -> bool:
    return False

async def process(self, input: dict, request: Request) -> dict | Response:
    gitinfo = git.get_git_info()
    return {"gitinfo": gitinfo, ...}
```

The `/health` endpoint is publicly reachable and returns git version and commit timestamp. This helps attackers identify the exact software version and check for known vulnerabilities.

**Recommended fix:**
Either require authentication for the full response, or return only a `{"status": "ok"}` body for unauthenticated callers.

---

#### M-2 — API key accepted in JSON request body (credential logging risk)

**File:** `run_ui.py:135-138`

```python
elif request.json and request.json.get("api_key"):
    api_key = request.json.get("api_key")
```

Secrets in request bodies may be captured by access logs, reverse proxies, WAFs, or error-reporting services. The `X-API-KEY` header should be the only accepted channel.

**Recommended fix:** Remove the body fallback and accept the API key exclusively via the `X-API-KEY` header.

---

#### M-3 — No account lockout on repeated login failures

**File:** `run_ui.py:203`

```python
await asyncio.sleep(1)
error = 'Invalid Credentials. Please try again.'
```

The 1-second delay slows brute-force attacks but does not stop them. There is no IP-based lockout, CAPTCHA, or exponential back-off after N failures.

**Recommended fix:**
Add a per-IP failure counter (e.g., using `rate_limiter.py` which already exists in the codebase) and lock out after 5–10 failures with exponential back-off.

---

#### M-4 — 5 GB upload limit can enable denial-of-service via disk exhaustion

**File:** `run_ui.py:51,63`

```python
UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024 * 1024
```

An authenticated attacker (or a compromised session) can upload up to 5 GB per request, potentially filling available disk space and disrupting the service.

**Recommended fix:** Reduce the default limit to a value appropriate for actual file sizes (e.g., 100 MB), and make the maximum configurable per use-case.

---

#### M-5 — Credential hash stored in session uses plain SHA-256 without salt

**File:** `python/helpers/login.py:10`

```python
return hashlib.sha256(f"{user}:{password}".encode()).hexdigest()
```

This hash is used only as a session marker (not for password storage), but the pattern means the hash is deterministic and the same across all instances. If an attacker obtains the hash value (e.g., via session fixation or cookie theft), they can verify guesses offline at full GPU speed without any key-stretching cost.

**Recommended fix:**
Incorporate the Flask `SECRET_KEY` or a server-side salt so the hash cannot be verified without server-side state:

```python
import hmac
salt = webapp.secret_key  # already a 32-byte random value
return hmac.new(salt.encode(), f"{user}:{password}".encode(), hashlib.sha256).hexdigest()
```

---

### LOW

---

#### L-1 — Global logging suppressed to `WARNING` level

**File:** `run_ui.py:37`

```python
logging.getLogger().setLevel(logging.WARNING)
```

Suppressing INFO-level logging makes post-incident forensic analysis harder. Authentication failures, unusual access patterns, and API errors may go unrecorded.

**Recommended fix:** Log authentication events (success, failure, IP) at INFO level to a dedicated security log.

---

#### L-2 — RSA key size 2048-bit (crypto.py)

**File:** `python/helpers/crypto.py:18`

```python
return rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
```

2048-bit RSA is currently acceptable but is approaching end-of-life recommendations. NIST recommends 3072+ bits for keys used beyond 2030.

**Recommended fix:** Increase `key_size` to `4096` or migrate to an EC-based scheme (e.g., X25519 for key exchange).

---

#### L-3 — WebSocket max HTTP buffer size 50 MB

**File:** `run_ui.py:77`

```python
max_http_buffer_size=50 * 1024 * 1024,
```

A 50 MB per-message buffer could allow memory exhaustion attacks over WebSocket connections.

**Recommended fix:** Reduce to a value commensurate with the largest legitimate message payload (most events should be well under 1 MB).

---

## Positive Findings

The following security controls are correctly implemented and should be maintained:

| Control | Location |
|--------|---------|
| CSRF double-submit (session + cookie/header) | `run_ui.py:178-188` |
| Session cookie `SameSite=Strict` and runtime-ID-scoped name | `run_ui.py:57-65` |
| Flask `SECRET_KEY` from `secrets.token_hex(32)` | `run_ui.py:49` |
| WebSocket origin validation (RFC 6455 + OWASP CSWSH) | `python/helpers/websocket.py:57-133` |
| Namespace gatekeeper for unknown WebSocket namespaces | `run_ui.py:279-293` |
| Loopback-only restriction for sensitive endpoints | `run_ui.py:147-158` |
| 1-second brute-force delay on login failure | `run_ui.py:203` |
| RFC endpoint disabled in Docker/production mode | `python/api/rfc.py:20` |
| HMAC-SHA256 with OAEP padding for RSA encryption | `python/helpers/crypto.py` |
| Filename sanitisation (Unicode NFC, forbidden chars, reserved names) | `python/helpers/security.py` |
| Streaming secrets filter (prevents key leakage in LLM output) | `python/helpers/secrets.py` |
| TLS centralised configuration (applied at startup) | `python/helpers/tls.py` |
| Auth + CSRF required by default on all `ApiHandler` subclasses | `python/helpers/api.py:33-42` |
| Auth + CSRF required by default on all `WebSocketHandler` subclasses | `python/helpers/websocket.py:381-395` |

---

## Severity Summary

| ID | Title | Severity | CVSS (approx.) |
|----|-------|----------|----------------|
| C-1 | FileBrowser `base_dir="/"` — full filesystem access | Critical | 9.1 |
| C-2 | Unrestricted file upload to any writable path | Critical | 9.0 |
| H-1 | Timing attack on login credential comparison | High | 7.5 |
| H-2 | Timing attack on API key comparison | High | 7.5 |
| H-3 | Timing attack on CSRF token comparison | High | 5.9 |
| H-4 | RFC endpoint — no auth/CSRF, only dev-mode guard | High | 7.3 |
| M-1 | Health endpoint discloses git version info | Medium | 5.3 |
| M-2 | API key accepted in request body | Medium | 4.3 |
| M-3 | No account lockout on repeated login failures | Medium | 5.3 |
| M-4 | 5 GB upload limit enables disk DoS | Medium | 4.9 |
| M-5 | Session credential hash uses unsalted SHA-256 | Medium | 4.3 |
| L-1 | Security-relevant events suppressed from logs | Low | 3.1 |
| L-2 | RSA key size 2048-bit | Low | 2.0 |
| L-3 | WebSocket buffer 50 MB | Low | 3.7 |

---

## Recommended Remediation Priority

1. **Immediately:** Fix C-1 (restrict `base_dir` to work directory) and C-2 (restore or formally document the upload policy).
2. **This sprint:** Fix H-1, H-2, H-3 (replace `==`/`!=` with `hmac.compare_digest`), and H-4 (add loopback restriction to RFC endpoint).
3. **Next sprint:** Address M-1 through M-5.
4. **Backlog:** L-1 through L-3.
