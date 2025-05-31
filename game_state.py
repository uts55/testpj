import random

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
        # self.status_effects = [] # Future placeholder for buffs/debuffs

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
        attack_bonus = self.combat_stats.get('attack_bonus', 0)
        total_attack = attack_roll + attack_bonus

        target_ac = target.combat_stats.get('armor_class', 10) # Default AC if not specified

        if total_attack >= target_ac:
            # HIT!
            dm_message += f" d20({attack_roll}) + ATK Bonus({attack_bonus}) = {total_attack} vs AC({target_ac}). HIT!"

            damage_dice_str = self.base_damage_dice
            num_dice = 1
            dice_sides = 4 # Default to 1d4 if parsing fails for some reason

            try:
                parts = damage_dice_str.lower().split('d')
                if len(parts) == 2: # Format "XdY" or "dY"
                    num_dice_str, dice_sides_str = parts
                    num_dice = int(num_dice_str) if num_dice_str else 1 # Handles "dY" as "1dY"
                    dice_sides = int(dice_sides_str)
                elif len(parts) == 1 and parts[0].isdigit(): # Format "Y" (fixed damage, interpreted as Y-sided die, 1 roll)
                    # This case might be ambiguous. Standard is XdY.
                    # For now, let's assume if it's just a number, it's "1d<number>" e.g. "4" becomes "1d4"
                    # However, the spec says "base_damage_dice should always be XdY"
                    # Sticking to XdY or dY. This path should ideally not be taken if format is enforced.
                    # raising ValueError for non "XdY" or "dY" formats.
                    raise ValueError(f"Invalid base_damage_dice format for {self.name}: '{damage_dice_str}'. Expected XdY or dY (e.g., 1d4, d6).")
                else: # Malformed
                    raise ValueError(f"Invalid base_damage_dice format for {self.name}: '{damage_dice_str}'. Expected XdY or dY (e.g., 1d4, d6).")

                if num_dice <=0 or dice_sides <= 0:
                    raise ValueError(f"Number of dice and sides must be positive. Got: {num_dice}d{dice_sides}")

            except ValueError as e: # Catch parsing errors or invalid numbers
                # Option: Default to a safe value like 1d4, or re-raise, or log and use default
                # For now, re-raise as it's a configuration issue for the character
                # print(f"Error parsing damage dice '{damage_dice_str}': {e}. Defaulting to 1d4.") # Debug
                # num_dice, dice_sides = 1, 4
                raise ValueError(f"Error parsing damage dice '{damage_dice_str}' for {self.name}: {e}")


            damage_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
            damage_bonus = self.combat_stats.get('damage_bonus', 0)
            total_damage = damage_roll + damage_bonus
            total_damage = max(0, total_damage) # Damage cannot be negative

            target.take_damage(total_damage)

            dm_message += f" Deals {num_dice}d{dice_sides}({damage_roll}) + DMG Bonus({damage_bonus}) = {total_damage} damage."
            dm_message += f" {target.name} HP: {target.current_hp}/{target.max_hp}."
            if not target.is_alive():
                dm_message += f" {target.name} has been defeated!"
        else:
            # MISS!
            dm_message += f" d20({attack_roll}) + ATK Bonus({attack_bonus}) = {total_attack} vs AC({target_ac}). MISS!"

        return dm_message


class Player(Character):
    """
    Represents the player character, inheriting from Character.
    Includes player-specific attributes like equipment.
    """
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str):
        """
        Initializes a new Player character.

        Args:
            id: Unique identifier for the player.
            name: Display name of the player.
            max_hp: Maximum health points.
            combat_stats: Dictionary of combat-related statistics.
            base_damage_dice: String representation of base damage dice.
        """
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.equipment = {}  # Example: {'weapon': {'name': 'Longsword', 'damage_dice': '1d8'}}
        self.inventory = [] # Player specific inventory, distinct from PlayerState's version if that's for world items

    # TODO: Method to equip items, which might modify combat_stats or damage_dice.
    # TODO: Player-specific actions or abilities.

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
    print("--- PlayerState Demonstration ---")
    player = PlayerState(initial_hp=80, max_hp=120)
    print(f"Initial Status: {player.get_status()}") # Expected: HP: 80/120, Inventory: [empty]

    player.take_damage(30)
    print(f"After taking 30 damage: {player.get_status()}") # Expected: HP: 50/120

    player.take_damage(100) # Taking more damage than HP
    print(f"After taking 100 more damage: {player.get_status()}") # Expected: HP: 0/120

    player.heal(50)
    print(f"After healing 50 HP: {player.get_status()}") # Expected: HP: 50/120

    player.heal(100) # Healing more than max_hp
    print(f"After healing 100 more HP: {player.get_status()}") # Expected: HP: 120/120

    print("\nInventory Management:")
    player.add_to_inventory("sword")
    print(f"Added sword: {player.get_status()}")
    player.add_to_inventory("potion of healing")
    print(f"Added potion: {player.get_status()}")
    player.add_to_inventory("shield")
    print(f"Added shield: {player.get_status()}")

    if player.remove_from_inventory("potion of healing"):
        print("Removed 'potion of healing'.")
    else:
        print("'potion of healing' not found to remove.")
    print(f"After removal attempt: {player.get_status()}")

    if player.remove_from_inventory("gold key"): # Item not in inventory
        print("Removed 'gold key'.") # This line won't be reached if not found
    else:
        print("'gold key' not found to remove.")
    print(f"After attempting to remove non-existent item: {player.get_status()}")

    print("\nTesting PlayerState Initialization Edge Cases:")
    try:
        p_invalid1 = PlayerState(initial_hp=-10)
    except ValueError as e:
        print(f"Caught expected error for negative initial_hp: {e}")
    try:
        p_invalid2 = PlayerState(max_hp=0)
    except ValueError as e:
        print(f"Caught expected error for zero max_hp: {e}")
    p_capped = PlayerState(initial_hp=150, max_hp=100)
    print(f"Player with initial_hp > max_hp: {p_capped.get_status()}") # Expected: HP: 100/100

    print("\nTesting PlayerState Method Edge Cases:")
    try:
        player.take_damage(-10)
    except ValueError as e:
        print(f"Caught expected error for negative damage: {e}")
    try:
        player.heal(-10)
    except ValueError as e:
        print(f"Caught expected error for negative heal: {e}")
    try:
        player.add_to_inventory("  ")
    except ValueError as e:
        print(f"Caught expected error for empty item name: {e}")
    print(f"Status after edge case method tests: {player.get_status()}")


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

    print("\n--- Determine Initiative Demonstration ---")
    # Mock participants
    # In a real scenario, these would be objects with 'id' and 'combat_stats' attributes.
    # For this test, we'll use simple mock objects (dictionaries that behave like objects).
    class MockParticipant:
        def __init__(self, id, initiative_bonus):
            self.id = id
            self.combat_stats = {'initiative_bonus': initiative_bonus}

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
    print(f"Participants 1: {[p.id for p in participants1]}")
    turn_order1 = determine_initiative(participants1)
    print(f"Turn order 1: {turn_order1}")
    assert len(turn_order1) == len(participants1)
    assert all(isinstance(pid, str) for pid in turn_order1) # Assuming IDs are strings

    print(f"\nParticipants 2 (empty): {[p.id for p in participants2]}")
    turn_order2 = determine_initiative(participants2)
    print(f"Turn order 2: {turn_order2}")
    assert len(turn_order2) == 0

    print(f"\nParticipants 3 (single): {[p.id for p in participants3]}")
    turn_order3 = determine_initiative(participants3)
    print(f"Turn order 3: {turn_order3}")
    assert len(turn_order3) == 1
    assert turn_order3[0] == "Eve"

    print("\n--- End of Initiative Demonstration ---")
