import asyncio
from fastmcp import Client, FastMCP

client = Client("http://localhost:8000/mcp")
# proxy = FastMCP.as_proxy(client, name="ProxyServer")


async def call_greet(name: str):
    async with client:
        # result = await client.call_tool("greet",`` {"name": name})
        # print(result)

        # result = await client.call_tool("get_average", {"numbers": [1, 2, 3, 4, 5]})
        # print(result)

        resources = await client.list_resources()
        print("Resources:", resources)
        import json

        try:
            config = next(iter(await client.read_resource("data://config")))
            print("Config :", config)
            setting = json.loads(config.text)
            print("Config setting:", setting)
        except Exception as e:
            print("Error fetching resource:", e)


asyncio.run(call_greet("Alice"))

# proxy.run("http")
