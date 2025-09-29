from fastmcp import FastMCP

app = FastMCP(name="math_mcp")


@app.tool(
    name="add",
    description="입력받은 두 숫자의 합을 반환합니다.",
    output_schema={
        "type": "object",
        "properties": {"result": {"type": "integer"}},
        "required": ["result"],
    },
)
def add(x: int, y: int):
    """두 숫자의 합을 반환합니다."""
    return {"result": x + y}


@app.tool(
    name="list_files",
    description="파일목록을 출력한다",
    output_schema={
        "type": "object",
        "properties": {
            "result": {
                "type": "array",
                "items": {"type": "string"},
                "description": "파일 목록",
            }
        },
        "required": ["result"],
    },
)
def list_files(directory: str = "."):
    """지정된 디렉토리의 파일 목록을 반환합니다."""
    import os

    try:
        files = os.listdir(directory)
        return {"result": files}
    except Exception as e:
        return {"result": [f"Error: {str(e)}"]}


if __name__ == "__main__":
    app.run("stdio")
