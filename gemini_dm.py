import logging
import time # Added for retry logic
import random # Added for jitter in retry logic
import google.generativeai as genai
from google.generativeai import types # Required for tools if used

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

    def send_message(self, user_prompt_text: str, rag_context: str = None, stream: bool = True) -> str:
        if not self.model:
            logger.error("Cannot send message: GenerativeModel is not initialized.")
            return "Error: Model not initialized."

        # History Truncation Logic
        if self.max_history_items is not None and len(self.history) > self.max_history_items:
            items_to_remove = len(self.history) - self.max_history_items
            # As per instructions, prioritize removing oldest items to meet the count, not necessarily pairs.
            if items_to_remove > 0: 
                logger.info(f"History length ({len(self.history)}) exceeds max ({self.max_history_items}). Truncating {items_to_remove} oldest items.")
                self.history = self.history[items_to_remove:]
                logger.info(f"History length after truncation: {len(self.history)}")

        contents_for_request = list(self.history) # Start with a copy of the current (potentially truncated) history

        # Add RAG context if provided
        if rag_context:
            rag_context_prompt = f"[참고 자료 (RAG 시스템 제공)]\n{rag_context}\n\n위 참고 자료를 바탕으로 답변해주세요."
            contents_for_request.append({"role": "user", "parts": [{"text": rag_context_prompt}]})
            logger.debug(f"Added RAG context to request: {rag_context_prompt}")

        # Add current user prompt
        contents_for_request.append({"role": "user", "parts": [{"text": user_prompt_text}]})
        logger.info(f"Sending user prompt to Gemini: {user_prompt_text}")

        final_full_response = ""
        final_model_response_parts_for_history = []

        for attempt in range(self.max_retries + 1):
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
                    print(current_attempt_full_response)
                    logger.info("Non-streamed response received.")

                final_full_response = current_attempt_full_response
                final_model_response_parts_for_history = current_attempt_model_parts
                logger.info(f"API call successful on attempt {attempt + 1}.")
                break # Exit loop on success

            except (types.BrokenResponseError, types.DeadlineExceededError) as e: # Retryable errors
                logger.warning(f"API call failed with {type(e).__name__} (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt == self.max_retries:
                    logger.error(f"Max retries reached for {type(e).__name__}. Giving up.")
                    final_full_response = f"Error: API call failed after {self.max_retries + 1} attempts due to {type(e).__name__}. ({e})"
                    final_model_response_parts_for_history = [{"text": final_full_response}] # Ensure history reflects the error
                    break # Break after final attempt
                # else: continue to next iteration for retry by letting the loop continue
            
            except types.StopCandidateException as e: # Not retryable
                logger.error(f"Gemini API request was stopped (not retryable): {e}", exc_info=False)
                final_full_response = f"Error: The request was blocked by the API. ({e})"
                final_model_response_parts_for_history = [{"text": final_full_response}]
                print(final_full_response) # Print error to console
                break # Do not retry

            except Exception as e: # General, potentially unexpected errors
                logger.error(f"An unexpected error occurred during API call (attempt {attempt + 1}/{self.max_retries + 1}): {e}", exc_info=True)
                if attempt == self.max_retries:
                    final_full_response = f"Error: An unexpected error occurred after {self.max_retries + 1} attempts. ({e})"
                    final_model_response_parts_for_history = [{"text": final_full_response}]
                    print(final_full_response) # Print error to console
                    break # Break after final attempt for general exceptions too
                # else: continue to next iteration for retry

        # Update history using the final state of response variables
        self.history.append({"role": "user", "parts": [{"text": user_prompt_text}]})

        if final_model_response_parts_for_history:
            self.history.append({"role": "model", "parts": final_model_response_parts_for_history})
            if not final_full_response and any(hasattr(p, 'function_call') for p in final_model_response_parts_for_history):
                logger.info("Model response contained function calls but no immediate text.")
        elif "Error:" in final_full_response:
            logger.info(f"Error occurred. Adding error message to history: {final_full_response}")
            self.history.append({"role": "model", "parts": [{"text": final_full_response}]})
        else:
            logger.warning("Model returned no parts and no specific error. Appending current final_full_response (which might be empty) to history.")
            self.history.append({"role": "model", "parts": [{"text": final_full_response if final_full_response else ""}]})

        return final_full_response
