from fastmcp import FastMCP

app = FastMCP("예제 서버")


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


if __name__ == "__main__":
    app.run("stdio")
