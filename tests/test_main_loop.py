import unittest
from unittest.mock import patch, MagicMock
import io
import contextlib
import os # For setting a dummy API key if needed, though mocking load_api_key is better

# Assuming main.py is in the parent directory.
# If main.py is structured to be importable (e.g., its main logic is in a main() function):
try:
    import main as main_module
except ImportError:
    # This structure might be needed if main.py is not directly in PYTHONPATH for tests
    # For this environment, assume it's importable or adjust path if necessary.
    # No, main.py is expected to be at the root of the project.
    # The test runner should handle path issues.
    main_module = __import__("main")


class TestMainLoop(unittest.TestCase):
    """Test cases for the main gameplay loop in main.py."""

    @patch('main.load_api_key') # Mocks load_api_key within the main_module
    @patch('main.GeminiDialogueManager') # Mocks GeminiDialogueManager within the main_module
    @patch('builtins.input')
    def test_single_interaction_and_quit(self, mock_input, MockGeminiDM, mock_load_api_key):
        """
        Test a single player input, DM response, and then quitting.
        """
        # --- Setup Mocks ---
        # Mock load_api_key to return a dummy key so main() doesn't exit early
        mock_load_api_key.return_value = "DUMMY_API_KEY"

        # Configure the mock GeminiDialogueManager instance
        mock_dm_instance = MockGeminiDM.return_value # This is the mock instance dm will use
        mock_dm_instance.send_message.return_value = "The DM responds: 'Interesting choice!'"

        # Configure mock_input to provide a sequence of inputs
        mock_input.side_effect = ["look around", "quit"]

        # --- Capture stdout ---
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            try:
                main_module.main()
            except SystemExit: # Catch sys.exit if main() calls it (it doesn't explicitly)
                pass
            except Exception as e:
                # If main() raises an unexpected error, fail the test and print it
                self.fail(f"main_module.main() raised an unexpected exception: {e}\nCaptured output:\n{captured_output.getvalue()}")


        # --- Assertions ---
        output_str = captured_output.getvalue()

        # Check for welcome message (flexible check)
        self.assertIn("Welcome to the AI-Powered Text Adventure!", output_str)

        # Check that input prompt appeared
        self.assertIn("What do you do? >", output_str)

        # Check that DM's (mocked) response was printed by GeminiDM's send_message
        # GeminiDM's send_message prints directly. If it's streaming, it prints chunks.
        # The return value "The DM responds: 'Interesting choice!'" is what we set.
        # main.py itself also prints "DM is crafting a response..."
        self.assertIn("DM is crafting a response...", output_str)
        # The actual response from the mocked send_message would be printed by send_message itself.
        # Since send_message is part of the mocked GeminiDialogueManager, its print behavior is also part of the mock.
        # If send_message was *not* printing, then main.py would need to print mock_dm_instance.send_message.return_value.
        # The current gemini_dm.py *does* print. So we expect "The DM responds: 'Interesting choice!'"
        # to be in the output because the mocked send_message would have "printed" it (if it were the real one).
        # However, the mock_dm_instance.send_message is a MagicMock; it doesn't inherently print its return value.
        # The main.py loop calls dm.send_message() but relies on it to print.
        # For this test, we need to ensure our mock behaves as if it printed, or check if main prints it.
        # main.py's loop:
        #   print("\nDM is crafting a response...")
        #   dm_response_full = dm.send_message(player_input, stream=True)
        #   logger.debug(f"DM full response received in main loop: '{dm_response_full[:250]}...'")
        # It does NOT print dm_response_full directly after the call.
        # Thus, for this test to pass as is, the MOCK send_message needs to print.
        # Let's adjust mock_dm_instance.send_message to also print to our captured output.

        def mock_send_message_with_print(message, stream=True):
            # Simulate the send_message printing behavior
            response = "The DM responds: 'Interesting choice!'" # Fixed response
            if stream: # Simulate streaming print
                print(response, end="", flush=True)
                print() # Newline after stream
            else:
                print(response)
            return response

        mock_dm_instance.send_message.side_effect = mock_send_message_with_print

        # Re-run with the printing mock
        mock_input.side_effect = ["look around", "quit"] # Reset side_effect for input
        mock_load_api_key.return_value = "DUMMY_API_KEY" # Ensure it's set for re-run
        MockGeminiDM.return_value = mock_dm_instance # Re-assign potentially new mock_dm_instance if needed

        captured_output = io.StringIO() # Reset captured output
        with contextlib.redirect_stdout(captured_output):
            try:
                main_module.main()
            except SystemExit:
                pass # Expected for "quit" if it causes a sys.exit, though current main.py breaks loop
            except Exception as e:
                self.fail(f"main_module.main() (second run) raised an unexpected exception: {e}\nCaptured output:\n{captured_output.getvalue()}")

        output_str = captured_output.getvalue()

        self.assertIn("The DM responds: 'Interesting choice!'", output_str, "Mocked DM response not found in output.")

        # Check for quit message
        self.assertIn("Thank you for playing!", output_str)

        # Verify calls
        mock_load_api_key.assert_called_once()
        MockGeminiDM.assert_called_once_with(
            api_key="DUMMY_API_KEY",
            gemini_model_name=main_module.DEFAULT_MODEL_NAME, # Assuming main_module has this as a global/constant
            system_instruction_text=main_module.DEFAULT_SYSTEM_INSTRUCTION,
            max_history_items=20 # This was hardcoded in main.py's call
        )
        # send_message would be called for "look around"
        mock_dm_instance.send_message.assert_called_with("look around", stream=True)
        self.assertEqual(mock_dm_instance.send_message.call_count, 1) # Called for "look around", then loop breaks for "quit"

    @patch('main.load_api_key')
    @patch('main.GeminiDialogueManager')
    @patch('builtins.input')
    def test_exit_command(self, mock_input, MockGeminiDM, mock_load_api_key):
        """Test that 'exit' command also terminates the loop."""
        mock_load_api_key.return_value = "DUMMY_API_KEY"
        mock_dm_instance = MockGeminiDM.return_value
        # No actual call to send_message will happen if "exit" is the first command

        mock_input.side_effect = ["exit"]

        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            try:
                main_module.main()
            except SystemExit:
                 pass # Should not happen with current main.py, it just breaks
            except Exception as e:
                self.fail(f"main_module.main() raised an unexpected exception: {e}\nCaptured output:\n{captured_output.getvalue()}")

        output_str = captured_output.getvalue()
        self.assertIn("Thank you for playing!", output_str)
        mock_dm_instance.send_message.assert_not_called() # send_message should not be called

    @patch('main.load_api_key')
    def test_no_api_key(self, mock_load_api_key):
        """Test that the game informs user and exits if API key is not found."""
        mock_load_api_key.return_value = None

        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            main_module.main() # Should execute and print error, then return

        output_str = captured_output.getvalue()
        self.assertIn("Critical Error: The GEMINI_API_KEY environment variable must be set", output_str)
        # Ensure it doesn't proceed to initialize DM or gameplay loop
        self.assertNotIn("Initializing GeminiDialogueManager", output_str)
        self.assertNotIn("What do you do? >", output_str)


if __name__ == '__main__':
    unittest.main()
