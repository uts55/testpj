import re # For skill command parsing and cast command
from game_state import PlayerState, determine_initiative, Player, NPC, Character
import os # Ensure os is imported early for getenv

import os # Ensure os is imported early for getenv

# Conditional imports for Tkinter based on test mode
is_test_mode_check_for_import = (os.getenv("RUNNING_INTERACTIVE_TEST") == "true")

if not is_test_mode_check_for_import:
    import tkinter as tk
    from ui import GamePlayFrame # Full UI version
else:
    # Define a local MockGamePlayFrame for test mode to avoid all Tkinter dependencies
    class MockGamePlayFrame:
        def __init__(self, master=None, process_input_callback=None,
                     save_game_callback=None, load_game_callback=None, exit_callback=None):
            print("UI_MOCK: MockGamePlayFrame initialized.")
            self.process_input_callback = process_input_callback
            self.exit_callback = exit_callback
            self._test_destroyed_flag = False

        def add_narration(self, message: str):
            print(f"UI_MOCK_NARRATION: {message}")

        def display_dialogue(self, npc_name: str, npc_text: str, player_choices: list[dict]):
            print(f"UI_MOCK_DIALOGUE: {npc_name}: {npc_text}")
            if player_choices:
                for i, choice_data in enumerate(player_choices):
                    print(f"  CHOICE {i+1}: {choice_data.get('text')}")
            else:
                print("  (No player choices)")

        def update_hp(self, hp_value: str):
            print(f"UI_MOCK_UPDATE_HP: {hp_value}")

        def enable_input(self):
            print("UI_MOCK_ACTION: Input enabled.")

        def disable_input(self):
            print("UI_MOCK_ACTION: Input disabled.")

        def is_destroyed(self):
            return self._test_destroyed_flag

    GamePlayFrame = MockGamePlayFrame # Use the mock class as GamePlayFrame in test mode


# --- Combat Flow Functions ---

def start_combat(player: Player, npcs: list[NPC], current_player_state: PlayerState) -> str:
    """
    Initializes combat, sets turn order, and notifies the DM.
    """
    if not isinstance(player, Player):
        return "Error: Player object is not of type Player."
    if not all(isinstance(npc, NPC) for npc in npcs):
        return "Error: Not all NPC objects are of type NPC."
    if not isinstance(current_player_state, PlayerState):
        return "Error: PlayerState object is not of type PlayerState."

    current_player_state.is_in_combat = True
    all_participants: list[Character] = [player] + npcs
    current_player_state.participants_in_combat = all_participants # Store actual objects

    current_player_state.turn_order = determine_initiative(all_participants) # Expects list of objects

    if not current_player_state.turn_order:
        current_player_state.is_in_combat = False
        # Reset participants if combat fails to start
        current_player_state.participants_in_combat = []
        return "Combat could not start: no participants or failed initiative determination."

    current_player_state.current_turn_character_id = current_player_state.turn_order[0]

    # Get names for the turn order string
    turn_order_names = []
    for char_id in current_player_state.turn_order:
        participant = next((p for p in all_participants if p.id == char_id), None)
        if participant:
            turn_order_names.append(participant.name)
        else:
            turn_order_names.append(f"Unknown({char_id})")


    turn_order_str = ", ".join(turn_order_names)
    first_character_name = "Unknown"
    first_char_obj = next((p for p in all_participants if p.id == current_player_state.current_turn_character_id), None)
    if first_char_obj:
        first_character_name = first_char_obj.name

    return f"Combat started! Turn order: {turn_order_str}. First up: {first_character_name} ({current_player_state.current_turn_character_id})."

def process_combat_turn(dm_manager, current_player_state: PlayerState, player_action: str = "") -> str:
    """
    Processes the current character's turn: handles status effects, action, attack, and advances to the next.
    Returns a message for the DM or player.
    """
    if not current_player_state.is_in_combat or not current_player_state.turn_order:
        return "Cannot process turn: not in combat or turn order is empty."

    if not current_player_state.current_turn_character_id:
        return "Cannot process turn: current_turn_character_id is not set."

    char_id = current_player_state.current_turn_character_id
    attacker = next((p for p in current_player_state.participants_in_combat if p.id == char_id), None)

    if attacker is None:
        # This should ideally not happen if char_id is always valid.
        # If it does, try to advance turn to prevent getting stuck.
        try:
            current_turn_index = current_player_state.turn_order.index(char_id) # This will fail if char_id is bad
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]
            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            next_attacker_name = next_attacker_obj.name if next_attacker_obj else "Unknown"
            return f"Error: Attacker with ID {char_id} not found. Advancing to {next_attacker_name} to prevent stall."
        except (ValueError, IndexError) as e:
            # If advancing also fails, combat state is critically corrupted.
            current_player_state.is_in_combat = False # Attempt to stop combat
            return f"Critical Error: Attacker {char_id} not found and cannot advance turn: {e}. Combat stopped."

    notification_parts = [] # Accumulate messages for the turn

    # --- Status Effects Tick ---
    status_effect_messages = attacker.tick_status_effects()
    if status_effect_messages:
        for effect_msg in status_effect_messages:
            notify_dm_event(dm_manager, effect_msg) # Send each status effect message individually
        notification_parts.extend(status_effect_messages)
        # is_attacker_alive_after_effects = attacker.is_alive() # This variable is not used later, can be removed if not needed

    if not attacker.is_alive():
        # Character died from status effects (e.g., poison)
        # notification_parts already contains death messages from tick_status_effects
        # Advance turn
        try:
            current_turn_index = current_player_state.turn_order.index(char_id)
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]
            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            next_attacker_name = next_attacker_obj.name if next_attacker_obj else "Unknown"
            notification_parts.append(f"{attacker.name} cannot take further actions this turn. Advancing to {next_attacker_name}.")
            return "\n".join(notification_parts)
        except (ValueError, IndexError) as e:
            # If advancing fails, combat state is critically corrupted.
            current_player_state.is_in_combat = False # Attempt to stop combat
            notification_parts.append(f"Error advancing turn after character succumbed to status effects: {e}. Combat stopped.")
            return "\n".join(notification_parts)

    # Original check for already defeated characters (e.g. by AoE before their turn)
    # This might be redundant if status effects kill them, but good as a fallback.
    if not attacker.is_alive(): # Re-check, though tick_status_effects should handle this.
        try:
            current_turn_index = current_player_state.turn_order.index(char_id)
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]
            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            next_attacker_name = next_attacker_obj.name if next_attacker_obj else "Unknown"
            notification_parts.append(f"{attacker.name} was already defeated. Advancing to {next_attacker_name}.")
            return "\n".join(notification_parts)
        except (ValueError, IndexError) as e:
            current_player_state.is_in_combat = False
            notification_parts.append(f"Error advancing turn for already defeated character: {e}. Combat stopped.")
            return "\n".join(notification_parts)

    action_message_segment = "" # Specific message for the action taken this turn
    turn_advanced = False

    if attacker == current_player_state.player_character: # Player's turn
        if not player_action:
            # This is a prompt FOR the player, not a DM message.
            return f"{attacker.name}'s turn. Type 'attack <target_name>', 'cast <spell_name> [on <target_name>]', or 'pass'."

        action_parts = player_action.lower().split(" ", 1)
        command = action_parts[0]

        if command == "attack":
            if len(action_parts) < 2:
                # This is UI feedback, not a DM message.
                return "Invalid action. Usage: attack <target_name>"
            target_name = action_parts[1]
            target = next((p for p in current_player_state.participants_in_combat
                           if p.name.lower() == target_name.lower() and p.is_alive()), None)
            if target:
                if target == attacker:
                    action_message_segment = f"{attacker.name} wisely decides not to attack themselves."
                else:
                    attack_notification = attacker.attack(target) # This is a DM message part
                    action_message_segment = attack_notification # Store for player feedback
                    if attack_notification and "attacks" in attack_notification: # Check if it's an actual attack message
                        notify_dm_event(dm_manager, attack_notification)
            else:
                # This is UI feedback if target is not found.
                return f"Target '{target_name}' not found, is not alive, or is invalid."
            turn_advanced = True # Attack action consumes the turn
        elif command == "cast":
            if len(action_parts) < 2:
                return "Invalid command. Usage: cast <spell_name> [on <target_name>]"

            spell_and_target_str = action_parts[1]
            # spell_name_str needs to be extracted carefully.
            # Target name is optional and follows " on ".
            # Spell names can have spaces.

            match = re.match(r"(.+?)(?:\s+on\s+(.+))?$", spell_and_target_str, re.IGNORECASE)

            if not match:
                # This regex should almost always match if action_parts[1] is not empty.
                # This case might occur if spell_and_target_str is empty or malformed in an unexpected way.
                return "Invalid cast command format. Usage: cast <spell_name> [on <target_name>]"

            spell_name_str = match.group(1).strip().title() # .title() to match SPELLBOOK keys
            target_name = None
            if match.group(2):
                target_name = match.group(2).strip()

            target_object = None
            if target_name:
                # Find the target in participants_in_combat
                target = next((p for p in current_player_state.participants_in_combat
                               if p.name.lower() == target_name.lower() and p.is_alive()), None)
                if not target:
                    return f"Target '{target_name}' not found or is not alive."
                target_object = target

            # Attacker is the player character, who has the cast_spell method
            success, message = attacker.cast_spell(spell_name_str, target_object)

            if success:
                notify_dm_event(dm_manager, message) # Send full spell outcome to DM
                action_message_segment = message # This will be part of player UI feedback
                turn_advanced = True
            else:
                return message # Return error message from cast_spell (e.g., "Spell not found", "No slots")
                # No turn advancement on failed cast due to bad input/unavailable resources

        elif command == "pass":
            action_message_segment = f"{attacker.name} passes their turn."
            notify_dm_event(dm_manager, action_message_segment) # Notify DM about passing
            turn_advanced = True
        else:
            # This is UI feedback for invalid command.
            return f"Invalid action: '{player_action}'. Type 'attack <target_name>', 'cast <spell_name> [on <target_name>]', or 'pass'."
            # For invalid actions, we don't advance the turn, player gets another try.

    else: # NPC's turn
        # Simple AI: Attack the player character if alive
        target = current_player_state.player_character
        if target and target.is_alive():
            attack_notification = attacker.attack(target) # DM message part
            action_message_segment = attack_notification # Store for player feedback
            if attack_notification and "attacks" in attack_notification: # Check if it's an actual attack message
                 notify_dm_event(dm_manager, attack_notification)
        elif target and not target.is_alive():
            action_message_segment = f"{attacker.name} sees the player {target.name} is defeated and looks for other targets (but finds none)." # DM message part
            # In a more complex scenario, NPC might choose another NPC or take other actions.
        else: # Should not happen if player_character is always set in PlayerState
             action_message_segment = f"{attacker.name} is confused and has no target." # DM message part
        turn_advanced = True # NPC turn always results in an action or attempted action

    if action_message_segment:
        notification_parts.append(action_message_segment)

    # Advance turn if an action was taken or turn was passed
    if turn_advanced:
        try:
            current_turn_index = current_player_state.turn_order.index(char_id)
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]

            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            if next_attacker_obj:
                 notification_parts.append(f"Next up: {next_attacker_obj.name}.")
            else: # Should ideally not happen if turn_order IDs are valid
                notification_parts.append(f"Next up: ID {current_player_state.current_turn_character_id} (name unknown).")

        except ValueError:
            notification_parts.append(f"Error: Character {char_id} not found in turn order. Combat state might be corrupted.")
            current_player_state.is_in_combat = False # Attempt to stop combat
        except IndexError:
            notification_parts.append(f"Error: Problem advancing turn. Combat state might be corrupted.")
            current_player_state.is_in_combat = False # Attempt to stop combat

    return "\n".join(notification_parts)

def check_combat_end_condition(player: Player, npcs: list[NPC], current_player_state: PlayerState) -> tuple[bool, str]:
    """
    Checks if combat has ended due to player defeat or all NPCs being defeated.
    Resets combat state if an end condition is met.
    """
    if not current_player_state.is_in_combat:
        return (not current_player_state.is_in_combat, "") # Already ended

    if not isinstance(player, Player) or not all(isinstance(npc, NPC) for npc in npcs):
        # This indicates a programming error if wrong types are passed.
        return (False, "Error: Type mismatch in check_combat_end_condition arguments.")

    player_defeated = not player.is_alive()
    all_npcs_defeated = bool(npcs) and all(not npc.is_alive() for npc in npcs)

    end_condition_met = False
    notification = ""

    if player_defeated:
        notification = f"Player {player.name} ({player.id}) has been defeated! Combat ends."
        end_condition_met = True
    elif all_npcs_defeated:
        notification = f"All NPCs ({', '.join(npc.name for npc in npcs)}) defeated! Combat ends."
        end_condition_met = True

    if end_condition_met:
        current_player_state.is_in_combat = False
        current_player_state.participants_in_combat = [] # Clear participants list
        current_player_state.current_turn_character_id = None
        current_player_state.turn_order = []
        return (True, notification)

    return (False, "")

# import google.generativeai as genai # This will be needed eventually
import os

# Placeholder for actual DM interaction
class GeminiDM:
    def __init__(self, model_name="gemini-1.5-flash-latest"):
        # For now, we won't initialize the actual API
        # genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        # self.model = genai.GenerativeModel(model_name)
        # self.chat = self.model.start_chat(history=[])
        print("GeminiDM initialized (mocked).")

    def send_message(self, message, stream=False):
        # Adjusted to handle potential multi-line messages better for console readability
        print(f"DM Received (stream={stream}):\n---\n{message}\n---")
        # Mocked response based on input
        if "hello" in message.lower():
            response = "Hello there! How can I help you today?"
        elif "fight" in message.lower() and not main_player_state.is_in_combat: # Check global state for this mock
            response = "A wild goblin appears!" # This will be overridden by combat logic if it starts
        elif main_player_state.is_in_combat:
            response = f"DM acknowledges the turn events." # Generic ack for multi-line
        else:
            response = f"DM echoes: {message}"

        print(f"DM Responds:\n---\n{response}\n---")
        if stream:
            # Streaming a multi-line response might look odd here, but for testing it's fine.
            # Real streaming would handle chunks of the actual response.
            for chunk in response.replace('\n', ' ').split(): # Replace newlines for stream test
                print(chunk, end=" ", flush=True)
            print()
        return response

def notify_dm_event(dm_manager, message: str):
    """Sends a formatted game event message to the DM."""
    if not message: # Do not send empty messages
        return
    try:
        # Make sure dm_manager is not None and has send_message
        if dm_manager and hasattr(dm_manager, 'send_message'):
            dm_manager.send_message(f"Game Event: {message}", stream=False)
        else:
            print(f"LOG: DM Manager not available. Event: {message}") # Fallback log
    except Exception as e:
        print(f"LOG: Error sending DM notification: {e}. Event: {message}") # Fallback log

# Global type hint for app can now safely use GamePlayFrame as it's defined in both paths
# (either imported from ui or defined as MockGamePlayFrame)

# --- Global PlayerState and Mock Entities for main game loop ---
import data_loader # Import the data_loader module

hero: Player = None
mock_npcs_in_encounter: list[NPC] = []
main_player_state: PlayerState = None
dm: GeminiDM = None # Global DM instance
app: GamePlayFrame = None # This will be an instance of ui.GamePlayFrame or MockGamePlayFrame

def get_fresh_npcs() -> list[NPC]:
    """Loads NPCs from data files using the DataLoader."""
    # This now uses the DataLoader to get NPC instances
    # Ensure your data_loader.py has load_npcs_from_directory implemented correctly
    loaded_npcs = data_loader.load_npcs_from_directory("data/NPCs")
    if not loaded_npcs:
        # Fallback or error handling if no NPCs are loaded
        # For testing, we might want to ensure at least one NPC is available.
        # This could be a place to create a default NPC if loading fails,
        # or raise an error, or ensure test files are always present.
        print("Warning: No NPCs loaded from data_loader. Creating a fallback NPC for testing.")
        fallback_dialogue = {
            "greetings": {"npc_text": "Fallback says hello.", "player_choices": [{"text": "Bye", "next_key": "farewell"}]},
            "farewell": {"npc_text": "Fallback says goodbye.", "player_choices": []}
        }
        return [NPC(id="fallback_001", name="Fallback NPC", max_hp=10, combat_stats={}, base_damage_dice="1d4", dialogue_responses=fallback_dialogue)]
    return loaded_npcs


def process_player_input(input_text: str):
    global hero, mock_npcs_in_encounter, main_player_state, dm, app

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
            # We might want to ensure that after exit_callback, the function returns.
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
                        item_data = game_state.ITEM_DATABASE.get(item_id)
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
                        item_data = game_state.ITEM_DATABASE.get(item_id)
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
                            item_data = game_state.ITEM_DATABASE.get(item_id)
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
                            item_data = game_state.ITEM_DATABASE.get(item_id)
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
                        success, message = game_state.player_buys_item(hero, npc, item_id_to_buy)
                        app.add_narration(message)
                        app.update_hp(f"{hero.current_hp}/{hero.max_hp}") # Refresh UI

                        # Re-display buy prompt
                        node_to_display = npc.get_dialogue_node("buy_items_prompt")
                        sells_item_ids_refresh = getattr(npc, 'sells_item_ids', [])
                        dynamic_choices_refresh = []
                        if sells_item_ids_refresh:
                            for item_id_refresh in sells_item_ids_refresh:
                                item_data_refresh = game_state.ITEM_DATABASE.get(item_id_refresh)
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
                        success, message = game_state.player_sells_item(hero, npc, item_id_to_sell)
                        app.add_narration(message)
                        app.update_hp(f"{hero.current_hp}/{hero.max_hp}") # Refresh UI

                        # Re-display sell prompt
                        node_to_display = npc.get_dialogue_node("sell_items_prompt")
                        player_inventory_refresh = hero.inventory
                        dynamic_choices_refresh = []
                        if player_inventory_refresh:
                            for item_id_refresh in player_inventory_refresh:
                                item_data_refresh = game_state.ITEM_DATABASE.get(item_id_refresh)
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
            mock_npcs_in_encounter = get_fresh_npcs() # Refresh NPCs
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

        else: # Skill checks or general message
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
    if app: app.add_narration("Save Game clicked (not implemented yet).")
    print("Dummy save_game_callback called")

def dummy_load():
    if app: app.add_narration("Load Game clicked (not implemented yet).")
    print("Dummy load_game_callback called")

def dummy_exit():
    global app
    # Use the global flag that was set at the start of main.py
    if not is_test_mode_check_for_import: # Normal GUI mode
        if app and hasattr(app, 'master') and app.master:
            # This implies app is the real GamePlayFrame from ui.py
            app.master.destroy()
        else:
            print("Attempting to exit GUI mode, but app or app.master not found.")
    else: # Test mode
        # app is expected to be MockGamePlayFrame
        print("UI_MOCK_ACTION: exit_callback called in TEST MODE. Setting _test_destroyed_flag.")
        if app and hasattr(app, '_test_destroyed_flag'):
            app._test_destroyed_flag = True
        else:
            print("UI_MOCK_ACTION: exit_callback called (test mode), but app or _test_destroyed_flag not available for MockGamePlayFrame.")

def main():
    global hero, mock_npcs_in_encounter, main_player_state, dm, app
    print("Starting game...")

    dm = GeminiDM()

    hero_player_data = {
        "id": "hero_1", "name": "Hero", "max_hp": 100,
        "combat_stats": {'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2, 'initiative_bonus': 3},
        "base_damage_dice": "1d8",
        "ability_scores": {"strength": 16, "dexterity": 14, "constitution": 15, "intelligence": 10, "wisdom": 12, "charisma": 13},
        "skills": ["athletics", "perception", "lockpicking", "persuasion", "stealth"],
        "proficiencies": {"skills": ["athletics", "lockpicking", "stealth"]},
        "equipment": {"weapon": "long_sword", "armor": "leather_armor"}
    }
    hero = Player(player_data=hero_player_data)
    mock_npcs_in_encounter = get_fresh_npcs() # This now uses data_loader
    main_player_state = PlayerState(player_character=hero)

    # is_test_mode = (os.getenv("RUNNING_INTERACTIVE_TEST") == "true") # Already determined by is_test_mode_check_for_import
    global app # Ensure app is treated as global for assignment here

    if not is_test_mode_check_for_import:
        # This block runs if it's NOT test mode (i.e., normal GUI execution)
        # Ensure tkinter and GamePlayFrame are available (already imported conditionally)
        root = tk.Tk()
        app = GamePlayFrame(master=root,
                          process_input_callback=process_player_input,
                          save_game_callback=dummy_save,
                          load_game_callback=dummy_load,
                          exit_callback=dummy_exit)
        app.add_narration("Welcome to the Text Adventure RPG!")
        app.add_narration("Type 'talk to 엘라라' to start a conversation, or 'fight' to battle goblins.")
        app.add_narration("You can also 'use <skill> on <target> (DC <value>)' or 'quit'.")
        app.update_hp(f"{hero.current_hp}/{hero.max_hp}")
        root.mainloop()
    else:
        # Test mode execution (is_test_mode_check_for_import is true)
        # GamePlayFrame from ui.py is the console-logging version
        app = GamePlayFrame(master=None, # master=None is handled by ui.py's test mode
                            process_input_callback=process_player_input,
                            save_game_callback=dummy_save,
                            load_game_callback=dummy_load,
                            exit_callback=dummy_exit)

        print("--- RUNNING INTERACTIVE TEST HARNESS (Console Mode) ---")
        # Initial "UI" updates for console
        app.add_narration("Welcome to the Text Adventure RPG! (Console Test Mode)")
        app.add_narration("Type 'talk to 엘라라' to start a conversation, or 'fight' to battle goblins.")
        app.add_narration("You can also 'use <skill> on <target> (DC <value>)' or 'quit'.")
        app.update_hp(f"{hero.current_hp}/{hero.max_hp}")

        test_inputs = [
            "talk to 엘라라",
            "1", # 마을에 대해 알려주세요.
            "1", # 고대 유물에 대해 아는 것이 있나요? (from about_village)
            "quit" # Terminate mid-dialogue
        ]
        for test_input in test_inputs:
            print(f"\nSimulating input: {test_input}")
            # Check if app was 'destroyed' by the previous input (e.g. "quit")
            # For MockGamePlayFrame, is_destroyed() checks _test_destroyed_flag
            if app.is_destroyed():
                print("Test harness: UI (console mock) was 'destroyed'. Stopping simulation.")
                break
            process_player_input(test_input)

        print("--- INTERACTIVE TEST HARNESS COMPLETE (Console Mode) ---")

if __name__ == "__main__":
    main()
