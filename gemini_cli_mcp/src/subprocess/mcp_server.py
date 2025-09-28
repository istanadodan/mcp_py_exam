#!/usr/bin/env python3
"""
간단한 MCP 서버 예제 - 계산기 도구
"""

import asyncio
import json
import sys
from typing import Dict, Any, List
import platform

# Fix for Windows asyncio issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class MCPCalculatorServer:
    def __init__(self):
        self.tools = {
            "calculator": {
                "name": "calculator",
                "description": "기본적인 수학 계산을 수행합니다",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "계산할 수학 표현식 (예: '2 + 3 * 4')",
                        }
                    },
                    "required": ["expression"],
                },
            }
        }

    def calculate(self, expression: str) -> float:
        """안전한 수학 계산"""
        try:
            # 보안을 위해 허용된 문자만 사용
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("허용되지 않은 문자가 포함되어 있습니다")

            result = eval(expression)
            return result
        except Exception as e:
            raise ValueError(f"계산 오류: {str(e)}")

    async def handle_list_tools(self) -> Dict[str, Any]:
        """사용 가능한 도구 목록 반환"""
        return {"jsonrpc": "2.0", "result": {"tools": list(self.tools.values())}}

    async def handle_call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """도구 호출 처리"""
        if tool_name == "calculator":
            try:
                expression = arguments.get("expression", "")
                result = self.calculate(expression)
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"계산 결과: {expression} = {result}",
                            }
                        ]
                    },
                }
            except Exception as e:
                return {"jsonrpc": "2.0", "error": {"code": -1, "message": str(e)}}
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"알 수 없는 도구: {tool_name}"},
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """요청 처리 메인 함수"""
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return await self.handle_list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return await self.handle_call_tool(tool_name, arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"알 수 없는 메소드: {method}"},
            }

    async def run(self):
        """MCP 서버 실행"""
        # 초기화 메시지
        init_response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "calculator-server", "version": "1.0.0"},
            },
        }

        print(json.dumps(init_response))
        sys.stdout.flush()

        # 요청 처리 루프
        async for line in self.read_lines():
            if line.strip():
                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    print(json.dumps(response))
                    sys.stdout.flush()
                except json.JSONDecodeError:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "JSON 파싱 오류"},
                    }
                    print(json.dumps(error_response))
                    sys.stdout.flush()

    async def read_lines(self):
        from concurrent.futures import ThreadPoolExecutor

        """표준 입력에서 줄 단위로 읽기"""
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)

        # reader = asyncio.StreamReader()
        # protocol = asyncio.StreamReaderProtocol(reader)
        # await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line = await loop.run_in_executor(executor, sys.stdin.readline)
            # line = await reader.readline()
            if not line:
                break
            yield line


if __name__ == "__main__":
    server = MCPCalculatorServer()
    # Run the server
    if platform.system() == "Windows":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.run())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        asyncio.run(server.run())
