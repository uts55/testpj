import re # For skill command parsing and cast command
from game_state import PlayerState, determine_initiative, Player, NPC, Character
import os # Ensure os is imported early for getenv
from gemini_dm import GeminiDM
import game_state # Required for module-level function calls
from combat_system import start_combat, process_combat_turn, check_combat_end_condition, notify_dm_event

# Conditional imports for Tkinter based on test mode
import tkinter as tk
from ui import GamePlayFrame # Full UI version




# Global type hint for app can now safely use GamePlayFrame as it's defined in both paths
# (either imported from ui or defined as MockGamePlayFrame)

from rag_manager import query_vector_db
from config import EMBEDDING_MODEL_NAME, VECTOR_DB_PATH, COLLECTION_NAME, GEMINI_MODEL_NAME
from game_state import GameState # Added for game instance

# --- Global PlayerState and Mock Entities for main game loop ---
import data_loader # Import the data_loader module
from data_loader import load_raw_data_from_sources # Specific import
from config import RAG_DOCUMENT_SOURCES # Specific import for RAG sources

# GameManager class to encapsulate global state
class GameManager:
    """
    Manages all game state including player, NPCs, DM, UI, and game state.
    
    This class encapsulates what were previously global variables to improve:
    - Testability: Easier to create isolated test instances
    - Maintainability: Clear ownership of state
    - Thread safety: Potential for future multi-instance support
    
    Usage:
        manager = GameManager()
        manager.initialize_dm()
        manager.initialize_player(player_data)
        manager.initialize_game_state()
        manager.load_game_data()
    """
    def __init__(self):
        self.hero: Player = None
        self.mock_npcs_in_encounter: list[NPC] = []
        self.main_player_state: PlayerState = None
        self.dm: GeminiDM = None
        self.app: GamePlayFrame = None
        self.game: GameState = None
    
    def initialize_dm(self):
        """Initialize the DM instance."""
        self.dm = GeminiDM(model_name=GEMINI_MODEL_NAME)
    
    def initialize_player(self, player_data: dict):
        """Initialize the player character."""
        self.hero = Player(player_data=player_data)
        self.main_player_state = PlayerState(player_character=self.hero)
    
    def initialize_game_state(self):
        """Initialize the game state with the player."""
        self.game = GameState(player_character=self.hero)
    
    def load_game_data(self):
        """Load all game data from sources."""
        print("Loading all game data for GameState initialization...")
        all_game_raw_data = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)
        self.game.initialize_from_raw_data(all_game_raw_data)
        print(f"GameState initialized. Items loaded: {len(self.game.items)}, NPCs: {len(self.game.npcs)}, Locations: {len(self.game.locations)}")
    
    def refresh_npcs(self):
        """Refresh NPCs in the encounter from the loaded game state."""
        if self.game and self.game.npcs:
             self.mock_npcs_in_encounter = list(self.game.npcs.values())
        else:
             self.mock_npcs_in_encounter = []

# Global GameManager instance
game_manager = GameManager()





def process_player_input(input_text: str, manager: GameManager):
    # Unpack manager for easier access/alias to match existing logic patterns, 
    # or just use manager.prop directly. Using aliases for minimal logic drift.
    hero = manager.hero
    mock_npcs_in_encounter = manager.mock_npcs_in_encounter
    main_player_state = manager.main_player_state
    dm = manager.dm
    app = manager.app
    game = manager.game
    # Note: 'game_state' used in calls (e.g. player_buys_item) usually refers to the module or class?
    # In player_buys_item(hero, npc, item_id, game_state), the last arg is type hinted as GameState instance.
    # So we should pass 'game' (which is manager.game).

    dm_message_to_send = ""
    raw_player_input = input_text # Use the input from UI

    # --- DIALOGUE LOGIC ---
    if main_player_state.is_in_dialogue():
        # Allow quitting even during dialogue
        if raw_player_input.lower() == "quit":
            if app and hasattr(app, 'exit_callback') and app.exit_callback:
                app.exit_callback() # This will call dummy_exit
            dm_message_to_send = "Player decided to quit the game."
            # No narration needed here as dummy_exit handles its own logging for test mode
            # and UI would close in real mode.
            return # Stop further processing after quit

        dm_message_to_send = None # Suppress DM messages while in dialogue UI updates
        current_npc_id = main_player_state.current_dialogue_npc_id
        current_key = main_player_state.current_dialogue_key
        npc = next((n for n in mock_npcs_in_encounter if n.id == current_npc_id), None)

        if not npc:
            app.add_narration("Error: NPC for current dialogue not found. Ending dialogue.")
            main_player_state.end_dialogue()
            app.display_dialogue("", "", []) # Clear dialogue UI
        else:
            # current_key should be valid if is_in_dialogue is true and NPC found
            node = npc.get_dialogue_node(current_key)
            if node is None: # Robust check for node
                app.add_narration(f"{npc.name} seems unsure how to respond to '{current_key}'. The conversation ends.")
                main_player_state.end_dialogue()
                app.display_dialogue(npc.name, "", []) # Clear buttons, enable input
                return # Avoid further processing this turn

            # --- Dynamic Item List Display ---
            if current_key == "buy_items_prompt":
                sells_item_ids = getattr(npc, 'sells_item_ids', [])
                dynamic_choices_for_buy = []
                if sells_item_ids:
                    for item_id in sells_item_ids:
                        item_data = game.items.get(item_id)
                        if item_data:
                            dynamic_choices_for_buy.append({
                                "text": f"{item_data.get('name', item_id)} ({item_data.get('buy_price', 'N/A')} Gold)",
                                "item_id": item_id, "action": "buy_selected_item"
                            })
                dynamic_choices_for_buy.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                app.display_dialogue(npc.name, node.get('npc_text'), dynamic_choices_for_buy)
                return # Wait for player's item selection

            elif current_key == "sell_items_prompt":
                player_inventory = hero.inventory
                dynamic_choices_for_sell = []
                if player_inventory:
                    for item_id in player_inventory:
                        item_data = game.items.get(item_id)
                        if item_data and item_data.get("sell_price") is not None: # Only show sellable items
                            dynamic_choices_for_sell.append({
                                "text": f"{item_data.get('name', item_id)} ({item_data.get('sell_price', 'N/A')} Gold)",
                                "item_id": item_id, "action": "sell_selected_item"
                            })
                dynamic_choices_for_sell.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                app.display_dialogue(npc.name, node.get('npc_text'), dynamic_choices_for_sell)
                return # Wait for player's item selection

            # --- Process player choice (numeric input) ---
            try:
                choice_num = int(raw_player_input)

                # Determine which list of choices to use
                active_choices = []
                if current_key == "buy_items_prompt":
                    sells_item_ids = getattr(npc, 'sells_item_ids', [])
                    if sells_item_ids:
                        for item_id in sells_item_ids:
                            item_data = game.items.get(item_id)
                            if item_data:
                                active_choices.append({
                                    "text": f"{item_data.get('name', item_id)} ({item_data.get('buy_price', 'N/A')} Gold)",
                                    "item_id": item_id, "action": "buy_selected_item"
                                })
                    active_choices.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                elif current_key == "sell_items_prompt":
                    player_inventory = hero.inventory
                    if player_inventory:
                        for item_id in player_inventory:
                            item_data = game.items.get(item_id)
                            if item_data and item_data.get("sell_price") is not None:
                                active_choices.append({
                                    "text": f"{item_data.get('name', item_id)} ({item_data.get('sell_price', 'N/A')} Gold)",
                                    "item_id": item_id, "action": "sell_selected_item"
                                })
                    active_choices.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                else: # Normal dialogue node
                    active_choices = node.get('player_choices', [])

                if active_choices and 1 <= choice_num <= len(active_choices):
                    selected_choice = active_choices[choice_num - 1]
                    action = selected_choice.get("action")

                    if action == "buy_selected_item":
                        item_id_to_buy = selected_choice["item_id"]
                        # game_state here refers to the module import? No, call expects GameState instance.
                        # Original code: from game_state import PlayerState ... but where is 'game_state' used as module?
                        # It seems 'game_state.player_buys_item' was a function call on the module.
                        # Checks top imports: 'import game_state' is NOT present, only 'from game_state import ...'.
                        # Wait, Step 20 output shows 'from game_state import PlayerState...'.
                        # But lines 545 used 'game_state.player_buys_item'.
                        # This implies 'import game_state' IS somewhere or I missed it?
                        # Ah, Step 20 line 2: 'from game_state import PlayerState...'.
                        # Line 442 had globals.
                        # Line 545: 'success, message = game_state.player_buys_item...'
                        # If 'import game_state' is not there, how did it work?
                        # Maybe 'import game_state' WAS added? Step 122 didn't show imports.
                        # Checking Step 20 again... Line 1: 'import re'. Line 2 'from game_state ...'.
                        # Line 3 'import os'.
                        # I suspect 'import game_state' might have been added or 'player_buys_item' was imported?
                        # Actually, looking at main.py content from Step 20, I don't see 'import game_state' standing alone.
                        # However, line 354: 'from game_state import GameState'.
                        # Maybe line 545 was actually relying on a missing import or I missed 'import game_state'.
                        # I will assume `import game_state` IS needed for those module-level function calls.
                        # I will add `import game_state` at the top of main.py later if needed, but for now I will fix the call to use the module if imported, or import the functions.
                        # Better Plan: Update valid python code to call the functions directly if imported, or import them.
                        # In `main.py` (Step 20), lines 2 just imports classes.
                        # I should probably change `game_state.player_buys_item` to `player_buys_item` and import it.
                        # BUT, for this Refactor step, I will stick to what creates less friction.
                        # I will assume `import game_state` exists or I'll change it to use `from game_state import player_buys_item` etc.
                        # Let's check imports in `main.py` again.
                        # Only `from game_state import ...` is visible.
                        # I will add the necessary imports to `main.py` as a separate step or just assume they are available if I use `from game_state import ...`.
                        # Wait, I cannot see `player_buys_item` in `from game_state import ...` in Step 20.
                        # So `main.py` might successfully run only if `import game_state` is present.
                        # If `main.py` was running before, it must have it.
                        # Let me verify if `import game_state` is in `main.py`.
                        # I'll check the top of `main.py` again in Step 72.
                        # It shows `from game_state import PlayerState...`.
                        # It does NOT show `import game_state`.
                        # So `game_state.player_buys_item` would FAIL unless `game_state` is the name of the imported module object, which happens if you do `import game_state`.
                        # Maybe I missed it.
                        # Let's look at `main.py` later. For now, I will use `game_state.player_buys_item` assuming `import game_state` will be fixed or present.
                        # Actually, to be safe, I should change it to `game_state_module.player_buys_item` and ensure I import `game_state` as `game_state_module`.
                        # OR, just import the functions.
                        # I'll stick to replacing `process_player_input` first. Uses `game_state` as module alias? 
                        # I will change the call to `game_state_module.player_buys_item` and add the import in a prep step?
                        # No, I should fix it here. usage: `game_state.player_buys_item(hero, npc, item_id_to_buy, game)`
                        # I will assume the user wants me to fix the logic structure first.
                        # I'll use `import game_state` inside the function? No that's bad.
                        # I'll rely on the `global game_state` if it exists? No.
                        # I will use `import game_state` at module level.
                        
                        # Use `game_state.player_buys_item`... assuming `import game_state` is there.
                        success, message = game_state.player_buys_item(hero, npc, item_id_to_buy, game)
                        app.add_narration(message)
                        app.update_hp(f"{hero.current_hp}/{hero.max_hp}") # Refresh UI

                        # Re-display buy prompt
                        node_to_display = npc.get_dialogue_node("buy_items_prompt")
                        sells_item_ids_refresh = getattr(npc, 'sells_item_ids', [])
                        dynamic_choices_refresh = []
                        if sells_item_ids_refresh:
                            for item_id_refresh in sells_item_ids_refresh:
                                item_data_refresh = game.items.get(item_id_refresh)
                                if item_data_refresh:
                                    dynamic_choices_refresh.append({
                                        "text": f"{item_data_refresh.get('name', item_id_refresh)} ({item_data_refresh.get('buy_price', 'N/A')} Gold)",
                                        "item_id": item_id_refresh, "action": "buy_selected_item"
                                    })
                        dynamic_choices_refresh.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                        app.display_dialogue(npc.name, node_to_display.get('npc_text'), dynamic_choices_refresh)
                        return

                    elif action == "sell_selected_item":
                        item_id_to_sell = selected_choice["item_id"]
                        success, message = game_state.player_sells_item(hero, npc, item_id_to_sell, game)
                        app.add_narration(message)
                        app.update_hp(f"{hero.current_hp}/{hero.max_hp}") # Refresh UI

                        # Re-display sell prompt
                        node_to_display = npc.get_dialogue_node("sell_items_prompt")
                        player_inventory_refresh = hero.inventory
                        dynamic_choices_refresh = []
                        if player_inventory_refresh:
                            for item_id_refresh in player_inventory_refresh:
                                item_data_refresh = game.items.get(item_id_refresh)
                                if item_data_refresh and item_data_refresh.get("sell_price") is not None:
                                    dynamic_choices_refresh.append({
                                        "text": f"{item_data_refresh.get('name', item_id_refresh)} ({item_data_refresh.get('sell_price', 'N/A')} Gold)",
                                        "item_id": item_id_refresh, "action": "sell_selected_item"
                                    })
                        dynamic_choices_refresh.append({"text": "그만 보겠습니다.", "next_key": "greetings_repeat", "action": "dialogue_navigation"})
                        app.display_dialogue(npc.name, node_to_display.get('npc_text'), dynamic_choices_refresh)
                        return

                    elif action == "dialogue_navigation" or action is None: # Default to dialogue navigation
                        next_key = selected_choice['next_key']
                        next_node_preview = npc.get_dialogue_node(next_key)
                        if not next_node_preview:
                            app.add_narration(f"{npc.name} seems confused. The conversation ends.")
                            main_player_state.end_dialogue()
                            app.display_dialogue(npc.name, "", [])
                            return

                        if not next_node_preview.get('player_choices', []) or next_key == "farewell":
                            final_npc_text = next_node_preview.get('npc_text', "Goodbye.")
                            app.add_narration(f"{npc.name}: {final_npc_text}")
                            if not next_node_preview.get('player_choices', []):
                                 app.add_narration("(No further choices available.)")
                            main_player_state.end_dialogue()
                            app.display_dialogue(npc.name, "", [])
                        else:
                            main_player_state.set_dialogue_key(next_key)
                            # New node will be displayed by the logic below
                elif active_choices:
                    app.add_narration("Invalid choice. Please click one of the options.")
            except ValueError:
                if node.get('player_choices', []) and not (current_key == "buy_items_prompt" or current_key == "sell_items_prompt"):
                     app.add_narration("Invalid input. Please click one of the available choices.")
                # If in buy/sell prompt, non-numeric input is ignored until a valid choice is made or "go back"

            # (Re-)Display current dialogue node if dialogue is still active (and not handled by buy/sell returns)
            if main_player_state.is_in_dialogue():
                current_dialogue_key_to_display = main_player_state.current_dialogue_key
                # Skip re-display if we are in buy/sell prompts as they handle their own display logic or return
                if current_dialogue_key_to_display not in ["buy_items_prompt", "sell_items_prompt"]:
                    node_to_display = npc.get_dialogue_node(current_dialogue_key_to_display)
                    if not node_to_display:
                        app.add_narration(f"Error: Current dialogue node '{current_dialogue_key_to_display}' missing. Ending.")
                        main_player_state.end_dialogue()
                        app.display_dialogue(npc.name, "", [])
                    else:
                        npc_text_to_display = node_to_display.get('npc_text', "...")
                        choices_to_display = node_to_display.get('player_choices', [])
                        app.display_dialogue(npc.name, npc_text_to_display, choices_to_display)
                        if not choices_to_display and not main_player_state.current_dialogue_key == "farewell":
                            app.add_narration("(The conversation seems to have reached a natural end.)")
                            main_player_state.end_dialogue()


    # --- COMBAT LOGIC ---
    elif main_player_state.is_in_combat:
        player_action_for_combat = raw_player_input
        turn_result_message = process_combat_turn(dm, main_player_state, player_action_for_combat)
        # UI feedback for invalid combat commands or prompts
        if any(prompt in turn_result_message for prompt in ["Type 'attack", "Invalid action", "Target '", "Invalid command", "Invalid cast"]):
            app.add_narration(turn_result_message)
        else: # Valid combat action results for DM
            dm_message_to_send = turn_result_message

        ended, end_notification = check_combat_end_condition(hero, mock_npcs_in_encounter, main_player_state)
        if ended:
            dm_message_to_send = (dm_message_to_send + "\n" if dm_message_to_send else "") + end_notification
            app.add_narration("\n--- Combat Over ---")
            if app: app.enable_input() # Ensure input is enabled after combat

    # --- NON-COMBAT COMMANDS (Fight, Talk, Skill, General) ---
    else:
        talk_match = re.match(r"talk to (.+)", raw_player_input, re.IGNORECASE)
        if talk_match:
            npc_name_to_talk = talk_match.group(1).strip()
            npc_to_talk = next((n for n in mock_npcs_in_encounter if n.name.lower() == npc_name_to_talk.lower()), None)
            if npc_to_talk:
                if npc_to_talk.dialogue_responses and npc_to_talk.get_dialogue_node("greetings"): # Also check if 'greetings' node exists
                    main_player_state.start_dialogue(npc_to_talk.id, "greetings")
                    first_node = npc_to_talk.get_dialogue_node("greetings") # Safe, checked above

                    # Ensure first_node is not None before accessing its attributes
                    # This check is slightly redundant due to get_dialogue_node("greetings") check above, but good for safety
                    if first_node:
                        app.display_dialogue(npc_to_talk.name, first_node.get('npc_text', "..."), first_node.get('player_choices', []))
                    else: # Should ideally not be reached if npc_to_talk.get_dialogue_node("greetings") passed
                        app.add_narration(f"Error: Could not load initial dialogue for {npc_to_talk.name} despite checks.")
                        main_player_state.end_dialogue() # Ensure dialogue state is cleared
                    dm_message_to_send = None
                else: # No dialogue_responses or no "greetings" node
                    app.add_narration(f"{npc_to_talk.name} doesn't seem to want to talk right now, or has nothing to say.")
                    dm_message_to_send = f"Player attempts to talk to {npc_to_talk.name}, but they offer no dialogue."
            else:
                app.add_narration(f"NPC '{npc_name_to_talk}' not found.")
                dm_message_to_send = f"Player attempts to talk to '{npc_name_to_talk}', but they are not found."

        elif raw_player_input.lower() == "fight":
            if app: app.enable_input() # Ensure input is enabled before starting new combat
            hero.current_hp = hero.max_hp
            manager.refresh_npcs() # Refresh NPCs using the manager method
            # Update local reference after refresh
            mock_npcs_in_encounter = manager.mock_npcs_in_encounter 
            
            start_message = start_combat(hero, mock_npcs_in_encounter, main_player_state)
            dm_message_to_send = start_message
            # If player's turn first, process_combat_turn will return a prompt
            if main_player_state.current_turn_character_id == hero.id:
                 app.add_narration(process_combat_turn(dm, main_player_state, "")) # Get initial prompt for player

        # Quit command handling was moved inside the dialogue block if active,
        # and remains here for non-dialogue, non-combat situations.
        elif raw_player_input.lower() == "quit":
            if app and hasattr(app, 'exit_callback') and app.exit_callback:
                app.exit_callback()
            dm_message_to_send = "Player decided to quit the game."
            return # Stop further processing

        # --- READ / EXAMINE COMMAND ---
        read_examine_match = re.match(r"^(?:read|examine)\s+(.+)$", raw_player_input, re.IGNORECASE)
        if read_examine_match:
            item_name_to_find = read_examine_match.group(1).strip().lower()
            found_item_object = None

            if hero and game and game.items: # Ensure hero, game, and game.items are available
                for item_id in hero.inventory:
                    item_obj = game.items.get(item_id)
                    if item_obj and item_obj.name.lower() == item_name_to_find:
                        found_item_object = item_obj
                        break

            if found_item_object:
                item = found_item_object
                dm_info_parts = []
                narration_message_sent = False

                if item.description:
                    app.add_narration(f"You examine the {item.name}: {item.description}")
                    dm_info_parts.append(f"Description: {item.description}")
                    narration_message_sent = True

                if item.lore_keywords:
                    query_text = " ".join(item.lore_keywords)
                    try:
                        retrieved_docs = query_vector_db(query_text, VECTOR_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL_NAME, n_results=2)
                        if retrieved_docs:
                            dm_info_parts.append("Associated RAG Information:")
                            for doc_idx, doc in enumerate(retrieved_docs):
                                doc_text = doc.get('document_text', 'No text available.')
                                doc_name = doc.get('metadata', {}).get('name', f'Unknown source {doc_idx+1}')
                                dm_info_parts.append(f"- {doc_name}: {doc_text[:150]}{'...' if len(doc_text) > 150 else ''}")
                        else:
                            dm_info_parts.append("No specific details found via RAG for its keywords.")
                    except Exception as e:
                        dm_info_parts.append(f"Error querying RAG: {e}")
                        print(f"Error during RAG query for '{item.name}': {e}") # Log to console

                if not narration_message_sent and not item.lore_keywords: # No description and no keywords
                    app.add_narration(f"You examine the {item.name}. There's nothing particularly noteworthy about it in terms of lore.")
                    notify_dm_event(dm, f"Player examines {item.name}, but it's not a lore item or has no details.")
                    dm_message_to_send = None
                elif not narration_message_sent and item.lore_keywords: # No description but HAS keywords
                     app.add_narration(f"You examine the {item.name}. It has no specific text, but you feel it might be important based on its nature.")
                     # DM notification will be built from dm_info_parts

                if dm_info_parts:
                    dm_message = f"Player reads/examines {item.name}.\n" + "\n".join(dm_info_parts)
                    notify_dm_event(dm, dm_message)
                elif narration_message_sent and not item.lore_keywords: # Had description but no keywords to process further for DM
                    notify_dm_event(dm, f"Player reads {item.name}. Description was: {item.description}")


                dm_message_to_send = None # Command handled
            else:
                app.add_narration(f"You don't have a '{read_examine_match.group(1).strip()}' in your inventory.")
                dm_message_to_send = None # Command handled (item not found)

        else: # Skill checks or general message (original else block)
            skill_command_pattern = r"^(?:use|try to)\s+(\w+)\s+(?:on|to)\s+(.+?)\s+\(DC\s*(\d+)\)$"
            match = re.match(skill_command_pattern, raw_player_input, re.IGNORECASE)
            if match:
                skill_name = match.group(1); target_description = match.group(2); dc_value = int(match.group(3))
                if hero and hasattr(hero, 'perform_skill_check'):
                    success, _, _, breakdown_str = hero.perform_skill_check(skill_name, dc_value)
                    dm_message_to_send = (
                        f"Player {hero.name} attempts to use {skill_name} {target_description} (DC {dc_value}).\n"
                        f"Roll Details: {breakdown_str}.\nOutcome: {'Success!' if success else 'Failure.'}")
                else:
                    dm_message_to_send = "Error: Hero object or skill check function not available."
                    app.add_narration("Error: Skill check could not be performed.")
            else:
                dm_message_to_send = raw_player_input # Fallback general message


    # Send DM message if any
    if dm_message_to_send and dm:
        response = dm.send_message(dm_message_to_send, stream=False) # Stream True can be messy with Tkinter
        if response and app:
            app.add_narration(f"DM: {response}")

    # Update UI labels (HP, etc.) - this should be done after every action
    if app and hero: # Check if app and hero exist
        app.update_hp(f"{hero.current_hp}/{hero.max_hp}")
        # app.update_location(main_player_state.player_character.current_location) # Assuming location is tracked
        # app.update_inventory(", ".join(hero.inventory) if hero.inventory else "Empty")
        # npc_names_in_encounter = [npc.name for npc in mock_npcs_in_encounter if npc.is_alive()]
        # app.update_npcs(", ".join(npc_names_in_encounter) if npc_names_in_encounter else "None")


def dummy_save():
    if game_manager.app: game_manager.app.add_narration("Save Game clicked (not implemented yet).")
    print("Dummy save_game_callback called")

def dummy_load():
    if game_manager.app: game_manager.app.add_narration("Load Game clicked (not implemented yet).")
    print("Dummy load_game_callback called")

def dummy_exit():
    if game_manager.app and hasattr(game_manager.app, 'master') and game_manager.app.master:
        game_manager.app.master.destroy()
    print("Game exited (GUI).")

def main():
    # global hero, mock_npcs_in_encounter, main_player_state, dm, app, game # Removed global decl
    # Local variables for initialization (they reference manager props but are just refs now)
    
    print("Starting game...")

    # Initialize using GameManager
    game_manager.initialize_dm()
    
    hero_player_data = {
        "id": "hero_1", "name": "Hero", "max_hp": 100,
        "combat_stats": {'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2, 'initiative_bonus': 3},
        "base_damage_dice": "1d8",
        "ability_scores": {"strength": 16, "dexterity": 14, "constitution": 15, "intelligence": 10, "wisdom": 12, "charisma": 13},
        "skills": ["athletics", "perception", "lockpicking", "persuasion", "stealth"],
        "proficiencies": {"skills": ["athletics", "lockpicking", "stealth"]},
        "equipment": {"weapon": "long_sword", "armor": "leather_armor"}
    }
    
    game_manager.initialize_player(hero_player_data)
    game_manager.initialize_game_state()
    game_manager.load_game_data()
    game_manager.refresh_npcs()
    
    # Update legacy global variables for backward compatibility
    hero = game_manager.hero
    mock_npcs_in_encounter = game_manager.mock_npcs_in_encounter
    main_player_state = game_manager.main_player_state
    dm = game_manager.dm
    game = game_manager.game
    # The TODO is now addressed. game.items should be populated if data files exist.

    # Add new lore items to inventory for testing the 'read' command
    if "old_journal_001" in game.items:
        hero.add_to_inventory("old_journal_001")
        print(f"DEBUG: Added 'old_journal_001' to hero's inventory. Current inv: {hero.inventory}")
    else:
        print("DEBUG: 'old_journal_001' not found in game.items. Cannot add to inventory.")

    if "ancient_tablet_fragment_001" in game.items:
        hero.add_to_inventory("ancient_tablet_fragment_001")
        print(f"DEBUG: Added 'ancient_tablet_fragment_001' to hero's inventory. Current inv: {hero.inventory}")
    else:
        print("DEBUG: 'ancient_tablet_fragment_001' not found in game.items. Cannot add to inventory.")

    if "historical_fragment_eldoria_001" in game.items:
        hero.add_to_inventory("historical_fragment_eldoria_001")
        print(f"DEBUG: Added 'historical_fragment_eldoria_001' to hero's inventory. Current inv: {hero.inventory}")
    else:
        print("DEBUG: 'historical_fragment_eldoria_001' not found in game.items. Cannot add to inventory.")

    # For testing a non-lore item, ensure one is in inventory (e.g. from initial setup)
    # hero_player_data already includes "healing_potion_small" and equips "iron_sword"
    # Let's ensure "iron_sword" is also in inventory if not equipped or for a generic read test
    # hero.inventory initially might be empty if not set in hero_player_data or cleared.
    # The Player class init for hero_player_data already puts "healing_potion_small" in inventory.
    # And "iron_sword" is set in equipment.
    # Let's add "iron_sword" to inventory if it's not there, just to be sure for testing "read iron_sword".
    if "iron_sword" in game.items and "iron_sword" not in hero.inventory:
        # Check if it's equipped; if so, unequip and add to inventory for this test, or just add.
        # For simplicity, just add it. The read command doesn't care about equipped status.
        hero.add_to_inventory("iron_sword")
        print(f"DEBUG: Added 'iron_sword' to hero's inventory for testing 'read' on a non-lore item. Current inv: {hero.inventory}")


    # Define wrapper for callback
    def process_player_input_wrapper(text: str):
        process_player_input(text, game_manager)

    # Initialize GUI
    root = tk.Tk()
    app = GamePlayFrame(master=root,
                      process_input_callback=process_player_input_wrapper,
                      save_game_callback=dummy_save,
                      load_game_callback=dummy_load,
                      exit_callback=dummy_exit)
    # Inject app into game_manager now that it's created
    game_manager.app = app
    
    app.add_narration("Welcome to the Text Adventure RPG!")
    app.add_narration("Type 'talk to 엘라라' to start a conversation, or 'fight' to battle goblins.")
    app.add_narration("You can also 'use <skill> on <target> (DC <value>)' or 'quit'.")
    app.update_hp(f"{hero.current_hp}/{hero.max_hp}")
    root.mainloop()

if __name__ == "__main__":
    main()



