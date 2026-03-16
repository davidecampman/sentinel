"""1Password CLI / Service Account integration for Sentinel.

Provides OnePasswordProvider, which resolves op:// secret references and
fetches all fields from a named vault item using the `op` CLI binary
authenticated via OP_SERVICE_ACCOUNT_TOKEN.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Dict, Optional

# Value prefix that marks a secrets.env entry as a 1Password reference
OP_REFERENCE_PREFIX = "op://"


class OnePasswordError(Exception):
    """Raised when the op CLI returns an error or is unavailable."""


class OnePasswordProvider:
    """Wraps the `op` CLI for service-account-authenticated secret access.

    Parameters
    ----------
    token:
        A 1Password service account token (``ops_…``).  When *None* the value
        is read from the ``OP_SERVICE_ACCOUNT_TOKEN`` environment variable.
    op_binary:
        Path to the ``op`` executable.  Defaults to ``op`` (resolved via
        ``$PATH``).
    timeout:
        Subprocess timeout in seconds.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        op_binary: str = "op",
        timeout: int = 10,
    ):
        self._token = token or os.environ.get("OP_SERVICE_ACCOUNT_TOKEN", "")
        self._op_binary = op_binary
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the op binary is on PATH and a token is configured."""
        return bool(self._token) and shutil.which(self._op_binary) is not None

    def test_connection(self) -> None:
        """Verify credentials by listing vaults.  Raises OnePasswordError on failure."""
        self._run(["vault", "list", "--format", "json"])

    def read(self, reference: str) -> str:
        """Resolve a single ``op://vault/item/field`` reference to its plaintext value.

        Parameters
        ----------
        reference:
            A fully-qualified 1Password secret reference, e.g.
            ``op://Engineering/Sentinel/ANTHROPIC_API_KEY``.

        Returns
        -------
        str
            The plaintext secret value.

        Raises
        ------
        OnePasswordError
            If the reference cannot be resolved.
        """
        output = self._run(["read", "--no-newline", reference])
        return output

    def get_item_fields(self, vault: str, item: str) -> Dict[str, str]:
        """Fetch all label→value pairs from a named vault item.

        Field labels are normalised to UPPER_CASE with spaces replaced by
        underscores so they map cleanly to environment-variable names.

        Parameters
        ----------
        vault:
            Vault name (or UUID).
        item:
            Item name (or UUID).

        Returns
        -------
        Dict[str, str]
            Mapping of normalised field label → plaintext value.
            Only ``STRING`` and ``CONCEALED`` type fields are included.

        Raises
        ------
        OnePasswordError
            If the item cannot be fetched.
        """
        raw = self._run(
            ["item", "get", item, "--vault", vault, "--format", "json"]
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OnePasswordError(
                f"op returned invalid JSON for item '{item}' in vault '{vault}': {exc}"
            ) from exc

        result: Dict[str, str] = {}
        for field in data.get("fields", []):
            ftype = field.get("type", "")
            if ftype not in ("STRING", "CONCEALED"):
                continue
            label: str = field.get("label", "")
            value: str = field.get("value", "")
            if not label:
                continue
            # Normalise: upper-case, spaces → underscores
            key = label.upper().replace(" ", "_")
            result[key] = value

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_env(self) -> Dict[str, str]:
        """Return a minimal environment dict for the op subprocess."""
        env: Dict[str, str] = {}
        # Forward only the token; avoid leaking the full process environment.
        if self._token:
            env["OP_SERVICE_ACCOUNT_TOKEN"] = self._token
        # op needs HOME to locate its config directory on some platforms.
        if "HOME" in os.environ:
            env["HOME"] = os.environ["HOME"]
        # PATH is required to locate helper binaries (e.g. git-credential-op).
        if "PATH" in os.environ:
            env["PATH"] = os.environ["PATH"]
        return env

    def _run(self, args: list[str]) -> str:
        """Run an op subcommand and return stdout.  Raises OnePasswordError on failure."""
        if not self._token:
            raise OnePasswordError(
                "No 1Password service account token configured. "
                "Set OP_SERVICE_ACCOUNT_TOKEN in your environment or in Settings."
            )
        binary = shutil.which(self._op_binary)
        if binary is None:
            raise OnePasswordError(
                f"The '{self._op_binary}' binary was not found on PATH. "
                "Install the 1Password CLI: https://developer.1password.com/docs/cli/get-started/"
            )

        cmd = [binary] + args
        try:
            result = subprocess.run(
                cmd,
                env=self._build_env(),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise OnePasswordError(
                f"op command timed out after {self._timeout}s: {' '.join(args)}"
            ) from exc
        except OSError as exc:
            raise OnePasswordError(f"Failed to launch op binary: {exc}") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise OnePasswordError(
                f"op exited with code {result.returncode}: {stderr}"
            )

        return result.stdout


def get_provider() -> OnePasswordProvider:
    """Return a provider configured from the current Sentinel settings."""
    from python.helpers import settings as _settings

    s = _settings.get_settings()
    token: str = s.get("op_service_account_token", "")  # type: ignore[arg-type]
    return OnePasswordProvider(token=token or None)
