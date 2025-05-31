import random

# Temporary Item Database (simulates loading from JSON)
# In a real system, this would be loaded from data/Items/*.json
ITEM_DATABASE = {
    "short_sword": {
        "id": "short_sword", "name": "Short Sword", "type": "weapon",
        "damage_dice": "1d6", "attack_bonus": 1, "damage_bonus": 0
    },
    "long_sword": { # Added for more testing options
        "id": "long_sword", "name": "Long Sword", "type": "weapon",
        "damage_dice": "1d8", "attack_bonus": 1, "damage_bonus": 1
    },
    "leather_armor": {
        "id": "leather_armor", "name": "Leather Armor", "type": "armor",
        "ac_bonus": 2
    },
    "wooden_shield": {
        "id": "wooden_shield", "name": "Wooden Shield", "type": "shield",
        "ac_bonus": 1
    },
    "steel_shield": { # Added for more testing options
        "id": "steel_shield", "name": "Steel Shield", "type": "shield",
        "ac_bonus": 2
    }
}

class Character:
    """
    Base class for all characters in the game, including players and NPCs.
    """
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str):
        """
        Initializes a new character.

        Args:
            id: Unique identifier for the character.
            name: Display name of the character.
            max_hp: Maximum health points.
            combat_stats: Dictionary of combat-related statistics.
                          Example keys: 'armor_class', 'attack_bonus',
                                        'damage_bonus', 'initiative_bonus'.
            base_damage_dice: String representation of base damage dice (e.g., "1d4").
        """
        if not isinstance(id, str) or not id.strip():
            raise ValueError("Character ID must be a non-empty string.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Character name must be a non-empty string.")
        if not isinstance(max_hp, int) or max_hp <= 0:
            raise ValueError("max_hp must be a positive integer.")
        if not isinstance(combat_stats, dict):
            raise TypeError("combat_stats must be a dictionary.")
        if not isinstance(base_damage_dice, str) or not base_damage_dice.strip(): # Basic check, can be more complex
            raise ValueError("base_damage_dice must be a non-empty string (e.g., '1d6').")

        self.id = id
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp  # Characters start at full health
        self.combat_stats = combat_stats
        self.base_damage_dice = base_damage_dice
        self.status_effects = []

    def add_status_effect(self, effect_name: str, duration: int, potency: int):
        """Adds or updates a status effect."""
        for effect in self.status_effects:
            if effect['name'] == effect_name:
                effect['duration'] = duration
                effect['potency'] = potency
                return f"{self.name}'s {effect_name} has been refreshed to {duration} turns."
        self.status_effects.append({'name': effect_name, 'duration': duration, 'potency': potency})
        return f"{self.name} is now {effect_name} for {duration} turns."

    def remove_status_effect(self, effect_name: str):
        """Removes a status effect by name."""
        self.status_effects = [effect for effect in self.status_effects if effect['name'] != effect_name]

    def tick_status_effects(self) -> list[str]:
        """Applies effects of active status conditions and decrements their duration."""
        messages = []
        for effect in list(self.status_effects): # Iterate over a copy
            if effect['name'] == 'poison':
                self.take_damage(effect['potency'])
                messages.append(f"{self.name} took {effect['potency']} damage from poison.")
                if not self.is_alive():
                    messages.append(f"{self.name} succumbed to poison.")
                    break  # Stop processing effects if character dies

            effect['duration'] -= 1
            if effect['duration'] <= 0:
                self.remove_status_effect(effect['name']) # Use the new method
                messages.append(f"{self.name} is no longer {effect['name']}.")
        return messages

    def take_damage(self, amount: int):
        """
        Reduces the character's current HP by the specified amount.
        HP cannot go below 0.

        Args:
            amount: The amount of damage to take. Must be a non-negative integer.

        Raises:
            TypeError: If amount is not an integer.
            ValueError: If amount is negative.
        """
        if not isinstance(amount, int):
            raise TypeError("Damage amount must be an integer.")
        if amount < 0:
            raise ValueError("Damage amount cannot be negative.")

        self.current_hp = max(0, self.current_hp - amount)
        # print(f"{self.name} took {amount} damage. Current HP: {self.current_hp}/{self.max_hp}") # Debug

    def heal(self, amount: int):
        """
        Increases the character's current HP by the specified amount.
        HP cannot exceed max_hp.

        Args:
            amount: The amount of HP to restore. Must be a non-negative integer.

        Raises:
            TypeError: If amount is not an integer.
            ValueError: If amount is negative.
        """
        if not isinstance(amount, int):
            raise TypeError("Heal amount must be an integer.")
        if amount < 0:
            raise ValueError("Heal amount cannot be negative.")

        self.current_hp = min(self.max_hp, self.current_hp + amount)
        # print(f"{self.name} healed {amount} HP. Current HP: {self.current_hp}/{self.max_hp}") # Debug

    def is_alive(self) -> bool:
        """
        Checks if the character is still alive.

        Returns:
            True if current_hp > 0, False otherwise.
        """
        return self.current_hp > 0

    def attack(self, target: 'Character') -> str:
        """
        Executes an attack from this character to the target character.

        Args:
            target: The Character object being attacked.

        Returns:
            A string message describing the attack and its outcome.

        Raises:
            ValueError: If the target is not a Character instance or if base_damage_dice format is invalid.
            TypeError: If target is not of type Character.
        """
        if not isinstance(target, Character):
            raise TypeError("Target must be an instance of Character.")

        # Ensure target is not self to prevent self-harm unless intended by game mechanics (not here)
        if self == target:
            return f"{self.name} cannot attack themselves." # Or raise an error

        dm_message = f"{self.name} attacks {target.name}."

        attack_roll = roll_dice(sides=20) # Standard d20 roll

        # Determine attacker's bonuses and damage dice
        is_player_attacker = isinstance(self, Player)

        current_attack_bonus = self.combat_stats.get('attack_bonus', 0)
        current_damage_bonus = self.combat_stats.get('damage_bonus', 0)
        current_damage_dice_str = self.base_damage_dice # Default for NPCs

        if is_player_attacker:
            player_weapon_stats = self.get_equipped_weapon_stats() # self is a Player instance
            current_damage_dice_str = player_weapon_stats["damage_dice"]
            # Weapon bonuses are added to base combat_stats bonuses
            current_attack_bonus += player_weapon_stats["attack_bonus"]
            current_damage_bonus += player_weapon_stats["damage_bonus"]

        total_attack = attack_roll + current_attack_bonus

        # Determine target's AC
        if isinstance(target, Player):
            target_ac = target.get_effective_armor_class() # Target is a Player instance
        else:
            target_ac = target.combat_stats.get('armor_class', 10) # Target is an NPC

        if total_attack >= target_ac:
            # HIT!
            dm_message += f" d20({attack_roll}) + ATK Bonus({current_attack_bonus}) = {total_attack} vs AC({target_ac}). HIT!"

            num_dice = 1
            dice_sides = 4 # Default to 1d4 if parsing fails for some reason

            try:
                parts = current_damage_dice_str.lower().split('d')
                if len(parts) == 2:
                    num_dice_str, dice_sides_str = parts
                    if not dice_sides_str: # Handles "1d"
                        raise ValueError("Dice sides component is missing.")
                    if not num_dice_str and not dice_sides_str: # Handles "d"
                         raise ValueError("Both number of dice and dice sides components are missing.")
                    if not num_dice_str and dice_sides_str: # Handles "d6"
                        num_dice = 1
                        dice_sides = int(dice_sides_str)
                    else: # Handles "1d6"
                        num_dice = int(num_dice_str)
                        dice_sides = int(dice_sides_str)
                elif len(parts) == 1 and parts[0].isdigit(): # Handles "4" as "1d4" - this is a specific interpretation.
                    # This interpretation might be too lenient. For strict "XdY" or "dY", this block could be removed.
                    # However, the test "test_attack_invalid_dice_format_raises_error_player"
                    # implies "invalid_dice" should fail, which it would if this "elif" is not met.
                    # The problem might be that "invalid_dice" does not trigger int() conversion error,
                    # but goes to the final "else".
                    # Let's keep the existing behavior for "4" becoming "1d4" for now as it was intended.
                    # The main issue is likely the broad "else" not being specific enough.
                    # The original code's "elif len(parts) == 1 and parts[0].isdigit():" path to raise error was incorrect.
                    # It should have been for "invalid_dice" type strings.
                    num_dice = 1
                    dice_sides = int(parts[0])
                    current_damage_dice_str = f"1d{dice_sides}" # Normalize for output message
                    # This specific conversion for "4" to "1d4" might be better handled by ensuring
                    # input dice strings are always "XdY" or "dY" upstream.
                    # For now, to pass the spirit of the original code's intent for this case:
                    # This part is problematic if parts[0] is not a digit.
                    # Let's refine the overall structure.

                # Refined structure:
                # Ensure parts are what we expect for XdY or dY
                if len(parts) != 2:
                    # Check for the "4" becoming "1d4" case, if it's a single number
                    if len(parts) == 1 and parts[0].isdigit():
                        num_dice = 1
                        dice_sides = int(parts[0])
                        current_damage_dice_str = f"1d{dice_sides}" # For message consistency
                    else: # Truly malformed
                        raise ValueError(f"Invalid format. Expected XdY or dY.")
                else: # len(parts) == 2
                    num_dice_str, dice_sides_str = parts
                    if not dice_sides_str: # e.g. "1d"
                        raise ValueError("Dice sides component is missing.")
                    if not num_dice_str: # e.g. "d6"
                        num_dice = 1
                    else:
                        num_dice = int(num_dice_str)
                    dice_sides = int(dice_sides_str)


                if num_dice <= 0 or dice_sides <= 0:
                    raise ValueError(f"Number of dice and sides must be positive. Got: {num_dice}d{dice_sides}")

            except ValueError as e: # Catches int() conversion errors or explicit raises
                raise ValueError(f"Error parsing damage dice '{current_damage_dice_str}' for {self.name}: {e}")


            damage_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
            total_damage = damage_roll + current_damage_bonus
            total_damage = max(0, total_damage) # Damage cannot be negative

            target.take_damage(total_damage)

            dm_message += f" Deals {num_dice}d{dice_sides}({damage_roll}) + DMG Bonus({current_damage_bonus}) = {total_damage} damage."
            dm_message += f" {target.name} HP: {target.current_hp}/{target.max_hp}."

            # Apply poison on 10% chance if target is still alive
            if target.is_alive(): # Only apply poison if the target survived the initial damage
                if random.randint(1, 100) <= 10: # 10% chance
                    # The add_status_effect method now returns a message.
                    # However, the attack method constructs its own dm_message.
                    # For now, we'll let the existing poison message logic in attack() handle it.
                    # If add_status_effect's message were needed here, we'd capture it:
                    # poison_msg = target.add_status_effect(effect_name='poison', duration=3, potency=2)
                    # if poison_msg: dm_message += f" {poison_msg}" # Or integrate it more smoothly
                    target.add_status_effect(effect_name='poison', duration=3, potency=2) # Keep original logic for now
                    dm_message += f" {target.name} has been poisoned!" # Original message for poison

            if not target.is_alive(): # Check again in case poison was instantly lethal (not with current setup, but good practice)
                dm_message += f" {target.name} has been defeated!"
        else:
            # MISS!
            dm_message += f" d20({attack_roll}) + ATK Bonus({current_attack_bonus}) = {total_attack} vs AC({target_ac}). MISS!"

        return dm_message


class Player(Character):
    """
    Represents the player character, inheriting from Character.
    Includes player-specific attributes like equipment.
    """
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str, equipment_data: dict = None): # Added equipment_data
        """
        Initializes a new Player character.

        Args:
            id: Unique identifier for the player.
            name: Display name of the player.
            max_hp: Maximum health points.
            combat_stats: Dictionary of combat-related statistics.
            base_damage_dice: String representation of base damage dice.
            equipment_data: Optional dictionary of item IDs to equip.
        """
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.equipment = {
            "weapon": None,
            "armor": None,
            "shield": None,
            # Future slots: "helmet", "boots", etc.
        }
        self.inventory = []
        # Store base AC, useful if armor is unequipped
        self.base_armor_class = combat_stats.get('armor_class', 10)

        if equipment_data:
            for slot, item_id in equipment_data.items():
                if item_id: # Ensure item_id is not None or empty
                    # We assume equip_item handles checks for valid slot and item_id.
                    # It will print warnings if item/slot is invalid.
                    self.equip_item(item_id, slot)


    def _load_item_data(self, item_id: str) -> dict:
        """Helper to fetch item data from the global ITEM_DATABASE."""
        if not item_id:
            return None
        return ITEM_DATABASE.get(item_id)

    def equip_item(self, item_id: str, slot: str) -> bool:
        """
        Equips an item to the specified slot if the slot exists.
        Returns True if successful, False otherwise.
        Assumes item_id is valid and exists in ITEM_DATABASE for simplicity here.
        A real implementation would check item type against slot type.
        """
        item_data = self._load_item_data(item_id)
        if not item_data:
            print(f"Warning: Item ID '{item_id}' not found in database. Cannot equip.")
            return False

        if slot not in self.equipment:
            print(f"Warning: Slot '{slot}' does not exist.")
            return False

        # Basic type checking for slot
        item_type = item_data.get("type")
        if slot == "weapon" and item_type != "weapon":
            print(f"Warning: Cannot equip item '{item_id}' ({item_type}) in weapon slot.")
            return False
        if slot == "armor" and item_type != "armor":
            print(f"Warning: Cannot equip item '{item_id}' ({item_type}) in armor slot.")
            return False
        if slot == "shield" and item_type != "shield":
            print(f"Warning: Cannot equip item '{item_id}' ({item_type}) in shield slot.")
            return False

        self.equipment[slot] = item_id
        # print(f"{self.name} equipped {item_data.get('name', item_id)} in {slot} slot.") # Debug
        return True

    def unequip_item(self, slot: str) -> str:
        """
        Unequips an item from the specified slot.
        Returns the item_id of the unequipped item, or None if no item was in the slot.
        """
        if slot not in self.equipment:
            print(f"Warning: Slot '{slot}' does not exist.")
            return None

        item_id = self.equipment.get(slot)
        if item_id:
            self.equipment[slot] = None
            # item_name = self._load_item_data(item_id).get('name', item_id) # Debug
            # print(f"{self.name} unequipped {item_name} from {slot} slot.") # Debug
        return item_id

    def get_equipped_weapon_stats(self) -> dict:
        """
        Returns the stats of the equipped weapon.
        Defaults to unarmed strike if no weapon is equipped.
        """
        weapon_id = self.equipment.get("weapon")
        if weapon_id:
            weapon_data = self._load_item_data(weapon_id)
            if weapon_data and weapon_data.get("type") == "weapon":
                return {
                    "damage_dice": weapon_data.get("damage_dice", "1d4"), # Default to 1d4 if missing
                    "attack_bonus": weapon_data.get("attack_bonus", 0),
                    "damage_bonus": weapon_data.get("damage_bonus", 0)
                }
        # Default unarmed strike
        return {"damage_dice": "1d4", "attack_bonus": 0, "damage_bonus": 0}

    def get_equipped_armor_ac_bonus(self) -> int:
        """
        Calculates the total AC bonus from equipped armor and shield.
        """
        total_ac_bonus = 0

        # Armor
        armor_id = self.equipment.get("armor")
        if armor_id:
            armor_data = self._load_item_data(armor_id)
            if armor_data and armor_data.get("type") == "armor":
                total_ac_bonus += armor_data.get("ac_bonus", 0)

        # Shield
        shield_id = self.equipment.get("shield")
        if shield_id:
            shield_data = self._load_item_data(shield_id)
            if shield_data and shield_data.get("type") == "shield":
                total_ac_bonus += shield_data.get("ac_bonus", 0)

        return total_ac_bonus

    def get_effective_armor_class(self) -> int:
        """
        Calculates the player's effective Armor Class including equipped items.
        Uses base_armor_class stored at initialization.
        """
        return self.base_armor_class + self.get_equipped_armor_ac_bonus()

    def add_to_inventory(self, item_name: str):
        """
        Adds an item to the player's inventory.

        Args:
            item_name: The name of the item to add. Must be a non-empty string.

        Raises:
            TypeError: If item_name is not a string.
            ValueError: If item_name is an empty or whitespace-only string.
        """
        if not isinstance(item_name, str):
            raise TypeError("Item name must be a string.")
        if not item_name.strip(): # Check if string is empty or only whitespace
            raise ValueError("Item name cannot be empty or just whitespace.")

        self.inventory.append(item_name)
        # print(f"Added '{item_name}' to inventory. Current inventory: {self.inventory}") # Debug

    def remove_from_inventory(self, item_name: str) -> bool:
        """
        Removes an item from the player's inventory, if it exists.

        Args:
            item_name: The name of the item to remove.

        Returns:
            True if the item was removed, False otherwise.

        Raises:
            TypeError: If item_name is not a string.
        """
        if not isinstance(item_name, str):
            raise TypeError("Item name must be a string.")

        try:
            self.inventory.remove(item_name)
            # print(f"Removed '{item_name}' from inventory. Current inventory: {self.inventory}") # Debug
            return True
        except ValueError:
            # Item not found in inventory
            # print(f"Item '{item_name}' not found in inventory.") # Debug
            return False

class NPC(Character):
    """
    Represents a Non-Player Character, inheriting from Character.
    """
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str, dialog: str = None):
        """
        Initializes a new NPC.

        Args:
            id: Unique identifier for the NPC.
            name: Display name of the NPC.
            max_hp: Maximum health points.
            combat_stats: Dictionary of combat-related statistics.
            base_damage_dice: String representation of base damage dice.
            dialog: Optional dialog string or structure for the NPC.
        """
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.dialog = dialog # NPCs might have specific dialog lines

    # TODO: NPC-specific behaviors, like AI decision-making in combat, dialog trees, etc.


class PlayerState:
    """
    Manages the overall game state, including combat lifecycle and a reference to the player.
    """
    def __init__(self, player_character: Player):
        """
        Initializes the game state.

        Args:
            player_character: The Player object representing the main player.

        Raises:
            TypeError: If player_character is not an instance of Player.
        """
        if not isinstance(player_character, Player):
            raise TypeError("player_character must be an instance of Player.")

        self.player_character = player_character

        # Combat state attributes
        self.participants_in_combat = [] # Now stores Character objects
        self.current_turn_character_id = None # Stores the ID of the current character
        self.turn_order = [] # List of character IDs in turn order
        self.is_in_combat = False

        # print(f"PlayerState initialized for {self.player_character.name}.") # Debug

    def take_damage(self, amount: int):
        """
        Applies damage to the player character.
        HP cannot go below 0. Delegates to the Player character.

        Args:
            amount: The amount of damage to take. Must be a non-negative integer.
        """
        self.player_character.take_damage(amount)
        # print(f"PlayerState: {self.player_character.name} took {amount} damage.") # Debug

    def heal(self, amount: int):
        """
        Heals the player character. Delegates to the Player character.

        Args:
            amount: The amount of HP to restore. Must be a non-negative integer.
        """
        self.player_character.heal(amount)
        # print(f"PlayerState: {self.player_character.name} healed {amount} HP.") # Debug


    def add_to_inventory(self, item_name: str):
        """
        Adds an item to the player character's inventory. Delegates to the Player character.

        Args:
            item_name: The name of the item to add. Must be a non-empty string.
        """
        self.player_character.add_to_inventory(item_name)
        # print(f"PlayerState: Added '{item_name}' to {self.player_character.name}'s inventory.") # Debug

    def remove_from_inventory(self, item_name: str) -> bool:
        """
        Removes an item from the player character's inventory. Delegates to the Player character.

        Args:
            item_name: The name of the item to remove.

        Returns:
            True if the item was removed, False otherwise.
        """
        return self.player_character.remove_from_inventory(item_name)

    def get_status(self) -> str:
        """
        Returns a string summarizing the player character's current HP and inventory.

        Returns:
            A string representing the player character's status.
        """
        pc = self.player_character
        inventory_str = ', '.join(pc.inventory) if pc.inventory else "empty"
        return f"Player: {pc.name}, HP: {pc.current_hp}/{pc.max_hp}, Inventory: [{inventory_str}]"

def roll_dice(sides: int, num_dice: int = 1) -> int:
    """
    Simulates rolling one or more dice with a specified number of sides.

    Args:
        sides: The number of sides on each die (e.g., 6 for a d6).
        num_dice: The number of dice to roll. Defaults to 1.

    Returns:
        The sum of the rolls from all dice.

    Raises:
        TypeError: If sides or num_dice are not integers.
        ValueError: If sides or num_dice are not positive.
    """
    if not isinstance(sides, int) or not isinstance(num_dice, int):
        raise TypeError("Sides and num_dice must be integers.")
    if sides <= 0:
        raise ValueError("Number of sides must be positive.")
    if num_dice <= 0:
        raise ValueError("Number of dice to roll must be positive.")

    total_roll = 0
    for _ in range(num_dice):
        total_roll += random.randint(1, sides)
    return total_roll

def determine_initiative(participants: list) -> list:
    """
    Determines the initiative order for a list of participants.

    Args:
        participants: A list of objects, where each object is expected to have
                      an 'id' attribute and a 'combat_stats' dictionary
                      containing an 'initiative_bonus' key.

    Returns:
        A list of participant IDs sorted by initiative score in descending order.
        Returns an empty list if the input participants list is empty.
    """
    if not participants:
        return []

    initiative_rolls = []
    for participant in participants:
        # Assume participant has 'id' and 'combat_stats' with 'initiative_bonus'
        # Error handling for missing keys could be added here for robustness
        initiative_bonus = participant.combat_stats.get('initiative_bonus', 0)
        roll = roll_dice(sides=20)
        total_initiative = roll + initiative_bonus
        initiative_rolls.append({'id': participant.id, 'initiative': total_initiative})

    # Sort by initiative score in descending order
    # In case of a tie, current sort is stable, preserving original order among tied elements.
    # A secondary sort key (e.g., participant.id) could be added if specific tie-breaking is needed.
    initiative_rolls.sort(key=lambda x: x['initiative'], reverse=True)

    return [entry['id'] for entry in initiative_rolls]

if __name__ == '__main__':
    # The __main__ block in game_state.py is primarily for basic, isolated tests.
    # It has been updated to reflect recent changes to Player and PlayerState constructors.

    print("\n--- Player and PlayerState Demonstration (with Equipment) ---")
    try:
        demo_combat_stats = {'initiative_bonus': 2, 'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1}
        demo_equipment = {
           "weapon": "long_sword", # Using long_sword for more impact
           "armor": "leather_armor",
           "shield": "wooden_shield",
           "helmet": "item_circlet_of_intellect" # This will be ignored by current equip_item
        }

        player_for_state = Player(id="p1", name="TestPlayer", max_hp=50,
                                  combat_stats=demo_combat_stats,
                                  base_damage_dice="1d4", # Base, but weapon should override
                                  equipment_data=demo_equipment)

        print(f"\nPlayer '{player_for_state.name}' created.")
        print(f"Base AC: {player_for_state.base_armor_class}")
        print(f"Equipped Weapon: {player_for_state.equipment.get('weapon')} -> Stats: {player_for_state.get_equipped_weapon_stats()}")
        print(f"Equipped Armor: {player_for_state.equipment.get('armor')} -> AC Bonus: {player_for_state._load_item_data(player_for_state.equipment.get('armor')).get('ac_bonus', 0) if player_for_state.equipment.get('armor') else 0}")
        print(f"Equipped Shield: {player_for_state.equipment.get('shield')} -> AC Bonus: {player_for_state._load_item_data(player_for_state.equipment.get('shield')).get('ac_bonus', 0) if player_for_state.equipment.get('shield') else 0}")
        print(f"Total AC Bonus from Armor/Shield: {player_for_state.get_equipped_armor_ac_bonus()}")
        print(f"Effective Armor Class: {player_for_state.get_effective_armor_class()}")

        player_state_demo = PlayerState(player_character=player_for_state)
        print(f"\nPlayerState Initial Status: {player_state_demo.get_status()}")

        player_state_demo.take_damage(10)
        print(f"After taking 10 damage: {player_state_demo.get_status()}")

        player_state_demo.heal(5)
        print(f"After healing 5 HP: {player_state_demo.get_status()}")

        print("\nInventory Management (via PlayerState):")
        player_state_demo.add_to_inventory("health_potion")
        print(f"Added health_potion: {player_state_demo.get_status()}")

        if player_state_demo.remove_from_inventory("health_potion"):
            print("Removed 'health_potion'.")
        else:
            print("'health_potion' not found to remove.")
        print(f"After removal: {player_state_demo.get_status()}")

        # Test attack (Player attacking a simple NPC)
        print("\n--- Combat Demonstration ---")
        npc_goblin = NPC(id="goblin1", name="Goblin Grunt", max_hp=15,
                         combat_stats={'armor_class': 13, 'attack_bonus': 2, 'damage_bonus': 0},
                         base_damage_dice="1d6")
        print(f"Created NPC: {npc_goblin.name} (AC: {npc_goblin.combat_stats['armor_class']}, HP: {npc_goblin.current_hp})")

        attack_message = player_for_state.attack(npc_goblin)
        print(attack_message)

        # Goblin attacks player
        if npc_goblin.is_alive():
            attack_message_npc = npc_goblin.attack(player_for_state)
            print(attack_message_npc)


    except Exception as e:
        print(f"Error during __main__ demonstration: {e}")


    print("\n--- Dice Rolling Demonstration ---")
    print(f"Rolling 1d6: {roll_dice(sides=6)}")
    print(f"Rolling 1d20: {roll_dice(sides=20)}")
    print(f"Rolling 3d6 (sum): {roll_dice(sides=6, num_dice=3)}")
    print(f"Rolling 2d10 (sum): {roll_dice(sides=10, num_dice=2)}")

    print("\nTesting Dice Rolling Edge Cases:")
    try:
        roll_dice(sides=0)
    except ValueError as e:
        print(f"Caught expected error for 0 sides: {e}")
    try:
        roll_dice(sides=6, num_dice=0)
    except ValueError as e:
        print(f"Caught expected error for 0 dice: {e}")
    try:
        roll_dice(sides="abc")
    except TypeError as e:
        print(f"Caught expected error for non-integer sides: {e}")
    try:
        roll_dice(sides=6, num_dice="two")
    except TypeError as e:
        print(f"Caught expected error for non-integer num_dice: {e}")

    print("\n--- End of Demonstration ---")

    # The __main__ block in game_state.py is primarily for basic, isolated tests of PlayerState
    # and dice rolling. It doesn't fully cover Character or Player interactions which are
    # better suited for dedicated test files like test_combat.py or test_game_state.py.
    # We will remove or comment out the PlayerState specific parts if they cause issues
    # due to constructor changes for Player that PlayerState might not be aware of in this old __main__.

    # For now, let's try to adapt the PlayerState instantiation for the demo,
    # or simplify the demo if it becomes too complex.
    # The Player class now requires more arguments.
    # Let's create a default Player for the demo.
    print("\n--- PlayerState Demonstration (adapted for new Player constructor) ---")
    try:
        # Create a default player for the PlayerState demonstration
        demo_player_combat_stats = {'initiative_bonus': 1, 'armor_class': 10, 'attack_bonus': 1, 'damage_bonus': 0}
        demo_player = Player(id="DemoHero", name="DemoHero", max_hp=100,
                             combat_stats=demo_player_combat_stats, base_damage_dice="1d4")

        # The old PlayerState demo used initial_hp, max_hp directly.
        # Now PlayerState takes a Player object.
        # The old PlayerState demo also had methods like take_damage, heal, add_to_inventory, remove_from_inventory, get_status
        # which now delegate to the Player object.

        player_state_demo = PlayerState(player_character=demo_player)
        print(f"Initial Status: {player_state_demo.get_status()}")

        player_state_demo.take_damage(30)
        print(f"After taking 30 damage: {player_state_demo.get_status()}")

        player_state_demo.take_damage(100)
        print(f"After taking 100 more damage: {player_state_demo.get_status()}")

        player_state_demo.heal(50)
        print(f"After healing 50 HP: {player_state_demo.get_status()}")

        player_state_demo.heal(100)
        print(f"After healing 100 more HP: {player_state_demo.get_status()}")

        print("\nInventory Management (via PlayerState):")
        player_state_demo.add_to_inventory("health_potion") # Note: item_name is just a string for inventory
        print(f"Added health_potion: {player_state_demo.get_status()}")

        if player_state_demo.remove_from_inventory("health_potion"):
            print("Removed 'health_potion'.")
        else:
            print("'health_potion' not found to remove.")
        print(f"After removal attempt: {player_state_demo.get_status()}")

    except Exception as e:
        print(f"Error during PlayerState demonstration: {e}")


    print("\n--- Dice Rolling Demonstration ---")
    # Mock participants
    # In a real scenario, these would be objects with 'id' and 'combat_stats' attributes.
    # For this test, we'll use simple mock objects (dictionaries that behave like objects).
    class MockParticipant: # Keep MockParticipant for determine_initiative demo
        def __init__(self, id, initiative_bonus):
            self.id = id
            self.combat_stats = {'initiative_bonus': initiative_bonus}

    print("\n--- Determine Initiative Demonstration ---") # Moved this line up to group with its content
    participants1 = [
        MockParticipant(id="Alice", initiative_bonus=2),
        MockParticipant(id="Bob", initiative_bonus=-1),
        MockParticipant(id="Charlie", initiative_bonus=5),
        MockParticipant(id="David", initiative_bonus=2), # Tie with Alice
    ]

    participants2 = [] # Empty list

    participants3 = [
        MockParticipant(id="Eve", initiative_bonus=0),
    ]

    # Note: Since initiative involves random rolls, the exact order can vary for ties
    # or close scores. We're primarily checking that it runs and returns IDs.
    print(f"Participants 1: {[p.id for p in participants1]}") #This will cause error if p.id does not exist
    turn_order1 = determine_initiative(participants1)
    print(f"Turn order 1: {turn_order1}")
    if participants1: # Add check to prevent error if participants1 is empty
        assert len(turn_order1) == len(participants1)
        assert all(isinstance(pid, str) for pid in turn_order1) # Assuming IDs are strings

    print(f"\nParticipants 2 (empty): {[p.id for p in participants2]}")
    turn_order2 = determine_initiative(participants2)
    print(f"Turn order 2: {turn_order2}")
    assert len(turn_order2) == 0

    print(f"\nParticipants 3 (single): {[p.id for p in participants3]}")
    turn_order3 = determine_initiative(participants3)
    print(f"Turn order 3: {turn_order3}")
    if participants3: # Add check here as well
        assert len(turn_order3) == 1
        assert turn_order3[0] == "Eve"

    print("\n--- End of Initiative Demonstration ---")
