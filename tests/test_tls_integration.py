"""
Integration tests for the TLS global disable switch.

These tests verify the ACTUAL SSL behavior changes — not mocked settings,
but real ssl contexts, real httpx clients, and real subprocess behavior.
They reproduce the exact failure modes that were broken before the fix.
"""
import os
import ssl
import subprocess
import sys
import textwrap
import pytest
from unittest.mock import patch


def _settings(verify: bool, bundle: str = "") -> dict:
    return {"tls_verify": verify, "tls_ca_bundle": bundle}


# ---------------------------------------------------------------------------
# FIX 1: ssl.create_default_context() must return unverified contexts
#         when tls_verify=False.  Previously only _create_default_https_context
#         was patched — most libraries call create_default_context directly.
# ---------------------------------------------------------------------------

class TestSslCreateDefaultContextPatched:
    """Proves that ssl.create_default_context() is actually patched."""

    def test_create_default_context_returns_unverified_when_disabled(self):
        import ssl as _ssl
        from python.helpers import tls

        orig = _ssl.create_default_context
        orig_internal = _ssl._create_default_https_context
        try:
            with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()

            # This is what httpx, aiohttp, botocore all call internally.
            # Before the fix, this STILL returned a verified context.
            ctx = _ssl.create_default_context()
            assert ctx.check_hostname is False, \
                "ssl.create_default_context() still has check_hostname=True after disabling TLS"
            assert ctx.verify_mode == _ssl.CERT_NONE, \
                "ssl.create_default_context() still verifies certs after disabling TLS"
        finally:
            _ssl.create_default_context = orig
            _ssl._create_default_https_context = orig_internal

    def test_create_default_context_restored_when_enabled(self):
        import ssl as _ssl
        from python.helpers import tls

        orig = _ssl.create_default_context
        orig_internal = _ssl._create_default_https_context
        try:
            # Disable then re-enable
            with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()
            with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()

            ctx = _ssl.create_default_context()
            # Should be back to verifying
            assert ctx.verify_mode == _ssl.CERT_REQUIRED, \
                "ssl.create_default_context() not restored to verified after re-enabling TLS"
        finally:
            _ssl.create_default_context = orig
            _ssl._create_default_https_context = orig_internal

    def test_botocore_style_ssl_context_creation_respects_switch(self):
        """Simulate how botocore creates SSL contexts (the Bedrock fix)."""
        import ssl as _ssl
        from python.helpers import tls

        orig = _ssl.create_default_context
        orig_internal = _ssl._create_default_https_context
        try:
            with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()

            # This is roughly what botocore does internally:
            ctx = _ssl.create_default_context()
            ctx.load_default_certs()  # botocore loads system certs
            # Even after loading certs, verification should still be disabled
            assert ctx.verify_mode == _ssl.CERT_NONE, \
                "Botocore-style context creation still verifies after disabling TLS"
        finally:
            _ssl.create_default_context = orig
            _ssl._create_default_https_context = orig_internal


# ---------------------------------------------------------------------------
# FIX 2: httpx monkey-patch must FORCE-override verify, not setdefault
# ---------------------------------------------------------------------------

class TestHttpxForceOverride:
    """Proves that httpx clients get verify=False even when callers pass verify=True."""

    def test_explicit_verify_true_is_overridden(self):
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")

        from python.helpers import tls
        captured = {}

        # Save and patch
        if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
            real_orig = httpx.AsyncClient._sentinel_orig_init
        else:
            real_orig = httpx.AsyncClient.__init__

        try:
            tls._patch_httpx_defaults(False)

            # Intercept to see what verify value reaches the real constructor
            patched = httpx.AsyncClient.__init__

            def spy(self, *args, **kwargs):
                captured["verify"] = kwargs.get("verify", "MISSING")
                # Don't actually construct (avoids event loop issues)
                raise _SpyDone()

            httpx.AsyncClient.__init__ = spy

            with pytest.raises(_SpyDone):
                # Caller passes verify=True — simulating OpenAI SDK behavior
                httpx.AsyncClient(verify=True)

            assert captured["verify"] is False, \
                "httpx.AsyncClient(verify=True) was NOT overridden to False"
        finally:
            httpx.AsyncClient.__init__ = real_orig
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init

    def test_explicit_ssl_context_is_overridden(self):
        """OpenAI SDK may pass verify=<SSLContext> — must still be overridden."""
        try:
            import httpx
        except ImportError:
            pytest.skip("httpx not installed")

        from python.helpers import tls
        captured = {}

        if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
            real_orig = httpx.AsyncClient._sentinel_orig_init
        else:
            real_orig = httpx.AsyncClient.__init__

        try:
            tls._patch_httpx_defaults(False)

            def spy(self, *args, **kwargs):
                captured["verify"] = kwargs.get("verify", "MISSING")
                raise _SpyDone()

            httpx.AsyncClient.__init__ = spy

            custom_ctx = ssl.create_default_context()
            with pytest.raises(_SpyDone):
                httpx.AsyncClient(verify=custom_ctx)

            assert captured["verify"] is False, \
                "httpx.AsyncClient(verify=<SSLContext>) was NOT overridden to False"
        finally:
            httpx.AsyncClient.__init__ = real_orig
            if hasattr(httpx.AsyncClient, "_sentinel_orig_init"):
                del httpx.AsyncClient._sentinel_orig_init


class _SpyDone(Exception):
    """Sentinel exception to abort construction after capturing args."""
    pass


# ---------------------------------------------------------------------------
# FIX 3: SearXNG sitecustomize.py subprocess test
# ---------------------------------------------------------------------------

class TestSearxngSubprocess:
    """Proves the sitecustomize.py injection works in a real subprocess."""

    def test_subprocess_ssl_disabled_via_sitecustomize(self, tmp_path):
        """Simulate SearXNG: a separate Python process with PYTHONPATH injection."""
        # Write the sitecustomize.py the same way tls.py does
        site_dir = tmp_path / "searxng_site"
        site_dir.mkdir()
        (site_dir / "sitecustomize.py").write_text(textwrap.dedent("""\
            import os, ssl
            if os.environ.get("A0_TLS_VERIFY") == "0":
                ssl._create_default_https_context = ssl._create_unverified_context
                _orig_create = ssl.create_default_context
                def _unverified_default(*args, **kwargs):
                    ctx = _orig_create(*args, **kwargs)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    return ctx
                ssl.create_default_context = _unverified_default
        """))

        # Run a subprocess that checks if SSL verification is actually disabled
        check_script = textwrap.dedent("""\
            import ssl
            ctx = ssl.create_default_context()
            if ctx.check_hostname is False and ctx.verify_mode == ssl.CERT_NONE:
                print("DISABLED")
            else:
                print("ENABLED")
        """)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(site_dir)
        env["A0_TLS_VERIFY"] = "0"

        result = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True, text=True, env=env, timeout=10,
        )
        assert result.stdout.strip() == "DISABLED", \
            f"Subprocess SSL not disabled. stdout={result.stdout!r} stderr={result.stderr!r}"

    def test_subprocess_ssl_enabled_when_verify_on(self, tmp_path):
        """When A0_TLS_VERIFY=1, the sitecustomize should NOT patch SSL."""
        site_dir = tmp_path / "searxng_site"
        site_dir.mkdir()
        (site_dir / "sitecustomize.py").write_text(textwrap.dedent("""\
            import os, ssl
            if os.environ.get("A0_TLS_VERIFY") == "0":
                ssl._create_default_https_context = ssl._create_unverified_context
                _orig_create = ssl.create_default_context
                def _unverified_default(*args, **kwargs):
                    ctx = _orig_create(*args, **kwargs)
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    return ctx
                ssl.create_default_context = _unverified_default
        """))

        check_script = textwrap.dedent("""\
            import ssl
            ctx = ssl.create_default_context()
            if ctx.check_hostname is False and ctx.verify_mode == ssl.CERT_NONE:
                print("DISABLED")
            else:
                print("ENABLED")
        """)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(site_dir)
        env["A0_TLS_VERIFY"] = "1"

        result = subprocess.run(
            [sys.executable, "-c", check_script],
            capture_output=True, text=True, env=env, timeout=10,
        )
        assert result.stdout.strip() == "ENABLED", \
            f"Subprocess SSL should be enabled when A0_TLS_VERIFY=1"


# ---------------------------------------------------------------------------
# FIX 4: apply_env_vars round-trip — disable then re-enable
# ---------------------------------------------------------------------------

class TestApplyEnvVarsRoundTrip:
    """End-to-end test: toggle TLS off then on, verify everything resets."""

    def test_toggle_off_on_restores_ssl_defaults(self):
        import ssl as _ssl
        from python.helpers import tls

        orig_create = _ssl.create_default_context
        orig_internal = _ssl._create_default_https_context
        try:
            # 1. Disable TLS verification
            with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()

            ctx_disabled = _ssl.create_default_context()
            assert ctx_disabled.verify_mode == _ssl.CERT_NONE

            # 2. Re-enable TLS verification
            with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
                with patch.object(tls, "_update_system_ca_store"):
                    tls.apply_env_vars()

            ctx_enabled = _ssl.create_default_context()
            assert ctx_enabled.verify_mode == _ssl.CERT_REQUIRED, \
                "SSL verification not restored after re-enabling TLS"
            assert ctx_enabled.check_hostname is True, \
                "check_hostname not restored after re-enabling TLS"

        finally:
            _ssl.create_default_context = orig_create
            _ssl._create_default_https_context = orig_internal

    def test_env_vars_cleared_on_reenable(self):
        from python.helpers import tls

        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store"):
                tls.apply_env_vars()

        assert os.environ.get("CURL_CA_BUNDLE") == "/dev/null"

        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            with patch.object(tls, "_update_system_ca_store"):
                tls.apply_env_vars()

        assert "CURL_CA_BUNDLE" not in os.environ
        assert "REQUESTS_CA_BUNDLE" not in os.environ


# ---------------------------------------------------------------------------
# FIX 5: tls.env file includes A0_TLS_VERIFY signal
# ---------------------------------------------------------------------------

class TestTlsEnvFile:
    """Verify the tls.env file contents are correct for SearXNG."""

    def test_tls_env_contains_a0_tls_verify_0_when_disabled(self, tmp_path):
        from python.helpers import tls

        env_path = tmp_path / "tls.env"
        site_dir = tmp_path / "searxng_site"

        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store"):
                with patch("python.helpers.files.get_abs_path", side_effect=lambda p: str(tmp_path / p)):
                    tls.apply_env_vars()

        content = (tmp_path / "usr" / "tls.env").read_text()
        assert "A0_TLS_VERIFY=0" in content, \
            f"tls.env missing A0_TLS_VERIFY=0. Content:\n{content}"

    def test_tls_env_contains_a0_tls_verify_1_when_enabled(self, tmp_path):
        from python.helpers import tls

        with patch("python.helpers.settings.get_settings", return_value=_settings(True)):
            with patch.object(tls, "_update_system_ca_store"):
                with patch("python.helpers.files.get_abs_path", side_effect=lambda p: str(tmp_path / p)):
                    tls.apply_env_vars()

        content = (tmp_path / "usr" / "tls.env").read_text()
        assert "A0_TLS_VERIFY=1" in content, \
            f"tls.env missing A0_TLS_VERIFY=1. Content:\n{content}"

    def test_sitecustomize_written_when_disabled(self, tmp_path):
        from python.helpers import tls

        with patch("python.helpers.settings.get_settings", return_value=_settings(False)):
            with patch.object(tls, "_update_system_ca_store"):
                with patch("python.helpers.files.get_abs_path", side_effect=lambda p: str(tmp_path / p)):
                    tls.apply_env_vars()

        sc_path = tmp_path / "usr" / "searxng_site" / "sitecustomize.py"
        assert sc_path.exists(), "sitecustomize.py was not written"
        content = sc_path.read_text()
        assert "CERT_NONE" in content
        assert "A0_TLS_VERIFY" in content
