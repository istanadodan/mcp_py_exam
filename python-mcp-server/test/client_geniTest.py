import asyncio
import sys  # Import sys for mocking argv
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import AsyncExitStack

# Assuming client_geni.py is in the same directory or accessible via PYTHONPATH
from test.src.client_geni import MCPClient
from google.genai import types as genai_types
from mcp import ClientSession, ToolInfo

# Mock StdioServerParameters if needed, or use the real one if simple
from mcp import StdioServerParameters


class TestMCPClient(unittest.IsolatedAsyncioTestCase):

    @patch("client_geni.genai.Client")
    @patch("client_geni.AsyncExitStack", new_callable=AsyncMock)
    def setUp(self, MockAsyncExitStack, MockGenaiClient):
        """Set up for test methods."""
        self.server_script_path = ["dummy_server.py"]
        self.mock_genai_client = MockGenaiClient.return_value
        self.mock_exit_stack = MockAsyncExitStack.return_value

        # Mock the generative model
        self.mock_model = MagicMock()
        self.mock_genai_client.GenerativeModel.return_value = self.mock_model

        self.client = MCPClient(server_script_path=self.server_script_path)
        # Replace the instance's exit_stack with the mock
        self.client.exit_stack = self.mock_exit_stack
        # Replace the instance's genai client with the mock
        self.client.client = self.mock_genai_client

    async def test_initialization(self):
        """Test the __init__ method."""
        self.assertEqual(self.client.server_script_path, self.server_script_path)
        self.assertIsNone(self.client.session)
        self.assertIsNotNone(self.client.client)
        self.assertEqual(self.client.tools, [])
        self.assertEqual(self.client.exit_stack, self.mock_exit_stack)

    @patch("client_geni.stdio_client", new_callable=AsyncMock)
    @patch("client_geni.ClientSession", new_callable=AsyncMock)
    async def test_connect_to_server_python(self, MockClientSession, MockStdioClient):
        """Test connect_to_server with a Python script."""
        # Mock stdio_client context manager
        mock_stdio_transport = (AsyncMock(), AsyncMock())  # (stdio, write)
        MockStdioClient.return_value.__aenter__.return_value = mock_stdio_transport

        # Mock ClientSession context manager
        mock_session = MockClientSession.return_value
        mock_session.initialize = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        self.client.session = None  # Ensure session starts as None

        await self.client.connect_to_server()

        # Assert stdio_client was called correctly
        MockStdioClient.assert_called_once()
        args, kwargs = MockStdioClient.call_args
        server_params = args[0]
        self.assertIsInstance(server_params, StdioServerParameters)
        self.assertEqual(server_params.command, "uv")
        self.assertEqual(server_params.args, self.server_script_path)

        # Assert exit_stack entered contexts
        self.mock_exit_stack.enter_async_context.assert_any_call(
            MockStdioClient.return_value
        )
        self.mock_exit_stack.enter_async_context.assert_any_call(mock_session)

        # Assert ClientSession was initialized
        MockClientSession.assert_called_once_with(
            mock_stdio_transport[0], mock_stdio_transport[1]
        )
        mock_session.initialize.assert_awaited_once()

        # Assert session is set
        self.assertEqual(self.client.session, mock_session)
        # Assert genai model was created
        self.mock_genai_client.GenerativeModel.assert_called_once_with(
            "gemini-2.5-pro-exp-03-25"
        )
        self.assertEqual(self.client.model, self.mock_model)

    async def test_connect_to_server_invalid_script(self):
        """Test connect_to_server with an invalid script type."""
        self.client.server_script_path = ["invalid_script.txt"]
        with self.assertRaises(ValueError) as cm:
            await self.client.connect_to_server()
        self.assertEqual(str(cm.exception), "Server script must be a .py or .js file")

    async def test_list_tools(self):
        """Test the list_tools method."""
        # Mock the session and its list_tools method
        self.client.session = AsyncMock(spec=ClientSession)
        mock_tool_list_response = MagicMock()
        mock_tool_list_response.tools = [
            ToolInfo(
                name="tool1",
                description="desc1",
                inputSchema={
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                },
            ),
            ToolInfo(
                name="tool2",
                description="desc2",
                inputSchema={
                    "type": "object",
                    "properties": {"param2": {"type": "integer"}},
                },
            ),
        ]
        self.client.session.list_tools = AsyncMock(return_value=mock_tool_list_response)

        await self.client.list_tools()

        self.client.session.list_tools.assert_awaited_once()
        self.assertEqual(len(self.client.tool), 2)
        # Check structure of the first tool
        tool1 = self.client.tool[0]
        self.assertIsInstance(tool1, genai_types.Tool)
        self.assertEqual(len(tool1.function_declarations), 1)
        decl1 = tool1.function_declarations[0]
        self.assertEqual(decl1.name, "tool1")
        self.assertEqual(decl1.description, "desc1")
        self.assertEqual(
            decl1.parameters.properties["param1"].type,
            genai_types.FunctionDeclaration.Type.STRING,
        )

    async def test_process_query(self):
        """Test the process_query method."""
        # Mock the genai client's generate_content method
        mock_response = MagicMock(spec=genai_types.GenerateContentResponse)
        self.client.client.models.generate_content = MagicMock(
            return_value=mock_response
        )
        # Ensure tools are set (e.g., by calling list_tools or setting manually)
        self.client.tool = [
            genai_types.Tool(function_declarations=[])
        ]  # Dummy tool list

        prompt = "Test prompt"
        response = await self.client.process_query(prompt)

        self.client.client.models.generate_content.assert_called_once()
        args, kwargs = self.client.client.models.generate_content.call_args
        self.assertEqual(kwargs.get("model"), "gemini-2.5-pro-exp-03-25")
        self.assertEqual(kwargs.get("contents"), prompt)
        self.assertIsNotNone(kwargs.get("config"))
        self.assertEqual(kwargs["config"].temperature, 0)
        self.assertEqual(kwargs["config"].tools, self.client.tool)

        self.assertEqual(response, mock_response)

    def test_print_candidates(self):
        """Test the print_candidates method."""
        # Create mock candidates
        mock_part1 = MagicMock()
        mock_part1.text = " Part 1 text "
        mock_part2 = MagicMock()
        mock_part2.text = None  # Test case where text might be None
        mock_part3 = MagicMock()
        mock_part3.text = "Part 3 text"

        mock_content = MagicMock()
        mock_content.role = "model"
        mock_content.parts = [mock_part1, mock_part2, mock_part3]

        mock_candidate1 = MagicMock(spec=genai_types.Candidate)
        mock_candidate1.content = mock_content

        candidates = [mock_candidate1]

        # Patch print to capture output
        with patch("builtins.print") as mock_print:
            self.client.print_candidates(candidates)

            # Assert print was called with expected output
            mock_print.assert_any_call("Candidate #1")
            mock_print.assert_any_call("Role       : model")
            mock_print.assert_any_call("Content    :")
            mock_print.assert_any_call("Part 1 text")  # Check stripping
            # mock_print should not be called for part2 as text is None
            mock_print.assert_any_call("Part 3 text")

    @patch("builtins.input")
    async def test_chat_loop(self, mock_input):
        """Test the interactive chat loop."""
        # Simulate user inputs: first a query, then 'quit'
        mock_input.side_effect = ["Test query", "quit"]

        # Mock process_query to avoid actual processing and check calls
        self.client.process_query = AsyncMock()
        # Mock print_candidates as it's called within the loop
        self.client.print_candidates = MagicMock()

        # Patch print to suppress output during test
        with patch("builtins.print"):
            await self.client.chat_loop()

        # Assert process_query was called with the first input
        self.client.process_query.assert_awaited_once_with("Test query")
        # Assert print_candidates was called after processing the query
        self.client.print_candidates.assert_called_once()
        # Assert input was called twice (for "Test query" and "quit")
        self.assertEqual(mock_input.call_count, 2)

    async def test_cleanup(self):
        """Test the cleanup method."""
        await self.client.cleanup()
        self.mock_exit_stack.aclose.assert_awaited_once()


# --- Tests for main function ---


# We need to patch items within the client_geni module where main is defined
@patch("client_geni.sys.argv", ["client_geni.py", "server.py"])
@patch("client_geni.load_dotenv")
@patch("client_geni.MCPClient", new_callable=MagicMock)
@patch("client_geni.asyncio.run")
async def test_main_success(MockAsyncioRun, MockMCPClient, MockLoadDotenv):
    """Test the main function success path."""
    # Mock the client instance and its methods
    mock_client_instance = MockMCPClient.return_value
    mock_client_instance.connect_to_server = AsyncMock()
    mock_client_instance.chat_loop = AsyncMock()
    mock_client_instance.cleanup = AsyncMock()

    # Import main locally to ensure patches are applied
    from test.src.client_geni import main

    # Run the main function (it's async, but we call it directly as asyncio.run is mocked)
    await main()

    # Assertions
    MockLoadDotenv.assert_called_once()
    MockMCPClient.assert_called_once_with(server_script_path=["server.py"])
    mock_client_instance.connect_to_server.assert_awaited_once()
    mock_client_instance.chat_loop.assert_awaited_once()
    mock_client_instance.cleanup.assert_awaited_once()  # Ensure cleanup is called


@patch("client_geni.sys.argv", ["client_geni.py", "server.py"])
@patch("client_geni.load_dotenv")
@patch("client_geni.MCPClient", new_callable=MagicMock)
@patch("client_geni.asyncio.run")
async def test_main_exception_in_loop(MockAsyncioRun, MockMCPClient, MockLoadDotenv):
    """Test the main function when an exception occurs during chat_loop."""
    mock_client_instance = MockMCPClient.return_value
    mock_client_instance.connect_to_server = AsyncMock()
    # Simulate an error during the chat loop
    mock_client_instance.chat_loop = AsyncMock(side_effect=Exception("Test Error"))
    mock_client_instance.cleanup = AsyncMock()

    from test.src.client_geni import main

    # Expect the exception to be caught by the try/finally in main
    await main()

    # Assertions
    MockLoadDotenv.assert_called_once()
    MockMCPClient.assert_called_once_with(server_script_path=["server.py"])
    mock_client_instance.connect_to_server.assert_awaited_once()
    mock_client_instance.chat_loop.assert_awaited_once()  # Called even if it raises error
    mock_client_instance.cleanup.assert_awaited_once()  # Crucially, cleanup should still run


if __name__ == "__main__":
    # We need to run the async tests using asyncio
    # unittest.main() doesn't handle IsolatedAsyncioTestCase directly when run as script
    # Instead, let the test runner discover and run the tests.
    # Running `python -m unittest client_geniTest.py` is the standard way.
    print("Run tests using 'python -m unittest client_geniTest.py'")
    # Or, if you absolutely need to run from here (less common for async):
    # suite = unittest.TestSuite()
    # loader = unittest.TestLoader()
    # suite.addTest(loader.loadTestsFromTestCase(TestMCPClient))
    # # Add tests for main if they were in a class
    # runner = unittest.TextTestRunner()
    # runner.run(suite)
    pass  # Keep the file runnable, but guide user to standard test execution
