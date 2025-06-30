import subprocess
from mcp.client import ClientSession
from pydantic import BaseModel
from ollama import chat as ChatOllama

# MCP 서버 백그라운드 실행
subprocess.Popen(["python", "server.py"])

# MCP 도구 불러오기
with ClientSession() as session:
    session.initialize()
    tools = session.get_tools()


class MagicOutputModel(BaseModel):
    text1: str
    text2: str


model = ChatOllama(model="llama3.2")

user_input = "Combine 'Hello' and 'World'"
response = model.chat(
    messages=[{"role": "user", "content": user_input}], format=MagicOutputModel
)

print(response)
