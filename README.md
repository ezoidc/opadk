# `opadk`

Plugin for [Agent Development Kit (ADK)](http://github.com/google/adk-python) that integrates with [Open Policy Agent (OPA)](https://github.com/open-policy-agent/opa) for policy enforcement on agent and tool usage.

## How to use

### Remote OPA server

```python
from google.adk.runners import Runner
from opadk import OPADKPlugin, OPARemoteClient

runner = Runner(
    # ...
    plugins=[
        OPADKPlugin(opa_client=OPARemoteClient(server_url="http://localhost:8181"))
    ],
)
```

#### Custom Headers

You can provide custom headers to the remote OPA client, which is useful for authentication or passing additional metadata:

```python
from google.adk.runners import Runner
from opadk import OPADKPlugin, OPARemoteClient

runner = Runner(
    # ...
    plugins=[
        OPADKPlugin(
            opa_client=OPARemoteClient(
                server_url="http://localhost:8181",
                headers={
                    "Authorization": "Bearer your-token-here",
                    "X-Custom-Header": "custom-value"
                }
            )
        )
    ],
)
```

### Local client

If `opa` is installed locally, the `OPARunClient` can be used to evaluate policies without needing a separate OPA server. The client must be provided with the path to a folder with Rego policies.

```python
from google.adk.runners import Runner
from opadk import OPADKPlugin, OPARunClient

runner = Runner(
    # ...
    plugins=[
        OPADKPlugin(opa_client=OPARunClient(bundle_path="./rego")),
    ],
)

```

## Rego Policies

The plugin will make a query that expects `data.adk.tool.allow` and `data.adk.agent.allow` rules to be defined to determine if an agent or tool can be invoked. To help the model recover from policy denials, reasoning messages can be added to the sets `data.adk.tool.deny.reasons` and `data.adk.agent.deny.reasons`.

```rego
package adk

# allow all agents by default
default agent.allow = true

# deny all tools by default
default tool.allow = false

tool.deny.reasons contains "No tools allowed"
```

### Input Structure

The Rego policy receives the following `input` structure from ADK:

- `state`: The current [ADK state](https://google.github.io/adk-docs/sessions/state).
- `agent`:
  - `name`: The name of the agent being invoked.
- `tool`:
  - `name`: The name of the tool being invoked.
  - `args`: The arguments passed to the tool.
- `events`: The list of events in the current [session](https://google.github.io/adk-docs/sessions/session/#the-session-object).

## Example Policies

### Access Control

```rego
_agents_by_user = {
  "user1": {"root_agent", "it_agent"},
  "user2": {"root_agent", "analytics_agent"},
}

_user_can_use_agent if {
  input.agent.name in _agents_by_user[input.state.user_id]
}

agent.allow if _user_can_use_agent

agent.reasons contains sprintf(
  "User does not have access to agent `%v`", [input.agent.name]
) if {
  not _user_can_use_agent
}
```

### User authorization

```rego
tool.allow if {
  input.tool.name in {"update_profile"}
  input.tool.args.user_id == input.state.user_id
}
```

### Enforce parameter values

```rego
_allowed_containers := {
  "python": "python:3.14-alpine@sha256:8373231e1e906ddfb457748bfc032c4c06ada8c759b7b62d9c73ec2a3c56e710",
}

_container_run_command_allowed if {
  input.tool.name in {"container_run"}
  input.tool.args.image == _allowed_containers[_]
}

tool.allow if {
  _container_run_command_allowed
}

tool.deny.reasons contains sprintf(
  "Parameter `image` must be one of: %v", [allowed_containers]
) if {
  not _container_run_command_allowed
  allowed_containers = [image | _allowed_containers[_] = image]
}
```
