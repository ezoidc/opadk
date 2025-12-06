package adk

# allow all agents by default
default agent.allow := true

# deny all tools by default
default tool.allow := false


tool.allow if {
  not deny_tool_call
}

deny_tool_call if unauthorized_commands
deny_tool_call if unauthorized_mkdir

unauthorized_commands if {
  input.tool.name == "execute_command"
  not input.tool.args.command in {
    "ls", "mkdir"
  }
}

tool.deny.reasons contains "Unauthorized command" if {
  unauthorized_commands
}


unauthorized_mkdir if {
  input.tool.name == "execute_command"
  input.tool.args.command == "mkdir"
  input.tool.args.args != ["-p", "/tmp/safe_directory"]
}

tool.deny.reasons contains "Unauthorized mkdir arguments" if {
  unauthorized_mkdir
}
