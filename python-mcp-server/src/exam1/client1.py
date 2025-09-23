import asyncio
import sys

# 가능성 있는 import 경로들
try:
    from mcp.client.stdio import stdio_client
except ImportError:
    raise ImportError(
        "stdio_client를 mcp.client.stdio에서 찾을 수 없습니다. 설치된 mcp 버전과 모듈 구조를 확인해주세요."
    )

try:
    from mcp import ClientSession, StdioServerParameters
except ImportError:
    raise ImportError(
        "ClientSession 또는 StdioServerParameters를 mcp에서 찾을 수 없습니다."
    )


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server1.py"],
    )

    async with stdio_client(server_params, errlog=sys.stderr) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            # 초기화 (필요한 경우)
            await session.initialize()

            tools_list = await session.list_tools()
            print("툴 목록:", tools_list)

            # 예: echo 툴 실행
            resp = await session.call_tool("echo", {"message": "테스트 MCP"})
            print("echo 응답:", resp)


if __name__ == "__main__":
    asyncio.run(main())
