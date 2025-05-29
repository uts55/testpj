# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
# traceback removed
import re # 정규 표현식 사용 (문장 분할 등)
import logging
import os # Added for checking file existence
# import json # No longer needed directly here, handled by data_loader
import tkinter as tk
import threading # Added for threading
from ui import Application

# Import project modules
import config # Global configuration constants
from data_loader import load_documents, filter_documents, extract_text_for_rag, split_text_into_chunks
from rag_manager import RAGManager
from gemini_dm import GeminiDialogueManager
from game_state import GameState, Player, NPC, Location, Item # Added for game state management

# --- Logging Configuration ---
# Basic config should be set up early, but specific logger instance for this file.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SAVE_GAME_FILENAME = "save_game.json"
MAIN_PLAYER_ID = "player_001"
DEFAULT_START_LOCATION_ID = "default_start_location"

# Global variable for the UI application instance
app_ui = None
game_state_manager = None # To hold the GameState instance
dialogue_manager = None # To hold the GeminiDialogueManager instance
rag_system_manager = None # To hold the RAGManager instance
root_tk_window = None # To hold the main Tkinter window instance


def handle_save_game():
    global game_state_manager, app_ui, SAVE_GAME_FILENAME
    if not game_state_manager:
        logger.warning("Save game called but game_state_manager is not initialized.")
        if app_ui:
            app_ui.add_narration("Error: Could not save game (GameState not ready).\n")
        return
    try:
        game_state_manager.save_game(SAVE_GAME_FILENAME)
        logger.info("Game saved via UI button.")
        if app_ui:
            app_ui.add_narration("Game Saved.\n")
    except Exception as e:
        logger.error(f"Error saving game: {e}", exc_info=True)
        if app_ui:
            app_ui.add_narration(f"Error: Could not save game. {type(e).__name__}\n")

def handle_load_game():
    global game_state_manager, app_ui, SAVE_GAME_FILENAME
    if not game_state_manager:
        logger.warning("Load game called but game_state_manager is not initialized.")
        if app_ui:
            app_ui.add_narration("Error: Could not load game (GameState not ready).\n")
        return
    try:
        game_state_manager.load_game(SAVE_GAME_FILENAME) # This method logs its own status
        update_ui_game_state() # Refresh UI based on loaded state
        logger.info("Game loaded via UI button.")
        if app_ui:
            app_ui.add_narration("Game Loaded. Narrative might be out of sync; continue your adventure!\n")
    except Exception as e:
        logger.error(f"Error loading game: {e}", exc_info=True)
        if app_ui:
            app_ui.add_narration(f"Error: Could not load game. {type(e).__name__}\n")

def handle_exit_game():
    global game_state_manager, app_ui, root_tk_window, SAVE_GAME_FILENAME
    logger.info("Exit game called via UI button.")
    if game_state_manager:
        game_state_manager.save_game(SAVE_GAME_FILENAME)
        logger.info("Game saved on exit.")
    if app_ui:
        app_ui.add_narration("Exiting game...\n")
    if root_tk_window:
        root_tk_window.destroy() # Close the Tkinter window
    else:
        logger.warning("Root Tkinter window not found for destruction.")


def update_ui_game_state():
    """Fetches current game state and updates all UI labels."""
    global app_ui, game_state_manager, MAIN_PLAYER_ID
    if not app_ui or not game_state_manager:
        logger.warning("Cannot update UI: app_ui or game_state_manager not initialized.")
        return

    player = game_state_manager.get_player(MAIN_PLAYER_ID)
    if player:
        # HP
        app_ui.update_hp(player.stats.get('hp', 'N/A'))

        # Location
        loc_name = "Unknown"
        location_obj = game_state_manager.locations.get(player.current_location)
        if location_obj:
            loc_name = location_obj.name
        app_ui.update_location(loc_name)

        # Inventory
        inventory_item_names = []
        if player.inventory:
            for item_id in player.inventory:
                item_obj = game_state_manager.items.get(item_id)
                inventory_item_names.append(item_obj.name if item_obj else item_id)
        inventory_str = ", ".join(inventory_item_names) if inventory_item_names else "Empty"
        app_ui.update_inventory(inventory_str)
        
        # NPCs
        npcs_in_loc_objs = game_state_manager.get_npcs_in_location(player.current_location)
        npc_names_list = [npc.name for npc in npcs_in_loc_objs] if npcs_in_loc_objs else []
        npcs_str = ", ".join(npc_names_list) if npc_names_list else "None"
        app_ui.update_npcs(npcs_str)
    else:
        logger.warning(f"Player {MAIN_PLAYER_ID} not found for UI update.")
        app_ui.update_hp("N/A")
        app_ui.update_location("Unknown")
        app_ui.update_inventory("N/A")
        app_ui.update_npcs("N/A")


def threaded_api_call_and_ui_updates(player_input_text):
    """
    This function runs in a separate thread to handle blocking API calls 
    and then schedules UI updates back in the main thread.
    """
    global app_ui, game_state_manager, dialogue_manager, rag_system_manager, root_tk_window, MAIN_PLAYER_ID

    player_for_action = game_state_manager.get_player(MAIN_PLAYER_ID) if game_state_manager else None
    # dm_response_text variable is not needed here as it's fully handled within the try-except for API call

    try:
        # --- Generate Current State Summary for Gemini ---
        # This part remains as it's prep for the API call.
        current_state_summary_for_dm = ""
        if player_for_action:
            player_hp = player_for_action.stats.get('hp', 'N/A')
            location_obj = game_state_manager.locations.get(player_for_action.current_location)
            location_name = location_obj.name if location_obj else player_for_action.current_location
            inventory_item_names = [game_state_manager.items.get(item_id).name if game_state_manager.items.get(item_id) else item_id for item_id in player_for_action.inventory]
            inventory_str = ", ".join(inventory_item_names) if inventory_item_names else 'Empty'
            npcs_in_loc_objs = game_state_manager.get_npcs_in_location(player_for_action.current_location)
            npc_names = [npc.name for npc in npcs_in_loc_objs] if npcs_in_loc_objs else ["None"]
            current_state_summary_for_dm = (
                f"[Current Game State for DM Context]\n"
                f"Player: {player_for_action.name} (HP: {player_hp})\n"
                f"Location: {location_name}\n"
                f"NPCs here: {', '.join(npc_names)}\n"
                f"Inventory: {inventory_str}\n"
            )
        prompt_for_gemini = f"{current_state_summary_for_dm}\nPlayer's Action: {player_input_text}"

        # --- RAG Context Retrieval ---
        rag_context_for_gemini = None
        if rag_system_manager and rag_system_manager.collection and rag_system_manager.collection.count() > 0:
            logger.info("\n[RAG] Searching for relevant context based on input...")
            # RAG search itself could also fail
            retrieved_context_docs = rag_system_manager.search(player_input_text, n_results=3)
            if retrieved_context_docs:
                logger.info(f"[RAG] Found {len(retrieved_context_docs)} context snippets.")
                rag_context_for_gemini = "\n".join([f"- {doc}" for doc in retrieved_context_docs])
            else:
                logger.info("[RAG] No additional relevant context found.")
        
        # --- Send to Gemini (DM) ---
        dm_response_text = "Error: DM is not connected or failed to respond." # Default if DM not available
        if dialogue_manager:
            logger.info("\nDM's Turn (Sending to Gemini in thread):")
            dm_response_text = dialogue_manager.send_message(
                user_prompt_text=prompt_for_gemini,
                rag_context=rag_context_for_gemini
            ) # This call is blocking and might raise exceptions.
        else:
            logger.warning("Dialogue Manager not available to process input.")
            # dm_response_text is already set to an error message.

        # --- Schedule DM response narration in main thread ---
        if app_ui and root_tk_window: # Ensure root_tk_window is available
            root_tk_window.after(0, lambda: app_ui.add_narration(f"{dm_response_text}\n"))

        # --- Basic Gemini Response Parsing and State Update (Scheduled) ---
        if player_for_action and dm_response_text: # Check dm_response_text is not None or empty
            if "you take 5 damage" in dm_response_text.lower(): # Example parsing
                logger.info("DM response indicates player takes 5 damage. Updating state.")
                player_for_action.take_damage(5) 
                game_state_manager.apply_event({'type': 'damage', 'target': MAIN_PLAYER_ID, 'amount': 5, 'source': 'gemini_response'})
                if app_ui and root_tk_window:
                    root_tk_window.after(0, lambda: app_ui.add_narration("You feel weaker as you take damage.\n"))
        
        # This specific check might be redundant if send_message itself raises an error handled by the outer try-except
        if "Error:" in dm_response_text and dialogue_manager and dialogue_manager.model is None:
             logger.error(f"DM response indicates model error. Response: {dm_response_text}")

    except Exception as e: # Catch exceptions from RAG, Gemini call, or other logic within the try.
        logger.error(f"Error in threaded_api_call_and_ui_updates: {e}", exc_info=True)
        ui_error_message = f"An error occurred: {type(e).__name__}. Please check logs or try again."
        if app_ui and root_tk_window:
            root_tk_window.after(0, lambda: app_ui.add_narration(ui_error_message + "\n"))
    finally:
        # --- Schedule UI updates and re-enable input in main thread ---
        if app_ui and root_tk_window:
            root_tk_window.after(0, update_ui_game_state) # Update all game state labels
            root_tk_window.after(0, lambda: app_ui.input_entry.config(state='normal'))
            root_tk_window.after(0, lambda: app_ui.send_button.config(state='normal'))
            logger.info("Input field and send button re-enabled.")


def process_player_input(player_input_text):
    """
    Processes the player's input text from the UI.
    Disables input, starts a thread for blocking calls, and re-enables input via the thread.
    """
    global app_ui, game_state_manager # Removed dialogue_manager, rag_system_manager as they are used in thread
    logger.info(f"UI Input Received for processing: {player_input_text}")

    # --- Handle truly local commands first (synchronously) ---
    # Example: if player_input_text.lower() == "/help":
    # if app_ui: app_ui.add_narration("Help: Type your actions...\n")
    # return 
    # Note: "save" and "exit" are handled by buttons now. USER_EXIT_COMMANDS might still be typed.
    if player_input_text.lower() in config.USER_EXIT_COMMANDS:
        handle_exit_game() # Use the existing exit handler
        return

    # --- Disable UI elements and start thread for Gemini call and other processing ---
    if app_ui:
        app_ui.input_entry.config(state='disabled')
        app_ui.send_button.config(state='disabled')
        logger.info("Input field and send button disabled.")

    # --- Local Action Processing (e.g., 'go', 'take') ---
    # These can modify game_state_manager directly before the thread starts or can be moved into the thread.
    # If moved into the thread, then current_state_summary_for_dm will reflect the state *before* these local actions.
    # If processed here, the summary reflects the state *after* these local actions.
    # Let's keep them here for now, as they modify state that the DM should be aware of immediately.
    player_for_action = game_state_manager.get_player(MAIN_PLAYER_ID) if game_state_manager else None
    if player_for_action:
        if player_input_text.lower().startswith("go "):
            direction = player_input_text.lower().split(" ", 1)[1]
            if player_for_action.current_location:
                current_loc_obj = game_state_manager.locations.get(player_for_action.current_location)
                if current_loc_obj and direction in current_loc_obj.exits:
                    new_location_id = current_loc_obj.exits[direction]
                    player_for_action.change_location(new_location_id) # State changed here
                    if app_ui:
                        new_loc_obj_name = game_state_manager.locations.get(new_location_id).name if game_state_manager.locations.get(new_location_id) else "an unknown place"
                        app_ui.add_narration(f"You move {direction} to {new_loc_obj_name}.\n") # Immediate feedback
                else:
                    if app_ui: app_ui.add_narration(f"You cannot go {direction} from here.\n")
        
        elif "take sword" in player_input_text.lower(): # Example command
            SWORD_ID = "sword_001" 
            if SWORD_ID not in game_state_manager.items:
                game_state_manager.items[SWORD_ID] = Item(id=SWORD_ID, name="Basic Sword", description="A simple steel sword.")
            if SWORD_ID not in player_for_action.inventory:
                player_for_action.add_item_to_inventory(SWORD_ID) # State changed here
                if app_ui: app_ui.add_narration(f"You take the {game_state_manager.items[SWORD_ID].name}.\n") # Immediate feedback
            else:
                if app_ui: app_ui.add_narration(f"You already have the {game_state_manager.items[SWORD_ID].name}.\n")
        
        # Since local actions might have changed the state, update UI labels here synchronously for these changes.
        # The subsequent DM call will then provide further narrative and potential further state changes.
        update_ui_game_state() 


    thread = threading.Thread(target=threaded_api_call_and_ui_updates, args=(player_input_text,))
    thread.start()


if __name__ == "__main__":
    # --- Environment and API Key Setup ---
    load_dotenv()
    api_key = os.getenv(config.GOOGLE_API_KEY_ENV)
    if not api_key:
        logger.critical(f"Error: {config.GOOGLE_API_KEY_ENV} environment variable not found.")
        # No UI yet to display this, so console critical and exit is appropriate
        exit()
    logger.info("API key loaded successfully.")

    # --- Initialize Managers (RAG, Gemini, GameState) ---
    # These are now assigned to global variables after initialization
    try:
        rag_system_manager = RAGManager(
            embedding_model_name=config.EMBEDDING_MODEL_NAME,
            vector_db_path=config.VECTOR_DB_PATH,
            collection_name=config.COLLECTION_NAME
        )
        if not rag_system_manager.collection:
             logger.critical("RAG Manager's collection not initialized. Exiting.")
             exit()
        logger.info("RAG Manager initialized.")

        # Document Loading for RAG (same as before, but uses rag_system_manager)
        all_documents = load_documents(config.RAG_DOCUMENT_SOURCES)
        processed_documents = filter_documents(all_documents, config.RAG_DOCUMENT_FILTERS) if config.RAG_DOCUMENT_FILTERS else all_documents
        text_chunks, document_ids, document_metadatas = [], [], []
        for i, doc in enumerate(processed_documents):
            extracted_text = extract_text_for_rag(doc, config.RAG_TEXT_FIELDS)
            if extracted_text:
                chunks_from_doc = split_text_into_chunks(extracted_text)
                doc_id_base = doc.get('id', f'doc_{i}')
                for chunk_idx, chunk_content in enumerate(chunks_from_doc):
                    text_chunks.append(chunk_content)
                    document_ids.append(f"{doc_id_base}_chunk_{chunk_idx}")
                    document_metadatas.append({'source_id': doc.get('id', 'unknown'), 'name': doc.get('name', 'Unnamed Document')})
        if text_chunks:
            rag_system_manager.add_documents_to_collection(text_chunks, document_ids, document_metadatas)
            logger.info(f"Total {len(text_chunks)} text chunks added to RAG system.")
        else:
            logger.warning("No text chunks available to add to RAG system.")
        logger.info("RAG Document Loading and Processing Finished.")

    except Exception as e:
        logger.critical(f"Failed to initialize or populate RAGManager: {e}", exc_info=True)
        exit()

    try:
        tools_list_for_gemini = [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] if 'GoogleSearchRetrieval' in dir(types) else None
        dm_system_instruction = "You are a Dungeon Master for a D&D 5e game..." # Keep it concise for this example
        dialogue_manager = GeminiDialogueManager(
            api_key=api_key,
            gemini_model_name=config.GEMINI_MODEL_NAME,
            tools=tools_list_for_gemini,
            system_instruction_text=dm_system_instruction,
            max_history_items=config.MAX_HISTORY_ITEMS
        )
        if not dialogue_manager.model:
            logger.critical("Gemini Dialogue Manager's model not initialized. Exiting.")
            exit()
        logger.info("Gemini Dialogue Manager initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize GeminiDialogueManager: {e}", exc_info=True)
        exit()

    game_state_manager = GameState()
    game_state_manager.load_game(SAVE_GAME_FILENAME) # Logs its own status
    if not game_state_manager.get_player(MAIN_PLAYER_ID):
        logger.info("No valid saved game for main player. Starting new game setup...")
        game_state_manager.initialize_new_game(MAIN_PLAYER_ID, "Adventurer", DEFAULT_START_LOCATION_ID)
    logger.info("Game state manager ready.")

    # --- Tkinter UI Setup ---
    root_tk_window = tk.Tk() # Assign to global
    app_ui = Application(
        master=root_tk_window, 
        process_input_callback=process_player_input,
        save_game_callback=handle_save_game,
        load_game_callback=handle_load_game,
        exit_callback=handle_exit_game
    )
    app_ui.pack(fill=tk.BOTH, expand=True) # Ensure Application frame itself fills the root window.
    
    # --- Initial DM Greeting and UI Update ---
    logger.info("\n--- Sending Initial Prompt to DM ---")
    initial_dm_response = "Welcome to your adventure!" # Default if API call fails
    try:
        # The send_message in dialogue_manager has been updated to return the full text
        # and it no longer prints directly to console by default.
        initial_dm_response = dialogue_manager.send_message(config.INITIAL_PROMPT_TEXT)
        if "Error:" in initial_dm_response and dialogue_manager.model is None:
             logger.critical(f"Initial message failed: Gemini model not available. Response: {initial_dm_response}")
             # Potentially update UI with error here
        elif not initial_dm_response and not dialogue_manager.history:
            logger.critical("Initial response empty & history not initiated. API/model issue.")
            # Potentially update UI with error here
    except Exception as e:
        logger.critical(f"Critical error during initial message to Gemini: {e}", exc_info=True)
        initial_dm_response = f"Error connecting to the DM: {e}" # Show error in UI

    app_ui.add_narration(initial_dm_response + "\n")

    # Update UI with initial game state using the new helper function
    update_ui_game_state()

    logger.info("\n--- Adventure Begins! Interact with the UI. ---")
    root_tk_window.mainloop() # Use the global variable

    logger.info("--- Tkinter mainloop ended. Application shutting down. ---")
    # Perform any final cleanup or saving if necessary, though saving is also tied to exit command.
    if game_state_manager: # Ensure it was initialized
        game_state_manager.save_game(SAVE_GAME_FILENAME)
        logger.info("Final game save attempt on shutdown.")

# --- END OF FILE main.py ---