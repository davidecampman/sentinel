from python.helpers.api import ApiHandler, Request, Response

from python.helpers import runtime

class RFC(ApiHandler):

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_auth(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        # RFC is a host-to-container bridge used only in development mode.
        # In Docker mode (--dockerized) call_development_function() bypasses
        # RFC entirely, so this endpoint serves no purpose and must be disabled
        # to eliminate the arbitrary module execution surface.
        if not runtime.is_development():
            raise Exception("RFC endpoint is disabled in Docker mode.")
        result = await runtime.handle_rfc(input) # type: ignore
        return result
