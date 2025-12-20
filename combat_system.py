
import re
from game_state import PlayerState, Player, NPC, Character, determine_initiative

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

    turn_advanced = False
    action_message_segment = "" # To be added to notification_parts

    if isinstance(attacker, Player):
        if not player_action:
            action_message_segment = f"It is your turn, {attacker.name}. What do you do? (Type 'attack <target>', 'cast <spell> [on <target>]', or 'pass')"
            turn_advanced = False # Pending player input
        else:
            # Process player command
            command_parts = player_action.lower().split()
            command = command_parts[0]
            action_parts = player_action.split() # Keep original case for names if needed, though we use lower for matching

            if command == "attack":
                if len(action_parts) < 2:
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
