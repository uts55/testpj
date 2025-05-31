from game_state import PlayerState, determine_initiative

# --- Mock Objects for Demonstration ---
class MockPlayer:
    def __init__(self, id, hp, initiative_bonus):
        self.id = id
        self.current_hp = hp
        self.combat_stats = {'initiative_bonus': initiative_bonus}

class MockNPC:
    def __init__(self, id, hp, initiative_bonus):
        self.id = id
        self.current_hp = hp # Assuming NPCs also use 'current_hp' for consistency
        self.combat_stats = {'initiative_bonus': initiative_bonus}

# --- Global PlayerState instance for demonstration ---
# In a real application, this might be managed differently (e.g., part of a game class)
# player_state_instance = PlayerState() # We'll create fresh instances in main for clarity

# --- Combat Flow Functions ---

def start_combat(player: MockPlayer, npcs: list[MockNPC], current_player_state: PlayerState) -> str:
    """
    Initializes combat, sets turn order, and notifies the DM.
    """
    current_player_state.is_in_combat = True

    all_participants = [player] + npcs
    # Ensure participants have 'id' and 'combat_stats' as expected by determine_initiative
    # The mock objects are created with these, real objects would need to conform.
    current_player_state.participants_in_combat = [p.id for p in all_participants]

    current_player_state.turn_order = determine_initiative(all_participants)

    if not current_player_state.turn_order:
        current_player_state.is_in_combat = False
        return "Combat could not start: no participants or failed initiative determination."

    current_player_state.current_turn_character_id = current_player_state.turn_order[0]

    turn_order_str = ", ".join(map(str, current_player_state.turn_order))
    return f"Combat started! Turn order: {turn_order_str}. First up: {current_player_state.current_turn_character_id}."

def process_combat_turn(current_player_state: PlayerState) -> str:
    """
    Processes the current character's turn and advances to the next.
    """
    if not current_player_state.is_in_combat or not current_player_state.turn_order:
        return "Cannot process turn: not in combat or turn order is empty."

    if not current_player_state.current_turn_character_id:
        # This might happen if combat ended and state was cleared before this function was called
        return "Cannot process turn: current_turn_character_id is not set."

    char_id = current_player_state.current_turn_character_id
    notification = f"{char_id}'s turn."

    # Placeholder for actual action selection and execution
    # print(f"Action placeholder for {char_id}")

    # Advance turn
    try:
        current_turn_index = current_player_state.turn_order.index(char_id)
        next_turn_index = (current_turn_index + 1) % len(current_player_state.turn_order)
        current_player_state.current_turn_character_id = current_player_state.turn_order[next_turn_index]
    except ValueError:
        # Should not happen if char_id is always from turn_order and turn_order is not modified externally mid-turn
        return f"Error: Character {char_id} not found in turn order. Combat state might be corrupted."
    except IndexError:
        # Should not happen with modulo arithmetic if turn_order is not empty
        return "Error: Problem advancing turn due to turn order indexing. Combat state might be corrupted."

    return notification

def check_combat_end_condition(player: MockPlayer, npcs: list[MockNPC], current_player_state: PlayerState) -> tuple[bool, str]:
    """
    Checks if combat has ended due to player defeat or all NPCs being defeated.
    Resets combat state if an end condition is met.
    """
    if not current_player_state.is_in_combat:
        # If called when not in combat, it means combat already ended or never started.
        # Return True if it's already marked as not in combat, as an "end condition" was previously met.
        return (not current_player_state.is_in_combat, "")

    player_defeated = player.current_hp <= 0
    # Ensure npcs list is not empty before checking all()
    all_npcs_defeated = bool(npcs) and all(npc.current_hp <= 0 for npc in npcs)


    end_condition_met = False
    notification = ""

    if player_defeated:
        notification = f"Player {player.id} has been defeated! Combat ends."
        end_condition_met = True
    elif all_npcs_defeated:
        notification = "All enemies defeated! Combat ends."
        end_condition_met = True

    if end_condition_met:
        current_player_state.is_in_combat = False
        current_player_state.participants_in_combat = []
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
main_player_state = PlayerState()
hero = MockPlayer(id="Hero", hp=100, initiative_bonus=3)
# Initialize with a couple of NPCs by default for testing "fight" command
mock_npcs_in_encounter = [
    MockNPC(id="Goblin_Alpha", hp=30, initiative_bonus=1),
    MockNPC(id="Goblin_Beta", hp=25, initiative_bonus=0)
]

def main():
    print("Starting game...")
    # dm = GeminiDM() # Initialize your actual DM here eventually
    dm = GeminiDM() # Using the mock DM for now

    # Initial message to DM
    # response = dm.send_message("Hello DM, the game is starting.", stream=True)
    # print(f"\nInitial DM response: {response}")

    while True:
        player_input = input("You: ")
        if player_input.lower() == "quit":
            print("Exiting game.")
            break

        dm_message_to_send = ""
        combat_messages = []

        if main_player_state.is_in_combat:
            # --- COMBAT LOGIC ---
            # Player input during combat could be "attack goblin_alpha", "hit hero", "next", etc.
            # For now, any input progresses the turn, but we can add simple damage simulation.

            # Simplified damage simulation for testing:
            if player_input.lower().startswith("hit "):
                parts = player_input.split(" ")
                if len(parts) == 2:
                    target_id = parts[1]
                    damage = 10 # Fixed damage for simulation
                    if target_id == hero.id:
                        hero.current_hp -= damage
                        main_player_state.take_damage(damage) # Assuming PlayerState also tracks player HP
                        combat_messages.append(f"DEBUG: Hero takes {damage} damage. HP: {hero.current_hp}")
                    else:
                        target_npc = next((npc for npc in mock_npcs_in_encounter if npc.id.lower() == target_id.lower()), None)
                        if target_npc:
                            target_npc.current_hp -= damage
                            combat_messages.append(f"DEBUG: {target_npc.id} takes {damage} damage. HP: {target_npc.current_hp}")
                        else:
                            combat_messages.append(f"DEBUG: Target {target_id} not found for 'hit' command.")

            # Always process turn and check end condition
            turn_notification = process_combat_turn(main_player_state)
            combat_messages.append(turn_notification)

            ended, end_notification = check_combat_end_condition(hero, mock_npcs_in_encounter, main_player_state)
            if ended:
                combat_messages.append(end_notification)

            # Join messages with newline, filtering out any potential None or empty strings
            dm_message_to_send = "\n".join(filter(None, combat_messages))

        elif player_input.lower() == "fight":
            if not main_player_state.is_in_combat:
                # (Re-)initialize NPCs for a new fight if desired, or use existing ones
                # For this test, we'll re-use/re-initialize mock_npcs_in_encounter if they were defeated.
                if all(npc.current_hp <= 0 for npc in mock_npcs_in_encounter):
                    print("DEBUG: All NPCs were defeated. Resetting them for a new fight.")
                    mock_npcs_in_encounter[0].current_hp = 30 # Reset HP
                    mock_npcs_in_encounter[1].current_hp = 25 # Reset HP
                if hero.current_hp <= 0:
                    hero.current_hp = 100 # Revive hero for a new fight
                    main_player_state.current_hp = 100 # Reset PlayerState HP

                start_message = start_combat(hero, mock_npcs_in_encounter, main_player_state)
                dm_message_to_send = start_message
            else:
                dm_message_to_send = "Already in combat!"
        else:
            # --- NON-COMBAT LOGIC ---
            dm_message_to_send = player_input


        if dm_message_to_send:
            # print(f"\nSending to DM: '{dm_message_to_send}'") # Debugging what's sent
            response = dm.send_message(dm_message_to_send, stream=True)
            # print(f"DM: {response}") # Raw response if not streaming

        # If combat ended this turn, print a clear "Combat Over" message after DM response
        if not main_player_state.is_in_combat and any("Combat ends." in msg for msg in combat_messages):
            print("\n--- Combat Over ---")


if __name__ == "__main__":
    # This replaces the old demonstration block
    main()
