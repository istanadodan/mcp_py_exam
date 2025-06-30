# LMStudio-MCP

A Model Control Protocol (MCP) server that allows Claude to communicate with locally running LLM models via LM Studio.

<img width="1881" alt="Screenshot 2025-03-22 at 16 50 53" src="https://github.com/user-attachments/assets/c203513b-28db-4be5-8c61-ebb8a24404ce" />

## Overview

LMStudio-MCP creates a bridge between Claude (with MCP capabilities) and your locally running LM Studio instance. This allows Claude to:

- Check the health of your LM Studio API
- List available models
- Get the currently loaded model
- Generate completions using your local models

This enables you to leverage your own locally running models through Claude's interface, combining Claude's capabilities with your private models.

## Prerequisites

- Python 3.7+
- [LM Studio](https://lmstudio.ai/) installed and running locally with a model loaded
- Claude with MCP access
- Required Python packages (see Installation)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/infinitimeless/LMStudio-MCP.git
   cd LMStudio-MCP
   ```

2. Install the required packages:
   ```bash
   pip install requests "mcp[cli]" openai
   ```

## MCP Configuration

For Claude to connect to this bridge, you need to configure the MCP settings properly. You can either:

1. **Use directly from GitHub**:
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

2. **Use local installation**:
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

For detailed MCP configuration instructions, see [MCP_CONFIGURATION.md](MCP_CONFIGURATION.md).

## Usage

1. Start your LM Studio application and ensure it's running on port 1234 (the default)

2. Load a model in LM Studio

3. If running locally (not using `uvx`), run the LMStudio-MCP server:
   ```bash
   python lmstudio_bridge.py
   ```

4. In Claude, connect to the MCP server when prompted by selecting "lmstudio-mcp"

## Available Functions

The bridge provides the following functions:

- `health_check()`: Verify if LM Studio API is accessible
- `list_models()`: Get a list of all available models in LM Studio
- `get_current_model()`: Identify which model is currently loaded
- `chat_completion(prompt, system_prompt, temperature, max_tokens)`: Generate text from your local model

## Known Limitations

- Some models (e.g., phi-3.5-mini-instruct_uncensored) may have compatibility issues
- The bridge currently uses only the OpenAI-compatible API endpoints of LM Studio
- Model responses will be limited by the capabilities of your locally loaded model

## Troubleshooting

### API Connection Issues

If Claude reports 404 errors when trying to connect to LM Studio:
- Ensure LM Studio is running and has a model loaded
- Check that LM Studio's server is running on port 1234
- Verify your firewall isn't blocking the connection
- Try using "127.0.0.1" instead of "localhost" in the API URL if issues persist

### Model Compatibility

If certain models don't work correctly:
- Some models might not fully support the OpenAI chat completions API format
- Try different parameter values (temperature, max_tokens) for problematic models
- Consider switching to a more compatible model if problems persist

For more detailed troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## License

MIT

## Acknowledgements

This project was originally developed as "Claude-LMStudio-Bridge_V2" and has been renamed and open-sourced as "LMStudio-MCP".
