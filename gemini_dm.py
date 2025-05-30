import logging
import time # Added for retry logic
import random # Added for jitter in retry logic
import google.generativeai as genai
from google.generativeai import types # Required for tools if used

# RAG integration imports
from data_loader import load_game_data
from rag_manager import retrieve_context as retrieve_rag_context

# Initialize logging for the module
logger = logging.getLogger(__name__)

class GeminiDialogueManager:
    def __init__(self, api_key: str, gemini_model_name: str, tools: list = None, system_instruction_text: str = None, max_history_items: int = None, max_retries: int = 3, initial_backoff_seconds: float = 1.0):
        self.model = None
        self.history = []
        self.tools = tools
        self.system_instruction_text = system_instruction_text
        self.max_history_items = max_history_items
        self.max_retries = max_retries
        self.initial_backoff_seconds = initial_backoff_seconds
        
        logger.info(f"Initializing GeminiDialogueManager with model: {gemini_model_name}")
        if self.system_instruction_text:
            logger.info(f"System instruction provided: '{self.system_instruction_text[:100]}...'") # Log first 100 chars
        else:
            logger.info("No system instruction provided.")

        if self.max_history_items is not None:
            logger.info(f"Maximum history items set to: {self.max_history_items}")
        else:
            logger.info("No maximum history item limit set (history can grow indefinitely).")

        logger.info(f"Retry configuration: max_retries={self.max_retries}, initial_backoff_seconds={self.initial_backoff_seconds:.1f}s")

        try:
            genai.configure(api_key=api_key)
            logger.info("Google Generative AI configured successfully.")
        except Exception as e:
            logger.critical(f"Failed to configure Google Generative AI: {e}", exc_info=True)
            # Depending on how critical this is, you might want to raise an exception
            # or ensure the model is not initialized if configuration fails.
            return # Stop initialization if genai cannot be configured

        try:
            self.model = genai.GenerativeModel(
                gemini_model_name,
                tools=self.tools,
                system_instruction=self.system_instruction_text
            )
            if self.system_instruction_text:
                logger.info(f"GenerativeModel '{gemini_model_name}' initialized successfully with system instruction.")
            else:
                logger.info(f"GenerativeModel '{gemini_model_name}' initialized successfully without system instruction.")
        except Exception as e:
            logger.critical(f"Failed to initialize GenerativeModel '{gemini_model_name}' with system instruction: {e}", exc_info=True)
            # Raise an exception or handle this case appropriately
            # For instance, self.model will remain None, and send_message should check for this.

    def send_message(self, user_prompt_text: str, stream: bool = True) -> str:
        """
        Sends a message to the Gemini model, incorporating RAG context.

        Args:
            user_prompt_text: The raw input from the player.
            stream: Whether to stream the response from Gemini.

        Returns:
            The model's response as a string.
        """
        if not self.model:
            logger.error("Cannot send message: GenerativeModel is not initialized.")
            return "Error: Model not initialized."

        # 1. Load game data
        # Consider caching this if performance becomes an issue. For now, load per call.
        logger.debug("Loading game data for RAG...")
        game_data = load_game_data()
        # load_game_data will print warnings for file issues (e.g. malformed JSON)

        # 2. Retrieve RAG context
        logger.debug(f"Retrieving RAG context for input: '{user_prompt_text[:100]}...'")
        actual_rag_context = retrieve_rag_context(user_prompt_text, game_data)
        logger.info(f"Retrieved RAG context: '{actual_rag_context[:200]}...'") # Log first 200 chars of context

        # 3. Prepare the prompt with RAG context
        final_user_prompt_for_model = user_prompt_text # Start with the original prompt

        if actual_rag_context and actual_rag_context != "No specific context found for your input.":
            rag_section_prompt = f"Relevant Information (from game world data):\n{actual_rag_context}\n---"
            final_user_prompt_for_model = f"{rag_section_prompt}\nPlayer's original input: {user_prompt_text}"
            logger.info("Prepended RAG context to user prompt.")
        elif actual_rag_context == "No specific context found for your input.":
            # Optionally, inform the model that a search was done and nothing specific was found.
            no_context_prompt = "Relevant Information (from game world data):\nNo specific context found for your input after searching available data.\n---"
            final_user_prompt_for_model = f"{no_context_prompt}\nPlayer's original input: {user_prompt_text}"
            logger.info("Prepended 'no specific context found' RAG message to user prompt.")
        # If actual_rag_context is empty, the original user_prompt_text is used.

        # History Truncation Logic
        if self.max_history_items is not None and len(self.history) > self.max_history_items:
            items_to_remove = len(self.history) - self.max_history_items
            if items_to_remove > 0: 
                logger.info(f"History length ({len(self.history)}) exceeds max ({self.max_history_items}). Truncating {items_to_remove} oldest items.")
                self.history = self.history[items_to_remove:]
                logger.info(f"History length after truncation: {len(self.history)}")

        contents_for_request = list(self.history) # Start with a copy of the current (potentially truncated) history

        # Add current user prompt (now potentially enhanced with RAG context)
        contents_for_request.append({"role": "user", "parts": [{"text": final_user_prompt_for_model}]})
        logger.info(f"Sending final prompt to Gemini: {final_user_prompt_for_model[:300]}...") # Log first 300 chars

        final_full_response = ""
        final_model_response_parts_for_history = [] # Store parts for history

        for attempt in range(self.max_retries + 1): # Retries for API calls
            current_attempt_full_response = ""
            current_attempt_model_parts = []

            if attempt > 0:
                wait_seconds = self.initial_backoff_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.1 * wait_seconds) # Add up to 10% jitter
                wait_seconds += jitter
                logger.info(f"Retrying API call (attempt {attempt}/{self.max_retries}) after {wait_seconds:.2f} seconds...")
                time.sleep(wait_seconds)

            try:
                logger.debug(f"Calling generate_content (attempt {attempt + 1}/{self.max_retries + 1}). Stream={stream}. Tools configured: {self.tools is not None}")
                response_stream = self.model.generate_content(
                    contents_for_request,
                    stream=stream,
                    tools=self.tools
                )

                if stream:
                    logger.info("Streaming response from Gemini:")
                    for chunk in response_stream:
                        chunk_text_parts = []
                        if chunk.parts:
                            for part in chunk.parts:
                                current_attempt_model_parts.append(part)
                                if hasattr(part, 'text') and part.text:
                                    chunk_text_parts.append(part.text)
                                if hasattr(part, 'function_call') and part.function_call:
                                    logger.info(f"Gemini Function Call requested (stream part): {part.function_call.name} args: {part.function_call.args}")
                                if hasattr(part, 'function_response') and part.function_response:
                                    logger.info(f"Gemini Function Response received (stream part): {part.function_response.name}")
                        if chunk_text_parts:
                            text_segment = "".join(chunk_text_parts)
                            print(text_segment, end="", flush=True)
                            current_attempt_full_response += text_segment
                    print()
                    logger.info("Streaming complete.")
                else: # Non-streaming
                    logger.info("Generating non-streamed response from Gemini.")
                    if hasattr(response_stream, 'parts') and response_stream.parts:
                        current_attempt_model_parts = list(response_stream.parts)
                        for part in current_attempt_model_parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                logger.info(f"Gemini Function Call requested: {part.function_call.name} args: {part.function_call.args}")
                            if hasattr(part, 'function_response') and part.function_response:
                                logger.info(f"Gemini Function Response received: {part.function_response.name}")
                    else:
                        logger.warning("Non-streamed response has no 'parts'.")
                    
                    if hasattr(response_stream, 'text') and response_stream.text:
                        current_attempt_full_response = response_stream.text
                    else:
                        current_attempt_full_response = ''.join(p.text for p in current_attempt_model_parts if hasattr(p, 'text') and p.text)
                    # Ensure the full response is printed if not streaming
                    if not stream and current_attempt_full_response:
                        print(current_attempt_full_response)
                    logger.info("Non-streamed response received.")

                final_full_response = current_attempt_full_response
                final_model_response_parts_for_history = current_attempt_model_parts # Save parts for history
                logger.info(f"API call successful on attempt {attempt + 1}.")
                break # Exit loop on success

            except (types.BrokenResponseError, types.DeadlineExceededError, types.InternalServerError, types.ServiceUnavailableError) as e: # Retryable errors
                logger.warning(f"API call failed with {type(e).__name__} (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"Max retries reached for {type(e).__name__}. Giving up.")
                    final_full_response = f"Error: API call failed after {self.max_retries + 1} attempts due to {type(e).__name__}. ({e})"
                    final_model_response_parts_for_history = [{"text": final_full_response}]
                    break
            
            except types.StopCandidateException as e: # Not retryable, content blocked
                logger.error(f"Gemini API request was stopped due to content policy (not retryable): {e}", exc_info=False)
                final_full_response = f"Error: The request was blocked by the API due to content policy. ({e})"
                final_model_response_parts_for_history = [{"text": final_full_response}]
                if not stream: print(final_full_response)
                break

            except Exception as e: # General, potentially unexpected errors (treat as not retryable by default)
                logger.error(f"An unexpected error occurred during API call (attempt {attempt + 1}/{self.max_retries + 1}): {e}", exc_info=True)
                # For a more robust solution, one might inspect 'e' further to decide if retry is warranted.
                # For now, only specific, known transient errors are retried.
                final_full_response = f"Error: An unexpected error occurred. ({e})"
                final_model_response_parts_for_history = [{"text": final_full_response}]
                if not stream: print(final_full_response)
                break # Break after final attempt for general exceptions too

        # Update history using the final user prompt that was sent to the model
        # and the model's response parts (or error message).
        self.history.append({"role": "user", "parts": [{"text": final_user_prompt_for_model}]})

        if final_model_response_parts_for_history: # If we have parts from the model (success or error message formatted as parts)
            self.history.append({"role": "model", "parts": final_model_response_parts_for_history})
            # If it was a function call without immediate text, log that.
            if not final_full_response and any(hasattr(p, 'function_call') for p in final_model_response_parts_for_history):
                logger.info("Model response primarily contained function calls, no immediate text output.")
        # If final_model_response_parts_for_history is empty but final_full_response contains an error string
        # (e.g. from max retries exceeded before any successful part processing), ensure that error is in history.
        elif "Error:" in final_full_response and not final_model_response_parts_for_history:
            logger.info(f"Error occurred, and no model parts were captured. Adding error string to history: {final_full_response}")
            self.history.append({"role": "model", "parts": [{"text": final_full_response}]})
        else: # Fallback, if parts are empty and no error string, save whatever full response we have (could be empty)
            logger.warning("Model returned no specific parts and no specific error string. Appending current final_full_response to history.")
            self.history.append({"role": "model", "parts": [{"text": final_full_response if final_full_response else "[No text content in response]"}]})

        return final_full_response
