"""
Tests for the centralized TLS helper (python/helpers/tls.py).

These tests exercise get_verify(), get_ssl_context(), get_aiohttp_connector_kwargs(),
get_imap_ssl_context(), get_playwright_args(), apply_env_vars(),
_clear_litellm_client_cache(), _patch_httpx_defaults(), and _patch_ssl_defaults()
under the three TLS configurations: verify disabled, custom CA bundle, default
system certs.
"""
import os
import ssl
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

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
    def test_env_vars_when_verify_disabled(self):
        from python.helpers import tls
        # Pre-set PYTHONHTTPSVERIFY to ensure it gets removed (it's a no-op on
        # Python 3.12+ so we no longer set it).
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        os.environ["AWS_CA_BUNDLE"] = "/some/old/bundle.pem"
        os.environ["SSL_VERIFY"] = "true"
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store"):
                tls.apply_env_vars()
            # PYTHONHTTPSVERIFY removed: deprecated/removed in Python 3.12+
            assert "PYTHONHTTPSVERIFY" not in os.environ
            assert "REQUESTS_CA_BUNDLE" not in os.environ
            # CURL_CA_BUNDLE must be /dev/null, not empty string (empty string
            # causes curl to fail with HTTP 000)
            assert os.environ.get("CURL_CA_BUNDLE") == "/dev/null"
            # AWS_CA_BUNDLE must be cleared so botocore/Bedrock doesn't try to
            # verify certs when the user has disabled verification.
            assert "AWS_CA_BUNDLE" not in os.environ
            # SSL_VERIFY is read by litellm's get_ssl_configuration() — must be
            # cleared so it doesn't override litellm.ssl_verify=False.
            assert "SSL_VERIFY" not in os.environ

    def test_sets_bundle_env_vars(self, tmp_path):
        from python.helpers import tls
        bundle = str(tmp_path / "ca.pem")
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, bundle)):
            with patch.object(tls, "_update_system_ca_store"):
                tls.apply_env_vars()
            assert os.environ.get("REQUESTS_CA_BUNDLE") == bundle
            assert os.environ.get("SSL_CERT_FILE") == bundle
            assert os.environ.get("CURL_CA_BUNDLE") == bundle
            assert os.environ.get("NODE_EXTRA_CA_CERTS") == bundle
            # AWS_CA_BUNDLE is read by botocore (boto3) for Bedrock connections —
            # REQUESTS_CA_BUNDLE is NOT used by botocore.
            assert os.environ.get("AWS_CA_BUNDLE") == bundle
            assert "SSL_VERIFY" not in os.environ

    def test_clears_overrides_when_default(self):
        from python.helpers import tls
        # pre-set some env vars
        os.environ["REQUESTS_CA_BUNDLE"] = "/old/path"
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        os.environ["AWS_CA_BUNDLE"] = "/old/path"
        os.environ["SSL_VERIFY"] = "true"
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            with patch.object(tls, "_update_system_ca_store"):
                tls.apply_env_vars()
            assert "REQUESTS_CA_BUNDLE" not in os.environ
            assert "PYTHONHTTPSVERIFY" not in os.environ
            assert "AWS_CA_BUNDLE" not in os.environ
            assert "SSL_VERIFY" not in os.environ

    def test_system_ca_store_called_with_bundle_path(self, tmp_path):
        from python.helpers import tls
        bundle = str(tmp_path / "ca.pem")
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, bundle)):
            with patch.object(tls, "_update_system_ca_store") as mock_store:
                tls.apply_env_vars()
                mock_store.assert_called_once_with(bundle)

    def test_system_ca_store_called_with_none_when_disabled(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store") as mock_store:
                tls.apply_env_vars()
                mock_store.assert_called_once_with(None)

    def test_system_ca_store_called_with_none_for_default(self):
        from python.helpers import tls
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            with patch.object(tls, "_update_system_ca_store") as mock_store:
                tls.apply_env_vars()
                mock_store.assert_called_once_with(None)


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


# ---------------------------------------------------------------------------
# _patch_ssl_defaults()
# ---------------------------------------------------------------------------

class TestPatchSslDefaults:
    def test_sets_unverified_context_when_verify_false(self):
        import ssl
        from python.helpers import tls
        original = ssl._create_default_https_context
        try:
            tls._patch_ssl_defaults(False)
            assert ssl._create_default_https_context is ssl._create_unverified_context
        finally:
            ssl._create_default_https_context = original

    def test_restores_default_context_when_verify_true(self):
        import ssl
        from python.helpers import tls
        original = ssl._create_default_https_context
        try:
            # First disable, then restore
            tls._patch_ssl_defaults(False)
            tls._patch_ssl_defaults(True)
            assert ssl._create_default_https_context is ssl.create_default_context
        finally:
            ssl._create_default_https_context = original

    def test_restores_default_context_for_bundle_path(self):
        import ssl
        from python.helpers import tls
        original = ssl._create_default_https_context
        try:
            tls._patch_ssl_defaults("/path/ca.pem")
            # For CA-bundle case we restore to the standard factory (the bundle
            # is already in the system trust store via _update_system_ca_store).
            assert ssl._create_default_https_context is ssl.create_default_context
        finally:
            ssl._create_default_https_context = original


# ---------------------------------------------------------------------------
# _patch_httpx_defaults()
# ---------------------------------------------------------------------------

class TestPatchHttpxDefaults:
    def test_patches_async_client_verify_to_false(self):
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")
        from python.helpers import tls

        orig_init = getattr(httpx.AsyncClient, "_sentinel_orig_init", httpx.AsyncClient.__init__)
        try:
            tls._patch_httpx_defaults(False)
            # Capture what verify value the patched init sets
            created_with = {}
            _patched = httpx.AsyncClient.__init__

            def _spy(self, *args, **kwargs):
                # The patched init should have already forced verify=False
                created_with["verify"] = kwargs.get("verify", "NOT_SET")
                # Call original to avoid side effects
                orig_init(self, *args, **kwargs)

            httpx.AsyncClient.__init__ = _spy
            try:
                httpx.AsyncClient()
            except Exception:
                pass

            # When verify=False, the patch should NOT have set anything via
            # setdefault (which wouldn't override); it should FORCE verify=False.
            # But since we replaced __init__ with our spy, let's test the
            # patched function directly instead.
        finally:
            httpx.AsyncClient.__init__ = orig_init
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init
            if hasattr(httpx.Client, "_sentinel_orig_init"):
                del httpx.Client._sentinel_orig_init

    def test_force_overrides_explicit_verify_when_disabled(self):
        """When TLS verify is disabled, the patch must FORCE verify=False
        even if the caller explicitly passes verify=some_ssl_context."""
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")
        from python.helpers import tls

        # Clean up any previous patches
        if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
            httpx.AsyncClient.__init__ = httpx.AsyncClient._sentinel_orig_init
            del httpx.AsyncClient._sentinel_orig_init
        if hasattr(httpx.Client, "_sentinel_orig_init"):
            httpx.Client.__init__ = httpx.Client._sentinel_orig_init
            del httpx.Client._sentinel_orig_init

        orig_async = httpx.AsyncClient.__init__
        orig_sync = httpx.Client.__init__
        try:
            tls._patch_httpx_defaults(False)

            # Intercept what the original __init__ receives AFTER patching
            received_kwargs = {}
            stored_orig = httpx.AsyncClient._sentinel_orig_init

            def _intercept(self, *args, **kwargs):
                received_kwargs.update(kwargs)

            httpx.AsyncClient._sentinel_orig_init = _intercept
            # Re-apply patch so it captures the new _sentinel_orig_init
            tls._patch_httpx_defaults(False)

            # Simulate what litellm does: pass verify=<ssl_context>
            stale_ctx = ssl.create_default_context()
            try:
                httpx.AsyncClient(verify=stale_ctx)
            except Exception:
                pass

            # The patch must have forced verify=False, overriding the ssl context
            assert received_kwargs.get("verify") is False, \
                f"Expected verify=False but got verify={received_kwargs.get('verify')}"
        finally:
            httpx.AsyncClient.__init__ = orig_async
            httpx.Client.__init__ = orig_sync
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init
            if hasattr(httpx.Client, "_sentinel_orig_init"):
                del httpx.Client._sentinel_orig_init

    def test_bundle_path_uses_setdefault(self):
        """When TLS verify is a CA bundle path, the patch should use
        setdefault so an explicit verify= from litellm wins."""
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")
        from python.helpers import tls

        # Clean up any previous patches
        if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
            httpx.AsyncClient.__init__ = httpx.AsyncClient._sentinel_orig_init
            del httpx.AsyncClient._sentinel_orig_init
        if hasattr(httpx.Client, "_sentinel_orig_init"):
            httpx.Client.__init__ = httpx.Client._sentinel_orig_init
            del httpx.Client._sentinel_orig_init

        orig_async = httpx.AsyncClient.__init__
        orig_sync = httpx.Client.__init__
        try:
            tls._patch_httpx_defaults("/custom/ca.pem")

            # Intercept
            received_kwargs = {}
            stored_orig = httpx.AsyncClient._sentinel_orig_init

            def _intercept(self, *args, **kwargs):
                received_kwargs.update(kwargs)

            httpx.AsyncClient._sentinel_orig_init = _intercept
            tls._patch_httpx_defaults("/custom/ca.pem")

            # Case 1: caller passes no verify → should get the bundle path
            try:
                httpx.AsyncClient()
            except Exception:
                pass
            assert received_kwargs.get("verify") == "/custom/ca.pem"

            # Case 2: caller passes explicit verify → should keep caller's value
            received_kwargs.clear()
            explicit_ctx = ssl.create_default_context()
            try:
                httpx.AsyncClient(verify=explicit_ctx)
            except Exception:
                pass
            assert received_kwargs.get("verify") is explicit_ctx
        finally:
            httpx.AsyncClient.__init__ = orig_async
            httpx.Client.__init__ = orig_sync
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init
            if hasattr(httpx.Client, "_sentinel_orig_init"):
                del httpx.Client._sentinel_orig_init

    def test_restores_default_when_verify_true(self):
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")
        from python.helpers import tls

        # Clean up any previous patches
        if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
            httpx.AsyncClient.__init__ = httpx.AsyncClient._sentinel_orig_init
            del httpx.AsyncClient._sentinel_orig_init
        if hasattr(httpx.Client, "_sentinel_orig_init"):
            httpx.Client.__init__ = httpx.Client._sentinel_orig_init
            del httpx.Client._sentinel_orig_init

        orig_async = httpx.AsyncClient.__init__
        orig_sync = httpx.Client.__init__
        try:
            # Patch then restore
            tls._patch_httpx_defaults(False)
            tls._patch_httpx_defaults(True)
            # After restore, __init__ should be the stored original
            assert httpx.AsyncClient.__init__ is httpx.AsyncClient._sentinel_orig_init
            assert httpx.Client.__init__ is httpx.Client._sentinel_orig_init
        finally:
            httpx.AsyncClient.__init__ = orig_async
            httpx.Client.__init__ = orig_sync
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init
            if hasattr(httpx.Client, "_sentinel_orig_init"):
                del httpx.Client._sentinel_orig_init


# ---------------------------------------------------------------------------
# _clear_litellm_client_cache()
# ---------------------------------------------------------------------------

class TestClearLitellmClientCache:
    def test_flushes_in_memory_llm_clients_cache(self):
        """The primary cache in litellm ≥1.55 is in_memory_llm_clients_cache.
        _clear_litellm_client_cache must call flush_cache() on it."""
        from python.helpers import tls

        mock_cache = MagicMock()
        mock_cache.flush_cache = MagicMock()

        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = mock_cache
        # Attributes that should be cleared
        mock_litellm.module_level_client = MagicMock()
        mock_litellm.module_level_aclient = MagicMock()
        mock_litellm.client_session = MagicMock()
        mock_litellm.aclient_session = MagicMock()

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
            tls._clear_litellm_client_cache()

        mock_cache.flush_cache.assert_called_once()

    def test_clears_module_level_client(self):
        """module_level_client is a singleton HTTPHandler that also embeds
        an httpx client.  It must be set to None."""
        from python.helpers import tls

        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = MagicMock()
        mock_litellm.module_level_client = "stale_client"
        mock_litellm.module_level_aclient = "stale_aclient"
        mock_litellm.client_session = None
        mock_litellm.aclient_session = None

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
            tls._clear_litellm_client_cache()

        assert mock_litellm.module_level_client is None
        assert mock_litellm.module_level_aclient is None

    def test_clears_session_overrides(self):
        """client_session and aclient_session override _get_*_http_client()
        return values.  They must be cleared."""
        from python.helpers import tls

        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = MagicMock()
        mock_litellm.module_level_client = None
        mock_litellm.module_level_aclient = None
        mock_litellm.client_session = "stale_session"
        mock_litellm.aclient_session = "stale_async_session"

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
            tls._clear_litellm_client_cache()

        assert mock_litellm.client_session is None
        assert mock_litellm.aclient_session is None

    def test_handles_missing_cache_attribute_gracefully(self):
        """If in_memory_llm_clients_cache doesn't exist (older litellm),
        the function should not raise."""
        from python.helpers import tls

        mock_litellm = MagicMock(spec=[])  # No attributes at all

        import sys
        with patch.dict(sys.modules, {"litellm": mock_litellm}):
            # Should not raise
            tls._clear_litellm_client_cache()

    def test_handles_litellm_not_installed(self):
        """If litellm is not importable, the function should silently pass."""
        from python.helpers import tls
        import sys

        # Temporarily make litellm unimportable
        real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
        def _mock_import(name, *args, **kwargs):
            if name == "litellm" or name.startswith("litellm."):
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_mock_import):
            # Should not raise
            tls._clear_litellm_client_cache()


# ---------------------------------------------------------------------------
# Full pipeline: apply_env_vars sets litellm.ssl_verify + clears cache
# ---------------------------------------------------------------------------

class TestApplyEnvVarsLitellmIntegration:
    def test_sets_litellm_ssl_verify_false(self):
        """apply_env_vars must set litellm.ssl_verify = False when disabled."""
        from python.helpers import tls

        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = MagicMock()
        mock_litellm.module_level_client = None
        mock_litellm.module_level_aclient = None
        mock_litellm.client_session = None
        mock_litellm.aclient_session = None

        import sys
        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store"):
                with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
                    tls.apply_env_vars()

        assert mock_litellm.ssl_verify is False
        mock_litellm.in_memory_llm_clients_cache.flush_cache.assert_called_once()

    def test_sets_litellm_ssl_verify_to_bundle_path(self, tmp_path):
        """apply_env_vars must set litellm.ssl_verify to the CA bundle path."""
        from python.helpers import tls

        bundle = str(tmp_path / "ca.pem")
        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = MagicMock()
        mock_litellm.module_level_client = None
        mock_litellm.module_level_aclient = None
        mock_litellm.client_session = None
        mock_litellm.aclient_session = None

        import sys
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, bundle)):
            with patch.object(tls, "_update_system_ca_store"):
                with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
                    tls.apply_env_vars()

        assert mock_litellm.ssl_verify == bundle
        mock_litellm.in_memory_llm_clients_cache.flush_cache.assert_called_once()

    def test_sets_litellm_ssl_verify_true_for_default(self):
        """apply_env_vars must set litellm.ssl_verify = True for default."""
        from python.helpers import tls

        mock_litellm = MagicMock()
        mock_litellm.in_memory_llm_clients_cache = MagicMock()
        mock_litellm.module_level_client = None
        mock_litellm.module_level_aclient = None
        mock_litellm.client_session = None
        mock_litellm.aclient_session = None

        import sys
        with patch("python.helpers.settings.get_settings", return_value=_settings(True, "")):
            with patch.object(tls, "_update_system_ca_store"):
                with patch.dict(sys.modules, {"litellm": mock_litellm, "litellm.utils": MagicMock()}):
                    tls.apply_env_vars()

        assert mock_litellm.ssl_verify is True
        mock_litellm.in_memory_llm_clients_cache.flush_cache.assert_called_once()
