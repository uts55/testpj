import logging
import random
from typing import TYPE_CHECKING

from utils import roll_dice, SKILL_ABILITY_MAP, PROFICIENCY_BONUS
from magic import SPELLBOOK, Spell
from quests import ALL_QUESTS
from gemini_dm import notify_dm
from items import Item, Weapon, Armor, Consumable # KeyItem is not directly used in Character/Player/NPC methods
from factions import Faction # For Player.change_faction_reputation type hint

if TYPE_CHECKING:
    from game_state import GameState # Forward declaration for type hinting

class Character:
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str):
        if not isinstance(id, str) or not id.strip(): raise ValueError("Character ID must be a non-empty string.")
        if not isinstance(name, str) or not name.strip(): raise ValueError("Character name must be a non-empty string.")
        if not isinstance(max_hp, int) or max_hp <= 0: raise ValueError("max_hp must be a positive integer.")
        if not isinstance(combat_stats, dict): raise TypeError("combat_stats must be a dictionary.")
        if not isinstance(base_damage_dice, str) or not base_damage_dice.strip(): raise ValueError("base_damage_dice must be a non-empty string.")
        self.id = id
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.combat_stats = combat_stats
        self.base_damage_dice = base_damage_dice
        self.status_effects = []
    def add_status_effect(self, effect_name: str, duration: int, potency: int):
        for effect in self.status_effects:
            if effect['name'] == effect_name:
                effect['duration'] = duration; effect['potency'] = potency
                return f"{self.name}'s {effect_name} refreshed to {duration} turns."
        self.status_effects.append({'name': effect_name, 'duration': duration, 'potency': potency})
        return f"{self.name} is now {effect_name} for {duration} turns."
    def remove_status_effect(self, effect_name: str):
        self.status_effects = [e for e in self.status_effects if e['name'] != effect_name]
    def tick_status_effects(self) -> list[str]:
        msgs = []
        for effect in list(self.status_effects):
            if effect['name'] == 'poison':
                self.take_damage(effect['potency'])
                msgs.append(f"{self.name} took {effect['potency']} from poison.")
                if not self.is_alive(): msgs.append(f"{self.name} succumbed to poison."); break
            effect['duration'] -= 1
            if effect['duration'] <= 0: self.remove_status_effect(effect['name']); msgs.append(f"{self.name} no longer {effect['name']}.")
        return msgs
    def take_damage(self, amount: int):
        if not isinstance(amount, int): raise TypeError("Damage amount int.")
        if amount < 0: raise ValueError("Damage amount non-negative.")
        self.current_hp = max(0, self.current_hp - amount)
    def heal(self, amount: int):
        if not isinstance(amount, int): raise TypeError("Heal amount int.")
        if amount < 0: raise ValueError("Heal amount non-negative.")
        self.current_hp = min(self.max_hp, self.current_hp + amount)
    def is_alive(self) -> bool: return self.current_hp > 0
    def attack(self, target: 'Character', game_state: 'GameState') -> str:
        if not isinstance(target, Character): raise TypeError("Target must be Character.")
        if self == target: return f"{self.name} cannot attack themselves."
        dm_msg = f"{self.name} attacks {target.name}."
        atk_roll = roll_dice(sides=20)
        cur_atk_bonus = self.combat_stats.get('attack_bonus', 0)
        cur_dmg_bonus = self.combat_stats.get('damage_bonus', 0)
        cur_dmg_dice = self.base_damage_dice
        if isinstance(self, Player):
            wp_stats = self.get_equipped_weapon_stats(game_state)
            cur_dmg_dice = wp_stats["damage_dice"]
            cur_atk_bonus += wp_stats["attack_bonus"]
            cur_dmg_bonus += wp_stats["damage_bonus"]
        total_atk = atk_roll + cur_atk_bonus
        target_ac = target.get_effective_armor_class(game_state) if isinstance(target, Player) else target.combat_stats.get('armor_class', 10)
        if total_atk >= target_ac:
            dm_msg += f" d20({atk_roll})+ATK({cur_atk_bonus})={total_atk} vs AC({target_ac}). HIT!"
            try:
                dice_parts_actual = cur_dmg_dice.lower().split('d')
                num_dice = 1
                dice_sides_str = "4" # Default if parsing fails unexpectedly before assignment
                dice_modifier = 0

                if len(dice_parts_actual) == 2: # "XdY" or "XdY+M" or "XdY-M"
                    num_dice = int(dice_parts_actual[0]) if dice_parts_actual[0] else 1
                    dice_sides_str = dice_parts_actual[1]
                elif len(dice_parts_actual) == 1 and dice_parts_actual[0].isdigit(): # "Y" -> 1dY
                    dice_sides_str = dice_parts_actual[0]
                    # Update cur_dmg_dice for logging to reflect 1dY format
                    # This part is tricky because cur_dmg_dice is used in the message.
                    # Let's ensure the original format for the message is preserved if it was just "Y"
                elif 'd' not in cur_dmg_dice and cur_dmg_dice.isdigit(): # Handles flat damage string like "5" as 1d5
                    num_dice = 1
                    dice_sides_str = cur_dmg_dice
                else: # Should not happen if validation is correct, but as fallback
                    raise ValueError(f"Invalid base dice format '{cur_dmg_dice}'")

                if '+' in dice_sides_str:
                    parts_modifier = dice_sides_str.split('+')
                    dice_sides = int(parts_modifier[0])
                    dice_modifier = int(parts_modifier[1])
                elif '-' in dice_sides_str:
                    parts_modifier = dice_sides_str.split('-')
                    dice_sides = int(parts_modifier[0])
                    dice_modifier = -int(parts_modifier[1])
                else:
                    dice_sides = int(dice_sides_str)

                if num_dice <= 0 or dice_sides <= 0:
                    raise ValueError("Number of dice and sides must be positive.")

                dmg_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
                # Total damage includes dice roll, modifier from dice string (e.g., +2 in 1d6+2), and combat stat bonus
                total_dmg = max(0, dmg_roll + dice_modifier + cur_dmg_bonus)
                target.take_damage(total_dmg)

                # Construct a representation of the dice part for the message, e.g., 1d6 from 1d6+2
                dice_for_msg = f"{num_dice}d{dice_sides}"
                dm_msg += f" Deals {dice_for_msg}({dmg_roll})"
                if dice_modifier != 0:
                    dm_msg += f"{'+' if dice_modifier > 0 else ''}{dice_modifier}"
                dm_msg += f"+DMG_STAT({cur_dmg_bonus})={total_dmg} damage."

            except ValueError as e:
                raise ValueError(f"Parse error for dice string '{cur_dmg_dice}' for {self.name}: {e}")
            # Damage is applied once inside the try block: target.take_damage(total_dmg)
            # The redundant call after the except block has been removed.

            dm_msg += f" {target.name} HP: {target.current_hp}/{target.max_hp}." # Single HP message after damage.
            if target.is_alive() and random.randint(1,100)<=10: target.add_status_effect('poison',3,2); dm_msg+=f" {target.name} poisoned!"
            if not target.is_alive(): dm_msg+=f" {target.name} defeated!"
        else: dm_msg+=f" d20({atk_roll})+ATK({cur_atk_bonus})={total_atk} vs AC({target_ac}). MISS!"
        return dm_msg

class Player(Character):
    def __init__(self, player_data: dict, equipment_data: dict = None): # equipment_data is legacy, not actively used for init
        super().__init__(player_data.get("id","player"), player_data.get("name","Player"), player_data.get("max_hp",10),
                         player_data.get("combat_stats",{}), player_data.get("base_damage_dice","1d4"))
        self.ability_scores = player_data.get("ability_scores",{})
        self.skills_list = player_data.get("skills",[])
        self.proficiencies_map = player_data.get("proficiencies",{"skills":[]})
        if "skills" not in self.proficiencies_map: self.proficiencies_map["skills"]=[]
        self.spell_slots = player_data.get("spell_slots",{})
        self.discovered_clues: list[str] = player_data.get("discovered_clues",[])
        self.experience_points = player_data.get("experience_points",0)
        self.inventory: list[str] = player_data.get("inventory",[]) # List of item IDs
        self.equipment: dict[str, str|None|dict] = player_data.get("equipment",{}) # Item IDs for equipped, or dict for currency
        if "currency" not in self.equipment: self.equipment["currency"]={}
        for slot in ["weapon","armor","shield"]: # Ensure equipment slots exist
            if slot not in self.equipment: self.equipment[slot]=None
        self.base_armor_class = self.combat_stats.get('armor_class',10)
        self.active_quests = player_data.get("active_quests",{}) # Dict: quest_id -> {"current_stage_id": str, "completed_optional_objectives": list[str]}
        self.completed_quests = player_data.get("completed_quests",[]) # List of quest_ids
        self.visited_locations: set[str] = set(player_data.get("visited_locations", []))
        self.faction_reputations: dict[str, int] = player_data.get("faction_reputations", {}) # faction_id -> reputation_score

    def _get_item_from_game_state(self, item_id:str, game_state:'GameState')->Item|None:
        if not item_id: return None
        # game_state.items should be a dict[str, Item]
        item = game_state.items.get(item_id)
        if not item: logging.warning(f"Player {self.name}: Item ID '{item_id}' not found in GameState.items.")
        return item

    def equip_item(self, item_id:str, slot:str, game_state:'GameState')->bool:
        item = self._get_item_from_game_state(item_id, game_state)
        if not item: return False
        if slot not in self.equipment: logging.warning(f"Player {self.name}: Slot '{slot}' nonexistent."); return False

        valid_equip = False
        if slot=="weapon" and isinstance(item,Weapon):
            valid_equip = True
        elif slot=="armor" and isinstance(item,Armor) and item.armor_type!="shield": # Main armor
            valid_equip = True
        elif slot=="shield" and isinstance(item,Armor) and item.armor_type=="shield": # Shield specific
            valid_equip = True

        if not valid_equip:
            logging.warning(f"Player {self.name}: Cannot equip {item.name}({item.item_type}) in {slot}.")
            return False

        currently_equipped_id = self.equipment.get(slot)
        if isinstance(currently_equipped_id, str) and currently_equipped_id != item_id:
            self.add_to_inventory(currently_equipped_id)

        self.equipment[slot]=item_id
        if item_id in self.inventory: self.remove_from_inventory(item_id)
        notify_dm(f"{self.name} equipped {item.name} in {slot}.")
        return True

    def unequip_item(self, slot:str, game_state:'GameState')->str|None:
        if slot not in self.equipment: logging.warning(f"Player {self.name}: Slot '{slot}' nonexistent."); return None
        item_id = self.equipment.get(slot)
        if isinstance(item_id,str): # Check if there's an item ID in the slot
            item_obj = self._get_item_from_game_state(item_id,game_state)
            name_of_item = item_obj.name if item_obj else item_id
            self.equipment[slot]=None # Remove from equipment slot
            self.add_to_inventory(item_id) # Add back to inventory
            notify_dm(f"{self.name} unequipped {name_of_item} from {slot}. Added to inventory.")
            return item_id
        return None # No item was in the slot

    def get_equipped_weapon_stats(self, game_state:'GameState')->dict:
        weapon_id = self.equipment.get("weapon")
        if isinstance(weapon_id, str):
            item = self._get_item_from_game_state(weapon_id, game_state)
            if isinstance(item, Weapon):
                return {"damage_dice": item.damage_dice, "attack_bonus": item.attack_bonus, "damage_bonus": item.damage_bonus}
        return {"damage_dice": self.base_damage_dice, "attack_bonus": 0, "damage_bonus": 0} # Fallback to base stats

    def get_equipped_armor_ac_bonus(self, game_state:'GameState')->int:
        ac_bonus = 0
        for slot_type in ["armor", "shield"]: # Iterate through armor and shield slots
            item_id = self.equipment.get(slot_type)
            if isinstance(item_id, str):
                item = self._get_item_from_game_state(item_id, game_state)
                if isinstance(item, Armor):
                    # Ensure armor is in 'armor' slot and shield in 'shield' slot
                    if (slot_type == "armor" and item.armor_type != "shield") or \
                       (slot_type == "shield" and item.armor_type == "shield"):
                        ac_bonus += item.ac_bonus
        return ac_bonus

    def get_effective_armor_class(self,game_state:'GameState')->int:
        return self.base_armor_class + self.get_equipped_armor_ac_bonus(game_state)

    def use_item(self,item_id:str,game_state:'GameState',target:'Character'=None)->tuple[bool,str]:
        if item_id not in self.inventory: return False, f"Item '{item_id}' not in inventory."
        item = self._get_item_from_game_state(item_id,game_state)
        if not item: return False, f"Item data for '{item_id}' not retrieved."
        if not isinstance(item,Consumable): return False, f"'{item.name}' is not consumable."

        target_char = target if target else self # Default to self if no target

        messages = [f"{self.name} uses {item.name}."]

        for effect_data in item.effects:
            effect_type = effect_data.get("effect_type")
            if effect_type == "heal":
                amount_str = effect_data.get("amount", "0")
                heal_amount = 0
                try:
                    if 'd' in amount_str:
                        parts = amount_str.split('d')
                        num_dice = int(parts[0]) if parts[0] else 1
                        dice_part = parts[1]
                        bonus = 0
                        if '+' in dice_part:
                            dice_sides_str, bonus_str = dice_part.split('+')
                            bonus = int(bonus_str)
                        else:
                            dice_sides_str = dice_part
                        heal_amount = roll_dice(sides=int(dice_sides_str), num_dice=num_dice) + bonus
                    else:
                        heal_amount = int(amount_str)

                    heal_amount = max(0, heal_amount) # Ensure healing isn't negative
                    target_char.heal(heal_amount)
                    messages.append(f"{target_char.name} healed for {heal_amount} HP. Current HP: {target_char.current_hp}/{target_char.max_hp}")
                except ValueError:
                    messages.append(f"Invalid amount format for healing: {amount_str}")
                    logging.error(f"Invalid heal amount format in item '{item_id}': {amount_str}")
            elif effect_type == "buff":
                stat = effect_data.get("stat", "UnknownStat")
                modifier = effect_data.get("modifier", 0)
                duration = effect_data.get("duration", 0)
                # Actual buff application logic would go here (e.g., modifying target_char.combat_stats temporarily or adding a status effect)
                messages.append(f"{target_char.name} receives a buff to {stat} by {modifier} for {duration} turns. (Buffs not fully implemented).")
                logging.info(f"Buff from item '{item_id}' applied to '{target_char.name}': stat {stat}, modifier {modifier}, duration {duration}")
            else:
                messages.append(f"Unknown effect type '{effect_type}' for item '{item.name}'.")

        self.remove_from_inventory(item_id)
        full_message = ". ".join(messages)
        notify_dm(full_message)
        return True, full_message

    def add_to_inventory(self,item_id:str):
        if not isinstance(item_id,str): raise TypeError("Item ID must be a string.");
        if not item_id.strip(): raise ValueError("Item ID cannot be an empty string.")
        self.inventory.append(item_id)

    def remove_from_inventory(self,item_id:str)->bool:
        if not isinstance(item_id,str): raise TypeError("Item ID must be a string.")
        try:
            self.inventory.remove(item_id)
            return True
        except ValueError: # Item not found in inventory
            return False

    def change_currency(self,gold_d=0,silver_d=0,copper_d=0)->bool:
        if "currency" not in self.equipment or not isinstance(self.equipment["currency"],dict):
            self.equipment["currency"] = {"gold":0, "silver":0, "copper":0} # Initialize if missing

        current_gold = self.equipment["currency"].get("gold",0)
        # Add other currency types if necessary

        if gold_d < 0 and current_gold < abs(gold_d): # Check if enough gold to spend
            return False

        self.equipment["currency"]["gold"] = current_gold + gold_d
        # Add silver and copper handling
        self.equipment["currency"]["silver"] = self.equipment["currency"].get("silver",0) + silver_d
        self.equipment["currency"]["copper"] = self.equipment["currency"].get("copper",0) + copper_d
        return True

    def get_ability_modifier(self,ability_name:str)->int:
        score = self.ability_scores.get(ability_name.lower())
        if score is None or not isinstance(score,int):
            logging.warning(f"Ability '{ability_name.lower()}' not found or invalid for player {self.name}. Defaulting modifier to 0.")
            return 0
        return (score - 10) // 2

    def perform_skill_check(self,skill_name:str,dc:int)->tuple[bool,int,int,str]:
        skill_normalized = skill_name.lower()
        roll = roll_dice(sides=20)

        ability_name = SKILL_ABILITY_MAP.get(skill_normalized)
        ability_modifier = 0
        ability_mod_str = "N/A"
        if ability_name:
            ability_modifier = self.get_ability_modifier(ability_name)
            ability_mod_str = str(ability_modifier)
        else:
            logging.warning(f"Skill '{skill_normalized}' not found in SKILL_ABILITY_MAP for player {self.name}.")

        proficiency_bonus_val = 0
        proficiency_bonus_str = "0"
        # Ensure proficiencies_map and 'skills' list exist
        player_proficiencies = self.proficiencies_map.get('skills', [])
        if not isinstance(player_proficiencies, list): player_proficiencies = []

        if skill_normalized in player_proficiencies:
            proficiency_bonus_val = PROFICIENCY_BONUS
            proficiency_bonus_str = str(proficiency_bonus_val)

        total_roll = roll + ability_modifier + proficiency_bonus_val
        success = total_roll >= dc

        breakdown = f"d20({roll}) + {ability_name.upper() if ability_name else 'N/A'}_MOD({ability_mod_str}) + PROF({proficiency_bonus_str}) = {total_roll} vs DC({dc})"
        return success, roll, total_roll, breakdown

    def cast_spell(self,spell_name:str,game_state:'GameState',target:'Character'=None)->tuple[bool,str]:
        spell = SPELLBOOK.get(spell_name)
        if not spell: return False, f"Spell '{spell_name}' not found in spellbook."

        actual_target = target if spell.target_type != "self" else self
        if not actual_target and spell.target_type != "self":
            return False, f"Spell '{spell_name}' requires a target."
        if not isinstance(actual_target, Character): # Ensure target is a Character (or subclass)
             return False, "Invalid target type for spell."

        slot_message_part = ""
        if spell.level > 0: # Check for spell slots for non-cantrips
            if not self.has_spell_slot(spell.level):
                return False, f"Not enough level {spell.level} spell slots to cast '{spell_name}'."
            if not self.consume_spell_slot(spell.level): # Should always succeed if has_spell_slot was true
                logging.error(f"Failed to consume spell slot for '{spell_name}' for player {self.name} despite check passing.")
                return False, f"Error consuming spell slot for '{spell_name}'."
            slot_message_part = f", consuming a level {spell.level} slot"

        base_value = 0
        dice_roll_str = ""
        if spell.dice_expression:
            try:
                parts = spell.dice_expression.lower().split('d')
                num_dice, dice_sides_str = (1, "0")
                if len(parts) == 2:
                    num_dice_str, dice_sides_str = parts
                    num_dice = int(num_dice_str) if num_dice_str else 1
                elif len(parts) == 1 and parts[0].isdigit(): # e.g. "6" meaning 1d6 if context implies, or just a flat number
                    dice_sides_str = parts[0] # For flat number, num_dice remains 1, dice_sides is the number
                    # This interpretation needs clarification. Assuming "XdY" or "Y" (flat)
                    # If it's just "Y", it should be treated as a flat value, not 1dY.
                    # Let's assume dice_expression is always XdY or XdY+Z for now for dice part.
                    # For flat values, they should be in spell.base_value_fixed or similar.
                    # Re-evaluating: if it's XdY or dY for dice.
                    # If spell.dice_expression is "10", it's likely a flat value, not 1d10.
                    # Let's refine: if 'd' is not in it, it's a flat bonus to a base_value_fixed or just the value.
                    # For now, assuming XdY format for dice_expression.
                    # The original code assumes XdY or Y (meaning 1dY). Let's stick to that for now.
                    num_dice = 1 # if only one part and it's digits, means 1d<value>
                else: # Should be XdY
                    raise ValueError("Invalid dice expression format.")

                dice_sides = int(dice_sides_str)
                if num_dice <=0 or dice_sides <=0: raise ValueError("Number of dice and dice sides must be positive.")

                roll_result = roll_dice(sides=dice_sides, num_dice=num_dice)
                base_value += roll_result
                dice_roll_str = f"{spell.dice_expression}({roll_result})"
            except ValueError as e:
                logging.error(f"Error parsing dice expression '{spell.dice_expression}' for spell '{spell_name}': {e}")
                return False, f"Error with spell '{spell_name}': Invalid dice expression."

        ability_modifier_value = 0
        modifier_str = ""
        if spell.stat_modifier_ability:
            ability_modifier_value = self.get_ability_modifier(spell.stat_modifier_ability)
            modifier_str = f" + {spell.stat_modifier_ability[:3].upper()}({ability_modifier_value})"

        total_value = max(0, base_value + ability_modifier_value) # Ensure non-negative result for effects
        effect_description = ""

        if spell.effect_type == "heal":
            actual_target.heal(total_value)
            effect_description = f"Healed {total_value} HP."
        elif spell.effect_type == "damage":
            actual_target.take_damage(total_value)
            effect_description = f"Dealt {total_value} {spell.name.lower().replace(' ', '_')} damage."
        # Add other effect types like "buff", "debuff", "control" here
        else:
            effect_description = "Unknown spell effect."
            logging.warning(f"Spell '{spell_name}' has an unknown effect_type: {spell.effect_type}")

        target_name_str = actual_target.name
        calculation_parts = [p for p in [dice_roll_str, modifier_str.replace(" + ","",1) if not dice_roll_str else modifier_str] if p]
        calculation_final_str = " ".join(calculation_parts)
        if calculation_final_str: calculation_final_str += f" = {total_value}"
        else: calculation_final_str = str(total_value) # If no dice or mod, just show total

        message = f"{self.name} casts '{spell_name}' on {target_name_str}{slot_message_part}. {effect_description} ({calculation_final_str})"
        return True, message

    def has_spell_slot(self,spell_level:int)->bool:
        return self.spell_slots.get(f"level_{spell_level}",{}).get("current",0) > 0

    def consume_spell_slot(self,spell_level:int)->bool:
        level_key = f"level_{spell_level}"
        if self.has_spell_slot(spell_level):
            self.spell_slots[level_key]["current"] -=1
            return True
        return False

    def apply_rewards(self,rewards:dict, game_state: 'GameState')->list[str]:
        messages = []
        if "xp" in rewards and isinstance(rewards["xp"],int) and rewards["xp"] > 0:
            self.experience_points += rewards["xp"]
            messages.append(f"Gained {rewards['xp']} XP.")
        if "items" in rewards and isinstance(rewards["items"],list):
            for item_id_reward in rewards["items"]:
                if isinstance(item_id_reward, str):
                    self.add_to_inventory(item_id_reward)
                    # Get item name for message if possible
                    item_object = self._get_item_from_game_state(item_id_reward, game_state)
                    item_name_for_msg = item_object.name if item_object else item_id_reward
                    messages.append(f"Obtained: {item_name_for_msg}.")
                else:
                    logging.warning(f"Invalid item_id type in rewards: {item_id_reward}")
        if "currency" in rewards and isinstance(rewards["currency"],dict):
            for currency_type, amount_reward in rewards["currency"].items():
                if isinstance(currency_type,str) and isinstance(amount_reward,int) and amount_reward > 0:
                    if "currency" not in self.equipment: self.equipment["currency"] = {} # Ensure dict exists
                    self.equipment["currency"][currency_type] = self.equipment.get("currency",{}).get(currency_type,0) + amount_reward
                    messages.append(f"Received {amount_reward} {currency_type}.")
                else:
                     logging.warning(f"Invalid currency type or amount in rewards: {currency_type},{amount_reward}")

        if "faction_rep_changes" in rewards and isinstance(rewards["faction_rep_changes"], list):
            for rep_change in rewards["faction_rep_changes"]:
                if isinstance(rep_change, dict):
                    faction_id_change = rep_change.get("faction_id")
                    amount_change = rep_change.get("amount")
                    if faction_id_change and isinstance(amount_change, int):
                        # change_faction_reputation is not defined yet, assuming it will be.
                        # For now, directly modify self.faction_reputations.
                        # self.change_faction_reputation(faction_id_change, amount_change, game_state)
                        self.faction_reputations[faction_id_change] = self.faction_reputations.get(faction_id_change, 0) + amount_change
                        faction_obj = game_state.factions.get(faction_id_change)
                        faction_name_msg = faction_obj.name if faction_obj else faction_id_change
                        change_type = "increased" if amount_change > 0 else "decreased"
                        messages.append(f"Reputation with {faction_name_msg} {change_type} by {abs(amount_change)}.")
                        notify_dm(f"Player {self.name} reputation with {faction_name_msg} changed by {amount_change} to {self.faction_reputations[faction_id_change]}.")

                    else:
                        logging.warning(f"Player {self.name}: Invalid faction reputation change data in rewards: {rep_change}")
                else:
                    logging.warning(f"Player {self.name}: Invalid entry in faction_rep_changes list: {rep_change}")

        if messages: notify_dm(f"Rewards for {self.name}: {'. '.join(messages)}.")
        return messages

    def change_faction_reputation(self, faction_id: str, amount: int, game_state: 'GameState'):
        """Changes player's reputation with a faction and notifies the DM."""
        if not faction_id or not isinstance(faction_id, str):
            logging.warning(f"Player {self.name}: Invalid faction_id for reputation change: {faction_id}")
            return
        if not isinstance(amount, int):
            logging.warning(f"Player {self.name}: Invalid amount for reputation change with {faction_id}: {amount}")
            return

        current_rep = self.faction_reputations.get(faction_id, 0)
        new_rep = current_rep + amount
        self.faction_reputations[faction_id] = new_rep

        faction = game_state.factions.get(faction_id)
        faction_name = faction.name if faction else faction_id
        change_direction = "increased" if amount > 0 else "decreased"
        if amount == 0: change_direction = "did not change"

        logging.info(f"Player {self.name}'s reputation with {faction_name} {change_direction} by {abs(amount)}. New reputation: {new_rep}")
        notify_dm(f"Player {self.name}'s reputation with {faction_name} {change_direction} by {abs(amount)} to {new_rep}.")


    def accept_quest(self, quest_id:str, initial_stage_id:str)->tuple[bool,str]:
        if quest_id in self.active_quests: return False, f"Quest '{quest_id}' is already active."
        if quest_id in self.completed_quests: return False, f"Quest '{quest_id}' has already been completed."

        quest_template = ALL_QUESTS.get(quest_id)
        if not quest_template: return False, f"Quest template '{quest_id}' not found."

        self.active_quests[quest_id] = {"current_stage_id": initial_stage_id, "completed_optional_objectives": []}

        description = f"Adventure '{quest_template.title}' begins!"
        stage = next((s for s in quest_template.stages if s["stage_id"] == initial_stage_id), None)
        if stage and stage.get("status_description"):
            description = stage["status_description"]

        notify_dm(f"Quest '{quest_id}' ({quest_template.title}) accepted by {self.name}. Current Stage: {initial_stage_id}. {description}")
        return True, f"Quest '{quest_template.title}' accepted."

    def advance_quest_stage(self,quest_id:str, new_stage_id:str)->tuple[bool,str]:
        if quest_id not in self.active_quests: return False, f"Quest '{quest_id}' is not active."

        quest_template = ALL_QUESTS.get(quest_id)
        if not quest_template: return False, f"Quest template '{quest_id}' not found (should not happen for active quest)."

        self.active_quests[quest_id]["current_stage_id"] = new_stage_id

        description = f"Player {self.name} advanced to stage '{new_stage_id}'."
        stage = next((s for s in quest_template.stages if s["stage_id"] == new_stage_id), None)
        if stage and stage.get("status_description"):
            description = stage["status_description"]

        notify_dm(f"Quest '{quest_id}' ({quest_template.title}) for {self.name} advanced. New Stage: {new_stage_id}. {description}")
        return True, f"Quest '{quest_template.title}' advanced to stage '{new_stage_id}'."

    def complete_optional_objective(self,quest_id:str, optional_objective_id:str)->tuple[bool,str]:
        if quest_id not in self.active_quests: return False, f"Quest '{quest_id}' is not active."

        quest_template = ALL_QUESTS.get(quest_id)
        if not quest_template: return False, f"Quest template '{quest_id}' not found."

        if optional_objective_id not in self.active_quests[quest_id]["completed_optional_objectives"]:
            self.active_quests[quest_id]["completed_optional_objectives"].append(optional_objective_id)

            description = f"Player {self.name} completed optional objective '{optional_objective_id}'."
            opt_obj_data = next((o for o in quest_template.optional_objectives if o["objective_id"] == optional_objective_id), None)
            if opt_obj_data and opt_obj_data.get("status_description"):
                description = opt_obj_data["status_description"]

            notify_dm(f"Optional objective '{optional_objective_id}' for quest '{quest_id}' ({quest_template.title}) completed by {self.name}. {description}")
            return True, f"Optional objective '{optional_objective_id}' for quest '{quest_template.title}' completed."
        return False, f"Optional objective '{optional_objective_id}' was already completed."

    def complete_quest(self,quest_id:str)->tuple[bool,str]:
        if quest_id not in self.active_quests: return False, f"Quest '{quest_id}' is not active or already completed."

        quest_template = ALL_QUESTS.get(quest_id)
        if not quest_template: return False, f"Quest template '{quest_id}' not found."

        del self.active_quests[quest_id]
        if quest_id not in self.completed_quests: self.completed_quests.append(quest_id)

        description = f"Quest '{quest_template.title}' completed by {self.name}!"
        if quest_template.description: # Overall quest description
            description = f"Player {self.name} completed: {quest_template.title}! {quest_template.description}"

        notify_dm(description)
        return True, f"Quest '{quest_template.title}' completed."

class NPC(Character):
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str,
                 dialogue_responses: dict = None, active_time_periods: list[str] | None = None,
                 is_currently_active: bool = True, faction_id: str | None = None,
                 sells_item_ids: list[str] | None = None): # Added faction_id and sells_item_ids
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.dialogue_responses = dialogue_responses if dialogue_responses else {}
        self.active_time_periods = active_time_periods # List of time periods like '오전', '오후'
        self.is_currently_active = is_currently_active # Based on current game time vs active_time_periods
        self.faction_id = faction_id
        self.sells_item_ids = sells_item_ids if sells_item_ids is not None else []


    def get_dialogue_node(self, key: str) -> dict | None:
        return self.dialogue_responses.get(key)

# Example of how PlayerState might look (if it's simple enough to not need its own file yet)
# This is not moved from game_state.py in this step, but shown for context if needed by Character/Player.
# For now, PlayerState is not used by Character/Player methods directly.
# class PlayerState:
#     def __init__(self, player_character: Player):
#         self.player_character = player_character
#         self.current_location_id: str | None = None
#         # ... other stateful player session data
#         self.is_in_combat = False
#         self.participants_in_combat: list[Character] = []
#         self.current_turn_character_id: str | None = None
#         self.turn_order: list[str] = []
#         self.current_dialogue_npc_id: str | None = None
#         self.current_dialogue_key: str | None = "greetings"
