# server1.py
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult

mcp = FastMCP("SimpleMCP")


@mcp.tool()
async def echo(message: str) -> CallToolResult:
    return CallToolResult(content=f"[Echo] {message}")


@mcp.tool()
async def strlen(text: str) -> CallToolResult:
    return CallToolResult(content=str(len(text)))


if __name__ == "__main__":
    mcp.run("stdio")
