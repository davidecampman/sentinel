from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers import subagents

# Keys from Settings that are allowed as per-profile model overrides
_ALLOWED_OVERRIDE_KEYS = {
    "chat_model_provider",
    "chat_model_name",
    "chat_model_api_base",
    "chat_model_ctx_length",
    "chat_model_ctx_history",
    "chat_model_vision",
    "util_model_provider",
    "util_model_name",
    "browser_model_provider",
    "browser_model_name",
}


class AgentProfileModelSet(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        profile = input.get("profile", "")
        overrides = input.get("overrides", {})

        if not profile:
            return {"ok": False, "error": "Profile name required"}

        if not isinstance(overrides, dict):
            return {"ok": False, "error": "Overrides must be a JSON object"}

        # Only keep allowed keys with non-empty values
        filtered = {
            k: v for k, v in overrides.items()
            if k in _ALLOWED_OVERRIDE_KEYS and v not in (None, "")
        }

        subagents.save_agent_model_overrides(profile, filtered)
        return {"ok": True, "overrides": filtered}
