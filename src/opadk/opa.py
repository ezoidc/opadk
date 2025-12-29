import asyncio
import json
import subprocess
from typing import Any, Literal

import aiohttp
from pydantic import BaseModel

from .models import OPADKResponse

Scope = Literal["agent", "tool"]


class OPABaseClient(BaseModel):
    async def is_allowed(self, scope: Scope, input: dict[str, Any]) -> OPADKResponse:
        raise NotImplementedError()


class OPARemoteClient(OPABaseClient):
    """
    OPA client that uses the eval API to query a remote OPA server.
    """

    server_url: str
    namespace: list[str] = ["adk"]
    headers: dict[str, str] = {}

    async def is_allowed(self, scope: Scope, input: dict[str, Any]) -> OPADKResponse:
        async with aiohttp.ClientSession(base_url=self.server_url) as session:
            url = f"/v1/data/{'/'.join(self.namespace)}/{scope}"
            async with session.post(
                url,
                json={"input": input},
                headers=self.headers,
            ) as response:
                json = await response.json()
                return OPADKResponse.model_validate(json.get("result"))
        raise Exception("OPA query failed")


class OPARunClient(OPABaseClient):
    """
    OPA client that runs the `opa eval` command locally for development/testing.
    """

    opa_path: str = "opa"
    bundle_path: str
    namespace: list[str] = ["adk"]

    async def is_allowed(self, scope: Scope, input: dict[str, Any]) -> OPADKResponse:
        query = ".".join(["data", *self.namespace, scope])
        process = await asyncio.create_subprocess_exec(
            self.opa_path,
            "eval",
            "--format",
            "json",
            "--bundle",
            self.bundle_path,
            "--stdin-input",
            query,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        stdout, _stderr = await process.communicate(json.dumps(input).encode())

        try:
            data = json.loads(stdout.decode())
        except Exception as e:
            raise Exception(f"Failed to decode OPA response: {e}")

        if data.get("errors"):
            raise Exception(f"OPA returned errors: {data['errors']}")

        result = data.get("result")
        if result and len(result) > 0:
            result = result[0]
            expressions = result.get("expressions")
            if expressions and len(expressions) > 0:
                value = expressions[0].get("value")
                return OPADKResponse(**value)
        raise Exception("OPA eval failed")
