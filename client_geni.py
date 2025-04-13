import asyncio
import os
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

    async def process_query(self, prompt: str) -> types.GenerateContentResponse:
        """
        Args:
            prompt: Prompt to send to the server
        """
        print(f"mcp_tools start: {prompt}")
        mcp_tools = await self.session.list_tools()
        print(f"mcp_tools: len{mcp_tools}")
        tools = [
            types.Tool(
                function_declarations=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            k: v
                            for k, v in tool.inputSchema.items()
                            if k not in ["additionalProperties", "$schema"]
                        },
                    },
                ]
            )
            for tool in mcp_tools.tools
        ]

        response: types.GenerateContentResponse = self.client.models.generate_content(
            model="gemini-2.5-pro-exp-03-25",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, tools=tools),
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

                response = await self.process_query(query)

                self.print_candidates(response.candidates)

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
