from agent import AgentContext, UserMessage
from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers import guids, message_queue as mq
from python.helpers.state_monitor_integration import mark_dirty_all


class SelfTest(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        from python.helpers.self_test import run_all

        # Run all diagnostic checks
        report = await run_all()

        # Create a fresh context for the results chat
        ctxid = guids.generate_id()
        context = self.use_context(ctxid)

        # Rename the chat so it's easy to find in the sidebar
        context.name = "Self Test"  # type: ignore[attr-defined]

        # Build the message that will appear as the user turn
        markdown = report.to_markdown()
        prompt = (
            f"{markdown}\n\n"
            "Please review these self-test results. "
            "Summarise what is working, call out any failures or warnings, "
            "and suggest corrective actions where needed."
        )

        # Log as a user message (appears in chat UI) and kick off the agent
        mq.log_user_message(context, prompt, [])
        context.communicate(UserMessage(prompt, []))

        mark_dirty_all(reason="api.self_test.SelfTest")

        return {
            "ok": True,
            "ctxid": ctxid,
            "overall": report.overall,
            "passed": report.passed,
            "failed": report.failed,
            "warned": report.warned,
        }
