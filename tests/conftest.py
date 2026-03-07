"""
conftest.py — Test environment bootstrap for Agent Zero Corporate Edition.

Agent Zero has several heavyweight dependencies (litellm, openai, simpleeval,
etc.) that are not available in the lightweight /opt/venv used by the test
runner.  Rather than installing the full production stack, we register
MagicMock stubs for every module that would otherwise fail to import.

Critically, stubs are injected at MODULE LEVEL so they are in place before
any test file imports.  We also explicitly attach the settings stub as an
attribute of the python.helpers package so that
    patch("python.helpers.settings.get_settings", ...)
can resolve the dotted path without triggering the real import chain.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _stub(name: str, **attrs) -> MagicMock:
    """Register a MagicMock stub in sys.modules and return it."""
    if name in sys.modules:
        return sys.modules[name]  # type: ignore[return-value]
    mod = MagicMock(spec=types.ModuleType(name))
    mod.__name__ = name
    mod.__package__ = name.rpartition(".")[0] or name
    mod.__spec__ = None
    mod.__path__ = []  # mark as package so sub-imports work
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# litellm  (used by models.py)
# ---------------------------------------------------------------------------
_litellm = _stub("litellm")
_litellm.completion = MagicMock()
_litellm.acompletion = MagicMock()
_litellm.embedding = MagicMock()
_stub("litellm.exceptions")
_stub("litellm.types")
_stub("litellm.types.utils", ModelResponse=type("ModelResponse", (), {}))

# ---------------------------------------------------------------------------
# openai
# ---------------------------------------------------------------------------
_stub("openai")
_stub("openai.types")
_stub("openai.types.chat")

# ---------------------------------------------------------------------------
# Other heavy top-level deps
# ---------------------------------------------------------------------------
_stub("models")
_stub("simpleeval")
_stub("anthropic")
_stub("boto3")
_stub("botocore")
_stub("botocore.exceptions")
_stub("tiktoken")
_stub("chromadb")
_stub("sentence_transformers")
_stub("git")  # gitpython exposes "git" top-level
_stub("yaml")

# ---------------------------------------------------------------------------
# python.helpers sub-modules that drag in heavy deps
# ---------------------------------------------------------------------------
_stub("python.helpers.runtime")
_stub("python.helpers.whisper")
_stub("python.helpers.git")
_stub("python.helpers.providers")
_stub("python.helpers.secrets")
_stub("python.helpers.print_style")
_stub("python.helpers.notification")
_stub("python.helpers.subagents")
_stub("python.helpers.task_scheduler")
_stub("python.helpers.mcp_handler")
_stub("python.helpers.tunnel_manager")

# ---------------------------------------------------------------------------
# python.helpers.settings — stub with a real get_settings callable so that
#   patch("python.helpers.settings.get_settings", ...)  works without
#   importing the full settings module (which pulls in litellm, models, etc.)
#
# We also attach the stub as an attribute of the python.helpers package
# object so unittest.mock can resolve the dotted path via getattr().
# ---------------------------------------------------------------------------
_settings_stub = _stub("python.helpers.settings", get_settings=MagicMock())

# Attach to the real python.helpers package object so getattr resolution works.
import python.helpers as _helpers_pkg  # noqa: E402 — package has no heavy deps
_helpers_pkg.settings = _settings_stub
