# 1Password Integration Plan

## Overview

This document describes the design for integrating 1Password into Sentinel's secret management
system. The goal is to let teams store and rotate secrets in 1Password and have Sentinel resolve
them at runtime, without ever writing plaintext secrets to disk.

Two complementary modes are planned:

| Mode | Description |
|------|-------------|
| **Reference mode** | Place `op://vault/item/field` URIs as values in `usr/secrets.env`; Sentinel resolves them at load time |
| **Mirror mode** | Point Sentinel at a dedicated 1Password item; all fields are imported as secrets on startup |

Both modes work with either authentication backend:

| Backend | How it authenticates |
|---------|---------------------|
| **CLI / Service Account** | `OP_SERVICE_ACCOUNT_TOKEN` env var; uses the `op` binary bundled or installed on the host |
| **1Password Connect** | Self-hosted Connect server; `OP_CONNECT_HOST` + `OP_CONNECT_TOKEN` env vars |

---

## Architecture

### New module: `python/helpers/onepassword.py`

Encapsulates all 1Password interaction behind a clean interface so the rest of the codebase never
imports the `op` binary or HTTP client directly.

```
OnePasswordConfig          – dataclass: method, token, connect_url, vault, item
OnePasswordProvider        – main class
  .is_available()          – returns True if op CLI found / Connect reachable
  .read(reference)         – resolve a single op:// reference → str
  .get_item_fields(vault, item) → Dict[str, str]
  .test_connection()       – raises on auth failure
```

**CLI path** (`method = "cli"`):

```python
subprocess.run(["op", "read", reference], env={"OP_SERVICE_ACCOUNT_TOKEN": ...})
```

For mirror mode:

```python
subprocess.run(["op", "item", "get", item, "--vault", vault, "--format", "json"])
```

**Connect path** (`method = "connect"`):

```
GET  {OP_CONNECT_HOST}/v1/vaults/{vault_id}/items/{item_id}
Authorization: Bearer {OP_CONNECT_TOKEN}
```

Uses `httpx` (already in the dependency tree via LiteLLM) for the HTTP calls.

---

### Changes to `python/helpers/secrets.py`

`SecretsManager.load_secrets()` gains a post-load resolution step:

```python
def load_secrets(self) -> Dict[str, str]:
    ...
    secrets = self._load_from_file()
    secrets = self._resolve_op_references(secrets)   # NEW – reference mode
    if op_mirror_enabled:
        secrets = self._merge_op_mirror(secrets)      # NEW – mirror mode
    self._secrets_cache = secrets
    return secrets
```

`_resolve_op_references` iterates values matching `^op://`, calls
`OnePasswordProvider.read()`, and replaces in-place. Failures raise `RepairableException`
so the agent surfaces a helpful message without crashing.

`_merge_op_mirror` calls `OnePasswordProvider.get_item_fields()` and merges the result
(1Password fields win over local values for the same key, making 1Password the source of
truth).

Cache invalidation is unchanged — the existing `_invalidate_all_caches()` path already clears
all instances, so secrets are re-fetched from 1Password on next access after a settings change.

---

### Settings additions (`python/helpers/settings.py`)

New fields in the `Settings` TypedDict:

```python
op_enabled: bool              # master switch
op_method: str                # "cli" | "connect"
op_service_account_token: str # for cli method (treated as a secret field)
op_connect_host: str          # for connect method
op_connect_token: str         # for connect method (treated as a secret field)
op_mirror_vault: str          # vault for mirror mode (empty = disabled)
op_mirror_item: str           # item name for mirror mode
```

`op_service_account_token` and `op_connect_token` are marked sensitive (like `auth_password`)
and stored in `.env` via the `dotenv` helper rather than in `settings.json`.

Default values:

```python
op_enabled=False,
op_method="cli",
op_service_account_token="",
op_connect_host="",
op_connect_token="",
op_mirror_vault="",
op_mirror_item="Sentinel",
```

---

### Environment variable support

Added to `.env.example`:

```bash
# ── 1Password (OPTIONAL) ──────────────────────────────────────────
# CLI / Service Account method:
# OP_SERVICE_ACCOUNT_TOKEN=ops_...
#
# Connect method:
# OP_CONNECT_HOST=https://connect.internal.example.com
# OP_CONNECT_TOKEN=...
```

Environment variables take precedence over values saved via Settings UI (same pattern as
`A0_SET_*` overrides used elsewhere in settings.py).

---

### UI

A new **1Password** subsection inside Settings > Security (existing tab):

- Toggle: **Enable 1Password integration**
- Radio: **Authentication method** (CLI / Service Account | Connect Server)
- Conditionally shown fields for token / connect URL
- **Test connection** button (calls a new API endpoint)
- Mirror mode section: vault + item name fields

---

### New API endpoint: `python/api/settings_op_test.py`

```
POST /api/settings_op_test
```

Instantiates `OnePasswordProvider` from current settings, calls `.test_connection()`, and
returns `{ "ok": true }` or `{ "ok": false, "error": "..." }`. Used by the **Test connection**
button.

---

## Implementation Steps

### Step 1 – Core provider (`python/helpers/onepassword.py`)

- [ ] `OnePasswordConfig` dataclass
- [ ] CLI authentication via `OP_SERVICE_ACCOUNT_TOKEN`; subprocess `op read` + `op item get`
- [ ] Connect HTTP client using `httpx`
- [ ] `test_connection()` — fetch a known system vault to verify credentials
- [ ] Graceful error handling: timeout, missing binary, auth failure

### Step 2 – SecretsManager integration

- [ ] `_resolve_op_references(secrets)` — resolve `op://` values
- [ ] `_merge_op_mirror(secrets)` — fetch and merge mirror item fields
- [ ] Guard both paths behind `op_enabled` flag read from settings
- [ ] Unit tests for reference resolution and mirror merge logic

### Step 3 – Settings

- [ ] Add new fields to `Settings` TypedDict and `get_default_settings()`
- [ ] Save/load token fields via `dotenv` (not JSON) to avoid plaintext in settings file
- [ ] `convert_out()` masking for token fields (same pattern as `auth_password`)
- [ ] `A0_SET_OP_*` env override support (automatic via `get_default_value()`)

### Step 4 – API endpoint

- [ ] `python/api/settings_op_test.py` — test connection endpoint
- [ ] Register in the API router

### Step 5 – UI

- [ ] 1Password section in `webui/index.html` settings panel
- [ ] JS: conditional field visibility based on method selection
- [ ] JS: "Test connection" button + result display
- [ ] JS: save/load new fields via existing settings API

### Step 6 – Docker / dependencies

- [ ] Add `op` CLI install to `docker/Dockerfile` (or document as optional host-level dep)
- [ ] `httpx` is already available; no new Python deps required for Connect
- [ ] Update `.env.example` with 1Password variables

### Step 7 – Documentation

- [ ] User guide: `docs/guides/1password-setup.md`
- [ ] Update `docs/developer/architecture.md` secrets section

---

## Security Considerations

- Tokens are stored in `.env` (not settings.json), masked in the UI, and never logged.
- `op://` references in `secrets.env` are resolved in-memory; the resolved values go through
  the existing `StreamingSecretsFilter` and placeholder system, so they are never written to
  disk or leaked through the LLM output stream.
- The `op` subprocess is invoked with a minimal environment (only `OP_SERVICE_ACCOUNT_TOKEN`
  forwarded) to avoid unintended variable leakage.
- Connect traffic must go over HTTPS; the existing `TLS_CA_BUNDLE` / `TLS_VERIFY` settings
  apply to the `httpx` client.
- Mirror mode merges 1Password fields *after* local secrets are loaded, giving 1Password
  precedence and ensuring a compromised `secrets.env` cannot shadow a rotated credential.

---

## Open Questions

1. **`op` binary distribution** — ship inside the Docker image (adds ~30 MB) vs. require
   users to mount it or install on the host. Shipping it simplifies setup; mounting keeps the
   image lean.
2. **Secret rotation** — should cache invalidation be triggered on a configurable TTL (e.g.,
   refresh every 15 minutes) in addition to the existing on-settings-change invalidation?
3. **Vault UUID vs. name** — `op item get` accepts names (human-friendly) or UUIDs (stable
   across renames). Start with names; document the UUID fallback.
4. **Multiple mirror items** — v1 targets one item per Sentinel instance. Multiple items (e.g.,
   one per project) could be addressed in a follow-up using the existing per-project secrets
   file pattern.
