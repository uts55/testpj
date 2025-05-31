from utils import roll_dice, SKILL_ABILITY_MAP, PROFICIENCY_BONUS
import random # random is still used by other parts of game_state.py like status effect application
import logging # For logging warnings
from magic import SPELLBOOK, Spell # Import necessary spellcasting components

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
    Includes player-specific attributes like equipment, abilities, and skills.
    """
    def __init__(self, player_data: dict, equipment_data: dict = None):
        """
        Initializes a new Player character.

        Args:
            player_data: Dictionary containing all player attributes including:
                         id, name, max_hp, combat_stats, base_damage_dice,
                         ability_scores, skills, and proficiencies.
            equipment_data: Optional dictionary of item IDs to equip. This could
                            alternatively be part of player_data itself.
        """
        # Extract core attributes for Character initialization from player_data
        player_id = player_data.get("id", "default_player_id")
        player_name = player_data.get("name", "Player")
        max_hp = player_data.get("max_hp", 10)  # Default to 10 if not provided
        combat_stats = player_data.get("combat_stats", {}) # Default to empty dict
        base_damage_dice = player_data.get("base_damage_dice", "1d4") # Default to 1d4

        super().__init__(player_id, player_name, max_hp, combat_stats, base_damage_dice)

        self.ability_scores = player_data.get("ability_scores", {})
        self.skills_list = player_data.get("skills", []) # List of all skills the player possesses
        self.proficiencies_map = player_data.get("proficiencies", {"skills": []}) # Map of proficiencies, e.g., {"skills": ["stealth", "arcana"]}
        if "skills" not in self.proficiencies_map: # Ensure 'skills' key exists
            self.proficiencies_map["skills"] = []

        # Initialize spell_slots
        self.spell_slots = player_data.get("spell_slots", {})


        self.equipment = {
            "weapon": None,
            "armor": None,
            "shield": None,
            # Future slots: "helmet", "boots", etc.
        }
        self.inventory = []
        # Store base AC, useful if armor is unequipped
        # This combat_stats is the one extracted from player_data
        self.base_armor_class = combat_stats.get('armor_class', 10)

        # Process equipment_data if provided (or could be nested in player_data)
        actual_equipment_data = equipment_data if equipment_data is not None else player_data.get("equipment")
        if actual_equipment_data:
            for slot, item_id in actual_equipment_data.items():
                if item_id: # Ensure item_id is not None or empty
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

    def get_ability_modifier(self, ability_name: str) -> int:
        """
        Calculates the modifier for a given ability score.

        Args:
            ability_name: The name of the ability (e.g., "strength", "dexterity").

        Returns:
            The calculated ability modifier. Returns 0 if ability name is invalid or score not found.
        """
        ability_name_lower = ability_name.lower()
        score = self.ability_scores.get(ability_name_lower)

        if score is None or not isinstance(score, int):
            logging.warning(f"Ability '{ability_name_lower}' not found or invalid for player {self.name}. Defaulting modifier to 0.")
            return 0

        return (score - 10) // 2

    def perform_skill_check(self, skill_name: str, dc: int) -> tuple[bool, int, int, str]:
        """
        Performs a skill check for the player.

        Args:
            skill_name: The name of the skill being checked (e.g., "stealth", "persuasion").
            dc: The difficulty class of the skill check.

        Returns:
            A tuple containing:
            - success (bool): True if the check succeeded, False otherwise.
            - d20_roll (int): The raw value rolled on the d20.
            - total_skill_value (int): The total value of the skill check after modifiers.
            - detailed_breakdown (str): A string detailing the calculation.
        """
        skill_name_norm = skill_name.lower()

        d20_roll = roll_dice(sides=20)

        ability_name = SKILL_ABILITY_MAP.get(skill_name_norm)
        ability_modifier = 0
        ability_mod_str = "N/A"

        if ability_name:
            ability_modifier = self.get_ability_modifier(ability_name)
            ability_mod_str = str(ability_modifier)
        else:
            logging.warning(f"Skill '{skill_name_norm}' not found in SKILL_ABILITY_MAP. No ability modifier applied for player {self.name}.")

        current_proficiency_bonus = 0
        prof_bonus_str = "0"
        # Ensure self.proficiencies_map and its 'skills' key are valid
        proficient_skills = self.proficiencies_map.get('skills', [])
        if not isinstance(proficient_skills, list): # Defensive check
            logging.warning(f"Player {self.name} has invalid proficiencies_map['skills']. Expected list, got {type(proficient_skills)}. Assuming no skill proficiencies.")
            proficient_skills = []

        if skill_name_norm in proficient_skills:
            current_proficiency_bonus = PROFICIENCY_BONUS
            prof_bonus_str = str(current_proficiency_bonus)

        total_skill_value = d20_roll + ability_modifier + current_proficiency_bonus
        success = total_skill_value >= dc

        detailed_breakdown = (f"d20({d20_roll}) + "
                              f"{ability_name.upper() if ability_name else 'N/A'}_MOD({ability_mod_str}) + "
                              f"PROF_BONUS({prof_bonus_str}) = {total_skill_value} vs DC({dc})")

        return success, d20_roll, total_skill_value, detailed_breakdown

    def has_spell_slot(self, spell_level: int) -> bool:
        """
        Checks if the player has an available spell slot for the given level.
        """
        slot_key = f"level_{spell_level}"
        if slot_key in self.spell_slots:
            return self.spell_slots[slot_key].get("current", 0) > 0
        return False

    def consume_spell_slot(self, spell_level: int) -> bool:
        """
        Consumes a spell slot of the given level if available.
        Returns True if a slot was consumed, False otherwise.
        """
        slot_key = f"level_{spell_level}"
        if self.has_spell_slot(spell_level):
            if slot_key in self.spell_slots and "current" in self.spell_slots[slot_key]:
                self.spell_slots[slot_key]["current"] -= 1
                return True
            else:
                # This case should ideally not be reached if has_spell_slot was true
                # and data structure is as expected.
                logging.warning(f"Spell slot {slot_key} structure incorrect for {self.name}.")
                return False
        return False

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

    def cast_spell(self, spell_name: str, target: 'Character' = None) -> tuple[bool, str]:
        """
        Casts a spell by name, targeting another character or self.
        Handles spell lookup, target validation, slot consumption, effect calculation, and application.
        """
        spell = SPELLBOOK.get(spell_name)
        if not spell:
            return False, f"Spell '{spell_name}' not found."

        actual_target = None
        if spell.target_type == "self":
            actual_target = self
        elif target is None:
            return False, f"Spell '{spell_name}' requires a target."
        elif not isinstance(target, Character): # Check if target is a Character instance
            return False, "Invalid target type. Target must be a Character."
        else:
            actual_target = target

        slot_message_part = ""
        if spell.level > 0: # Assuming level 0 spells (cantrips) don't use slots
            if not self.has_spell_slot(spell.level):
                return False, f"No level {spell.level} spell slots available for '{spell_name}'."
            if not self.consume_spell_slot(spell.level):
                # This should ideally not happen if has_spell_slot passed.
                logging.error(f"Failed to consume spell slot for '{spell_name}' for {self.name} despite check passing.")
                return False, f"Failed to consume spell slot for '{spell_name}' (error)."
            slot_message_part = f", consuming a level {spell.level} slot"

        base_effect_value = 0
        dice_roll_str = ""
        if spell.dice_expression:
            try:
                parts = spell.dice_expression.lower().split('d')
                num_dice = 1
                dice_sides = 0
                if len(parts) == 2:
                    num_dice_str, dice_sides_str = parts
                    if num_dice_str: # "1d6"
                        num_dice = int(num_dice_str)
                    else: # "d6"
                        num_dice = 1
                    dice_sides = int(dice_sides_str)
                elif len(parts) == 1 and parts[0].isdigit(): # "6" interpreted as "1d6"
                    num_dice = 1
                    dice_sides = int(parts[0])
                else:
                    raise ValueError(f"Invalid dice expression format: {spell.dice_expression}")

                if num_dice <= 0 or dice_sides <= 0:
                    raise ValueError(f"Dice numbers must be positive: {spell.dice_expression}")

                roll_result = roll_dice(sides=dice_sides, num_dice=num_dice)
                base_effect_value += roll_result
                dice_roll_str = f"{spell.dice_expression}({roll_result})"
            except ValueError as e:
                logging.error(f"Error parsing dice expression '{spell.dice_expression}' for spell '{spell_name}': {e}")
                return False, f"Error processing spell '{spell_name}': Invalid dice expression."

        ability_modifier_value = 0
        mod_str = ""
        if spell.stat_modifier_ability:
            ability_modifier_value = self.get_ability_modifier(spell.stat_modifier_ability)
            mod_str = f" + {spell.stat_modifier_ability[:3].upper()}({ability_modifier_value})"

        total_effect_value = base_effect_value + ability_modifier_value
        total_effect_value = max(0, total_effect_value) # Effects generally shouldn't be negative

        effect_description = ""
        if spell.effect_type == "heal":
            actual_target.heal(total_effect_value)
            effect_description = f"Healed {total_effect_value} HP."
        elif spell.effect_type == "damage":
            actual_target.take_damage(total_effect_value)
            effect_description = f"Dealt {total_effect_value} {spell.name.lower().replace(' ', '_')} damage."
        else:
            effect_description = "Unknown spell effect."
            logging.warning(f"Spell '{spell_name}' has an unknown effect_type: {spell.effect_type}")


        target_name = actual_target.name if actual_target else "Unknown" # Should always have actual_target by now

        # Construct calculation details, ensuring it's not empty if no dice or mod
        calculation_details_parts = []
        if dice_roll_str:
            calculation_details_parts.append(dice_roll_str)
        if mod_str:
            # Ensure '+' is only added if dice_roll_str was present, or it's the first element.
            # The mod_str already contains " + MOD(val)"
            if not dice_roll_str : # if mod_str is first, remove its leading " + "
                 mod_str = f"{spell.stat_modifier_ability[:3].upper()}({ability_modifier_value})"
            calculation_details_parts.append(mod_str)

        calculation_final_str = "".join(calculation_details_parts)
        if calculation_final_str : # if there are calculation parts, add " = total"
             calculation_final_str += f" = {total_effect_value}"
        else: # No dice, no mod, but there might be a fixed base value (not in current Spell, but for future)
             calculation_final_str = f"{total_effect_value}"


        message = (f"{self.name} casts '{spell_name}' on {target_name}{slot_message_part}. "
                   f"{effect_description} ({calculation_final_str})")

        return True, message

class NPC(Character):
    """
    Represents a Non-Player Character, inheriting from Character.
    """
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str, dialogue_responses: dict = None):
        """
        Initializes a new NPC.

        Args:
            id: Unique identifier for the NPC.
            name: Display name of the NPC.
            max_hp: Maximum health points.
            combat_stats: Dictionary of combat-related statistics.
            base_damage_dice: String representation of base damage dice.
            dialogue_responses: Optional dictionary containing the NPC's dialogue tree.
        """
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.dialogue_responses = dialogue_responses # NPCs might have specific dialog lines

    def get_dialogue_node(self, key: str) -> dict | None:
        """
        Retrieves a dialogue node from the NPC's dialogue_responses.

        Args:
            key: The key for the desired dialogue node (e.g., "greetings").

        Returns:
            The dialogue node dictionary if found, otherwise None.
        """
        if self.dialogue_responses is None:
            return None
        return self.dialogue_responses.get(key)

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

        # Dialogue state attributes
        self.current_dialogue_npc_id: str | None = None
        self.current_dialogue_key: str | None = None

        # print(f"PlayerState initialized for {self.player_character.name}.") # Debug

    def start_dialogue(self, npc_id: str, initial_key: str = "greetings"):
        """Starts a dialogue session with an NPC."""
        self.current_dialogue_npc_id = npc_id
        self.current_dialogue_key = initial_key

    def end_dialogue(self):
        """Ends the current dialogue session."""
        self.current_dialogue_npc_id = None
        self.current_dialogue_key = None

    def is_in_dialogue(self) -> bool:
        """Checks if the player is currently in a dialogue."""
        return self.current_dialogue_npc_id is not None

    def set_dialogue_key(self, key: str):
        """Sets the current dialogue key to advance the conversation."""
        self.current_dialogue_key = key

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

# roll_dice function removed from here, will use the one from utils.py

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
    # This block is for demonstration and basic testing when running game_state.py directly.
    # It shows how to use the classes and functions defined in this file.

    # --- Player and Equipment/Combat Demonstration ---
    # This section demonstrates creating a Player, equipping items, and basic combat.
    # Note: The Player class constructor was updated to primarily use player_data.
    print("\n--- Player, Equipment, and Combat Demonstration ---")
    try:
        # Player data for the demonstration hero
        hero_main_data = {
            "id": "hero_main", "name": "MainHero", "max_hp": 75,
            "combat_stats": {'armor_class': 12, 'attack_bonus': 4, 'damage_bonus': 2, 'initiative_bonus': 3},
            "base_damage_dice": "1d6", # Base for when unarmed or if weapon lacks dice
            "ability_scores": {"strength": 15, "dexterity": 14, "constitution": 13, "intelligence": 10, "wisdom": 12, "charisma": 8},
            "skills": ["athletics", "perception", "stealth"],
            "proficiencies": {"skills": ["athletics", "stealth"]},
            "equipment": {
                "weapon": "long_sword",
                "armor": "leather_armor",
                "shield": "wooden_shield"
            }
        }
        # Equipment_data is passed via player_data["equipment"] as per new constructor handling
        hero_for_main_demo = Player(player_data=hero_main_data)

        print(f"\nPlayer '{hero_for_main_demo.name}' created.")
        print(f"Base AC (from combat_stats): {hero_for_main_demo.base_armor_class}") # Should be 12
        print(f"Effective AC (with equipment): {hero_for_main_demo.get_effective_armor_class()}") # 12 + 2 (leather) + 1 (shield) = 15
        weapon_stats = hero_for_main_demo.get_equipped_weapon_stats()
        print(f"Equipped Weapon: {hero_for_main_demo.equipment.get('weapon')} -> Stats: {weapon_stats}")

        # NPC for combat demo
        npc_enemy = NPC(id="goblin_chief", name="Goblin Chief", max_hp=40,
                        combat_stats={'armor_class': 14, 'attack_bonus': 3, 'damage_bonus': 1},
                        base_damage_dice="1d8")
        print(f"Created NPC: {npc_enemy.name} (AC: {npc_enemy.combat_stats['armor_class']}, HP: {npc_enemy.current_hp})")

        # Combat
        attack_msg_hero = hero_for_main_demo.attack(npc_enemy)
        print(attack_msg_hero)
        if npc_enemy.is_alive():
            attack_msg_npc = npc_enemy.attack(hero_for_main_demo)
            print(attack_msg_npc)

    except Exception as e:
        print(f"Error during Player/Combat demonstration: {e}")

    # --- PlayerState and Skill Check Demonstration ---
    # This section focuses on PlayerState and the newer skill check mechanisms.
    print("\n--- PlayerState and Skill Check Demonstration ---")
    try:
        player_skill_demo_data = {
            "id": "skill_hero", "name": "SkillDemoHero",
            "ability_scores": {"strength": 12, "dexterity": 18, "charisma": 15, "intelligence": 11, "wisdom": 9},
            "skills": ["athletics", "stealth", "persuasion", "investigation", "insight", "nonexistent_skill"],
            "proficiencies": {"skills": ["stealth", "persuasion"]}, # Proficient in Stealth (DEX) & Persuasion (CHA)
            "max_hp": 50, # Required by Player constructor via player_data
            "combat_stats": {'armor_class': 10, 'attack_bonus': 1, 'damage_bonus': 0, 'initiative_bonus':4}, # Required
            "base_damage_dice": "1d4" # Required
        }
        skill_demo_player = Player(player_data=player_skill_demo_data)

        print(f"\nSkill Demo Player '{skill_demo_player.name}' created.")
        print(f"Abilities: {skill_demo_player.ability_scores}")
        print(f"Skills List: {skill_demo_player.skills_list}")
        print(f"Proficiencies: {skill_demo_player.proficiencies_map.get('skills')}")

        print("\nSkill Check Examples:")
        # Stealth (Proficient, DEX 18 -> +4) vs DC 15
        # Expected: d20 + 4 (DEX) + PROFICIENCY_BONUS (2)
        success, _, total, breakdown = skill_demo_player.perform_skill_check("stealth", 15)
        print(f"Stealth Check (DC 15): {'Success' if success else 'Failure'} - Total: {total}. Breakdown: {breakdown}")

        # Athletics (Not Proficient, STR 12 -> +1) vs DC 10
        # Expected: d20 + 1 (STR) + 0
        success, _, total, breakdown = skill_demo_player.perform_skill_check("athletics", 10)
        print(f"Athletics Check (DC 10): {'Success' if success else 'Failure'} - Total: {total}. Breakdown: {breakdown}")

        # Nonexistent Skill (No ability, No proficiency) vs DC 5
        # Expected: d20 + 0 + 0
        success, _, total, breakdown = skill_demo_player.perform_skill_check("nonexistent_skill", 5)
        print(f"Nonexistent Skill Check (DC 5): {'Success' if success else 'Failure'} - Total: {total}. Breakdown: {breakdown}")

        # PlayerState with this player
        ps_demo = PlayerState(player_character=skill_demo_player)
        print(f"\nPlayerState Initial Status: {ps_demo.get_status()}")
        ps_demo.take_damage(10)
        print(f"After 10 damage: {ps_demo.get_status()}")
        ps_demo.heal(5)
        print(f"After 5 healing: {ps_demo.get_status()}")

    except Exception as e:
        print(f"Error during PlayerState/Skill demonstration: {e}")

    # --- Dice Rolling and Initiative Demonstration ---
    print("\n--- Dice Rolling and Initiative Demonstration ---")
    try:
        print(f"Rolling 1d6: {roll_dice(sides=6)}")
        print(f"Rolling 3d8: {roll_dice(sides=8, num_dice=3)}")

        # Mock participants for initiative
        class MockParticipant:
            def __init__(self, id_val, init_bonus):
                self.id = id_val
                self.combat_stats = {'initiative_bonus': init_bonus}

        participants = [
            MockParticipant(id_val="Alice", init_bonus=3),
            MockParticipant(id_val="Bob", init_bonus=1),
            MockParticipant(id_val="Charlie", init_bonus=3), # Tie with Alice
        ]
        turn_order = determine_initiative(participants)
        print(f"Turn order for {[p.id for p in participants]}: {turn_order}")

    except Exception as e:
        print(f"Error during Dice/Initiative demonstration: {e}")

    print("\n--- End of All Demonstrations ---")
