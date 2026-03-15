"""
Centralized TLS/SSL configuration for Agent Zero Corporate Edition.

All HTTP clients (aiohttp, httpx, requests, IMAPClient, Playwright) should
obtain their SSL/verify parameters from this module so that a single setting
controls certificate verification across the entire application.

Settings controlled via the Agent Zero UI (Settings → Network → TLS):
  tls_verify    bool  – When False, all certificate verification is disabled.
                        When True, the CA bundle (or system certs) is used.
  tls_ca_bundle str   – Absolute path to a PEM CA bundle file.  Leave empty
                        to use the system / certifi default bundle.
"""

from __future__ import annotations

import os
import ssl
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    import aiohttp

# Destination inside Ubuntu's system CA trust store.
# update-ca-certificates scans /usr/local/share/ca-certificates/ for *.crt files.
_SYSTEM_CA_CERT = "/usr/local/share/ca-certificates/sentinel-ca.crt"

# NSS databases used by Chromium on Linux (system-wide and root-user).
# Initialised during image build by install_playwright.sh.
_NSS_CERT_NICKNAME = "sentinel-ca"
_NSS_DBS = ["sql:/etc/pki/nssdb", "sql:/root/.pki/nssdb"]


def get_verify() -> Union[bool, str]:
    """
    Return the value to pass as *verify* to the requests library.

    Do NOT use this for httpx — httpx does not accept a string path for
    verify in newer versions.  Use get_ssl_context() for httpx clients.

    Returns:
        False           – verification disabled
        str (path)      – path to custom CA bundle
        True            – use system/certifi default bundle
    """
    from python.helpers import settings as _settings
    s = _settings.get_settings()
    if not s.get("tls_verify", True):
        return False
    bundle = (s.get("tls_ca_bundle") or "").strip()
    if bundle:
        return bundle
    return True


def get_ssl_context() -> Union[ssl.SSLContext, bool]:
    """
    Return an ssl.SSLContext (or False) suitable for aiohttp connectors.

    Returns:
        False                   – verification disabled (aiohttp accepts False)
        ssl.SSLContext          – context loaded with the configured CA bundle
                                  or the default context with system certs
    """
    verify = get_verify()
    if verify is False:
        return False
    if isinstance(verify, str):
        ctx = ssl.create_default_context(cafile=verify)
        return ctx
    # True → default system context
    return ssl.create_default_context()


def get_aiohttp_connector_kwargs() -> dict:
    """
    Return keyword arguments for aiohttp.TCPConnector.

    Usage::
        connector = aiohttp.TCPConnector(**tls.get_aiohttp_connector_kwargs())
    """
    ssl_ctx = get_ssl_context()
    return {"ssl": ssl_ctx}


def get_imap_ssl_context() -> Union[ssl.SSLContext, None]:
    """
    Return an ssl.SSLContext for IMAPClient / SMTP, or None to use the
    default (which will then be unverified if tls_verify is False).

    When verification is disabled we return a context with check_hostname and
    verify_mode both disabled.
    """
    verify = get_verify()
    if verify is False:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if isinstance(verify, str):
        return ssl.create_default_context(cafile=verify)
    return ssl.create_default_context()


def get_playwright_args() -> list[str]:
    """
    Return additional Chromium launch arguments for Playwright.

    When verification is disabled, --ignore-certificate-errors is added.
    When a custom CA bundle is provided the path is passed via
    --use-mock-keychain-root-cert-path (Linux: handled through NSS/GLIB env).
    """
    verify = get_verify()
    args: list[str] = []
    if verify is False:
        args.append("--ignore-certificate-errors")
    elif isinstance(verify, str):
        # Chromium on Linux uses NSS; point it at the custom bundle via env
        # (applied in apply_env_vars below).  No extra CLI arg needed.
        pass
    return args


def get_litellm_kwargs() -> dict:
    """
    Return keyword arguments to inject into litellm completion/embedding calls.

    LiteLLM's get_ssl_configuration() uses ssl_verify for both the boolean
    disable flag AND the CA bundle path (a string path is accepted directly).
    ssl_certificate is for mutual-TLS client certs — do NOT use it for CA bundles.

    Usage::
        kwargs.update(tls.get_litellm_kwargs())
        litellm.acompletion(model=..., messages=..., **kwargs)
    """
    verify = get_verify()
    if verify is False:
        return {"ssl_verify": False}
    if isinstance(verify, str):
        # Pass the CA bundle path as ssl_verify — litellm passes it straight
        # through to httpx as the verify= parameter (string path accepted).
        return {"ssl_verify": verify}
    return {}


def _patch_ssl_defaults(verify: Union[bool, str]) -> None:
    """
    Patch ssl._create_default_https_context so every new ssl context inherits
    the configured TLS verification mode.

    This is the most reliable way to make libraries that create their own ssl
    contexts (httpx, aiohttp, botocore, etc.) respect our TLS settings, even
    when they don't honour environment variables or per-call kwargs.

    Called by apply_env_vars() after the standard env-var setup.
    """
    import ssl as _ssl_mod

    if verify is False:
        # Unverified context – disables certificate verification globally for
        # all new ssl contexts created via ssl.create_default_context() or
        # ssl._create_default_https_context().
        _ssl_mod._create_default_https_context = _ssl_mod._create_unverified_context
    else:
        # Restore the standard default (system certs / certifi).  The CA-bundle
        # case is already handled via SSL_CERT_FILE + _update_system_ca_store(),
        # so ssl.create_default_context() will automatically load the bundle
        # from the system trust store.
        _ssl_mod._create_default_https_context = _ssl_mod.create_default_context


def _patch_httpx_defaults(verify: Union[bool, str]) -> None:
    """
    Monkey-patch httpx.AsyncClient and httpx.Client so that every new client
    uses our SSL verification setting by default.

    LiteLLM (and the underlying OpenAI SDK) create httpx clients internally.
    Setting litellm.ssl_verify is supposed to propagate the setting, but a
    long-standing regression (BerriAI/litellm#9340) means the async client
    path does not always honour it.  Patching the httpx constructors ensures
    the correct ssl.SSLContext is used no matter how or when the client is
    created.

    Uses setdefault() so that any caller that passes an explicit verify=
    argument still wins – we only supply the default.
    """
    try:
        import httpx as _httpx  # type: ignore

        # ── Store originals once on first call ──────────────────────────────
        if not hasattr(_httpx.AsyncClient, "_sentinel_orig_init"):
            _httpx.AsyncClient._sentinel_orig_init = _httpx.AsyncClient.__init__
        if not hasattr(_httpx.Client, "_sentinel_orig_init"):
            _httpx.Client._sentinel_orig_init = _httpx.Client.__init__

        if verify is True:
            # Restore original constructors (system/certifi default certs).
            _httpx.AsyncClient.__init__ = _httpx.AsyncClient._sentinel_orig_init
            _httpx.Client.__init__ = _httpx.Client._sentinel_orig_init
        else:
            # verify is False or a CA-bundle path string.
            _verify = verify
            _orig_async = _httpx.AsyncClient._sentinel_orig_init
            _orig_sync = _httpx.Client._sentinel_orig_init

            def _patched_async_init(self, *args, **kwargs):  # type: ignore[misc]
                kwargs.setdefault("verify", _verify)
                _orig_async(self, *args, **kwargs)

            def _patched_sync_init(self, *args, **kwargs):  # type: ignore[misc]
                kwargs.setdefault("verify", _verify)
                _orig_sync(self, *args, **kwargs)

            _httpx.AsyncClient.__init__ = _patched_async_init
            _httpx.Client.__init__ = _patched_sync_init
    except Exception:
        pass


def _clear_litellm_client_cache() -> None:
    """
    Clear LiteLLM's cached HTTP clients so they are recreated on the next call.

    LiteLLM caches openai.AsyncOpenAI / openai.OpenAI instances that embed an
    httpx client built at construction time.  After changing SSL settings we
    must discard those stale clients; otherwise the new ssl._create_default_https_context
    and httpx defaults only take effect for clients created *after* this call.

    This is best-effort: attribute names differ across litellm versions.
    """
    try:
        import litellm as _ll  # type: ignore

        # Module-level client attributes seen across litellm v1.x versions.
        for _attr in (
            "_async_openai_client",
            "_openai_client",
            "client_session",
            "aclient",
            "client",
        ):
            if hasattr(_ll, _attr) and getattr(_ll, _attr) is not None:
                try:
                    setattr(_ll, _attr, None)
                except Exception:
                    pass

        # Also clear any provider-level caches in litellm.utils if present.
        try:
            import litellm.utils as _ll_utils  # type: ignore

            for _attr in ("_async_openai_client", "_openai_client"):
                if hasattr(_ll_utils, _attr) and getattr(_ll_utils, _attr) is not None:
                    try:
                        setattr(_ll_utils, _attr, None)
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception:
        pass


def _update_system_ca_store(bundle_path: Union[str, None]) -> None:
    """
    Install or remove the custom CA bundle from every system trust store that
    matters on Ubuntu, then rebuild/refresh each one:

    1. OpenSSL store (/usr/local/share/ca-certificates/ + update-ca-certificates)
       → picked up by ssl.create_default_context(), so aiohttp, httpx, botocore/
         Bedrock, requests, and every other Python HTTP library gets the cert
         automatically without any per-library env-var wiring.

    2. NSS store (/etc/pki/nssdb and /root/.pki/nssdb via certutil)
       → picked up by Chromium/Playwright, which uses libnss3 on Linux instead
         of the OpenSSL store.

    Both stores are managed together so a single "upload cert + restart"
    workflow in the UI covers all TLS-speaking components in the container.

    This is a best-effort operation: it silently skips any store that is
    missing or inaccessible (e.g. non-Ubuntu dev environments).

    Args:
        bundle_path: Absolute path to a PEM CA bundle to install, or None to
                     remove any previously installed bundle.
    """
    import shutil
    import subprocess

    # ── 1. OpenSSL / system trust store ─────────────────────────────────────
    try:
        if bundle_path:
            os.makedirs(os.path.dirname(_SYSTEM_CA_CERT), exist_ok=True)
            shutil.copy2(bundle_path, _SYSTEM_CA_CERT)
        else:
            if os.path.exists(_SYSTEM_CA_CERT):
                os.remove(_SYSTEM_CA_CERT)

        subprocess.run(["update-ca-certificates"], capture_output=True, check=False)
    except Exception:
        pass

    # ── 2. NSS store (Chromium / Playwright) ────────────────────────────────
    for nss_db in _NSS_DBS:
        try:
            db_dir = nss_db[len("sql:"):]
            if not os.path.isdir(db_dir):
                continue
            # Always delete first so re-installs don't accumulate duplicates.
            subprocess.run(
                ["certutil", "-D", "-d", nss_db, "-n", _NSS_CERT_NICKNAME],
                capture_output=True,
                check=False,
            )
            if bundle_path:
                subprocess.run(
                    [
                        "certutil", "-A",
                        "-d", nss_db,
                        "-n", _NSS_CERT_NICKNAME,
                        "-t", "CT,,",
                        "-i", bundle_path,
                    ],
                    capture_output=True,
                    check=False,
                )
        except Exception:
            pass


def apply_env_vars() -> None:
    """
    Export TLS settings as environment variables so that libraries which
    respect them (requests, httpx, curl, openssl) pick up the right certs
    automatically.  Also installs or removes the custom CA bundle from the
    Ubuntu system trust store so that ssl.create_default_context() — used
    by aiohttp, botocore/Bedrock, and others — picks up the cert without
    needing per-library configuration.  Finally, configures LiteLLM's global
    SSL properties so that all subsequent litellm calls use the correct CA
    bundle / verification mode.

    Should be called once during _apply_settings().
    """
    verify = get_verify()
    if verify is False:
        # Signal libraries to skip verification.
        # PYTHONHTTPSVERIFY=0 was deprecated and removed in Python 3.12 — unset it
        # so it doesn't cause confusion on Python 3.12+.
        os.environ.pop("PYTHONHTTPSVERIFY", None)
        # Use /dev/null instead of empty string: empty string causes curl to fail
        # immediately with HTTP 000 (can't open file ""), while /dev/null provides
        # an empty-but-valid path that prevents that crash.
        os.environ["CURL_CA_BUNDLE"] = "/dev/null"
        # Remove any previously set bundle paths so they don't override.
        os.environ.pop("REQUESTS_CA_BUNDLE", None)
        os.environ.pop("SSL_CERT_FILE", None)
        os.environ.pop("NODE_EXTRA_CA_CERTS", None)
        # AWS_CA_BUNDLE is read by botocore (boto3) for AWS service connections
        # including Bedrock.  Clear it so any pre-existing value doesn't force
        # certificate verification when the user has disabled it.
        os.environ.pop("AWS_CA_BUNDLE", None)
    elif isinstance(verify, str):
        # Custom CA bundle path.
        os.environ["REQUESTS_CA_BUNDLE"] = verify
        os.environ["SSL_CERT_FILE"] = verify
        os.environ["CURL_CA_BUNDLE"] = verify
        os.environ["NODE_EXTRA_CA_CERTS"] = verify
        # botocore (boto3) reads AWS_CA_BUNDLE for AWS service TLS verification
        # (e.g. Bedrock).  REQUESTS_CA_BUNDLE is NOT used by botocore.
        os.environ["AWS_CA_BUNDLE"] = verify
        os.environ.pop("PYTHONHTTPSVERIFY", None)
    else:
        # Restore defaults – remove overrides.
        os.environ.pop("PYTHONHTTPSVERIFY", None)
        os.environ.pop("REQUESTS_CA_BUNDLE", None)
        os.environ.pop("SSL_CERT_FILE", None)
        os.environ.pop("CURL_CA_BUNDLE", None)
        os.environ.pop("NODE_EXTRA_CA_CERTS", None)
        os.environ.pop("AWS_CA_BUNDLE", None)

    # Install / remove the cert from Ubuntu's system trust store so that
    # ssl.create_default_context() picks it up globally (aiohttp, botocore, …).
    _update_system_ca_store(verify if isinstance(verify, str) else None)

    # ── Patch ssl module defaults ──────────────────────────────────────────
    # Must run BEFORE configuring LiteLLM so that any clients it creates from
    # this point forward inherit the correct ssl context factory.
    _patch_ssl_defaults(verify)

    # ── Patch httpx client constructors ───────────────────────────────────
    # LiteLLM (via the OpenAI SDK) creates httpx.AsyncClient instances.  A
    # regression (BerriAI/litellm#9340) means the async path ignores
    # ssl_verify in some versions.  Patching the constructors here ensures
    # every new httpx client, regardless of who creates it, inherits our
    # verify setting.
    _patch_httpx_defaults(verify)

    # ── Configure LiteLLM global SSL properties ───────────────────────────
    # ssl_verify accepts bool OR a CA bundle path string.
    # ssl_certificate is for mutual-TLS client certs — never set it here.
    try:
        import litellm as _litellm  # type: ignore
        if verify is False:
            _litellm.ssl_verify = False
        elif isinstance(verify, str):
            _litellm.ssl_verify = verify  # CA bundle path, not ssl_certificate
        else:
            _litellm.ssl_verify = True
    except ImportError:
        pass

    # ── Discard stale LiteLLM client cache ────────────────────────────────
    # After updating ssl defaults and litellm.ssl_verify, evict any cached
    # httpx clients so the next LiteLLM call creates fresh ones that pick up
    # the new SSL configuration.
    _clear_litellm_client_cache()

    # Write a shell-sourceable env file so SearXNG (a separate supervisord
    # process in its own virtualenv) can pick up the same TLS settings.
    try:
        from python.helpers import files as _files
        env_path = _files.get_abs_path("usr/tls.env")
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        if verify is False:
            lines = [
                # PYTHONHTTPSVERIFY=0 is a no-op on Python 3.12+ — unset it.
                "unset PYTHONHTTPSVERIFY",
                # Empty string crashes curl (HTTP 000); /dev/null is a valid path
                # that prevents the crash.
                "export CURL_CA_BUNDLE=/dev/null",
                "unset REQUESTS_CA_BUNDLE",
                "unset SSL_CERT_FILE",
                "unset NODE_EXTRA_CA_CERTS",
                "unset AWS_CA_BUNDLE",
            ]
        elif isinstance(verify, str):
            lines = [
                f"export REQUESTS_CA_BUNDLE={verify}",
                f"export SSL_CERT_FILE={verify}",
                f"export CURL_CA_BUNDLE={verify}",
                f"export NODE_EXTRA_CA_CERTS={verify}",
                f"export AWS_CA_BUNDLE={verify}",
                "unset PYTHONHTTPSVERIFY",
            ]
        else:
            lines = [
                "unset PYTHONHTTPSVERIFY",
                "unset REQUESTS_CA_BUNDLE",
                "unset SSL_CERT_FILE",
                "unset CURL_CA_BUNDLE",
                "unset NODE_EXTRA_CA_CERTS",
                "unset AWS_CA_BUNDLE",
            ]
        with open(env_path, "w") as _f:
            _f.write("\n".join(lines) + "\n")
        os.chmod(env_path, 0o644)
    except Exception:
        pass
