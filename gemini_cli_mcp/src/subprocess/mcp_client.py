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
from typing import Dict, Any, List, Optional

# import google.generativeai as genai 2025년 8월 31일 이후 종료

from google import genai
from dataclasses import dataclass


async def call_tool(
    self, server_name: str, tool_name: str, arguments: Dict[str, Any]
) -> Optional[str]:
    """
    MCP 서버의 도구 호출

    Args:
        server_name: 서버 이름
        tool_name: 도구 이름
        arguments: 도구 인수

    Returns:
        도구 실행 결과
    """
    if server_name not in self.servers:
        return f"서버 '{server_name}'를 찾을 수 없습니다."

    server = self.servers[server_name]

    try:
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        server.input_queue.put(json.dumps(tool_request))

        # 응답 읽기 (타임아웃 포함)
        for _ in range(100):  # 10초 대기
            try:
                response_line = server.output_queue.get(timeout=0.1)
                if response_line:
                    response = json.loads(response_line)

                    if "result" in response:
                        content = response["result"].get("content", [])
                        if content and len(content) > 0:
                            return content[0].get("text", "응답이 없습니다.")
                    elif "error" in response:
                        return f"도구 실행 오류: {response['error']['message']}"

                    return "알 수 없는 응답 형식입니다."
            except queue.Empty:
                continue
            except json.JSONDecodeError as e:
                print(f"도구 응답 JSON 디코딩 오류: {e}")
                continue

        return "도구 호출 타임아웃"

    except Exception as e:
        return f"도구 호출 중 오#!/usr/bin/env python3"


# Windows에서 ProactorEventLoop 문제 해결
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-001"):
        """
        Gemini MCP 클라이언트 초기화

        Args:
            api_key: Gemini API 키
            model_name: 사용할 Gemini 모델명
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.servers: Dict[str, MCPServer] = {}
        self.chat_session = None

    def _read_output(self, process, output_queue, error_queue):
        """별도 스레드에서 프로세스 출력 읽기"""

        def read_stdout():
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    output_queue.put(line.strip())
            except Exception as e:
                error_queue.put(f"stdout 읽기 오류: {e}")

        def read_stderr():
            try:
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    error_queue.put(f"stderr: {line.strip()}")
            except Exception as e:
                error_queue.put(f"stderr 읽기 오류: {e}")

        # stdout, stderr 각각 별도 스레드에서 읽기
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)

        stdout_thread.start()
        stderr_thread.start()

    def _write_input(self, process, input_queue):
        """별도 스레드에서 프로세스 입력 쓰기"""

        def write_stdin():
            try:
                while True:
                    try:
                        message = input_queue.get(timeout=0.1)
                        if message is None:  # 종료 신호
                            break
                        process.stdin.write(message + "\n")
                        process.stdin.flush()
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"stdin 쓰기 오류: {e}")
                        break
            except Exception as e:
                print(f"입력 스레드 오류: {e}")

        input_thread = threading.Thread(target=write_stdin, daemon=True)
        input_thread.start()
        return input_thread

    async def connect_server(self, server_path: str) -> bool:
        """
        MCP 서버에 연결

        Args:
            server_path: MCP 서버 스크립트 경로

        Returns:
            연결 성공 여부
        """
        try:
            # 큐 생성
            input_queue = queue.Queue()
            output_queue = queue.Queue()
            error_queue = queue.Queue()

            # 서버 프로세스 시작
            process = subprocess.Popen(
                [sys.executable, server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )

            # I/O 스레드 시작
            self._read_output(process, output_queue, error_queue)
            input_thread = self._write_input(process, input_queue)

            # 초기화 메시지 전송
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "gemini-mcp-client", "version": "1.0.0"},
                },
            }

            input_queue.put(json.dumps(init_request))

            # 응답 읽기 (타임아웃 포함)
            response_received = False
            response_line = ""
            for _ in range(50):  # 5초 대기
                try:
                    response_line = output_queue.get(timeout=0.1)
                    if response_line:
                        response = json.loads(response_line)
                        print(f"서버 초기화 응답: {response}")
                        response_received = True
                        break
                except queue.Empty:
                    continue
                except json.JSONDecodeError as e:
                    print(f"JSON 디코딩 오류: {e}, 응답: {response_line}")
                    continue

            if not response_received:
                print("초기화 응답을 받지 못했습니다.")
                process.terminate()
                return False

            # 도구 목록 요청
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }

            input_queue.put(json.dumps(tools_request))

            # 도구 목록 응답 읽기
            tools_received = False
            for _ in range(50):
                try:
                    tools_response_line = output_queue.get(timeout=0.1)
                    if tools_response_line:
                        tools_response = json.loads(tools_response_line)

                        if "result" in tools_response:
                            tools = tools_response["result"].get("tools", [])
                            server_name = os.path.basename(server_path)

                            self.servers[server_name] = MCPServer(
                                name=server_name,
                                process=process,
                                tools=tools,
                                input_queue=input_queue,
                                output_queue=output_queue,
                                error_queue=error_queue,
                            )

                            print(f"✅ 서버 '{server_name}' 연결 성공")
                            print(
                                f"사용 가능한 도구: {[tool['name'] for tool in tools]}"
                            )
                            tools_received = True
                            break
                        else:
                            print(f"도구 목록 응답 오류: {tools_response}")
                            break
                except queue.Empty:
                    continue
                except json.JSONDecodeError as e:
                    print(f"도구 목록 JSON 디코딩 오류: {e}")
                    continue

            if not tools_received:
                print(f"❌ 서버 '{server_path}' 도구 목록 가져오기 실패")
                process.terminate()
                return False

            return True

        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[str]:
        """
        MCP 서버의 도구 호출

        Args:
            server_name: 서버 이름
            tool_name: 도구 이름
            arguments: 도구 인수

        Returns:
            도구 실행 결과
        """
        if server_name not in self.servers:
            return f"서버 '{server_name}'를 찾을 수 없습니다."

        server = self.servers[server_name]

        try:
            tool_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }

            server.input_queue.put(json.dumps(tool_request))

            # 응답 읽기 (타임아웃 포함)
            for _ in range(100):  # 10초 대기
                try:
                    response_line = server.output_queue.get(timeout=0.1)
                    if response_line:
                        response = json.loads(response_line)

                        if "result" in response:
                            content = response["result"].get("content", [])
                            if content and len(content) > 0:
                                return content[0].get("text", "응답이 없습니다.")
                        elif "error" in response:
                            return f"도구 실행 오류: {response['error']['message']}"

                        return "알 수 없는 응답 형식입니다."
                except queue.Empty:
                    continue
                except json.JSONDecodeError as e:
                    print(f"도구 응답 JSON 디코딩 오류: {e}")
                    continue

            return "도구 호출 타임아웃"

        except Exception as e:
            return f"도구 호출 중 오#!/usr/bin/env python3"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """사용 가능한 모든 도구 목록 반환"""
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.tools:
                tool_info = tool.copy()
                tool_info["server"] = server_name
                all_tools.append(tool_info)
        return all_tools

    async def chat(self, message: str) -> str:
        """
        Gemini와 채팅하며 필요시 MCP 도구 사용

        Args:
            message: 사용자 메시지

        Returns:
            Gemini 응답
        """
        # 사용 가능한 도구 정보를 프롬프트에 포함
        tools_info = self.get_available_tools()
        tools_description = "\n".join(
            [
                f"- {tool['name']} (서버: {tool['server']}): {tool['description']}"
                for tool in tools_info
            ]
        )

        system_prompt = f"""
당신은 MCP(Model Context Protocol) 도구를 사용할 수 있는 AI 어시스턴트입니다.

사용 가능한 도구들:
{tools_description}

사용자의 요청을 처리하기 위해 적절한 도구가 필요하다면, 다음 형식으로 도구 호출을 요청하세요:

TOOL_CALL: {{
  "server": "서버명",
  "tool": "도구명",
  "arguments": {{인수 딕셔너리}}
}}

도구 호출 결과를 받은 후 최종 답변을 제공하세요.
"""

        try:
            full_prompt = f"{system_prompt}\n\n사용자: {message}"
            response = self.model.generate_content(full_prompt)
            response_text = response.text

            # 도구 호출이 필요한지 확인
            if "TOOL_CALL:" in response_text:
                # 도구 호출 부분 추출
                tool_call_start = response_text.find("TOOL_CALL:")
                tool_call_end = response_text.find("}", tool_call_start) + 1
                tool_call_json = response_text[
                    tool_call_start + 10 : tool_call_end
                ].strip()

                try:
                    tool_call = json.loads(tool_call_json)
                    server_name = tool_call["server"]
                    tool_name = tool_call["tool"]
                    arguments = tool_call["arguments"]

                    print(f"🔧 도구 호출: {server_name}/{tool_name}")

                    # 도구 실행
                    tool_result = await self.call_tool(
                        server_name, tool_name, arguments
                    )

                    # 도구 결과를 포함한 최종 응답 생성
                    final_prompt = f"""
{system_prompt}

사용자: {message}

도구 호출 결과:
서버: {server_name}
도구: {tool_name}
결과: {tool_result}

위 결과를 바탕으로 사용자에게 최종 답변을 제공하세요.
"""

                    final_response = self.model.generate_content(final_prompt)
                    return final_response.text

                except json.JSONDecodeError:
                    return response_text

            return response_text

        except Exception as e:
            return f"오류가 발생했습니다: {e}"

    def cleanup(self):
        """모든 서버 프로세스 정리"""
        for server in self.servers.values():
            server.process.terminate()
        self.servers.clear()


async def main():
    """메인 실행 함수"""
    # 환경 변수에서 API 키 가져오기
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY 환경 변수를 설정해주세요.")
        return

    client = GeminiMCPClient(api_key)

    # 명령줄 인수로 전달된 서버들 연결
    if len(sys.argv) > 1:
        for server_path in sys.argv[1:]:
            await client.connect_server(server_path)

    print("\n🤖 Gemini MCP 채팅 시작")
    print("명령어:")
    print("- 'add_server <경로>': 새 MCP 서버 추가")
    print("- 'list_tools': 사용 가능한 도구 목록")
    print("- 'quit': 종료")
    print("-" * 50)

    try:
        while True:
            user_input = input("\n당신: ").strip()

            if user_input.lower() == "quit":
                break
            elif user_input.startswith("add_server "):
                server_path = user_input[11:].strip()
                await client.connect_server(server_path)
            elif user_input == "list_tools":
                tools = client.get_available_tools()
                if tools:
                    print("\n사용 가능한 도구:")
                    for tool in tools:
                        print(
                            f"- {tool['name']} ({tool['server']}): {tool['description']}"
                        )
                else:
                    print("연결된 도구가 없습니다.")
            else:
                response = await client.chat(user_input)
                print(f"\nGemini: {response}")

    except KeyboardInterrupt:
        print("\n\n채팅을 종료합니다.")

    finally:
        client.cleanup()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
