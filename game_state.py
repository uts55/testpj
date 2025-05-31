import random

class PlayerState:
    """
    Represents the state of the player, including HP and inventory.
    """
    def __init__(self, initial_hp: int = 100, max_hp: int = 100, combat_stats: dict = None):
        """
        Initializes the player's state.

        Args:
            initial_hp: The starting health points of the player. Defaults to 100.
            max_hp: The maximum health points the player can have. Defaults to 100.
            combat_stats: A dictionary containing combat-related stats. Defaults to None.
        
        Raises:
            TypeError: If HP values are not integers.
            ValueError: If HP values are not positive, or initial_hp > max_hp (though this is capped).
        """
        if not isinstance(initial_hp, int) or not isinstance(max_hp, int):
            raise TypeError("HP values must be integers.")
        if max_hp <= 0: # initial_hp can be 0 if player starts with 0 HP, but max_hp must be positive
            raise ValueError("max_hp must be a positive integer.")
        if initial_hp < 0:
            raise ValueError("initial_hp cannot be negative.")

        self.max_hp = max_hp
        self.current_hp = min(initial_hp, max_hp) # Ensure current_hp doesn't exceed max_hp
        
        self.inventory = []

        # Combat state attributes
        self.participants_in_combat = []
        self.current_turn_character_id = None
        self.turn_order = []
        self.is_in_combat = False

        # Combat stats
        self.combat_stats = combat_stats or {'initiative_bonus': 0}

        # print(f"PlayerState initialized. HP: {self.current_hp}/{self.max_hp}, Inventory: {self.inventory}, Combat Stats: {self.combat_stats}") # Debug

    def take_damage(self, amount: int):
        """
        Reduces the player's HP by the specified amount.
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
        # print(f"Took {amount} damage. Current HP: {self.current_hp}/{self.max_hp}") # Debug

    def heal(self, amount: int):
        """
        Increases the player's HP by the specified amount.
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
        # print(f"Healed {amount} HP. Current HP: {self.current_hp}/{self.max_hp}") # Debug

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

    def get_status(self) -> str:
        """
        Returns a string summarizing the player's current HP and inventory.

        Returns:
            A string representing the player's status.
        """
        inventory_str = ', '.join(self.inventory) if self.inventory else "empty"
        return f"HP: {self.current_hp}/{self.max_hp}, Inventory: [{inventory_str}]"

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
