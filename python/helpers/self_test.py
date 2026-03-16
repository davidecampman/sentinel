"""
Sentinel self-test module.
Runs a suite of lightweight diagnostic checks and returns structured results.
"""
from __future__ import annotations

import importlib
import os
import secrets
import shutil
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

Status = Literal["pass", "fail", "warn", "skip"]

# Map provider names to the env-var that holds their API key
_PROVIDER_KEY_MAP: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "cohere": "COHERE_API_KEY",
}


@dataclass
class TestResult:
    name: str
    status: Status
    message: str
    detail: str = ""
    sub_results: list[tuple[Status, str]] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class SelfTestReport:
    results: list[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warned: int = 0
    skipped: int = 0
    total_ms: int = 0

    def add(self, result: TestResult) -> None:
        self.results.append(result)
        if result.status == "pass":
            self.passed += 1
        elif result.status == "fail":
            self.failed += 1
        elif result.status == "warn":
            self.warned += 1
        elif result.status == "skip":
            self.skipped += 1

    @property
    def overall(self) -> Status:
        if self.failed:
            return "fail"
        if self.warned:
            return "warn"
        return "pass"

    def to_markdown(self) -> str:
        icon: dict[str, str] = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}

        lines = [
            "## 🔍 Sentinel Self-Test Report",
            "",
            f"**Overall:** {icon[self.overall]} {self.overall.upper()}  "
            f"| Passed: {self.passed} | Failed: {self.failed} "
            f"| Warnings: {self.warned} | Skipped: {self.skipped}",
            f"**Duration:** {self.total_ms} ms",
            "",
            "| Status | Test | Message | Time |",
            "|--------|------|---------|------|",
        ]

        for r in self.results:
            detail = f" — {r.detail}" if r.detail else ""
            lines.append(
                f"| {icon[r.status]} | **{r.name}** | {r.message}{detail} | {r.duration_ms} ms |"
            )

        # Detailed breakdown for failed and warned checks
        notable = [r for r in self.results if r.status in ("fail", "warn")]
        if notable:
            lines += ["", "---", ""]
            for r in notable:
                heading_icon = icon[r.status]
                lines += [f"### {heading_icon} {r.name}", ""]
                lines.append(f"**Status:** {r.status.upper()}  ")
                lines.append(f"**Summary:** {r.message}  ")
                if r.detail:
                    lines.append(f"**Detail:** {r.detail}  ")
                if r.sub_results:
                    lines.append("")
                    lines.append("**Sub-checks:**")
                    lines.append("")
                    for sub_status, sub_msg in r.sub_results:
                        lines.append(f"- {icon[sub_status]} {sub_msg}")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(
    name: str,
    fn: Callable[[], tuple[Status, str, str] | tuple[Status, str, str, list[tuple[Status, str]]]],
) -> TestResult:
    t0 = time.monotonic()
    try:
        result = fn()
        if len(result) == 4:
            status, message, detail, sub_results = result  # type: ignore[misc]
        else:
            status, message, detail = result  # type: ignore[misc]
            sub_results = []
    except Exception as exc:
        status, message, detail, sub_results = "fail", f"Unexpected exception: {exc}", "", []
    duration_ms = int((time.monotonic() - t0) * 1000)
    return TestResult(
        name=name,
        status=status,
        message=message,
        detail=detail,
        sub_results=sub_results,
        duration_ms=duration_ms,
    )


def _worst(*statuses: Status) -> Status:
    order: list[Status] = ["fail", "warn", "skip", "pass"]
    for s in order:
        if s in statuses:
            return s
    return "pass"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_env_vars() -> TestResult:
    def _check():
        providers = [
            ("ANTHROPIC_API_KEY", "Anthropic"),
            ("OPENAI_API_KEY", "OpenAI"),
            ("OPENROUTER_API_KEY", "OpenRouter"),
            ("GOOGLE_API_KEY", "Google"),
            ("GROQ_API_KEY", "Groq"),
        ]
        sub: list[tuple[Status, str]] = []
        present: list[str] = []

        for key, label in providers:
            val = os.getenv(key, "")
            if val:
                masked = val[:4] + "…" + val[-4:] if len(val) > 8 else "****"
                sub.append(("pass", f"{label} ({key}): set ({masked})"))
                present.append(label)
            else:
                sub.append(("warn", f"{label} ({key}): not set"))

        auth_login = os.getenv("A0_AUTH_LOGIN", "")
        if auth_login:
            sub.append(("pass", "A0_AUTH_LOGIN: set"))
        else:
            sub.append(("warn", "A0_AUTH_LOGIN: not set (running in no-auth mode)"))

        if not present:
            return "fail", "No LLM API key configured", "At least one provider key is required", sub

        status: Status = "pass" if auth_login else "warn"
        return status, f"{len(present)} provider(s) configured: {', '.join(present)}", "", sub

    return _run("Environment Variables", _check)


def check_core_imports() -> TestResult:
    def _check():
        modules = [
            ("langchain_core", "LangChain core"),
            ("flask", "Flask"),
            ("socketio", "Socket.IO"),
            ("pydantic", "Pydantic"),
            ("dotenv", "python-dotenv"),
            ("requests", "requests"),
            ("uvicorn", "Uvicorn"),
            ("fastapi", "FastAPI"),
        ]
        sub: list[tuple[Status, str]] = []
        failed = []

        for mod, label in modules:
            try:
                m = importlib.import_module(mod)
                version = getattr(m, "__version__", "?")
                sub.append(("pass", f"{label} ({mod}): v{version}"))
            except ImportError as e:
                sub.append(("fail", f"{label} ({mod}): {e}"))
                failed.append(label)

        if failed:
            return "fail", f"{len(failed)} core import(s) failed: {', '.join(failed)}", "", sub
        return "pass", f"All {len(modules)} core modules importable", "", sub

    return _run("Core Imports", _check)


def check_heavy_imports() -> TestResult:
    def _check():
        modules = [
            ("chromadb", "ChromaDB (vector store)"),
            ("faiss", "FAISS (vector search)"),
            ("sentence_transformers", "Sentence Transformers (embeddings)"),
            ("playwright", "Playwright (browser automation)"),
            ("whisper", "Whisper (speech-to-text)"),
        ]
        sub: list[tuple[Status, str]] = []
        available = []
        unavailable = []

        for mod, label in modules:
            try:
                m = importlib.import_module(mod)
                version = getattr(m, "__version__", "?")
                sub.append(("pass", f"{label}: v{version}"))
                available.append(label)
            except ImportError as e:
                reason = str(e).split("No module named")[-1].strip().strip("'")
                sub.append(("warn", f"{label}: not installed (missing: {reason})"))
                unavailable.append(label)
            except Exception as e:
                sub.append(("warn", f"{label}: import error — {e}"))
                unavailable.append(label)

        if len(unavailable) == len(modules):
            return "warn", "All optional deps unavailable", "Features requiring these will be disabled", sub
        if unavailable:
            return (
                "warn",
                f"{len(unavailable)} optional dep(s) unavailable",
                f"Unavailable: {', '.join(unavailable)}",
                sub,
            )
        return "pass", f"All {len(modules)} optional deps available", "", sub

    return _run("Optional Dependencies", _check)


def check_agent_config() -> TestResult:
    def _check():
        from initialize import initialize_agent
        config = initialize_agent()
        if config is None:
            return "fail", "initialize_agent() returned None", "", []

        sub: list[tuple[Status, str]] = []

        # Chat model
        chat_model = getattr(config, "chat_model", None)
        if chat_model is None:
            sub.append(("fail", "chat_model: not configured"))
        else:
            provider = getattr(chat_model, "provider", "unknown").lower()
            name = getattr(chat_model, "name", "unknown")
            ctx = getattr(chat_model, "ctx_length", 0)
            vision = getattr(chat_model, "vision", False)
            sub.append(("pass", f"chat_model: {provider}/{name} (ctx: {ctx}, vision: {vision})"))

            # Check the API key for this provider is actually set
            expected_key = _PROVIDER_KEY_MAP.get(provider)
            if expected_key:
                if os.getenv(expected_key):
                    sub.append(("pass", f"API key for {provider} ({expected_key}): present"))
                else:
                    # Could be using api_base (local/self-hosted), so warn not fail
                    api_base = getattr(chat_model, "api_base", "")
                    if api_base:
                        sub.append(("pass", f"API key for {provider}: using api_base={api_base}"))
                    else:
                        sub.append(("warn", f"API key for {provider} ({expected_key}): not set and no api_base"))
            else:
                sub.append(("pass", f"Provider '{provider}' uses custom auth (no standard key check)"))

        # Utility model
        util_model = getattr(config, "utility_model", None)
        if util_model:
            sub.append(("pass", f"utility_model: {getattr(util_model, 'provider', '?')}/{getattr(util_model, 'name', '?')}"))
        else:
            sub.append(("warn", "utility_model: not configured"))

        # Embeddings model
        emb_model = getattr(config, "embeddings_model", None)
        if emb_model:
            sub.append(("pass", f"embeddings_model: {getattr(emb_model, 'provider', '?')}/{getattr(emb_model, 'name', '?')}"))
        else:
            sub.append(("warn", "embeddings_model: not configured (memory/knowledge features will be limited)"))

        worst = _worst(*[s for s, _ in sub])
        msg = f"Agent config loaded"
        if chat_model:
            msg += f" (chat: {getattr(chat_model, 'provider', '?')}/{getattr(chat_model, 'name', '?')})"
        return worst, msg, "", sub

    return _run("Agent Configuration", _check)


def check_agent_context() -> TestResult:
    def _check():
        from agent import AgentContext
        from initialize import initialize_agent
        config = initialize_agent()
        ctx = AgentContext(config=config)
        ctx_id = ctx.id
        agent0 = getattr(ctx, "agent0", None)

        sub: list[tuple[Status, str]] = [
            ("pass", f"Context ID: {ctx_id}"),
            ("pass", f"Agent instance: {type(agent0).__name__ if agent0 else 'None'}"),
        ]

        # Verify log is available
        log = getattr(ctx, "log", None)
        if log is not None:
            sub.append(("pass", "Log subsystem: initialised"))
        else:
            sub.append(("warn", "Log subsystem: not available on context"))

        # Clean up the test context
        try:
            AgentContext._contexts.pop(ctx_id, None)  # type: ignore[attr-defined]
        except Exception:
            pass

        return "pass", f"AgentContext created (id: {ctx_id[:8]}…)", "", sub

    return _run("Agent Context Creation", _check)


def check_llm_ping() -> TestResult:
    def _check():
        import asyncio
        from initialize import initialize_agent

        config = initialize_agent()
        chat_model_cfg = getattr(config, "chat_model", None)
        if chat_model_cfg is None:
            return "skip", "No chat model configured — skipping LLM ping", "", []

        provider = getattr(chat_model_cfg, "provider", "unknown")
        name = getattr(chat_model_cfg, "name", "unknown")

        # Check API key before attempting the call
        expected_key = _PROVIDER_KEY_MAP.get(provider.lower())
        if expected_key and not os.getenv(expected_key):
            api_base = getattr(chat_model_cfg, "api_base", "")
            if not api_base:
                return (
                    "warn",
                    f"LLM ping skipped — {provider} API key not set",
                    f"Set {expected_key} to enable live connectivity check",
                    [],
                )

        from models import get_chat_model

        sub: list[tuple[Status, str]] = []
        sub.append(("pass", f"Target model: {provider}/{name}"))

        try:
            kwargs = chat_model_cfg.build_kwargs()
            model = get_chat_model(provider, name, chat_model_cfg, **kwargs)

            async def _ping():
                response, _ = await model.unified_call(
                    user_message="Reply with only the single word: pong",
                    max_tokens=10,
                )
                return response.strip()

            response_text = asyncio.get_event_loop().run_until_complete(_ping())
            sub.append(("pass", f"Response received: {response_text!r}"))
            return "pass", f"LLM ping successful ({provider}/{name})", "", sub

        except Exception as e:
            sub.append(("fail", f"Call failed: {e}"))
            return "fail", f"LLM ping failed: {type(e).__name__}", str(e)[:200], sub

    return _run("LLM Connectivity Ping", _check)


def check_filesystem() -> TestResult:
    def _check():
        from python.helpers import files

        paths_to_check = [
            ("work_dir", files.get_abs_path("work_dir")),
            ("memory", files.get_abs_path("memory")),
            ("knowledge", files.get_abs_path("knowledge")),
            ("logs", files.get_abs_path("logs")),
            ("usr/uploads", files.get_abs_path("usr/uploads")),
        ]

        sub: list[tuple[Status, str]] = []
        issues = 0

        for label, path in paths_to_check:
            exists = os.path.exists(path)
            if not exists:
                try:
                    os.makedirs(path, exist_ok=True)
                    exists = True
                    sub.append(("warn", f"{label}: created (did not exist) — {path}"))
                    issues += 1
                except Exception as e:
                    sub.append(("fail", f"{label}: cannot create — {e}"))
                    issues += 1
                    continue

            # Permissions
            r = os.access(path, os.R_OK)
            w = os.access(path, os.W_OK)
            x = os.access(path, os.X_OK)
            perms = f"{'r' if r else '-'}{'w' if w else '-'}{'x' if x else '-'}"

            # Disk free for this mount
            try:
                usage = shutil.disk_usage(path)
                free_gb = usage.free / (1024 ** 3)
                total_gb = usage.total / (1024 ** 3)
                disk_info = f"disk: {free_gb:.1f} GB free / {total_gb:.1f} GB total"
            except Exception:
                disk_info = "disk: unknown"

            if not w:
                sub.append(("fail", f"{label}: not writable (perms: {perms}) — {path}"))
                issues += 1
            else:
                sub.append(("pass", f"{label}: ok (perms: {perms}, {disk_info}) — {path}"))

        worst = _worst(*[s for s, _ in sub])
        if issues:
            return worst, f"{issues} path issue(s) found", "", sub
        return "pass", f"All {len(paths_to_check)} directories accessible and writable", "", sub

    return _run("Filesystem", _check)


def check_security_crypto() -> TestResult:
    def _check():
        sub: list[tuple[Status, str]] = []

        # CSRF token generation
        token = secrets.token_hex(32)
        if token and len(token) == 64:
            sub.append(("pass", f"secrets.token_hex(32): produces 64-char hex token"))
        else:
            sub.append(("fail", f"secrets.token_hex(32): unexpected output {token!r}"))

        # hash_data / verify_data round-trip
        try:
            from python.helpers.crypto import hash_data, verify_data
            test_data, test_pw = "sentinel-self-test", "test-password"
            hashed = hash_data(test_data, test_pw)
            valid = verify_data(test_data, hashed, test_pw)
            invalid = verify_data("wrong-data", hashed, test_pw)
            if valid and not invalid:
                sub.append(("pass", "hash_data/verify_data: round-trip correct (valid ✓, tampered ✗)"))
            else:
                sub.append(("fail", f"hash_data/verify_data: incorrect result (valid={valid}, tampered_accepted={invalid})"))
        except Exception as e:
            sub.append(("fail", f"crypto helpers: {e}"))

        # Session secret entropy
        session_key = secrets.token_hex(32)
        sub.append(("pass", f"Session key generation: {len(session_key)}-char hex (256-bit entropy)"))

        worst = _worst(*[s for s, _ in sub])
        return worst, "Cryptographic primitives checked", "", sub

    return _run("Security / Crypto", _check)


def check_settings() -> TestResult:
    def _check():
        from python.helpers.settings import Settings
        sub: list[tuple[Status, str]] = []

        s = Settings.get()
        if s is None:
            sub.append(("warn", "Settings.get() returned None"))
            return "warn", "Settings returned None", "", sub

        # Report a few key fields if accessible
        for attr in ("chat_model_provider", "chat_model_name", "agent_name", "agent_profile"):
            val = None
            # Settings may be a dict or a Pydantic model
            if isinstance(s, dict):
                val = s.get(attr)
            else:
                val = getattr(s, attr, None)
            if val is not None:
                sub.append(("pass", f"{attr}: {val}"))

        if not sub:
            sub.append(("pass", "Settings object loaded (fields not individually inspectable)"))

        return "pass", "Settings loaded successfully", "", sub

    return _run("Settings", _check)


def check_tls() -> TestResult:
    def _check():
        from python.helpers.tls import get_ca_bundle
        sub: list[tuple[Status, str]] = []

        ca = get_ca_bundle()
        if ca:
            exists = os.path.exists(ca)
            sub.append(
                ("pass" if exists else "warn",
                 f"Custom CA bundle: {ca} ({'exists' if exists else 'PATH NOT FOUND'})"),
            )
        else:
            sub.append(("pass", "CA bundle: using system defaults"))

        # Check TLS_VERIFY env var
        tls_verify = os.getenv("TLS_VERIFY", "").lower()
        if tls_verify in ("false", "0", "no"):
            sub.append(("warn", "TLS_VERIFY is disabled — certificate validation is OFF"))
        else:
            sub.append(("pass", "TLS_VERIFY: enabled (default)"))

        worst = _worst(*[s for s, _ in sub])
        return worst, "TLS configuration checked", "", sub

    return _run("TLS / SSL Config", _check)


def check_websocket_manager() -> TestResult:
    def _check():
        from python.helpers.websocket_manager import WebSocketManager
        sub: list[tuple[Status, str]] = []

        sub.append(("pass", f"WebSocketManager class: importable"))

        for method in ("get_instance", "emit", "disconnect_all"):
            if hasattr(WebSocketManager, method):
                sub.append(("pass", f"Method {method}: present"))
            else:
                sub.append(("warn", f"Method {method}: not found on WebSocketManager"))

        worst = _worst(*[s for s, _ in sub])
        return worst, "WebSocket manager checked", "", sub

    return _run("WebSocket Manager", _check)


def check_model_providers_config() -> TestResult:
    def _check():
        from python.helpers import files
        import yaml  # type: ignore

        config_path = files.get_abs_path("conf/model_providers.yaml")
        sub: list[tuple[Status, str]] = []

        if not os.path.exists(config_path):
            sub.append(("fail", f"File not found: {config_path}"))
            return "fail", "model_providers.yaml missing", config_path, sub

        sub.append(("pass", f"File exists: {config_path}"))

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            sub.append(("fail", f"Parse error: {e}"))
            return "fail", "model_providers.yaml failed to parse", str(e), sub

        if not data:
            sub.append(("warn", "File is empty"))
            return "warn", "model_providers.yaml is empty", "", sub

        if isinstance(data, list):
            sub.append(("pass", f"Provider entries: {len(data)}"))
            chat_providers = [p.get("name", "?") for p in data if isinstance(p, dict) and p.get("chat")]
            if chat_providers:
                sub.append(("pass", f"Chat providers: {', '.join(str(p) for p in chat_providers[:8])}"))
        elif isinstance(data, dict):
            sub.append(("pass", f"Config keys: {', '.join(list(data.keys())[:8])}"))

        return "pass", f"model_providers.yaml loaded ({len(data) if isinstance(data, (list, dict)) else '?'} entries)", "", sub

    return _run("Model Providers Config", _check)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_all() -> SelfTestReport:
    """Run all self-tests and return a structured report."""
    report = SelfTestReport()
    t0 = time.monotonic()

    checks = [
        check_env_vars,
        check_core_imports,
        check_heavy_imports,
        check_agent_config,
        check_agent_context,
        check_llm_ping,
        check_filesystem,
        check_security_crypto,
        check_settings,
        check_tls,
        check_websocket_manager,
        check_model_providers_config,
    ]

    for check in checks:
        result = check()
        report.add(result)

    report.total_ms = int((time.monotonic() - t0) * 1000)
    return report
