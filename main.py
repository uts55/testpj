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
from tkinter import messagebox, simpledialog, Toplevel, Listbox, Scrollbar, Button  # Added Toplevel, Listbox, Scrollbar, Button
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
from utils import roll_dice # Added for combat

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
    global game_state_manager, dialogue_manager, game_play_frame, root_tk_window, MAIN_PLAYER_ID
    logger.info("Attempting to load an existing game...")

    if not game_state_manager:
        logger.error("GameStateManager not initialized. Cannot load game.")
        messagebox.showerror("Load Game Error", "GameStateManager not ready. Cannot load game.", parent=root_tk_window)
        return

    if not os.path.isdir(config.SAVE_GAME_DIR):
        logger.error(f"Save game directory not found: {config.SAVE_GAME_DIR}")
        messagebox.showerror("Load Game Error", f"Save directory '{config.SAVE_GAME_DIR}' not found.", parent=root_tk_window)
        return

    save_files = [f for f in os.listdir(config.SAVE_GAME_DIR) if f.endswith(".json")]

    if not save_files:
        logger.info("No save files found.")
        messagebox.showinfo("Load Game", "No save files found in the save directory.", parent=root_tk_window)
        return

    load_window = Toplevel(root_tk_window)
    load_window.title("Load Game")
    load_window.geometry("300x250") # Adjust as needed
    load_window.transient(root_tk_window) # Make it modal-like
    load_window.grab_set() # Grab focus

    listbox_frame = tk.Frame(load_window)
    listbox_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

    scrollbar = Scrollbar(listbox_frame, orient=tk.VERTICAL)
    listbox = Listbox(listbox_frame, yscrollcommand=scrollbar.set, exportselection=False)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    for sf in save_files:
        listbox.insert(tk.END, sf)

    def on_load_selected():
        # These globals are assigned to or modified within this nested function
        global game_play_frame, dialogue_manager, root_tk_window, MAIN_PLAYER_ID
        # game_state_manager is accessed via the global scope of load_existing_game, but not reassigned here.

        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Load Game", "Please select a save file to load.", parent=load_window)
            return

        selected_filename = listbox.get(selected_indices[0])
        selected_path = os.path.join(config.SAVE_GAME_DIR, selected_filename)
        
        logger.info(f"Attempting to load: {selected_path}")
        game_state_manager.load_game(selected_path) # GameState.load_game logs its own messages

        if game_state_manager.get_player(MAIN_PLAYER_ID):
            logger.info(f"Player {MAIN_PLAYER_ID} found. Load successful for {selected_filename}.")
            messagebox.showinfo("Load Game", f"Game '{selected_filename}' loaded successfully!", parent=load_window)
            load_window.destroy()

            if dialogue_manager:
                dialogue_manager.history = []
                logger.info("Dialogue history cleared for loaded game.")
            else:
                logger.error("DialogueManager not initialized. Cannot clear history.")

            if game_play_frame:
                game_play_frame.destroy()
                logger.info("Previous GamePlayFrame instance destroyed.")

            game_play_frame = GamePlayFrame(
                master=root_tk_window,
                process_input_callback=process_player_input,
                save_game_callback=handle_save_game,
                load_game_callback=handle_load_game,
                exit_callback=handle_exit_game_via_game_play_ui
            )
            logger.info("New GamePlayFrame instance created for loaded game.")

            show_frame(game_play_frame)
            logger.info("Switched to GamePlayFrame for loaded game.")

            update_ui_game_state()

            if game_play_frame:
                game_play_frame.add_narration(f"Game '{selected_filename}' loaded. Continue your adventure!\n")
            logger.info("GamePlayFrame updated and narration added.")

        else:
            logger.warning(f"Failed to load game from {selected_filename} or player not found.")
            messagebox.showerror("Load Error", f"Failed to load '{selected_filename}'. File might be corrupted or not a valid save.", parent=load_window)
            # Optionally, clear game_state if load was partial and bad: game_state_manager.initialize_new_game(...) or similar reset.

    def on_cancel_load():
        load_window.destroy()

    button_frame = tk.Frame(load_window)
    button_frame.pack(pady=5, padx=10, fill=tk.X)

    load_button = Button(button_frame, text="Load Selected", command=on_load_selected)
    load_button.pack(side=tk.LEFT, expand=True, padx=5)

    cancel_button = Button(button_frame, text="Cancel", command=on_cancel_load)
    cancel_button.pack(side=tk.RIGHT, expand=True, padx=5)

# --- Callback Functions for UI interactions ---
def handle_save_game():
    global game_state_manager, game_play_frame, root_tk_window
    if not game_state_manager:
        logger.warning("Save game called but game_state_manager is not initialized.")
        if game_play_frame:
            game_play_frame.add_narration("Error: Could not save game (GameState not ready).\n")
        return

    filename = simpledialog.askstring("Save Game", "Enter filename for save:", parent=root_tk_window)

    if filename:
        # Ensure the filename ends with .json, but don't add if user included it
        if not filename.lower().endswith(".json"):
            actual_filename = filename + ".json"
        else:
            actual_filename = filename
            filename = filename[:-5] # Remove .json for the narration message part

        save_path = os.path.join(config.SAVE_GAME_DIR, actual_filename)
        try:
            game_state_manager.save_game(save_path)
            logger.info(f"Game saved to {save_path} via UI button.")
            if game_play_frame:
                game_play_frame.add_narration(f"Game saved as {filename}.json.\n")
        except Exception as e:
            logger.error(f"Error saving game to {save_path}: {e}", exc_info=True)
            if game_play_frame:
                game_play_frame.add_narration(f"Error: Could not save game to {filename}.json. {type(e).__name__}\n")
    else:
        logger.info("Save game cancelled by user.")
        if game_play_frame:
            game_play_frame.add_narration("Save cancelled.\n")

def handle_load_game(): # This is the in-game load game button callback
    global game_state_manager, game_play_frame # SAVE_GAME_FILENAME removed from globals
    if not game_state_manager:
        logger.warning("Load game called but game_state_manager is not initialized.")
        if game_play_frame: 
            game_play_frame.add_narration("Error: Could not load game (GameState not ready).\n")
        return

    # Removed direct load logic from in-game button
    logger.info("In-game load button clicked. Directed user to Main Menu for loading.")
    if game_play_frame:
        game_play_frame.add_narration(
            "To load a specific save file, please use the 'Load Saved Game' option from the Main Menu.\n"
            "Progress since your last explicit save might be lost if you load from Main Menu without saving now.\n"
        )

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
        # Corrected to access hit_points directly as 'stats' attribute doesn't exist
        hp_current = player.hit_points.get('current', 'N/A') if player.hit_points else 'N/A'
        game_play_frame.update_hp(str(hp_current)) # Ensure it's a string for UI

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


def threaded_api_call_and_ui_updates(input_for_dm):
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
            player_hp = player_for_action.hit_points.get('current', 'N/A') if player_for_action.hit_points else 'N/A'
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
        prompt_for_gemini = f"{current_state_summary_for_dm}\nContext/Event: {input_for_dm}"

        # --- RAG Context Retrieval ---
        rag_context_for_gemini = None
        if rag_system_manager and rag_system_manager.collection and rag_system_manager.collection.count() > 0:
            logger.info("\n[RAG] Searching for relevant context based on input...")
            retrieved_context_docs = rag_system_manager.search(input_for_dm, n_results=3) # Use input_for_dm for RAG search
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

    # --- Attack Command ---
    elif player_input_text.lower().startswith("attack "):
        parts = player_input_text.split(" ", 1)
        if len(parts) > 1:
            target_npc_name = parts[1].strip()
            player = game_state_manager.get_player(MAIN_PLAYER_ID)

            if player and player.current_location:
                npcs_in_location = game_state_manager.get_npcs_in_location(player.current_location)
                npc_target = None
                for npc_obj in npcs_in_location:
                    if npc_obj.name.lower() == target_npc_name.lower():
                        npc_target = npc_obj
                        break

                if npc_target:
                    if npc_target.hp > 0: # Check if NPC is already defeated
                        damage_amount = roll_dice(6) # e.g., 1d6 damage
                        npc_target.take_damage(damage_amount)

                        player_feedback_message = f"You attack {npc_target.name} and deal {damage_amount} damage."
                        if npc_target.hp > 0:
                            player_feedback_message += f" Their HP is now {npc_target.hp}."
                        else:
                            player_feedback_message += f" {npc_target.name} has been defeated!"

                        if game_play_frame: # Check if UI is available
                            game_play_frame.add_narration(player_feedback_message + "\n")

                        update_ui_game_state() # Update UI immediately

                        text_for_dm = f"Player {player.name} attacked {npc_target.name}, dealing {damage_amount} damage. {npc_target.name}'s current HP is {npc_target.hp}."
                        if npc_target.hp == 0:
                            text_for_dm += f" {npc_target.name} has fallen in combat and is now defeated."

                        # Start the thread with this descriptive text for the DM
                        thread = threading.Thread(target=threaded_api_call_and_ui_updates, args=(text_for_dm,))
                        thread.start()
                        return # Attack handled, prevent further processing of this input
                    else:
                        if game_play_frame:
                            game_play_frame.add_narration(f"{npc_target.name} is already defeated.\n")
                        # No DM message needed if target already down, re-enable input directly
                        if game_play_frame:
                            game_play_frame.input_entry.config(state='normal')
                            game_play_frame.send_button.config(state='normal')
                        return
                else:
                    if game_play_frame:
                        game_play_frame.add_narration(f"You don't see anyone named '{target_npc_name}' here to attack.\n")
                    # No DM message, re-enable input
                    if game_play_frame:
                        game_play_frame.input_entry.config(state='normal')
                        game_play_frame.send_button.config(state='normal')
                    return
        else:
            if game_play_frame:
                game_play_frame.add_narration("Who do you want to attack? (e.g., attack Goblin)\n")
            # No DM message, re-enable input
            if game_play_frame:
                game_play_frame.input_entry.config(state='normal')
                game_play_frame.send_button.config(state='normal')
            return
    # --- Roll Command ---
    elif player_input_text.lower().startswith("roll "):
        command_part = player_input_text.lower().split(" ", 1)[1].strip() # e.g., "d20" or "1d20"

        num_dice = 1 # Currently supporting 1 die
        sides = 0

        # Simple parsing for "d<N>" or "1d<N>"
        if command_part.startswith('d'):
            try:
                sides = int(command_part[1:])
            except ValueError:
                if game_play_frame:
                    game_play_frame.add_narration(f"Invalid dice format: '{command_part}'. Use 'd<number>', e.g., 'roll d20'.\n")
                if game_play_frame: # Re-enable input
                    game_play_frame.input_entry.config(state='normal')
                    game_play_frame.send_button.config(state='normal')
                return
        elif 'd' in command_part:
            parts = command_part.split('d')
            if len(parts) == 2:
                try:
                    # For now, only support 1dX, parts[0] should be '1' or empty
                    if parts[0] == '' or parts[0] == '1':
                        sides = int(parts[1])
                    else:
                        if game_play_frame:
                            game_play_frame.add_narration(f"Unsupported dice format: '{command_part}'. Try 'd<number>' or '1d<number>'.\n")
                        if game_play_frame: # Re-enable input
                            game_play_frame.input_entry.config(state='normal')
                            game_play_frame.send_button.config(state='normal')
                        return
                except ValueError:
                    if game_play_frame:
                        game_play_frame.add_narration(f"Invalid dice numbers: '{command_part}'.\n")
                    if game_play_frame: # Re-enable input
                        game_play_frame.input_entry.config(state='normal')
                        game_play_frame.send_button.config(state='normal')
                    return
            else: # Invalid format like "d" or "d20d"
                if game_play_frame:
                    game_play_frame.add_narration(f"Invalid dice format: '{command_part}'.\n")
                if game_play_frame: # Re-enable input
                    game_play_frame.input_entry.config(state='normal')
                    game_play_frame.send_button.config(state='normal')
                return
        else: # No 'd' found, e.g. "roll 20"
            if game_play_frame:
                game_play_frame.add_narration(f"Invalid dice format: '{command_part}'. Did you mean 'd{command_part}'?\n")
            if game_play_frame: # Re-enable input
                game_play_frame.input_entry.config(state='normal')
                game_play_frame.send_button.config(state='normal')
            return

        if sides > 0:
            roll_result = roll_dice(sides)
            player_feedback = f"You roll a d{sides} and get: {roll_result}.\n"
            if game_play_frame:
                game_play_frame.add_narration(player_feedback)

            player = game_state_manager.get_player(MAIN_PLAYER_ID) # Get player for name
            player_name = player.name if player else "Player"
            text_for_dm = f"{player_name} rolls a d{sides} for an action, getting a {roll_result}."

            thread = threading.Thread(target=threaded_api_call_and_ui_updates, args=(text_for_dm,))
            thread.start()
            return # Dice roll handled
        else: # Fallback, should be caught by parsing
            if game_play_frame:
                game_play_frame.add_narration(f"Could not determine the type of dice to roll from '{command_part}'.\n")
            if game_play_frame: # Re-enable input
                game_play_frame.input_entry.config(state='normal')
                game_play_frame.send_button.config(state='normal')
            return

    # If we reach here, no specific local command was fully handled and returned.
    # So, pass the original player_input_text to the DM.
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
    # global main_menu_frame, settings_frame # Removed incorrect global statement
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