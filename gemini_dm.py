import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()


class GeminiDM:
    """
    Dungeon Master powered by Google's Gemini AI.
    Handles conversation with the AI model for game narration and responses.
    """
    
    def __init__(self, model_name="gemini-1.5-flash-latest"):
        """
        Initialize the GeminiDM with API key validation and model setup.
        
        Args:
            model_name: The Gemini model to use (default: gemini-1.5-flash-latest)
            
        Raises:
            ValueError: If GOOGLE_API_KEY is not found in environment variables
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.chat = self.model.start_chat(history=[])
            print(f"GeminiDM initialized successfully with model: {model_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GeminiDM: {e}")
    
    def send_message(self, message, stream=False):
        """
        Send a message to the Gemini AI and get a response.
        
        Args:
            message: The message to send to the AI
            stream: If True, stream the response chunk by chunk
            
        Returns:
            The AI's response as a string
        """
        try:
            response = self.chat.send_message(message, stream=stream)
            
            if stream:
                # Stream the response chunk by chunk
                full_response = ""
                for chunk in response:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
                print()  # New line after streaming completes
                return full_response
            else:
                # Return the complete response
                return response.text
                
        except Exception as e:
            error_message = f"Error communicating with Gemini AI: {e}"
            print(error_message)
            return error_message


def notify_dm(message: str) -> None:
    """
    Sends a notification to the Dungeon Master.
    For now, it just prints the message to the console.
    """
    print(f"DM NOTIFICATION: {message}")


if __name__ == '__main__':
    # Example usage:
    notify_dm("Player Valerius has entered the Whispering Woods.")
    notify_dm("A goblin ambush is imminent!")
    
    # Test GeminiDM class
    try:
        dm = GeminiDM()
        response = dm.send_message("Hello, I'm starting a new D&D adventure. Can you help me?")
        print(f"DM Response: {response}")
    except Exception as e:
        print(f"Error testing GeminiDM: {e}")
