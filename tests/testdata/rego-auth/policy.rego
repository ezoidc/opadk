package adk.testing

default tool.allow = false
default agent.allow = false

tool.allow if {
  input.state.tool_allowed
}

agent.allow if {
  input.state.agent_allowed
}

tool.deny.reasons contains "No tools allowed" if {
  not tool.allow
}

agent.deny.reasons contains "No agents allowed" if {
  not agent.allow
}
