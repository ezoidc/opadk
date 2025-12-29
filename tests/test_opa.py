import asyncio
import unittest

from opadk import OPARemoteClient, OPARunClient
from opadk.opa import Scope


class TestOPA(unittest.IsolatedAsyncioTestCase):
    def _cases(self) -> list[tuple[Scope, dict, bool, list[str]]]:
        return [
            ("tool", {"tool_allowed": True}, True, []),
            ("tool", {"tool_allowed": False}, False, ["No tools allowed"]),
            ("agent", {"agent_allowed": True}, True, []),
            ("agent", {"agent_allowed": False}, False, ["No agents allowed"]),
        ]

    async def test_opa_run_client(self):
        client = OPARunClient(
            bundle_path="tests/testdata/rego", namespace=["adk", "testing"]
        )

        for scope, state, expected, reasons in self._cases():
            with self.subTest(scope=scope, state=state, expected=expected):
                outcome = await client.is_allowed(
                    scope=scope,
                    input={"state": state},
                )
                self.assertEqual(outcome.allow, expected)
                self.assertEqual(outcome.deny.reasons, reasons)

    async def test_opa_remote_client(self):
        proc = await asyncio.create_subprocess_exec(
            "opa",
            "run",
            "--server",
            "--addr",
            "127.0.0.1:8181",
            "--bundle",
            "tests/testdata/rego",
            stderr=asyncio.subprocess.PIPE,
        )
        if proc.returncode is not None:
            raise RuntimeError("Failed to start OPA server for testing.")

        assert proc.stderr is not None
        await proc.stderr.readline()
        await asyncio.sleep(0.1)  # Give OPA server time to start

        client = OPARemoteClient(
            server_url="http://127.0.0.1:8181",
            namespace=["adk", "testing"],
        )

        for scope, state, expected, reasons in self._cases():
            with self.subTest(scope=scope, state=state, expected=expected):
                outcome = await client.is_allowed(
                    scope=scope,
                    input={"state": state},
                )
                self.assertEqual(outcome.allow, expected)
                self.assertEqual(outcome.deny.reasons, reasons)

        proc.terminate()
        await proc.wait()

    async def test_opa_remote_client_with_headers(self):
        # Start OPA server with authentication enabled
        proc = await asyncio.create_subprocess_exec(
            "opa",
            "run",
            "--server",
            "--addr",
            "127.0.0.1:8182",
            "--bundle",
            "tests/testdata/rego-auth",
            "--authentication=token",
            "--authorization=basic",
            stderr=asyncio.subprocess.PIPE,
        )
        if proc.returncode is not None:
            raise RuntimeError("Failed to start OPA server for testing.")

        assert proc.stderr is not None
        await proc.stderr.readline()
        await asyncio.sleep(0.1)  # Give OPA server time to start

        # Test without valid authorization header - should fail
        client_no_auth = OPARemoteClient(
            server_url="http://127.0.0.1:8182",
            namespace=["adk", "testing"],
        )

        try:
            await client_no_auth.is_allowed(
                scope="tool",
                input={"state": {"tool_allowed": True}},
            )
            self.fail("Expected request to fail without authorization")
        except Exception:
            # Expected - request should fail without proper auth
            pass

        # Test with valid bearer token authorization header - should succeed
        client_with_auth = OPARemoteClient(
            server_url="http://127.0.0.1:8182",
            namespace=["adk", "testing"],
            headers={"Authorization": "Bearer test-token"},
        )

        outcome = await client_with_auth.is_allowed(
            scope="tool",
            input={"state": {"tool_allowed": True}},
        )
        self.assertEqual(outcome.allow, True)
        self.assertEqual(outcome.deny.reasons, [])

        proc.terminate()
        await proc.wait()
