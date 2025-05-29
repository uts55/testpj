import unittest
from unittest.mock import patch, MagicMock, call
import time # For checking time.sleep calls

# Assuming gemini_dm.py is in the same directory or accessible via PYTHONPATH
from gemini_dm import GeminiDialogueManager 
import google.generativeai.types as Types 

# Helper Mock Classes (as suggested in the prompt)
class MockPart:
    def __init__(self, text=None, function_call=None, function_response=None):
        self.text = text
        if text is not None and not isinstance(text, str):
            raise ValueError(f"MockPart.text must be a string, got {type(text)}")
        self.function_call = function_call
        self.function_response = function_response

    def __repr__(self):
        return f"MockPart(text='{self.text}', function_call={self.function_call}, function_response={self.function_response})"

class MockChunk: # For streaming responses
    def __init__(self, parts_list=None):
        self.parts = parts_list if parts_list is not None else []
        # Mimic google.generativeai.types.GenerateContentResponse structure for chunks
        # Each chunk has candidates, and each candidate has content (which has parts)
        # For simplicity in mocking, we'll assume chunk directly has parts that are relevant.
        # The production code iterates through chunk.parts, so this should align.
        
        # self.function_calls = None # This was in original gemini_dm for older library versions
        # if self.parts and any(p.function_call for p in self.parts):
        #    self.function_calls = [p.function_call for p in self.parts if p.function_call]


class MockNonStreamResponse: # For non-streaming responses
    def __init__(self, parts_list=None, text_override=None):
        self.parts = parts_list if parts_list is not None else []
        
        # Calculate .text from parts if not overridden
        if text_override is not None:
            self.text = text_override
        else:
            self.text = "".join(p.text for p in self.parts if hasattr(p, 'text') and p.text)
        
        # self.function_calls = None # Mimic potential structure
        # if self.parts and any(p.function_call for p in self.parts):
        #    self.function_calls = [p.function_call for p in self.parts if p.function_call]


class TestGeminiDialogueManager(unittest.TestCase):

    def setUp(self):
        # Basic parameters for GeminiDialogueManager
        self.api_key = "test_api_key"
        self.model_name = "test_model"
        # Mock genai.configure to prevent actual configuration attempts
        self.patcher_configure = patch('google.generativeai.configure')
        self.mock_genai_configure = self.patcher_configure.start()

    def tearDown(self):
        self.patcher_configure.stop()
        patch.stopall() # Stops any other patches started with patch decorators or patch.start()

    @patch('gemini_dm.genai.GenerativeModel')
    def test_system_prompt_initialization_with_prompt(self, MockGenerativeModel):
        """Test GDM initialization WITH a system prompt."""
        system_prompt = "You are a helpful assistant."
        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            system_instruction_text=system_prompt
        )
        MockGenerativeModel.assert_called_once_with(
            self.model_name,
            tools=dm.tools, # tools will be None by default
            system_instruction=system_prompt
        )

    @patch('gemini_dm.genai.GenerativeModel')
    def test_system_prompt_initialization_without_prompt(self, MockGenerativeModel):
        """Test GDM initialization WITHOUT a system prompt."""
        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name
            # system_instruction_text is omitted
        )
        MockGenerativeModel.assert_called_once_with(
            self.model_name,
            tools=dm.tools, # tools will be None by default
            system_instruction=None # Expecting None or it not being passed if default is None
        )

    @patch('gemini_dm.genai.GenerativeModel')
    def test_history_truncation(self, MockGenerativeModel):
        """Test history truncation logic."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.return_value = MockNonStreamResponse(
            parts_list=[MockPart(text="response")]
        )

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            max_history_items=3 
        )

        # Populate history with more items than max_history_items
        dm.history = [
            {"role": "user", "parts": [MockPart(text="u1")]},
            {"role": "model", "parts": [MockPart(text="m1")]},
            {"role": "user", "parts": [MockPart(text="u2")]},
            {"role": "model", "parts": [MockPart(text="m2")]},
            {"role": "user", "parts": [MockPart(text="u3")]} # 5 items
        ]
        
        original_history_for_assertion = list(dm.history) # copy for assertion

        dm.send_message("new_user_prompt")

        # Assert that generate_content was called with truncated history
        # Original 5 items, max 3. items_to_remove = 2.
        # Kept history for API call: original_history_for_assertion[2:] -> u2, m2, u3
        # Then new user prompt "new_user_prompt" is added.
        expected_contents_for_request = [
            original_history_for_assertion[2], # u2
            original_history_for_assertion[3], # m2
            original_history_for_assertion[4], # u3
            {"role": "user", "parts": [{"text": "new_user_prompt"}]}
        ]
        
        args, kwargs = mock_model_instance.generate_content.call_args
        # self.assertEqual(kwargs['contents'], expected_contents_for_request) # This was the old way
        self.assertEqual(args[0], expected_contents_for_request) # contents is the first positional arg

        # Assert that dm.history itself is updated correctly after the call
        # It was truncated to 3 items [u2, m2, u3], then "new_user_prompt" and "response" were added.
        # So, after send_message, dm.history should be [u2, m2, u3, new_user_prompt_part, model_response_part]
        self.assertEqual(len(dm.history), 5) 
        self.assertEqual(dm.history[0]["parts"][0].text, "u2") # Check that oldest were removed
        self.assertEqual(dm.history[1]["parts"][0].text, "m2")
        self.assertEqual(dm.history[2]["parts"][0].text, "u3")
        self.assertEqual(dm.history[3]["parts"][0].text, "new_user_prompt")
        self.assertEqual(dm.history[4]["parts"][0].text, "response")


    @patch('time.sleep', return_value=None) # Mock time.sleep to avoid delays
    @patch('gemini_dm.genai.GenerativeModel')
    def test_retry_logic_broken_response_success_on_retry(self, MockGenerativeModel, mock_sleep):
        """Test retry logic succeeds after BrokenResponseError."""
        mock_model_instance = MockGenerativeModel.return_value
        
        # Configure side_effect: first call raises error, second call succeeds
        mock_model_instance.generate_content.side_effect = [
            Types.BrokenResponseError("API broke"),
            MockNonStreamResponse(parts_list=[MockPart(text="successful response")])
        ]

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            max_retries=2,
            initial_backoff_seconds=0.01 # Use small backoff for test speed
        )

        response_text = dm.send_message("test prompt")

        self.assertEqual(mock_model_instance.generate_content.call_count, 2)
        self.assertEqual(response_text, "successful response")
        mock_sleep.assert_called_once() # Should have slept once before the retry

    @patch('time.sleep', return_value=None)
    @patch('gemini_dm.genai.GenerativeModel')
    def test_retry_logic_max_retries_reached(self, MockGenerativeModel, mock_sleep):
        """Test retry logic when max retries are reached for BrokenResponseError."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = Types.BrokenResponseError("API broke consistently")

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            max_retries=2, # Total 3 attempts (initial + 2 retries)
            initial_backoff_seconds=0.01
        )

        response_text = dm.send_message("test prompt")

        self.assertEqual(mock_model_instance.generate_content.call_count, 3) # Initial + 2 retries
        self.assertTrue("Error: API call failed after 3 attempts due to BrokenResponseError" in response_text)
        self.assertEqual(mock_sleep.call_count, 2) # Slept before 2nd and 3rd attempts

    @patch('gemini_dm.genai.GenerativeModel')
    def test_stop_candidate_exception_no_retry(self, MockGenerativeModel):
        """Test that StopCandidateException is not retried."""
        mock_model_instance = MockGenerativeModel.return_value
        mock_model_instance.generate_content.side_effect = Types.StopCandidateException("Blocked by API")

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            max_retries=3 
        )

        response_text = dm.send_message("test prompt")

        self.assertEqual(mock_model_instance.generate_content.call_count, 1)
        self.assertTrue("Error: The request was blocked by the API." in response_text)

# Test Function Call Handling - Conceptual (will add if time permits)
# This requires more intricate mocking of the response stream and parts.

    @patch('gemini_dm.genai.GenerativeModel')
    def test_function_call_handling_streaming(self, MockGenerativeModel):
        """Test handling of API-managed function call and response in streaming mode."""
        mock_model_instance = MockGenerativeModel.return_value

        # Mock FunctionCall and FunctionResponse objects
        mock_fc = Types.FunctionCall(name="test_tool", args={"param": "value"})
        # The 'response' in FunctionResponse is a dict, not a string.
        mock_fr_response_content = {"result": "tool success"}
        mock_fr = Types.FunctionResponse(name="test_tool", response=mock_fr_response_content)
        
        final_text = "Final answer after tool use"

        # Configure generate_content to return a stream of mock chunks
        mock_stream = [
            MockChunk(parts_list=[MockPart(function_call=mock_fc)]),
            MockChunk(parts_list=[MockPart(function_response=mock_fr)]),
            MockChunk(parts_list=[MockPart(text=final_text)])
        ]
        mock_model_instance.generate_content.return_value = mock_stream

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            tools=[MagicMock()] # Dummy tool list to enable tool processing path
        )

        user_prompt = "prompt that triggers a tool"
        returned_text = dm.send_message(user_prompt, stream=True)

        # 1. Assert the returned text
        self.assertEqual(returned_text, final_text)

        # 2. Assert history
        # Expected history: [user_prompt, model_response_with_all_parts]
        self.assertEqual(len(dm.history), 2)
        
        user_history_entry = dm.history[0]
        self.assertEqual(user_history_entry["role"], "user")
        self.assertEqual(user_history_entry["parts"][0]["text"], user_prompt) # Assuming parts is a list of dicts

        model_history_entry = dm.history[1]
        self.assertEqual(model_history_entry["role"], "model")
        
        # Check parts of the model's response in history
        model_parts_in_history = model_history_entry["parts"]
        self.assertEqual(len(model_parts_in_history), 3)
        
        # Verify each part - using direct object comparison as MockPart objects are appended
        # The actual code appends the actual Part objects from the API response.
        # So, we should compare against the mock_fc, mock_fr, and a text part.
        # The current MockPart doesn't perfectly align with genai.types.Part for direct comparison.
        # Let's check attributes:
        self.assertEqual(model_parts_in_history[0].function_call.name, mock_fc.name)
        self.assertEqual(model_parts_in_history[0].function_call.args, mock_fc.args)
        
        self.assertEqual(model_parts_in_history[1].function_response.name, mock_fr.name)
        self.assertEqual(model_parts_in_history[1].function_response.response, mock_fr.response)

        self.assertEqual(model_parts_in_history[2].text, final_text)

    @patch('gemini_dm.genai.GenerativeModel')
    def test_function_call_handling_non_streaming(self, MockGenerativeModel):
        """Test handling of API-managed function call and response in non-streaming mode."""
        mock_model_instance = MockGenerativeModel.return_value

        mock_fc = Types.FunctionCall(name="search_tool", args={"query": "gemini api"})
        mock_fr_response_content = {"summary": "Gemini API is cool."}
        mock_fr = Types.FunctionResponse(name="search_tool", response=mock_fr_response_content)
        final_text = "The Gemini API is indeed cool."

        # Create a list of MockPart objects for the response
        response_parts = [
            MockPart(function_call=mock_fc),
            MockPart(function_response=mock_fr),
            MockPart(text=final_text)
        ]
        
        # Configure generate_content to return a MockNonStreamResponse
        # The MockNonStreamResponse calculates its .text attribute from parts.
        mock_response_obj = MockNonStreamResponse(parts_list=response_parts)
        self.assertEqual(mock_response_obj.text, final_text) # Verify mock helper
        
        mock_model_instance.generate_content.return_value = mock_response_obj

        dm = GeminiDialogueManager(
            api_key=self.api_key,
            gemini_model_name=self.model_name,
            tools=[MagicMock()] # Dummy tool list
        )

        user_prompt = "tell me about gemini api"
        returned_text = dm.send_message(user_prompt, stream=False)

        # 1. Assert the returned text
        self.assertEqual(returned_text, final_text)

        # 2. Assert history
        self.assertEqual(len(dm.history), 2)
        
        user_history_entry = dm.history[0]
        self.assertEqual(user_history_entry["role"], "user")
        # The parts in history are actual dictionaries from the code, not MockPart objects
        self.assertEqual(user_history_entry["parts"][0]["text"], user_prompt)

        model_history_entry = dm.history[1]
        self.assertEqual(model_history_entry["role"], "model")
        
        model_parts_in_history = model_history_entry["parts"] # These are actual Part objects
        self.assertEqual(len(model_parts_in_history), 3)

        self.assertEqual(model_parts_in_history[0].function_call.name, mock_fc.name)
        self.assertEqual(model_parts_in_history[0].function_call.args, mock_fc.args)
        
        self.assertEqual(model_parts_in_history[1].function_response.name, mock_fr.name)
        self.assertEqual(model_parts_in_history[1].function_response.response, mock_fr.response)

        self.assertEqual(model_parts_in_history[2].text, final_text)

if __name__ == '__main__':
    unittest.main()
