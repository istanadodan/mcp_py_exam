#!/usr/bin/env python3
import asyncio
import json
import sys
import subprocess
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)
import mcp.server.stdio

app = Server("gemini-cli")


@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="gemini_query",
            description="Gemini AI에게 질문하고 응답받기",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gemini에게 보낼 질문"},
                    "model": {
                        "type": "string",
                        "description": "사용할 Gemini 모델 (기본값: gemini-pro)",
                        "default": "gemini-pro",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="gemini_chat",
            description="Gemini와 대화형 채팅",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "채팅 메시지"},
                    "session_id": {
                        "type": "string",
                        "description": "채팅 세션 ID (선택사항)",
                        "default": "default",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="gemini_image_analysis",
            description="이미지 분석 요청",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "분석할 이미지 파일 경로",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "이미지에 대한 질문 또는 분석 요청",
                    },
                },
                "required": ["image_path", "prompt"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    try:
        if name == "gemini_query":
            query = arguments["query"]
            model = arguments.get("model", "gemini-pro")

            cmd = ["gemini", "query", "--model", model, query]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return CallToolResult(
                    content=[TextContent(type="text", text=result.stdout.strip())]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"오류: {result.stderr}")],
                    isError=True,
                )

        elif name == "gemini_chat":
            message = arguments["message"]
            session_id = arguments.get("session_id", "default")

            cmd = ["gemini", "chat", "--session", session_id, message]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return CallToolResult(
                    content=[TextContent(type="text", text=result.stdout.strip())]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"오류: {result.stderr}")],
                    isError=True,
                )

        elif name == "gemini_image_analysis":
            image_path = arguments["image_path"]
            prompt = arguments["prompt"]
            print(f"image_path:{image_path}, prompt:{prompt}")

            cmd = ["gemini", "analyze", "--image", image_path, prompt]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                return CallToolResult(
                    content=[TextContent(type="text", text=result.stdout.strip())]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"오류: {result.stderr}")],
                    isError=True,
                )

        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"알 수 없는 도구: {name}")],
                isError=True,
            )

    except subprocess.TimeoutExpired:
        return CallToolResult(
            content=[TextContent(type="text", text="요청 시간 초과")], isError=True
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"실행 오류: {str(e)}")],
            isError=True,
        )


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
