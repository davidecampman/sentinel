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


def apply_env_vars() -> None:
    """
    Export TLS settings as environment variables so that libraries which
    respect them (requests, httpx, curl, openssl) pick up the right certs
    automatically.

    Should be called once during _apply_settings().
    """
    verify = get_verify()
    if verify is False:
        # Signal libraries to skip verification.
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        os.environ["CURL_CA_BUNDLE"] = ""  # empty = disable
        # Remove any previously set bundle paths so they don't override.
        os.environ.pop("REQUESTS_CA_BUNDLE", None)
        os.environ.pop("SSL_CERT_FILE", None)
        os.environ.pop("NODE_EXTRA_CA_CERTS", None)
    elif isinstance(verify, str):
        # Custom CA bundle path.
        os.environ["REQUESTS_CA_BUNDLE"] = verify
        os.environ["SSL_CERT_FILE"] = verify
        os.environ["CURL_CA_BUNDLE"] = verify
        os.environ["NODE_EXTRA_CA_CERTS"] = verify
        os.environ.pop("PYTHONHTTPSVERIFY", None)
    else:
        # Restore defaults – remove overrides.
        os.environ.pop("PYTHONHTTPSVERIFY", None)
        os.environ.pop("REQUESTS_CA_BUNDLE", None)
        os.environ.pop("SSL_CERT_FILE", None)
        os.environ.pop("CURL_CA_BUNDLE", None)
        os.environ.pop("NODE_EXTRA_CA_CERTS", None)
