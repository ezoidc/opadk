package system.authz

import rego.v1

# By default, deny requests
default allow := false

# Allow requests with valid bearer token
allow if {
    input.identity == "test-token"
}
