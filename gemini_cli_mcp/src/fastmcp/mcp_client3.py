"""
Gemini MCP 클라이언트 - MCP 서버와 통신하는 클라이언트
"""

import asyncio
import json
import subprocess
import sys
import os
import platform
import threading
import queue
from typing import Dict, Any, List, Optional, cast
from contextlib import AsyncExitStack  # for managing mulple async tasks
from mcp import ClientSession, StdioServerParameters, types as mcptypes
from mcp.client.stdio import stdio_client

# import google.generativeai as genai 2025년 8월 31일 이후 종료

from google import genai
from google.genai import types as genai_types
from google.genai.types import Tool, FunctionDeclaration, GenerateContentConfig
from dataclasses import dataclass


@dataclass
class MCPServer:
    """MCP 서버 정보"""

    name: str
    process: subprocess.Popen
    tools: List[Dict[str, Any]]
    input_queue: queue.Queue
    output_queue: queue.Queue
    error_queue: queue.Queue


class GeminiMCPClient:
    def __init__(self, api_key: str, project_id: str):
        """
        Gemini MCP 클라이언트 초기화

        Args:
            api_key: Gemini API 키
            model_name: 사용할 Gemini 모델명
        """
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        self.genai_client = genai.Client(api_key=api_key)

    async def connect_to_server(self, server_script_path: str) -> bool:
        """
        MCP 서버에 연결

        Args:
            server_path: MCP 서버 스크립트 경로

        Returns:
            연결 성공 여부
        """
        command = "python" if server_script_path.endswith(".py") else "node"

        server_params = StdioServerParameters(
            command=command, args=[server_script_path]
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(*stdio_transport)
        )
        # Send an initialization reqeust to the MCP server.
        await self.session.initialize()

        return True

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[mcptypes.CallToolResult]:
        """
        MCP 서버의 도구 호출

        Args:
            tool_name: 도구 이름
            arguments: 도구 인수

        Returns:
            도구 실행 결과
        """
        if not self.session:
            return

        return await self.session.call_tool(name=tool_name, arguments=arguments)

    async def get_available_tools(self) -> list[mcptypes.Tool]:
        """사용 가능한 모든 도구 목록 반환"""
        if self.session:
            response = await self.session.list_tools()
            tools = response.tools
            print(f"✅ 서버 연결 성공, tools: {[tool.name for tool in tools]}")
            return tools
        return []

    async def cleanup(self):
        """모든 서버 프로세스 정리"""
        # self.stdio.close()
        # self.write.close()
        if self.exit_stack:
            await self.exit_stack.aclose()

    async def chat(self, message: str) -> str:
        """
        Gemini와 채팅하며 필요시 MCP 도구 사용

        Args:
            message: 사용자 메시지

        Returns:
            Gemini 응답
        """
        model = "gemini-2.5-flash-lite"

        # 사용 가능한 도구 정보를 프롬프트에 포함
        tools_info: List[Any] = await self.get_available_tools()
        tools_description = "\n".join(
            [
                f"- {tool.name} (스키마: {tool.inputSchema}): {tool.description}"
                for tool in tools_info
            ]
        )

        system_prompt = f"""
당신은 MCP(Model Context Protocol) 도구를 사용할 수 있는 AI 어시스턴트입니다.

사용 가능한 도구들:
{tools_description}

사용자의 요청을 처리하기 위해 적절한 도구가 필요하다면, 다음 형식으로 도구 호출을 요청하세요:

TOOL_CALL: {{
  "tool": "도구명",
  "arguments": {{인수 딕셔너리}}
}}

도구 호출 결과를 받은 후 최종 답변을 제공하세요.
"""
        try:
            full_prompt = f"{system_prompt}\n\n사용자: {message}"
            response: genai_types.GenerateContentResponse = (
                self.genai_client.chats.create(model=model).send_message(
                    message=full_prompt
                )
            )

            response_text = response.text
            if response_text is None:
                return "응답이 없습니다."

            # 도구 호출이 필요한지 확인
            if "TOOL_CALL:" in response_text:
                # 도구 호출 부분 추출
                tool_call_start = response_text.find("TOOL_CALL:")
                tool_call_end = response_text.rfind("}") + 1
                tool_call_json = response_text[
                    tool_call_start + 10 : tool_call_end
                ].strip()

                try:
                    tool_call = json.loads(tool_call_json.replace(r"\n", ""))
                    tool_name = tool_call["tool"]
                    arguments = tool_call["arguments"]

                    print(f"🔧 도구 호출: {tool_name}/{arguments}")

                    # 도구 실행
                    tool_result: Optional[mcptypes.CallToolResult] = (
                        await self.call_tool(tool_name, arguments)
                    )
                    if tool_result is None:
                        return "도구 호출에 실패했습니다."

                    tool_answer = cast(
                        mcptypes.TextContent, tool_result.content[0]
                    ).text

                    # 도구 결과를 포함한 최종 응답 생성
                    final_prompt = f"""
{system_prompt}

사용자: {message}

도구 호출 결과:
도구: {tool_name}
결과: {tool_answer}
 

위 결과를 바탕으로 사용자에게 최종 답변을 제공하세요.
"""

                    # self.genai_client.chats.create(model="gemini-1.5-turbo").send_message
                    final_response = self.genai_client.chats.create(
                        model=model
                    ).send_message(message=final_prompt)
                    if final_response.text is None:
                        return "최종 응답이 없습니다."
                    return final_response.text

                except json.JSONDecodeError:
                    return response_text

            return response_text

        except Exception as e:
            return f"오류가 발생했습니다: {e}"


async def main():
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    project_id = os.getenv("PROJECT_ID")
    if api_key is None or project_id is None:
        print("GENAI_API_KEY 또는 GENAI_PROJECT_ID 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)
    client = None
    try:
        client = GeminiMCPClient(api_key=api_key, project_id=project_id)
        await client.connect_to_server(
            r"D:\works\ai-projects\agentic-mcp-proj\gemini_cli_mcp\src\fastmcp\mcp_server3.py"
        )
        print(f"결과 = {await client.chat("1+3은 얼마인가요?")}")
    finally:
        if client:
            await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
