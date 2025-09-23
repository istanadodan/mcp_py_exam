from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

app = FastAPI(title="MCP Add Server", description="MCP 서버: a + b 계산")


class AddRequest(BaseModel):
    a: int
    b: int


class AddResponse(BaseModel):
    result: int


@app.post("/", response_model=AddResponse)
async def add_numbers(request: AddRequest) -> AddResponse:
    """
    MCP 서버: 두 정수 a, b를 받아 합을 반환
    """
    try:
        result = request.a + request.b
        return AddResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# MCP 서버 메타데이터 엔드포인트 (선택사항, MCP 스펙 준수)
@app.get("/.well-known/mcp.json")
async def mcp_manifest() -> Dict[str, Any]:
    return {
        "name": "addition-server",
        "version": "1.0.0",
        "description": "Adds two integers",
        "tools": [
            {
                "name": "add",
                "description": "Adds two integers a and b",
                "inputSchema": {
                    "type": "object",
                    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"],
                },
                "outputSchema": {
                    "type": "object",
                    "properties": {"result": {"type": "integer"}},
                },
            }
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
