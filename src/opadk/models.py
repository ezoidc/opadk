from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel


class OPADKDenyResponse(BaseModel):
    reasons: list[str] = []


class OPADKResponse(BaseModel):
    allow: bool = False
    deny: OPADKDenyResponse = OPADKDenyResponse()


class OPADKRequestAgent(BaseModel):
    name: str


class OPADKRequestTool(BaseModel):
    name: str
    args: dict[str, Any]


class OPADKRequestInput(BaseModel):
    """
    Input schema for OPA policy evaluation.
    """

    state: dict[str, Any]
    agent: OPADKRequestAgent
    tool: Optional[OPADKRequestTool] = None
    events: Optional[list[dict[str, Any]]] = None

    @classmethod
    def from_callback_context(
        cls,
        callback_context: CallbackContext,
    ) -> "OPADKRequestInput":
        return cls(
            state=callback_context.state.to_dict(),
            agent=OPADKRequestAgent(name=callback_context.agent_name),
            events=_serialize_events(callback_context.session.events),
        )

    @classmethod
    def from_tool_callback(
        cls,
        tool_context: ToolContext,
        tool: BaseTool,
        tool_args: dict[str, Any],
    ) -> "OPADKRequestInput":
        return cls(
            state=tool_context.state.to_dict(),
            agent=OPADKRequestAgent(name=tool_context.agent_name),
            tool=OPADKRequestTool(
                name=tool.name,
                args=tool_args,
            ),
            events=_serialize_events(tool_context.session.events),
        )


def _serialize_events(events: list[Event]) -> list[dict[str, Any]]:
    return [
        e.model_dump(
            mode="json", exclude_none=True, exclude_defaults=True, exclude_unset=True
        )
        for e in events
    ]
