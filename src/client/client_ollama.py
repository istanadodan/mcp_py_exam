import asyncio
from contextlib import AsyncExitStack
from typing import Optional
from ollama import ChatResponse, Client
from langchain_openai import ChatOpenAI
from langchain.tools.mcp
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
        self.client = ChatOpenAI(
            base_url="http://localhost:11434/v1", api_key="lm-studio"
        )
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

        self.tools = await self._create_tool_list()

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                template_prompt = f"""
{query}
날씨에 대해서는 도구를 반드시 이용하여야하며, 
필요한 경우, 도구에 필요한 입력값(예: 위도/경도)은 묻지말고 스스로 찾도록 할 것.
"""
                try:
                    response = await self.process_query(template_prompt)
                    result = await self.parse_answer(query, response)
                    print(result)
                except genai.errors.ClientError as e:
                    print(f"[{e.status}: {e.message}")

                profiles = await self.session.read_resource("knowledge://profile/alice")
                print(f"content: {profiles.contents[0].text}")
                # # response
                # answer1 = response.text

                # if response.function_calls:
                #     message = {"role": "user", "message": [{"text": query}]}
                #     history.append(message)

                #     answer2 = []
                #     for fc in response.function_calls:
                #         func_answer = await self.session.call_tool(
                #             name=fc.name, arguments=fc.args
                #         )
                #         answer2 += [t.text for t in func_answer.content]

                #     answer1 += "\n--\n".join(answer2)
                #     message = {"role": "function", "message": [{"text": answer1}]}
                #     history.append(message)

                #     answer3 = await self.process_query("\n".join(history))

                #     self.print_candidates(answer3.candidates)
                # else:
                #     self.print_candidates(response.candidates)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def parse_answer(self, query, response):
        """Parse the response from the server"""
        print(
            f"query: {query} \ntext: {response.text} \nfunction: {response.function_calls} \ncandidates: {len(response.candidates[0].content.parts)}"
        )
        if not response.function_calls:
            return response.text or ""

        for function_call in response.function_calls:
            tool_answer = await self.session.call_tool(
                name=function_call.name,
                arguments=function_call.args,
            )
            pre_query = query + response.text if response.text else query
            query_with_tool_answer = "\n\n".join(
                [pre_query] + [t.text for t in tool_answer.content]
            )
            response = await self.process_query(query_with_tool_answer)
            return await self.parse_answer(query, response)

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
