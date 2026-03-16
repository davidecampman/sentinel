"""
Sentinel self-test module.
Runs a suite of lightweight diagnostic checks and returns structured results.
"""
from __future__ import annotations

import importlib
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

Status = Literal["pass", "fail", "warn", "skip"]


@dataclass
class TestResult:
    name: str
    status: Status
    message: str
    detail: str = ""
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
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️"}
        lines = [
            "## 🔍 Sentinel Self-Test Report",
            "",
            f"**Overall:** {icon[self.overall]} {self.overall.upper()}  "
            f"| Passed: {self.passed} | Failed: {self.failed} "
            f"| Warnings: {self.warned} | Skipped: {self.skipped}",
            f"**Duration:** {self.total_ms} ms",
            "",
            "| Status | Test | Message |",
            "|--------|------|---------|",
        ]
        for r in self.results:
            detail = f" — {r.detail}" if r.detail else ""
            lines.append(f"| {icon[r.status]} | **{r.name}** | {r.message}{detail} |")

        failed_results = [r for r in self.results if r.status == "fail"]
        if failed_results:
            lines += ["", "### ❌ Failed Tests", ""]
            for r in failed_results:
                lines.append(f"**{r.name}**: {r.message}")
                if r.detail:
                    lines.append(f"> {r.detail}")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(name: str, fn: Callable[[], tuple[Status, str, str]]) -> TestResult:
    t0 = time.monotonic()
    try:
        status, message, detail = fn()
    except Exception as exc:
        status, message, detail = "fail", f"Unexpected exception: {exc}", ""
    duration_ms = int((time.monotonic() - t0) * 1000)
    return TestResult(name=name, status=status, message=message, detail=detail, duration_ms=duration_ms)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_env_vars() -> TestResult:
    def _check():
        providers = [
            ("ANTHROPIC_API_KEY", "Anthropic"),
            ("OPENAI_API_KEY", "OpenAI"),
            ("OPENROUTER_API_KEY", "OpenRouter"),
        ]
        present = [label for key, label in providers if os.getenv(key)]
        missing = [f"{key} ({label})" for key, label in providers if not os.getenv(key)]

        if not present:
            return "fail", "No LLM API key configured", f"Missing: {', '.join(missing)}"

        detail_parts = []
        if missing:
            detail_parts.append(f"Optional missing: {', '.join(m.split(' ')[1].strip('()') for m in missing)}")
        if not os.getenv("A0_AUTH_LOGIN"):
            detail_parts.append("A0_AUTH_LOGIN not set (no-auth mode)")

        status: Status = "warn" if detail_parts else "pass"
        return status, f"{', '.join(present)} configured", "; ".join(detail_parts)

    return _run("Environment Variables", _check)


def check_core_imports() -> TestResult:
    def _check():
        modules = [
            "langchain_core",
            "flask",
            "socketio",
            "pydantic",
            "dotenv",
            "requests",
        ]
        failed = []
        for mod in modules:
            try:
                importlib.import_module(mod)
            except ImportError as e:
                failed.append(f"{mod} ({e})")

        if failed:
            return "fail", f"{len(failed)} import(s) failed", ", ".join(failed)
        return "pass", f"All {len(modules)} core modules importable", ""

    return _run("Core Imports", _check)


def check_heavy_imports() -> TestResult:
    def _check():
        modules = ["chromadb", "faiss", "sentence_transformers", "playwright"]
        results = {}
        for mod in modules:
            try:
                importlib.import_module(mod)
                results[mod] = True
            except ImportError:
                results[mod] = False

        missing = [m for m, ok in results.items() if not ok]
        if len(missing) == len(modules):
            return "warn", "All optional heavy deps missing", ", ".join(missing)
        if missing:
            return "warn", f"{len(missing)} optional dep(s) unavailable", ", ".join(missing)
        return "pass", f"All {len(modules)} optional deps available", ""

    return _run("Optional Dependencies", _check)


def check_agent_config() -> TestResult:
    def _check():
        from initialize import initialize_agent
        config = initialize_agent()
        if config is None:
            return "fail", "initialize_agent() returned None", ""
        chat_model = getattr(config, "chat_model", None)
        if chat_model is None:
            return "fail", "AgentConfig has no chat_model", ""
        model_name = getattr(chat_model, "name", "unknown")
        return "pass", f"Agent config loaded (model: {model_name})", ""

    return _run("Agent Configuration", _check)


def check_agent_context() -> TestResult:
    def _check():
        from agent import AgentContext
        from initialize import initialize_agent
        config = initialize_agent()
        ctx = AgentContext(config=config)
        ctx_id = ctx.id
        # Clean up the test context
        try:
            AgentContext._contexts.pop(ctx_id, None)  # type: ignore[attr-defined]
        except Exception:
            pass
        return "pass", f"AgentContext created (id: {ctx_id[:8]}…)", ""

    return _run("Agent Context Creation", _check)


def check_filesystem() -> TestResult:
    def _check():
        from python.helpers import files
        paths_to_check = [
            ("work_dir", files.get_abs_path("work_dir")),
            ("memory", files.get_abs_path("memory")),
            ("knowledge", files.get_abs_path("knowledge")),
            ("logs", files.get_abs_path("logs")),
        ]
        issues = []
        for label, path in paths_to_check:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    issues.append(f"{label}: cannot create ({e})")
            elif not os.access(path, os.W_OK):
                issues.append(f"{label}: not writable")

        if issues:
            return "warn", f"{len(issues)} path issue(s)", "; ".join(issues)
        return "pass", f"All {len(paths_to_check)} required directories accessible", ""

    return _run("Filesystem", _check)


def check_security_crypto() -> TestResult:
    def _check():
        # Verify Python's secrets module works (used for CSRF tokens, session keys)
        token = secrets.token_hex(32)
        if not token or len(token) != 64:
            return "fail", f"secrets.token_hex produced unexpected output: {token!r}", ""
        # Verify hash_data from crypto helper
        from python.helpers.crypto import hash_data, verify_data
        test_data = "sentinel-self-test"
        test_password = "test-password"
        hashed = hash_data(test_data, test_password)
        if not verify_data(test_data, hashed, test_password):
            return "fail", "hash_data/verify_data round-trip failed", ""
        return "pass", "Cryptographic primitives working", ""

    return _run("Security / Crypto", _check)


def check_settings() -> TestResult:
    def _check():
        from python.helpers.settings import Settings
        s = Settings.get()
        if s is None:
            return "warn", "Settings.get() returned None", ""
        return "pass", "Settings loaded successfully", ""

    return _run("Settings", _check)


def check_tls() -> TestResult:
    def _check():
        from python.helpers.tls import get_ca_bundle
        ca = get_ca_bundle()
        detail = f"CA bundle: {ca}" if ca else "Using default system CAs"
        return "pass", "TLS configuration loaded", detail

    return _run("TLS / SSL Config", _check)


def check_websocket_manager() -> TestResult:
    def _check():
        from python.helpers.websocket_manager import WebSocketManager
        # Verify class is importable and has expected interface
        if not (hasattr(WebSocketManager, "get_instance") or hasattr(WebSocketManager, "__init__")):
            return "warn", "WebSocketManager missing expected interface", ""
        return "pass", "WebSocketManager importable", ""

    return _run("WebSocket Manager", _check)


def check_model_providers_config() -> TestResult:
    def _check():
        from python.helpers import files
        config_path = files.get_abs_path("conf/model_providers.yaml")
        if not os.path.exists(config_path):
            return "fail", "model_providers.yaml not found", config_path
        try:
            import yaml  # type: ignore
        except ImportError:
            return "warn", "PyYAML not available for config validation", ""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
            if not data:
                return "warn", "model_providers.yaml is empty", ""
            count = len(data) if isinstance(data, (list, dict)) else 0
            return "pass", f"model_providers.yaml loaded ({count} entries)", ""
        except Exception as e:
            return "fail", f"Failed to parse model_providers.yaml: {e}", ""

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
