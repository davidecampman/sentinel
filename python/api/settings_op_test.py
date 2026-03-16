from python.helpers.api import ApiHandler, Request, Response
from python.helpers.onepassword import OnePasswordError, get_provider


class SettingsOpTest(ApiHandler):
    """POST /api/settings_op_test — verify 1Password CLI connectivity.

    Accepts an optional ``token`` field in the request body so the UI can test
    a newly entered token before the user saves settings.  Falls back to the
    token stored in the current settings when none is provided.
    """

    async def process(self, input: dict, request: Request) -> dict | Response:
        token: str = input.get("token", "").strip()

        if token:
            from python.helpers.onepassword import OnePasswordProvider
            provider = OnePasswordProvider(token=token)
        else:
            provider = get_provider()

        if not provider.is_available():
            binary_missing = not __import__("shutil").which("op")
            if binary_missing:
                return {
                    "ok": False,
                    "error": (
                        "The 'op' binary was not found on PATH. "
                        "Install the 1Password CLI: "
                        "https://developer.1password.com/docs/cli/get-started/"
                    ),
                }
            return {
                "ok": False,
                "error": "No 1Password service account token configured.",
            }

        try:
            provider.test_connection()
            return {"ok": True}
        except OnePasswordError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:
            return {"ok": False, "error": f"Unexpected error: {exc}"}

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]
