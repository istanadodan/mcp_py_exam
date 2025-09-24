from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from fastapi import FastAPI

# mcp = FastMCP(
#     "My MCP Server",
#     instructions="This server provides data analysis tools. Call get_average() to analyze numerial data.",
#     # tools=["greet", "get_average"],
# )

app = FastAPI()

mcp = FastMCP.from_fastapi(
    app,
    "My MCP Server",
    instructions="This server provides data analysis tools. Call get_average() to analyze numerial data.",
)


@app.get("/get_average")
async def get_average(numbers: list[float]) -> float:
    return sum(numbers) / len(numbers) if numbers else 0.0


@app.get("/test")
async def get_ok() -> float:
    return PlainTextResponse("OK", status_code=200)


@mcp.tool
def get_average(numbers: list[float]) -> float:
    return sum(numbers) / len(numbers) if numbers else 0.0


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "data": {"type": "string"},
        },
    }
)
def greet(name: str) -> dict:
    """Return a greeting message"""
    return {"data": f"Hello, {name}!"}


@mcp.custom_route("/health", methods=["GET"])
def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK", status_code=200)


@mcp.resource("data://config")
def get_config() -> dict:
    """애플리케이션 설정값을 리소스로 제공"""
    return {
        "db_host": "localhost",
        "db_port": 5432,
        "feature_flag": True,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
