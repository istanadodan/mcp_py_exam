import os
import asyncio
import google.generativeai as genai
from fast_mcp import FastMCPClient, ToolCallRequest, ToolCallResponse

# Configure Gemini API Key (assuming it's set as an environment variable)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)

# Define the Gemini model interaction function
async def call_gemini_model(prompt: str, tools: list) -> dict:
    """
    Calls the Gemini model with the given prompt and tools.
    Handles potential function calls requested by the model.
    """
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest', # Or another appropriate model
        # generation_config=generation_config, # Optional: Add generation config if needed
        # safety_settings=safety_settings, # Optional: Add safety settings if needed
        tools=tools # Pass the MCP tools to Gemini
    )
    response = await model.generate_content_async(prompt)

    try:
        # Check if the model requested a function call
        function_call = response.candidates[0].content.parts[0].function_call
        if function_call:
            # Prepare the response for FastMCP to handle the tool call
            return {
                "type": "tool_call",
                "tool_name": function_call.name,
                "tool_args": dict(function_call.args),
            }
        else:
            # Return the text response if no function call
            return {"type": "text", "content": response.text}
    except (ValueError, IndexError, AttributeError):
        # Handle cases where the response structure doesn't contain a function call
        # or has unexpected format
        try:
            return {"type": "text", "content": response.text}
        except ValueError:
             # Handle cases where response.text might fail (e.g., blocked content)
             print(f"Warning: Could not extract text from Gemini response. Response: {response}")
             return {"type": "text", "content": "[Blocked or Empty Response]"}


# Define the MCP Tool Handler
async def handle_mcp_tool_call(request: ToolCallRequest) -> ToolCallResponse:
    """
    Placeholder function to handle tool calls received from the MCP server.
    In a real application, this would execute the requested tool.
    """
    print(f"Received tool call request: {request.name} with args: {request.arguments}")
    # Example: Simulate tool execution success
    # In a real scenario, you would execute the tool and get the actual result.
    tool_result_content = f"Successfully executed tool '{request.name}' with arguments: {request.arguments}"
    return ToolCallResponse(
        tool_call_id=request.tool_call_id,
        tool_name=request.name,
        content=[{"type": "text", "text": tool_result_content}]
    )

async def main():
    # Initialize FastMCPClient
    # Replace 'ws://localhost:8765' with the actual MCP server WebSocket URL
    mcp_server_url = os.getenv("MCP_SERVER_URL", "ws://localhost:8765")
    client = FastMCPClient(mcp_server_url)

    # Register the tool call handler
    client.on_tool_call(handle_mcp_tool_call)

    try:
        await client.connect()
        print("MCP Client Connected.")

        # Get available tools from the MCP server
        mcp_tools = await client.list_tools()
        print(f"Available MCP Tools: {[tool.name for tool in mcp_tools]}")

        # Convert MCP tools to Gemini tool format
        gemini_tools = [
             # TODO: Convert MCP tool schemas to Gemini's FunctionDeclaration format
             # This requires mapping MCP's JSON schema to Gemini's format.
             # Example (needs proper implementation based on actual tool schemas):
             # genai.protos.FunctionDeclaration(
             #     name=tool.name,
             #     description=tool.description,
             #     parameters=genai.protos.Schema(...) # Convert inputSchema
             # ) for tool in mcp_tools
        ]
        print("Note: Gemini tool conversion needs implementation.")


        # Example interaction loop
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            # Call Gemini with user input and available tools
            gemini_response = await call_gemini_model(user_input, tools=gemini_tools)

            if gemini_response["type"] == "tool_call":
                print(f"Gemini requested tool call: {gemini_response['tool_name']}")
                # FastMCP handles sending the request and receiving the response via the handler
                # The handler `handle_mcp_tool_call` will be invoked by FastMCP internally.
                # We might need to send the tool result back to Gemini for a final answer.
                # This part requires careful handling of the conversation flow.
                # For now, we just print the simulated result from the handler.
                # A more complete implementation would involve:
                # 1. FastMCP calls `handle_mcp_tool_call`.
                # 2. `handle_mcp_tool_call` executes the tool.
                # 3. The result from `handle_mcp_tool_call` (ToolCallResponse) needs to be
                #    formatted as a FunctionResponse and sent back to Gemini.
                # 4. Call `generate_content_async` again with the FunctionResponse.
                print("Tool call handling simulation (see handle_mcp_tool_call output).")
                # Placeholder for sending tool result back to Gemini if needed

            elif gemini_response["type"] == "text":
                print(f"Gemini: {gemini_response['content']}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client.is_connected:
            await client.disconnect()
            print("MCP Client Disconnected.")

if __name__ == "__main__":
    # Add environment variables for GEMINI_API_KEY and optionally MCP_SERVER_URL
    # For example, create a .env file:
    # GEMINI_API_KEY=your_gemini_api_key
    # MCP_SERVER_URL=ws://your_mcp_server_url
    from dotenv import load_dotenv
    load_dotenv() # Load environment variables from .env file

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except ValueError as ve:
         print(f"Configuration Error: {ve}")