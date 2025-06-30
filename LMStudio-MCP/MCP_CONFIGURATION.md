# Claude MCP Configuration Guide

This guide explains how to configure Claude to connect with the LMStudio-MCP server. When using Claude with Model Control Protocol (MCP), you need to properly configure the MCP JSON configuration file to establish the connection.

## MCP Configuration File

Claude's MCP functionality requires a configuration file that specifies how to launch and connect to MCP servers. There are two ways to add the LMStudio-MCP server to your configuration:

### Method 1: Direct Launch (Local Installation)

If you've cloned the repository locally and want Claude to launch the server directly:

```json
{
  "lmstudio-mcp": {
    "command": "/bin/bash",
    "args": [
      "-c",
      "cd /path/to/LMStudio-MCP && source venv/bin/activate && python lmstudio_bridge.py"
    ]
  }
}
```

Replace `/path/to/LMStudio-MCP` with the actual path where you've cloned the repository.

### Method 2: Using UVX (Remote Installation)

You can also use `uvx` to have Claude install and run the server directly from GitHub:

```json
{
  "lmstudio-mcp": {
    "command": "uvx",
    "args": [
      "https://github.com/infinitimeless/LMStudio-MCP"
    ]
  }
}
```

This method will automatically fetch the latest version from GitHub and run it.

## Full Configuration Example

Here's a full configuration example that includes both methods (you would typically only need one):

```json
{
  "lmstudio-mcp-local": {
    "command": "/bin/bash",
    "args": [
      "-c",
      "cd ~/LMStudio-MCP && source venv/bin/activate && python lmstudio_bridge.py"
    ]
  },
  "lmstudio-mcp-github": {
    "command": "uvx",
    "args": [
      "https://github.com/infinitimeless/LMStudio-MCP"
    ]
  }
}
```

## Adding to Existing Configuration

If you already have other MCP servers configured, you'll need to add the LMStudio-MCP configuration to your existing JSON file. Make sure to maintain the proper JSON structure with commas between entries.

Example of adding to existing configuration:

```json
{
  "other-mcp-server": {
    "command": "...",
    "args": [
      "..."
    ]
  },
  "lmstudio-mcp": {
    "command": "uvx",
    "args": [
      "https://github.com/infinitimeless/LMStudio-MCP"
    ]
  }
}
```

## Launching the MCP Server in Claude

1. Start a conversation with Claude
2. Click on "Connect an MCP server" (or similar option in the interface)
3. Select "lmstudio-mcp" from the list of available servers
4. Claude will launch the server and connect to it

Once connected, you can use the LMStudio-MCP functions in your conversation with Claude:
- `health_check()`
- `list_models()`
- `get_current_model()`
- `chat_completion(prompt, system_prompt, temperature, max_tokens)`

## Troubleshooting Configuration

If Claude has trouble launching the MCP server:

1. Check that the path in your configuration is correct
2. Ensure you have the right permissions to execute the script
3. Verify that your virtual environment is properly set up
4. Make sure LM Studio is running and accessible

For more details on MCP configuration, refer to Anthropic's official documentation on Model Control Protocol.
