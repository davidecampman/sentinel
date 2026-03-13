"""
Tests for the centralized TLS helper (python/helpers/tls.py).

These tests exercise get_verify(), get_ssl_context(), get_aiohttp_connector_kwargs(),
get_imap_ssl_context(), get_playwright_args(), and apply_env_vars() under the
three TLS configurations: verify disabled, custom CA bundle, default system certs.
"""
import os
import ssl
import pytest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings(verify: bool, bundle: str = "") -> dict:
    """Return a minimal settings dict for patching."""
    return {"tls_verify": verify, "tls_ca_bundle": bundle}


# ---------------------------------------------------------------------------
# get_verify()
# ---------------------------------------------------------------------------

class TestGetVerify:
    def test_returns_false_when_verify_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            assert tls.get_verify() is False

    def test_returns_bundle_path_when_set(self, tmp_path):
        from python.helpers import tls
        bundle = str(tmp_path / "ca.pem")
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, bundle)):
            assert tls.get_verify() == bundle

    def test_returns_true_when_no_bundle(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            assert tls.get_verify() is True

    def test_strips_whitespace_from_bundle_path(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "  /path/ca.pem  ")):
            assert tls.get_verify() == "/path/ca.pem"


# ---------------------------------------------------------------------------
# get_ssl_context()
# ---------------------------------------------------------------------------

class TestGetSslContext:
    def test_returns_false_when_verify_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            assert tls.get_ssl_context() is False

    def test_returns_ssl_context_for_default(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            ctx = tls.get_ssl_context()
            assert isinstance(ctx, ssl.SSLContext)

    def test_returns_ssl_context_with_custom_bundle(self, tmp_path):
        from python.helpers import tls
        # create a minimal PEM bundle (just need the file to exist for SSLContext)
        bundle = tmp_path / "ca.pem"
        # copy system default certs into test bundle so SSLContext can load it
        import certifi
        bundle.write_bytes(open(certifi.where(), 'rb').read())
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, str(bundle))):
            ctx = tls.get_ssl_context()
            assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# get_aiohttp_connector_kwargs()
# ---------------------------------------------------------------------------

class TestGetAiohttpConnectorKwargs:
    def test_returns_dict_with_ssl_key(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            kwargs = tls.get_aiohttp_connector_kwargs()
            assert "ssl" in kwargs

    def test_ssl_is_false_when_verify_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            kwargs = tls.get_aiohttp_connector_kwargs()
            assert kwargs["ssl"] is False


# ---------------------------------------------------------------------------
# get_imap_ssl_context()
# ---------------------------------------------------------------------------

class TestGetImapSslContext:
    def test_returns_ssl_context(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            ctx = tls.get_imap_ssl_context()
            assert isinstance(ctx, ssl.SSLContext)

    def test_verify_disabled_disables_cert_check(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            ctx = tls.get_imap_ssl_context()
            assert ctx.verify_mode == ssl.CERT_NONE
            assert ctx.check_hostname is False


# ---------------------------------------------------------------------------
# get_playwright_args()
# ---------------------------------------------------------------------------

class TestGetPlaywrightArgs:
    def test_no_extra_args_when_verify_enabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            assert tls.get_playwright_args() == []

    def test_ignore_cert_errors_when_verify_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            args = tls.get_playwright_args()
            assert "--ignore-certificate-errors" in args


# ---------------------------------------------------------------------------
# apply_env_vars()
# ---------------------------------------------------------------------------

class TestApplyEnvVars:
    def test_sets_pythonhttpsverify_when_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            tls.apply_env_vars()
            assert os.environ.get("PYTHONHTTPSVERIFY") == "0"
            assert "REQUESTS_CA_BUNDLE" not in os.environ

    def test_sets_bundle_env_vars(self, tmp_path):
        from python.helpers import tls
        bundle = str(tmp_path / "ca.pem")
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, bundle)):
            tls.apply_env_vars()
            assert os.environ.get("REQUESTS_CA_BUNDLE") == bundle
            assert os.environ.get("SSL_CERT_FILE") == bundle
            assert os.environ.get("CURL_CA_BUNDLE") == bundle
            assert os.environ.get("NODE_EXTRA_CA_CERTS") == bundle

    def test_clears_overrides_when_default(self):
        from python.helpers import tls
        # pre-set some env vars
        os.environ["REQUESTS_CA_BUNDLE"] = "/old/path"
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            tls.apply_env_vars()
            assert "REQUESTS_CA_BUNDLE" not in os.environ
            assert "PYTHONHTTPSVERIFY" not in os.environ


# ---------------------------------------------------------------------------
# get_litellm_kwargs()
# ---------------------------------------------------------------------------

class TestGetLitellmKwargs:
    def test_returns_ssl_verify_false_when_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            kwargs = tls.get_litellm_kwargs()
            assert kwargs.get("ssl_verify") is False

    def test_returns_ssl_verify_as_bundle_path(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "/path/ca.pem")):
            kwargs = tls.get_litellm_kwargs()
            # CA bundle path goes into ssl_verify, NOT ssl_certificate
            # (ssl_certificate is for mutual-TLS client certs in litellm)
            assert kwargs.get("ssl_verify") == "/path/ca.pem"
            assert "ssl_certificate" not in kwargs

    def test_returns_empty_dict_for_default(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            kwargs = tls.get_litellm_kwargs()
            assert kwargs == {}
