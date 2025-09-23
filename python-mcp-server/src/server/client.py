import subprocess
import json


def send_message(proc, payload):
    body = json.dumps(payload)
    message = f"Content-Length: {len(body)}\r\n\r\n{body}"
    proc.stdin.write(message)
    proc.stdin.flush()


def read_message(proc):
    # 헤더 읽기
    headers = {}
    while True:
        line = proc.stdout.readline()
        if not line.strip():
            break
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        return None

    body = proc.stdout.read(content_length)
    return json.loads(body)


print("Starting MCP server...")
proc = subprocess.Popen(
    ["uv", "run", "wheather_mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

# 1. initialize 요청
initialize_req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"capabilities": {}},
}
send_message(proc, initialize_req)
print("<< initialize response:", read_message(proc))

# 2. initialized 알림
initialized_req = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
send_message(proc, initialized_req)

# 3. get_forecast 요청
forecast_req = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "get_forecast",
    "params": {"latitude": 34.0522, "longitude": -118.2437},
}
send_message(proc, forecast_req)
print("<< forecast response:", read_message(proc))
