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
from tkinter import messagebox # Added for load game popups
import threading # Added for threading
from ui import GamePlayFrame
from ui.main_menu_frame import MainMenuFrame
from ui.settings_frame import SettingsFrame

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

# SAVE_GAME_FILENAME = "save_game.json" # Moved to config.py
MAIN_PLAYER_ID = "player_001"
DEFAULT_START_LOCATION_ID = "default_start_location"

# Global variables for UI frames and managers
# app_ui is now game_play_frame
game_play_frame = None # Will hold the GamePlayFrame instance
main_menu_frame = None
settings_frame = None
current_frame = None # To keep track of the currently visible frame

game_state_manager = None # To hold the GameState instance
dialogue_manager = None # To hold the GeminiDialogueManager instance
rag_system_manager = None # To hold the RAGManager instance
root_tk_window = None # To hold the main Tkinter window instance


# --- Frame Management ---
def show_frame(frame_instance):
    global current_frame
    if current_frame:
        current_frame.pack_forget() # Or grid_forget() if using grid
    current_frame = frame_instance
    current_frame.pack(fill=tk.BOTH, expand=True) # Or grid()

# --- Game Flow Functions ---
def start_new_game():
    global game_state_manager, dialogue_manager, game_play_frame, root_tk_window, MAIN_PLAYER_ID, DEFAULT_START_LOCATION_ID
    logger.info("Starting a new game...")

    if game_state_manager:
        game_state_manager.initialize_new_game(MAIN_PLAYER_ID, "Adventurer", DEFAULT_START_LOCATION_ID)
    else:
        logger.error("GameStateManager not initialized. Cannot start new game.")
        # Optionally, inform the user via a dialog or main menu message update
        return

    if dialogue_manager:
        dialogue_manager.history = [] # Clear history for a new game
        logger.info("Dialogue history cleared.")
    else:
        logger.error("DialogueManager not initialized. Cannot clear history.")
        # This is problematic for game consistency.

    # Instantiate or re-initialize GamePlayFrame
    # For simplicity, destroying and recreating if it exists.
    if game_play_frame:
        game_play_frame.destroy() 
        logger.info("Previous GamePlayFrame instance destroyed.")

    game_play_frame = GamePlayFrame(
        master=root_tk_window,
        process_input_callback=process_player_input,
        save_game_callback=handle_save_game,
        load_game_callback=handle_load_game, # This callback might need adjustment if called from gameplay
        exit_callback=handle_exit_game_via_game_play_ui
    )
    logger.info("New GamePlayFrame instance created.")
    
    show_frame(game_play_frame)
    logger.info("Switched to GamePlayFrame.")

    # Send initial prompt to DM
    initial_dm_response = "Welcome to your new adventure!" # Default
    try:
        if dialogue_manager:
            initial_dm_response = dialogue_manager.send_message(config.INITIAL_PROMPT_TEXT)
            if not initial_dm_response: # Handle empty response case
                 initial_dm_response = "The adventure begins in silence... (DM sent an empty opening)"
                 logger.warning("Initial DM response was empty.")
        else:
            logger.error("Dialogue manager not available for initial prompt.")
            initial_dm_response = "Error: Dialogue Manager not available. Cannot start the game."
    except Exception as e:
        logger.error(f"Error sending initial prompt: {e}", exc_info=True)
        initial_dm_response = f"Error: Could not get initial message from DM. {type(e).__name__}"

    if game_play_frame:
        game_play_frame.add_narration(initial_dm_response + "\n")
    
    update_ui_game_state() # Update HP, location, etc.
    logger.info("Initial game state UI updated.")

def load_existing_game():
    global game_state_manager, dialogue_manager, game_play_frame, root_tk_window, MAIN_PLAYER_ID # SAVE_GAME_FILENAME removed from globals
    logger.info("Attempting to load an existing game...")

    if not game_state_manager:
        logger.error("GameStateManager not initialized. Cannot load game.")
        messagebox.showerror("Load Game Error", "GameStateManager not ready. Cannot load game.")
        return

    # Attempt to load the game. load_game logs its own errors/status.
    game_state_manager.load_game(config.SAVE_GAME_FILENAME) # Use config.SAVE_GAME_FILENAME

    # Check if loading was successful by verifying player data
    if game_state_manager.get_player(MAIN_PLAYER_ID):
        logger.info(f"Player {MAIN_PLAYER_ID} found in loaded game state. Load successful.")
        messagebox.showinfo("Load Game", "Game loaded successfully!")

        if dialogue_manager:
            dialogue_manager.history = [] # Clear history for the loaded game session
            logger.info("Dialogue history cleared for loaded game.")
        else:
            logger.error("DialogueManager not initialized. Cannot clear history for loaded game.")
            # This could be a non-critical issue if history isn't strictly needed immediately

        if game_play_frame:
            game_play_frame.destroy()
            logger.info("Previous GamePlayFrame instance destroyed.")

        game_play_frame = GamePlayFrame(
            master=root_tk_window,
            process_input_callback=process_player_input,
            save_game_callback=handle_save_game,
            load_game_callback=handle_load_game, # This is the in-game load button
            exit_callback=handle_exit_game_via_game_play_ui
        )
        logger.info("New GamePlayFrame instance created for loaded game.")
        
        show_frame(game_play_frame)
        logger.info("Switched to GamePlayFrame for loaded game.")
        
        update_ui_game_state() # Refresh GamePlayFrame with loaded data
        
        if game_play_frame:
            game_play_frame.add_narration("Game loaded. Continue your adventure!\n")
        logger.info("GamePlayFrame updated and narration added for loaded game.")

    else:
        logger.warning(f"Failed to load game or player {MAIN_PLAYER_ID} not found after load attempt.")
        messagebox.showerror("Load Game", "Failed to load game. File not found or corrupted.")
        # Remain on MainMenuFrame


# --- Callback Functions for UI interactions ---
def handle_save_game():
    global game_state_manager, game_play_frame # SAVE_GAME_FILENAME removed from globals
    if not game_state_manager:
        logger.warning("Save game called but game_state_manager is not initialized.")
        if game_play_frame:
            game_play_frame.add_narration("Error: Could not save game (GameState not ready).\n")
        return
    try:
        game_state_manager.save_game(config.SAVE_GAME_FILENAME) # Use config.SAVE_GAME_FILENAME
        logger.info("Game saved via UI button.")
        if game_play_frame:
            game_play_frame.add_narration("Game Saved.\n")
    except Exception as e:
        logger.error(f"Error saving game: {e}", exc_info=True)
        if game_play_frame:
            game_play_frame.add_narration(f"Error: Could not save game. {type(e).__name__}\n")

def handle_load_game(): # This is the in-game load game button callback
    global game_state_manager, game_play_frame # SAVE_GAME_FILENAME removed from globals
    if not game_state_manager:
        logger.warning("Load game called but game_state_manager is not initialized.")
        if game_play_frame: 
            game_play_frame.add_narration("Error: Could not load game (GameState not ready).\n")
        return
    try:
        game_state_manager.load_game(config.SAVE_GAME_FILENAME) # Use config.SAVE_GAME_FILENAME
        # If game_play_frame exists and is the current view, update it.
        if game_play_frame and current_frame == game_play_frame:
             update_ui_game_state() 
        logger.info("Game loaded via UI button.")
        if game_play_frame: 
            game_play_frame.add_narration("Game Loaded from in-game button. Narrative might be out of sync.\n")
    except Exception as e:
        logger.error(f"Error loading game from in-game button: {e}", exc_info=True)
        if game_play_frame: 
            game_play_frame.add_narration(f"Error: Could not load game. {type(e).__name__}\n")


def handle_exit_game_via_game_play_ui(): 
    global game_state_manager, game_play_frame, root_tk_window # SAVE_GAME_FILENAME removed from globals
    logger.info("Exit game called via GamePlay UI button.")
    if game_state_manager:
        game_state_manager.save_game(config.SAVE_GAME_FILENAME) # Use config.SAVE_GAME_FILENAME
        logger.info("Game saved on exit from game play.")
    if game_play_frame:
        game_play_frame.add_narration("Exiting game...\n") 
    if root_tk_window:
        root_tk_window.destroy() # Close the Tkinter window
    else:
        logger.warning("Root Tkinter window not found for destruction during exit from game play UI.")


def update_ui_game_state():
    """Fetches current game state and updates all UI labels for GamePlayFrame."""
    global game_play_frame, game_state_manager, MAIN_PLAYER_ID # app_ui changed to game_play_frame
    if not game_play_frame or not game_state_manager:
        logger.warning("Cannot update UI: game_play_frame or game_state_manager not initialized.")
        return

    player = game_state_manager.get_player(MAIN_PLAYER_ID)
    if player:
        # HP
        game_play_frame.update_hp(player.stats.get('hp', 'N/A'))

        # Location
        loc_name = "Unknown"
        location_obj = game_state_manager.locations.get(player.current_location)
        if location_obj:
            loc_name = location_obj.name
        game_play_frame.update_location(loc_name)

        # Inventory
        inventory_item_names = []
        if player.inventory:
            for item_id in player.inventory:
                item_obj = game_state_manager.items.get(item_id)
                inventory_item_names.append(item_obj.name if item_obj else item_id)
        inventory_str = ", ".join(inventory_item_names) if inventory_item_names else "Empty"
        game_play_frame.update_inventory(inventory_str)
        
        # NPCs
        npcs_in_loc_objs = game_state_manager.get_npcs_in_location(player.current_location)
        npc_names_list = [npc.name for npc in npcs_in_loc_objs] if npcs_in_loc_objs else []
        npcs_str = ", ".join(npc_names_list) if npc_names_list else "None"
        game_play_frame.update_npcs(npcs_str)
    else:
        logger.warning(f"Player {MAIN_PLAYER_ID} not found for UI update.")
        game_play_frame.update_hp("N/A")
        game_play_frame.update_location("Unknown")
        game_play_frame.update_inventory("N/A")
        game_play_frame.update_npcs("N/A")


def threaded_api_call_and_ui_updates(player_input_text):
    """
    This function runs in a separate thread to handle blocking API calls 
    and then schedules UI updates back in the main thread.
    """
    global game_play_frame, game_state_manager, dialogue_manager, rag_system_manager, root_tk_window, MAIN_PLAYER_ID # app_ui changed to game_play_frame

    player_for_action = game_state_manager.get_player(MAIN_PLAYER_ID) if game_state_manager else None
    # dm_response_text variable is not needed here as it's fully handled within the try-except for API call

    try:
        # --- Generate Current State Summary for Gemini ---
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
            retrieved_context_docs = rag_system_manager.search(player_input_text, n_results=3)
            if retrieved_context_docs:
                logger.info(f"[RAG] Found {len(retrieved_context_docs)} context snippets.")
                rag_context_for_gemini = "\n".join([f"- {doc}" for doc in retrieved_context_docs])
            else:
                logger.info("[RAG] No additional relevant context found.")
        
        # --- Send to Gemini (DM) ---
        dm_response_text = "Error: DM is not connected or failed to respond."
        if dialogue_manager:
            logger.info("\nDM's Turn (Sending to Gemini in thread):")
            dm_response_text = dialogue_manager.send_message(
                user_prompt_text=prompt_for_gemini,
                rag_context=rag_context_for_gemini
            )
        else:
            logger.warning("Dialogue Manager not available to process input.")

        # --- Schedule DM response narration in main thread ---
        if game_play_frame and root_tk_window: 
            root_tk_window.after(0, lambda: game_play_frame.add_narration(f"{dm_response_text}\n"))

        # --- Basic Gemini Response Parsing and State Update (Scheduled) ---
        if player_for_action and dm_response_text: 
            if "you take 5 damage" in dm_response_text.lower(): 
                logger.info("DM response indicates player takes 5 damage. Updating state.")
                player_for_action.take_damage(5) 
                game_state_manager.apply_event({'type': 'damage', 'target': MAIN_PLAYER_ID, 'amount': 5, 'source': 'gemini_response'})
                if game_play_frame and root_tk_window:
                    root_tk_window.after(0, lambda: game_play_frame.add_narration("You feel weaker as you take damage.\n"))
        
        if "Error:" in dm_response_text and dialogue_manager and dialogue_manager.model is None:
             logger.error(f"DM response indicates model error. Response: {dm_response_text}")

    except Exception as e: 
        logger.error(f"Error in threaded_api_call_and_ui_updates: {e}", exc_info=True)
        ui_error_message = f"An error occurred: {type(e).__name__}. Please check logs or try again."
        if game_play_frame and root_tk_window:
            root_tk_window.after(0, lambda: game_play_frame.add_narration(ui_error_message + "\n"))
    finally:
        # --- Schedule UI updates and re-enable input in main thread ---
        if game_play_frame and root_tk_window:
            root_tk_window.after(0, update_ui_game_state) 
            root_tk_window.after(0, lambda: game_play_frame.input_entry.config(state='normal'))
            root_tk_window.after(0, lambda: game_play_frame.send_button.config(state='normal'))
            logger.info("Input field and send button re-enabled.")


def process_player_input(player_input_text):
    """
    Processes the player's input text from the UI.
    Disables input, starts a thread for blocking calls, and re-enables input via the thread.
    """
    global game_play_frame, game_state_manager # app_ui changed to game_play_frame
    logger.info(f"UI Input Received for processing: {player_input_text}")

    if player_input_text.lower() in config.USER_EXIT_COMMANDS:
        handle_exit_game_via_game_play_ui() 
        return

    if game_play_frame:
        game_play_frame.input_entry.config(state='disabled')
        game_play_frame.send_button.config(state='disabled')
        logger.info("Input field and send button disabled.")

    player_for_action = game_state_manager.get_player(MAIN_PLAYER_ID) if game_state_manager else None
    if player_for_action:
        if player_input_text.lower().startswith("go "):
            direction = player_input_text.lower().split(" ", 1)[1]
            if player_for_action.current_location:
                current_loc_obj = game_state_manager.locations.get(player_for_action.current_location)
                if current_loc_obj and direction in current_loc_obj.exits:
                    new_location_id = current_loc_obj.exits[direction]
                    player_for_action.change_location(new_location_id) 
                    if game_play_frame:
                        new_loc_obj_name = game_state_manager.locations.get(new_location_id).name if game_state_manager.locations.get(new_location_id) else "an unknown place"
                        game_play_frame.add_narration(f"You move {direction} to {new_loc_obj_name}.\n") 
                else:
                    if game_play_frame: game_play_frame.add_narration(f"You cannot go {direction} from here.\n")
        
        elif "take sword" in player_input_text.lower(): 
            SWORD_ID = "sword_001" 
            if SWORD_ID not in game_state_manager.items:
                game_state_manager.items[SWORD_ID] = Item(id=SWORD_ID, name="Basic Sword", description="A simple steel sword.")
            if SWORD_ID not in player_for_action.inventory:
                player_for_action.add_item_to_inventory(SWORD_ID) 
                if game_play_frame: game_play_frame.add_narration(f"You take the {game_state_manager.items[SWORD_ID].name}.\n") 
            else:
                if game_play_frame: game_play_frame.add_narration(f"You already have the {game_state_manager.items[SWORD_ID].name}.\n")
        
        update_ui_game_state() 

    thread = threading.Thread(target=threaded_api_call_and_ui_updates, args=(player_input_text,))
    thread.start()


if __name__ == "__main__":
    # --- Environment and API Key Setup ---
    load_dotenv()
    api_key = os.getenv(config.GOOGLE_API_KEY_ENV)
    if not api_key:
        logger.critical(f"Error: {config.GOOGLE_API_KEY_ENV} environment variable not found.")
        exit()
    logger.info("API key loaded successfully.")

    # --- Initialize Managers (RAG, Gemini, GameState) ---
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
        dm_system_instruction = "You are a Dungeon Master for a D&D 5e game..." 
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

    game_state_manager = GameState() # Initialize, but don't load/new game here.
    logger.info("Game state manager initialized (empty).")

    # --- Tkinter UI Setup ---
    root_tk_window = tk.Tk() 
    root_tk_window.title("Text Adventure RPG") 
    root_tk_window.geometry("800x600") 

    # Callbacks for MainMenuFrame
    # placeholder_load_game is replaced by load_existing_game
    def open_settings_menu(): 
        global settings_frame
        logger.info("Opening Settings frame.")
        show_frame(settings_frame)

    def exit_game_from_main_menu(): 
        logger.info("Exit game clicked from Main Menu.")
        if root_tk_window:
            root_tk_window.destroy()

    # Instantiate Frames
    global main_menu_frame, settings_frame 
    main_menu_frame = MainMenuFrame(root_tk_window,
                                   start_new_game, 
                                   load_existing_game, # Actual function for Load Game
                                   open_settings_menu, 
                                   exit_game_from_main_menu)
    
    def show_main_menu_from_settings_callback(): 
        global main_menu_frame
        logger.info("Returning to Main Menu from Settings.")
        show_frame(main_menu_frame)

    settings_frame = SettingsFrame(root_tk_window, show_main_menu_from_settings_callback)

    # Show MainMenuFrame First
    logger.info("Showing Main Menu Frame.")
    show_frame(main_menu_frame)
    
    logger.info("\n--- Application Initialized. Waiting for user interaction in Main Menu. ---")
    root_tk_window.mainloop() 

    logger.info("--- Tkinter mainloop ended. Application shutting down. ---")
    if game_state_manager and game_play_frame and current_frame == game_play_frame: # Check if game was active
        game_state_manager.save_game(config.SAVE_GAME_FILENAME) # Use config.SAVE_GAME_FILENAME
        logger.info("Final game save attempt on shutdown (if game was active).")

# --- END OF FILE main.py ---