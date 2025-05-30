import os
import logging
from gemini_dm import GeminiDialogueManager # Assuming gemini_dm.py contains GeminiDialogueManager

# Configure basic logging for the main application
# Adjust level to DEBUG for more verbose output from GeminiDialogueManager if needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Logger for main.py
gem_dm_logger = logging.getLogger('gemini_dm') # Specifically get the logger from gemini_dm
# Set gemini_dm logger level. If you want verbose logs from gemini_dm, set to logging.DEBUG
# For normal operation, logging.INFO or logging.WARNING might be preferred.
gem_dm_logger.setLevel(logging.INFO)

# --- Configuration ---
DEFAULT_MODEL_NAME = "gemini-1.5-flash-latest" # A common default model, adjust if needed
# More detailed system instruction
DEFAULT_SYSTEM_INSTRUCTION = (
    "You are an expert Dungeon Master for a fantasy text-based adventure game. "
    "Your primary role is to create an immersive and engaging narrative experience. "
    "Describe the environment, characters, and events in vivid detail. "
    "Respond to player actions realistically within the game world's logic. "
    "Introduce challenges, puzzles, and opportunities for role-playing. "
    "When 'Relevant Information' is provided below the player's input, you MUST use it "
    "to inform your response, making the game world consistent and dynamic. "
    "If no specific 'Relevant Information' is provided, rely on your general knowledge and the established game context. "
    "Maintain a consistent tone suitable for a fantasy adventure. "
    "Format your responses clearly for console display. Use paragraphs for descriptions "
    "and distinct lines for dialogue if NPCs are speaking."
)

def load_api_key():
    """
    Loads the Gemini API key from the environment variable 'GEMINI_API_KEY'.
    Logs critical error and informs the user if the key is not found.
    Returns:
        str: The API key if found, otherwise None.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.critical("GEMINI_API_KEY environment variable not found. This is mandatory.")
        print("\n==================== CRITICAL ERROR ====================")
        print("The GEMINI_API_KEY environment variable is not set.")
        print("This key is essential for the AI Dungeon Master to function.")
        print("Please set this environment variable and restart the game.")
        print("Example (bash/zsh): export GEMINI_API_KEY='your_actual_api_key_here'")
        print("Example (Windows CMD): set GEMINI_API_KEY=your_actual_api_key_here")
        print("Example (PowerShell): $env:GEMINI_API_KEY='your_actual_api_key_here'")
        print("========================================================")
        return None
    logger.info("GEMINI_API_KEY loaded successfully from environment variable.")
    return api_key

def main():
    """
    Main function to initialize and run the AI-powered text adventure game loop.
    """
    # Configure logging for this specific run
    run_log_level = os.environ.get("GAME_LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, run_log_level, logging.INFO)
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info(f"Starting the AI-Powered Text Adventure Game with log level {run_log_level}...")
    print("\n========================================")
    print(" Welcome to the AI-Powered Text Adventure!")
    print("========================================")
    print("You are about to embark on a journey crafted by an AI Dungeon Master.")
    print("Describe your actions, explore the world, and make choices that shape your story.")
    print("\nType 'quit' or 'exit' at any time to end your adventure.")
    print("Let's begin...\n")

    api_key = load_api_key()
    if not api_key:
        # load_api_key() already prints detailed user message and logs critical error
        return

    logger.info(f"Initializing GeminiDialogueManager with model: {DEFAULT_MODEL_NAME}")
    try:
        dm = GeminiDialogueManager(
            api_key=api_key,
            gemini_model_name=DEFAULT_MODEL_NAME,
            system_instruction_text=DEFAULT_SYSTEM_INSTRUCTION,
            max_history_items=20 # Keeps the last 10 pairs of user/model turns
        )
        logger.info("GeminiDialogueManager initialized successfully.")
    except Exception as e:
        logger.critical(f"Fatal error during GeminiDialogueManager initialization: {e}", exc_info=True)
        print(f"\nError: Could not initialize the AI Dungeon Master. A critical error occurred: {e}")
        print("Please ensure your API key is correct, the model name is valid, and there are no network issues.")
        print("Check the logs for more detailed information. The game cannot continue.")
        return

    try:
        while True:
            player_input = input("\nWhat do you do? > ").strip()

            if player_input.lower() in ["quit", "exit"]:
                logger.info("Player initiated 'quit' command.")
                print("\nThank you for playing! Adventure awaits another time. Goodbye.")
                break

            if not player_input:
                print("It seems you're lost in thought... Please type an action to continue your adventure.")
                continue

            logger.info(f"Player input received: '{player_input}'")

            print("\nThe AI Dungeon Master is pondering your action...")

            dm_response_full = dm.send_message(player_input, stream=True)

            logger.debug(f"DM full response string from send_message (main.py): '{dm_response_full[:300]}...'")

            # Critical error checks from DM response. send_message itself might log these too.
            if dm_response_full.startswith("Error: Model not initialized.") or \
               dm_response_full.startswith("Error: The request was blocked by the API"):
                logger.critical(f"Critical error received from GeminiDialogueManager: {dm_response_full}. Terminating game loop.")
                print(f"\nA critical error occurred with the AI DM: {dm_response_full}")
                print("This usually indicates a problem with the API configuration or service. The game cannot continue.")
                break
            elif "Error:" in dm_response_full and "API call failed after" in dm_response_full : # check for max retries error
                logger.critical(f"Persistent API call failure: {dm_response_full}. Terminating game loop.")
                print(f"\nThere was a persistent problem communicating with the AI DM: {dm_response_full}")
                print("Please check your network connection and API key status. The game cannot continue.")
                break


    except KeyboardInterrupt:
        logger.info("Game loop interrupted by user (Ctrl+C).")
        print("\n\nYour adventure has been paused by your command! Thank you for playing. Goodbye.")
    except Exception as e:
        logger.error(f"An unexpected critical error occurred in the main gameplay loop: {e}", exc_info=True)
        print(f"\nAn unexpected critical error occurred: {e}. The adventure must unfortunately end. Please check the logs for details.")
    finally:
        logger.info("Game session ended. Performing cleanup if any.")
        print("\nGame session concluded. Until next time, adventurer!")

if __name__ == "__main__":
    main()
