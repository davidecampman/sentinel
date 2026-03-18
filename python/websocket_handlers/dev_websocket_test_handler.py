from __future__ import annotations

from typing import Any, Dict

from python.helpers import runtime
from python.helpers.websocket import WebSocketHandler, WebSocketResult


class DevWebsocketTestHandler(WebSocketHandler):
    """Handler for the developer WebSocket event console (diagnostics)."""

    @classmethod
    def get_event_types(cls) -> list[str]:
        return [
            "ws_event_console_subscribe",
            "ws_event_console_unsubscribe",
        ]

    async def process_event(
        self, event_type: str, data: Dict[str, Any], sid: str
    ) -> dict[str, Any] | WebSocketResult | None:
        if event_type == "ws_event_console_subscribe":
            if not runtime.is_development():
                return self.result_error(
                    code="NOT_AVAILABLE",
                    message="Event console is available only in development mode",
                )
            registered = self.manager.register_diagnostic_watcher(self.namespace, sid)
            if not registered:
                return self.result_error(
                    code="SUBSCRIBE_FAILED",
                    message="Unable to subscribe to diagnostics",
                )
            return self.result_ok(
                {"status": "subscribed", "timestamp": data.get("requestedAt")}
            )

        if event_type == "ws_event_console_unsubscribe":
            self.manager.unregister_diagnostic_watcher(self.namespace, sid)
            return self.result_ok({"status": "unsubscribed"})

        return self.result_error(
            code="UNKNOWN_EVENT",
            message="Unhandled event",
            details=event_type,
        )
