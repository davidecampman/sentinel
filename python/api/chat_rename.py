from python.helpers.api import ApiHandler, Input, Output, Request, Response
from agent import AgentContext
from python.helpers import persist_chat


class RenameChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")
        new_name = input.get("name", "").strip()

        if not ctxid:
            return Response(status_code=400, content={"error": "Missing context id."})

        if not new_name:
            return Response(status_code=400, content={"error": "Name cannot be empty."})

        context = AgentContext.use(ctxid)
        if not context:
            return Response(status_code=404, content={"error": "Context not found."})

        context.name = new_name
        context.name_locked = True
        persist_chat.save_tmp_chat(context)

        from python.helpers.state_monitor_integration import mark_dirty_all
        mark_dirty_all(reason="api.chat_rename.RenameChat")

        return {
            "ok": True,
            "context": ctxid,
            "name": new_name,
        }
