# Troubleshooting Guide

This guide focuses on common issues encountered when using LMStudio-MCP, especially related to model compatibility.

## Connection Issues

### 404 Errors When Connecting to LM Studio

If you encounter 404 errors when Claude attempts to connect to LM Studio:

1. Verify that LM Studio is running and has a model loaded
2. Check that the LM Studio server is running on port 1234 (default)
3. Try these fixes:
   - In `lmstudio_bridge.py`, change `http://localhost:1234/v1` to `http://127.0.0.1:1234/v1`
   - Restart LM Studio and ensure the server is running
   - Check your firewall settings to ensure the connection isn't blocked

## Model Compatibility Issues

### Problems with phi-3.5-mini-instruct_uncensored

The phi-3.5-mini-instruct_uncensored model is known to have compatibility issues with the OpenAI chat completions API format. Here are some potential workarounds:

1. **Try a different model format**: If available, try using the non-uncensored version of phi-3.5-mini
2. **Adjust API parameters**:
   - Reduce the `max_tokens` value (try 256 or 512 instead of 1024)
   - Set `temperature` to a lower value (0.3-0.5)
   - Simplify your prompts to be more direct

### Other Model Compatibility Issues

Different models might have different API requirements and constraints:

1. **Response format issues**: Some models don't properly format their responses according to the OpenAI chat API spec
2. **Token limitations**: Models might have different context window sizes
3. **System prompt handling**: Some models ignore or incorrectly process system prompts

## General Debugging

If you need more detailed debugging information:

1. Run the bridge with detailed logging to stdout/stderr:
   ```bash
   python lmstudio_bridge.py 2>&1 | tee debug_log.txt
   ```

2. Look for error messages in the LM Studio interface or logs

3. Try a simple test prompt first to verify basic functionality

## If All Else Fails

If you encounter persistent issues with a specific model:

1. Try a different model that's known to work well with the OpenAI chat completions API
2. Check the LM Studio GitHub repository or forums for model-specific issues or recommendations
3. Consider contributing your findings to this repository to help others