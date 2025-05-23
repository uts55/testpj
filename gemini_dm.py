import logging
import google.generativeai as genai
from google.generativeai import types # Required for tools if used

# Initialize logging for the module
logger = logging.getLogger(__name__)

class GeminiDialogueManager:
    def __init__(self, api_key: str, gemini_model_name: str, tools: list = None):
        self.model = None
        self.history = []
        self.tools = tools
        
        logger.info(f"Initializing GeminiDialogueManager with model: {gemini_model_name}")

        try:
            genai.configure(api_key=api_key)
            logger.info("Google Generative AI configured successfully.")
        except Exception as e:
            logger.critical(f"Failed to configure Google Generative AI: {e}", exc_info=True)
            # Depending on how critical this is, you might want to raise an exception
            # or ensure the model is not initialized if configuration fails.
            return # Stop initialization if genai cannot be configured

        try:
            self.model = genai.GenerativeModel(gemini_model_name)
            logger.info(f"GenerativeModel '{gemini_model_name}' initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize GenerativeModel '{gemini_model_name}': {e}", exc_info=True)
            # Raise an exception or handle this case appropriately
            # For instance, self.model will remain None, and send_message should check for this.

    def send_message(self, user_prompt_text: str, rag_context: str = None, stream: bool = True) -> str:
        if not self.model:
            logger.error("Cannot send message: GenerativeModel is not initialized.")
            return "Error: Model not initialized."

        contents_for_request = list(self.history) # Start with a copy of the current history

        # Add RAG context if provided
        if rag_context:
            rag_context_prompt = f"[참고 자료 (RAG 시스템 제공)]\n{rag_context}\n\n위 참고 자료를 바탕으로 답변해주세요."
            contents_for_request.append({"role": "user", "parts": [{"text": rag_context_prompt}]})
            logger.debug(f"Added RAG context to request: {rag_context_prompt}")

        # Add current user prompt
        contents_for_request.append({"role": "user", "parts": [{"text": user_prompt_text}]})
        logger.info(f"Sending user prompt to Gemini: {user_prompt_text}")

        full_response = ""
        try:
            logger.debug(f"Calling generate_content with stream={stream}. Tools configured: {self.tools is not None}")
            response_stream = self.model.generate_content(
                contents_for_request,
                stream=stream,
                tools=self.tools
            )

            if stream:
                logger.info("Streaming response from Gemini:")
                for chunk in response_stream:
                    chunk_text = ""
                    if chunk.parts:
                        # Ensure part.text exists before joining
                        chunk_text = ''.join(part.text for part in chunk.parts if hasattr(part, 'text'))
                    elif hasattr(chunk, 'text'): # Fallback if chunk directly has text (might not be typical for streaming parts)
                        chunk_text = chunk.text
                    
                    if chunk_text: # Only print and append if there's text
                        print(chunk_text, end="", flush=True)
                        full_response += chunk_text
                    # Log function calls if present (and if tools are configured)
                    if self.tools and chunk.function_calls:
                         logger.info(f"Gemini Function Call requested: {chunk.function_calls}")
                         # In a real scenario, you'd handle these. For now, just logging.
                print() # Newline after streaming is complete
                logger.info("Streaming complete.")
            else: # Non-streaming response (less likely path based on stream=True default)
                logger.info("Generating non-streamed response from Gemini.")
                # For non-streaming, the response object (response_stream here) is the complete response.
                # Accessing .text might depend on the exact structure of the response object
                # when stream=False. Typically, you'd access response.text or response.parts[0].text
                if response_stream.parts:
                    full_response = ''.join(part.text for part in response_stream.parts if hasattr(part, 'text'))
                elif hasattr(response_stream, 'text'): # A direct .text attribute
                    full_response = response_stream.text
                print(full_response) # Print the full response if not streaming
                logger.info("Non-streamed response received.")

        except types.StopCandidateException as e: # Specific exception for blocked prompts
            logger.error(f"Gemini API request was stopped: {e}", exc_info=True)
            full_response = f"Error: The request was blocked by the API. ({e})"
            print(full_response)
        except types.BrokenResponseError as e: # Specific exception for broken API responses
            logger.error(f"Gemini API response was broken or malformed: {e}", exc_info=True)
            full_response = f"Error: The API returned a broken response. ({e})"
            print(full_response)
        except Exception as e:
            logger.error(f"Error during Gemini API call or stream processing: {e}", exc_info=True)
            # It's good to provide some feedback even if the error is unexpected.
            full_response = f"An unexpected error occurred while communicating with the AI. ({e})"
            print(full_response) # Print error message to console as well

        # Update history
        # We add the user's raw prompt, not the one potentially augmented with RAG context here,
        # as the RAG context was a temporary addition for that specific call.
        # The model's response, however, was based on that augmented context.
        self.history.append({"role": "user", "parts": [{"text": user_prompt_text}]})
        if full_response: # Only add model response to history if it's not empty
            self.history.append({"role": "model", "parts": [{"text": full_response}]})
        else:
            logger.warning("Model returned an empty response. This will be reflected in history.")
            # Still add a model entry to keep roles balanced, or decide on a different strategy
            self.history.append({"role": "model", "parts": [{"text": ""}]})


        return full_response
