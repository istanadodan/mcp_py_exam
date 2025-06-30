"""Utility & helper functions."""

import json
from pathlib import Path
from typing import Dict, Any
import aiofiles

from langchain_core.messages import BaseMessage


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


async def load_mcp_config_json(filepath: str = "mcp_config.json") -> Dict[str, Any]:
    """
    Load the mcp_config.json file and process the configuration.

    This function:
    1. Reads the mcp_config.json file
    2. Loads it as a Python dictionary
    3. For each server in mcpServers that doesn't already have a transport field:
       - Adds "transport": "stdio" if the command is "npx"
       - Adds "transport": "sse" otherwise

    Returns:
        Dict[str, Any]: The processed configuration dictionary

    Raises:
        FileNotFoundError: If the mcp_config.json file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    # Determine the path of the mcp_config.json file
    config_path = Path(__file__).parent / filepath

    try:
        # Load the JSON file asynchronously using aiofiles

        async with aiofiles.open(config_path, "r") as f:
            content = await f.read()
            config = json.loads(content)

        # Process each server configuration
        if "mcpServers" in config:
            for server_name, server_config in config["mcpServers"].items():
                # Skip if transport is already defined
                if "transport" in server_config:
                    continue

                # Add the appropriate transport based on the command
                # command 파라미터가 없는 경우 무시하고 기본값으로 "sse" 사용
                if "command" in server_config and server_config["command"] == "npx":
                    server_config["transport"] = "stdio"
                else:
                    server_config["transport"] = "sse"

        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file", e.doc, e.pos)
