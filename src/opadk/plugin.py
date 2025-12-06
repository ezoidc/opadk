from typing import Any, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from .models import OPADKRequestInput, OPADKResponse
from .opa import OPABaseClient


class OPADKPlugin(BasePlugin):
    """
    Plugin that integrates OPA policy checks into agent and tool invocations.
    """

    opa_client: OPABaseClient

    def __init__(
        self,
        opa_client: OPABaseClient,
    ) -> None:
        super().__init__(name="opadk_plugin")
        self.opa_client = opa_client

    async def before_agent_callback(
        self, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        outcome = await self.opa_client.is_allowed(
            scope="agent",
            input=OPADKRequestInput.from_callback_context(
                callback_context=callback_context,
            ).model_dump(),
        )

        if not outcome.allow:
            return self.agent_access_denied_response(outcome)

    async def before_tool_callback(
        self,
        *,
        tool_context: ToolContext,
        tool: BaseTool,
        tool_args: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        outcome = await self.opa_client.is_allowed(
            scope="tool",
            input=OPADKRequestInput.from_tool_callback(
                tool_context=tool_context,
                tool=tool,
                tool_args=tool_args,
            ).model_dump(),
        )

        if not outcome.allow:
            return self.tool_access_denied_response(outcome)

    def tool_access_denied_response(self, outcome: OPADKResponse) -> dict[str, Any]:
        """
        Response when tool access is denied by policy.
        """
        return {
            "error": "Tool invocation not allowed by policy.",
            "reasons": outcome.deny.reasons,
        }

    def agent_access_denied_response(self, outcome: OPADKResponse) -> types.Content:
        """
        Response when agent access is denied by policy.
        """
        parts = ["Agent invocation not allowed by policy."]

        if outcome.deny.reasons:
            parts.append("Reasons:")
            for reason in outcome.deny.reasons:
                parts.append(f"- {reason}")

        return types.Content(
            parts=[
                types.Part.from_text(
                    text="\n".join(parts),
                ),
            ]
        )
