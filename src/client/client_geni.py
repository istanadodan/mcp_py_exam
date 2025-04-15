import asyncio
from contextlib import AsyncExitStack
from typing import Optional
from google import genai
from google.genai import types
from google.genai.types import Candidate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv


class MCPClient:

    def __init__(
        self,
        server_script_path,
    ) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.server_script_path = server_script_path
        # model
        self.client = genai.Client()
        self.tools = []
        print(self.server_script_path)

    # methods will go here
    async def connect_to_server(self) -> StdioServerParameters:
        """
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = self.server_script_path[-1].endswith(".py")
        is_js = self.server_script_path[-1].endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "uv" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=self.server_script_path, env=None
        )
        print(f"server_params: {server_params}")
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await self.session.initialize()
        print(f"session get")

        self.tools = await self._create_tool_list()

    # MCP 서버로부터 사용 가능한 도구 목록을 가져와 Google AI 형식으로 변환합니다.
    async def _create_tool_list(self):
        """List available tools"""
        # MCP 세션을 통해 서버의 도구 목록을 비동기적으로 요청합니다.
        mcp_tools = await self.session.list_tools()
        print(f"list_tools: {mcp_tools}")  # 가져온 도구 목록 로깅 (디버깅용)

        # 가져온 MCP 도구 목록을 Google AI SDK가 요구하는 types.Tool 형식으로 변환합니다.
        return [
            types.Tool(
                function_declarations=[  # 각 도구에 대한 함수 선언 목록
                    {
                        "name": tool.name,  # 도구 이름
                        "description": tool.description,  # 도구 설명
                        "parameters": {  # 도구 입력 파라미터 스키마
                            k: v
                            for k, v in tool.inputSchema.items()
                            # 불필요한 스키마 속성('additionalProperties', '$schema') 제외
                            if k not in ["additionalProperties", "$schema"]
                        },
                    },
                ]
            )
            # mcp_tools 응답 내의 각 도구에 대해 반복 처리
            for tool in mcp_tools.tools
        ]

    # 쿼리와 도구 목록을 모델에 전달하여 응답 생성
    async def process_query(self, prompt: str) -> types.GenerateContentResponse:
        """
        Args:
            prompt: Prompt to send to the server
        """
        print(f"mcp_tools start: {prompt}")

        response: types.GenerateContentResponse = self.client.models.generate_content(
            model="gemini-2.5-pro-exp-03-25",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, tools=self.tools),
        )

        return response

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                answer3 = ""
                response = await self.process_query(query)
                answer1 = response.text
                if response.function_calls:
                    answer2 = []
                    for fc in response.function_calls:
                        func_answer = await self.session.call_tool(
                            name=fc.name, arguments=fc.args
                        )
                        answer2.append(
                            "\n--\n".join([t.text for t in func_answer.content])
                        )

                    answer1 += "\n--\n".join(answer2)
                    answer3 = await self.process_query(answer1)

                print(answer3.candidates[0].content.parts[0].text)

                # self.print_candidates(response.candidates)

            except Exception as e:
                print(f"\nError: {str(e)}")

    def print_candidates(self, candidates: list[Candidate]):
        """Print the candidates from the response"""

        # 예시: 실제 응답 객체에서 가져온다고 가정
        for i, candidate in enumerate(candidates, 1):
            print(f"Candidate #{i}")
            print(f"Role       : {candidate.content.role}")
            print("Content    :")
            for part in candidate.content.parts:
                if part.text:
                    print(part.text.strip())
                elif part.function_call.name:
                    print(f"{part.function_call.name}({part.function_call.args})")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    # Initialize the client session
    client = MCPClient(
        server_script_path=sys.argv[1:],
        # server_parameters=WebSocketServerParameters(url="ws://localhost:8765"),
    )
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    load_dotenv()  # load environment variables from .env

    asyncio.run(main())
