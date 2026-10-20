"""Regression: structuredContent must survive isError=True tool results (issue #619)."""

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.shared.memory import create_connected_server_and_client_session

from langchain_mcp_adapters.tools import load_mcp_tools

STRUCTURED_ERROR = {"code": "RATE_LIMITED", "retry_after": 30}
SCHEMA = {"type": "object", "properties": {}}


def _build_server():
    server = Server("repro")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="err_structured_only",
                description="error, structuredContent, no text",
                inputSchema=SCHEMA,
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "err_structured_only":
            return types.CallToolResult(
                content=[],
                structuredContent=STRUCTURED_ERROR,
                isError=True,
            )
        raise ValueError(name)

    return server


async def test_error_structured_content_reaches_artifact():
    async with create_connected_server_and_client_session(_build_server()) as session:
        await session.initialize()
        tools = {t.name: t for t in await load_mcp_tools(session)}
        msg = await tools["err_structured_only"].ainvoke(
            {"args": {}, "id": "1", "type": "tool_call"}
        )
        assert msg.status == "error"
        assert msg.artifact is not None
        assert msg.artifact["structured_content"] == STRUCTURED_ERROR


if __name__ == "__main__":
    anyio.run(test_error_structured_content_reaches_artifact)
