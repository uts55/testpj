from game_state import PlayerState, determine_initiative, Player, NPC, Character

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

def process_combat_turn(current_player_state: PlayerState, player_action: str = "") -> str:
    """
    Processes the current character's turn: handles action, attack, and advances to the next.
    Returns a message for the DM or player.
    """
    if not current_player_state.is_in_combat or not current_player_state.turn_order:
        return "Cannot process turn: not in combat or turn order is empty."

    if not current_player_state.current_turn_character_id:
        return "Cannot process turn: current_turn_character_id is not set."

    char_id = current_player_state.current_turn_character_id
    attacker = next((p for p in current_player_state.participants_in_combat if p.id == char_id), None)

    if attacker is None:
        return f"Error: Attacker with ID {char_id} not found in participants list. Combat state corrupted."

    if not attacker.is_alive():
        # Skip turn if the current character is not alive (e.g. defeated by AoE before their turn)
        # Advance turn
        try:
            current_turn_index = current_player_state.turn_order.index(char_id)
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]
            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            next_attacker_name = next_attacker_obj.name if next_attacker_obj else "Unknown"
            return f"{attacker.name} is defeated and cannot take a turn. Advancing to {next_attacker_name}."
        except (ValueError, IndexError) as e:
            return f"Error advancing turn after defeated character: {e}. Combat state corrupted."


    action_message = ""
    turn_advanced = False

    if attacker == current_player_state.player_character: # Player's turn
        if not player_action:
            return f"{attacker.name}'s turn. Type 'attack <target_name>' or 'pass'."

        action_parts = player_action.lower().split(" ", 1)
        command = action_parts[0]

        if command == "attack":
            if len(action_parts) < 2:
                return "Invalid action. Usage: attack <target_name>"
            target_name = action_parts[1]
            target = next((p for p in current_player_state.participants_in_combat
                           if p.name.lower() == target_name.lower() and p.is_alive()), None)
            if target:
                if target == attacker:
                    action_message = f"{attacker.name} wisely decides not to attack themselves."
                else:
                    action_message = attacker.attack(target)
            else:
                action_message = f"Target '{target_name}' not found, is not alive, or is invalid."
            turn_advanced = True # Attack action consumes the turn
        elif command == "pass":
            action_message = f"{attacker.name} passes their turn."
            turn_advanced = True
        else:
            action_message = f"Invalid action: '{player_action}'. Type 'attack <target_name>' or 'pass'."
            # For invalid actions, we don't advance the turn, player gets another try.
            return action_message

    else: # NPC's turn
        # Simple AI: Attack the player character if alive
        target = current_player_state.player_character
        if target and target.is_alive():
            action_message = attacker.attack(target)
        elif target and not target.is_alive():
            action_message = f"{attacker.name} sees the player {target.name} is defeated and looks for other targets (but finds none)."
            # In a more complex scenario, NPC might choose another NPC or take other actions.
        else: # Should not happen if player_character is always set in PlayerState
             action_message = f"{attacker.name} is confused and has no target."
        turn_advanced = True # NPC turn always results in an action or attempted action

    # Advance turn if an action was taken or turn was passed
    if turn_advanced:
        try:
            current_turn_index = current_player_state.turn_order.index(char_id)
            # Ensure all participants in turn_order are still valid (alive) or skip them
            # This simple advance just goes to next ID, assumes check_combat_end or next turn processing handles defeated chars
            next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
            current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]

            # Append next turn info to the message
            next_attacker_obj = next((p for p in current_player_state.participants_in_combat if p.id == current_player_state.current_turn_character_id), None)
            if next_attacker_obj:
                 action_message += f"\nNext up: {next_attacker_obj.name}."
            else: # Should ideally not happen if turn_order IDs are valid
                action_message += f"\nNext up: ID {current_player_state.current_turn_character_id} (name unknown)."

        except ValueError:
            return f"{action_message}\nError: Character {char_id} not found in turn order. Combat state might be corrupted."
        except IndexError:
            return f"{action_message}\nError: Problem advancing turn. Combat state might be corrupted."

    return action_message

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

# --- Global PlayerState and Mock Entities for main game loop ---
# These will be properly initialized in main() using the real classes
hero: Player = None # Will be Player("Hero", ...)
mock_npcs_in_encounter: list[NPC] = [] # Will be [NPC(...), NPC(...)]
main_player_state: PlayerState = None # Will be PlayerState(hero)


def main():
    print("Starting game...")
    # dm = GeminiDM() # Initialize your actual DM here eventually
    dm = GeminiDM() # Using the mock DM for now

    # Initial message to DM
    # response = dm.send_message("Hello DM, the game is starting.", stream=True)
    # print(f"\nInitial DM response: {response}")

    # Initialize global game objects (hero, NPCs, player_state)
    # This needs to be done once, outside the loop, or when a new game starts.
    # For now, we'll do it here.
    global hero, mock_npcs_in_encounter, main_player_state
    hero = Player(id="hero_1", name="Hero", max_hp=100,
                  combat_stats={'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2, 'initiative_bonus': 3},
                  base_damage_dice="1d8")

    # Reset or initialize NPCs for encounters
    # It's better to create new NPC instances for each fight or reset them fully.
    def get_fresh_npcs():
        return [
            NPC(id="goblin_a", name="Goblin Alpha", max_hp=30,
                combat_stats={'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1, 'initiative_bonus': 1},
                base_damage_dice="1d6", dialog="Grrr!"),
            NPC(id="goblin_b", name="Goblin Beta", max_hp=25,
                combat_stats={'armor_class': 10, 'attack_bonus': 2, 'damage_bonus': 0, 'initiative_bonus': 0},
                base_damage_dice="1d4", dialog="Me hit you!")
        ]
    mock_npcs_in_encounter = get_fresh_npcs()

    main_player_state = PlayerState(player_character=hero)


    while True:
        player_input_for_dm = "" # What the player types, to be sent to DM if not a combat command
        player_action_for_combat = "" # Specific combat action for process_combat_turn

        raw_player_input = input("You: ")
        if raw_player_input.lower() == "quit":
            print("Exiting game.")
            break

        dm_message_to_send = "" # This will be the primary message for the DM
        ui_feedback = [] # Messages for the player's UI, not for DM (e.g., invalid command prompts)

        if main_player_state.is_in_combat:
            # --- COMBAT LOGIC ---
            # Player input during combat is an action for their turn.
            player_action_for_combat = raw_player_input

            # Process the turn. This will handle player action or NPC AI.
            # It returns a message that is usually for the DM (attack results, etc.)
            # or a prompt for the player if more input is needed (e.g. "Your turn. Type 'attack...'")
            turn_result_message = process_combat_turn(main_player_state, player_action_for_combat)

            # Check if the message is a prompt for the player or a DM message
            if "Type 'attack" in turn_result_message or "Invalid action" in turn_result_message or "Target '" in turn_result_message:
                ui_feedback.append(turn_result_message)
            else: # It's a DM message (attack, pass, NPC action)
                dm_message_to_send = turn_result_message

            # Check for combat end after processing the turn
            ended, end_notification = check_combat_end_condition(hero, mock_npcs_in_encounter, main_player_state)
            if ended:
                if dm_message_to_send: # Append end notification to existing DM message
                    dm_message_to_send += "\n" + end_notification
                else: # Or set it as the DM message if no other action message this turn
                    dm_message_to_send = end_notification
                ui_feedback.append("\n--- Combat Over ---")


        elif raw_player_input.lower() == "fight":
            if not main_player_state.is_in_combat:
                # Reset hero and NPCs for a new fight
                hero.current_hp = hero.max_hp # Heal hero
                hero.inventory = [] # Clear inventory for a fresh start if desired
                # It's important that PlayerState's player_character IS hero, so this heals the one PlayerState uses.

                mock_npcs_in_encounter = get_fresh_npcs() # Get fresh NPCs

                # Ensure PlayerState is correctly re-initialized for combat if needed,
                # or simply reset its combat-specific attributes.
                # PlayerState already holds the 'hero' instance.
                # start_combat will reset participants, turn order, etc.

                start_message = start_combat(hero, mock_npcs_in_encounter, main_player_state)
                dm_message_to_send = start_message
            else:
                ui_feedback.append("Already in combat!")
        else:
            # --- NON-COMBAT LOGIC ---
            # Player input is a general message to the DM
            dm_message_to_send = raw_player_input


        # Print UI feedback first
        if ui_feedback:
            for msg in ui_feedback:
                print(msg)

        # Then send any message intended for the DM
        if dm_message_to_send:
            response = dm.send_message(dm_message_to_send, stream=True)
            # print(f"DM: {response}") # Raw response if not streaming if needed for debug

if __name__ == "__main__":
    # This replaces the old demonstration block
    main()
