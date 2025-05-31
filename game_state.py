from utils import roll_dice, SKILL_ABILITY_MAP, PROFICIENCY_BONUS
import random # random is still used by other parts of game_state.py like status effect application
import logging # For logging warnings
from magic import SPELLBOOK, Spell # Import necessary spellcasting components
from gemini_dm import notify_dm # Import for DM notifications
from quests import ALL_QUESTS # Import for accessing quest details
from factions import Faction # Added import

# Import necessary functions/classes from data_loader and config for the main block
import json # For main block example printing
from data_loader import load_raw_data_from_sources, create_npc_from_data
from config import RAG_DOCUMENT_SOURCES


# --- CLASS DEFINITIONS (Location, Item, Weapon, Armor, Consumable, KeyItem, Character, Player, NPC) ---
# These class definitions are assumed to be the same as provided in the previous successful step.
# For brevity in this tool call, I will not repeat them here, but they are part of the file.

class Location:
    """
    Represents a game location or region.
    JSON structure: (as previously defined)
    """
    def __init__(self, id: str, name: str, description: str, exits: dict[str, str],
                 item_ids: list[str] = None, npc_ids: list[str] = None, game_object_ids: list[str] = None):
        self.id = id
        self.name = name
        self.description = description
        self.exits = exits if exits is not None else {}
        self.item_ids = item_ids if item_ids is not None else []
        self.npc_ids = npc_ids if npc_ids is not None else []
        self.game_object_ids = game_object_ids if game_object_ids is not None else []
    def __repr__(self): return f"<Location(id='{self.id}', name='{self.name}')>"

class Item:
    """ Base class for all items. JSON structure: (as previously defined) """
    def __init__(self, id: str, name: str, description: str, item_type: str,
                 weight: float = 0.0, value: dict = None, lore_keywords: list[str] = None):
        if not id or not isinstance(id, str): raise ValueError("Item ID must be a non-empty string.")
        if not name or not isinstance(name, str): raise ValueError("Item name must be a non-empty string.")
        self.id = id
        self.name = name
        self.description = description
        self.item_type = item_type
        self.weight = weight
        self.value = value if value is not None else {"buy": 0, "sell": 0}
        self.lore_keywords = lore_keywords if lore_keywords is not None else []
    def __repr__(self): return f"<Item(id='{self.id}', name='{self.name}', type='{self.item_type}')>"

class Weapon(Item):
    """ Weapon item. JSON structure: (as previously defined) """
    def __init__(self, id: str, name: str, description: str,
                 damage_dice: str, attack_bonus: int = 0, damage_bonus: int = 0,
                 weapon_type: str = "sword", weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, description, "weapon", weight, value, lore_keywords)
        if not damage_dice or not isinstance(damage_dice, str): raise ValueError("Weapon damage_dice must be a non-empty string.")
        self.damage_dice = damage_dice
        self.attack_bonus = attack_bonus
        self.damage_bonus = damage_bonus
        self.weapon_type = weapon_type
    def __repr__(self): return f"<Weapon(id='{self.id}', name='{self.name}', damage='{self.damage_dice}')>"

class Armor(Item):
    """ Armor item. JSON structure: (as previously defined) """
    def __init__(self, id: str, name: str, description: str,
                 ac_bonus: int, armor_type: str = "medium",
                 weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, description, "armor", weight, value, lore_keywords)
        if not isinstance(ac_bonus, int): raise ValueError("Armor ac_bonus must be an integer.")
        self.ac_bonus = ac_bonus
        self.armor_type = armor_type
    def __repr__(self): return f"<Armor(id='{self.id}', name='{self.name}', ac_bonus='{self.ac_bonus}')>"

class Consumable(Item):
    """ Consumable item. JSON structure: (as previously defined) """
    def __init__(self, id: str, name: str, description: str,
                 effects: list[dict], weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, description, "consumable", weight, value, lore_keywords)
        if not isinstance(effects, list): raise ValueError("Consumable effects must be a list.")
        self.effects = effects
    def __repr__(self): return f"<Consumable(id='{self.id}', name='{self.name}', effects_count='{len(self.effects)}')>"

class KeyItem(Item):
    """ Key item. JSON structure: (as previously defined) """
    def __init__(self, id: str, name: str, description: str,
                 unlocks: list[str] = None, weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, description, "key_item", weight, value, lore_keywords)
        self.unlocks = unlocks if unlocks is not None else []
    def __repr__(self): return f"<KeyItem(id='{self.id}', name='{self.name}')>"

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
                parts = cur_dmg_dice.lower().split('d')
                num_dice, dice_sides = (1,4)
                if len(parts)==2: num_dice,dice_sides = (int(parts[0]) if parts[0] else 1), int(parts[1])
                elif len(parts)==1 and parts[0].isdigit(): num_dice,dice_sides = 1,int(parts[0]); cur_dmg_dice=f"1d{dice_sides}"
                else: raise ValueError("Invalid XdY or dY.")
                if num_dice<=0 or dice_sides<=0: raise ValueError("Dice/sides positive.")
            except ValueError as e: raise ValueError(f"Parse error '{cur_dmg_dice}' for {self.name}: {e}")
            dmg_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
            total_dmg = max(0, dmg_roll + cur_dmg_bonus)
            target.take_damage(total_dmg)
            dm_msg += f" Deals {num_dice}d{dice_sides}({dmg_roll})+DMG({cur_dmg_bonus})={total_dmg} damage."
            dm_msg += f" {target.name} HP: {target.current_hp}/{target.max_hp}."
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
        self.inventory: list[str] = player_data.get("inventory",[])
        self.equipment: dict[str, str|None|dict] = player_data.get("equipment",{})
        if "currency" not in self.equipment: self.equipment["currency"]={}
        for slot in ["weapon","armor","shield"]:
            if slot not in self.equipment: self.equipment[slot]=None
        self.base_armor_class = self.combat_stats.get('armor_class',10)
        self.active_quests = player_data.get("active_quests",{})
        self.completed_quests = player_data.get("completed_quests",[])
    def _get_item_from_game_state(self, item_id:str, game_state:'GameState')->Item|None:
        if not item_id: return None
        item = game_state.items.get(item_id)
        if not item: logging.warning(f"Player {self.name}: Item ID '{item_id}' not found in GameState.items.")
        return item
    def equip_item(self, item_id:str, slot:str, game_state:'GameState')->bool:
        item = self._get_item_from_game_state(item_id, game_state)
        if not item: return False
        if slot not in self.equipment: logging.warning(f"Player {self.name}: Slot '{slot}' nonexistent."); return False
        valid = (slot=="weapon" and isinstance(item,Weapon)) or \
                (slot=="armor" and isinstance(item,Armor) and item.armor_type!="shield") or \
                (slot=="shield" and isinstance(item,Armor) and item.armor_type=="shield")
        if not valid: logging.warning(f"Player {self.name}: Cannot equip {item.name}({item.item_type}) in {slot}."); return False
        curr_item_id = self.equipment.get(slot)
        if isinstance(curr_item_id,str) and curr_item_id!=item_id: self.add_to_inventory(curr_item_id)
        self.equipment[slot]=item_id
        if item_id in self.inventory: self.remove_from_inventory(item_id)
        notify_dm(f"{self.name} equipped {item.name} in {slot}.")
        return True
    def unequip_item(self, slot:str, game_state:'GameState')->str|None:
        if slot not in self.equipment: logging.warning(f"Player {self.name}: Slot '{slot}' nonexistent."); return None
        item_id = self.equipment.get(slot)
        if isinstance(item_id,str):
            item_obj = self._get_item_from_game_state(item_id,game_state)
            name = item_obj.name if item_obj else item_id
            self.equipment[slot]=None
            self.add_to_inventory(item_id)
            notify_dm(f"{self.name} unequipped {name} from {slot}. Added to inventory.")
            return item_id
        return None
    def get_equipped_weapon_stats(self, game_state:'GameState')->dict:
        wp_id = self.equipment.get("weapon")
        if isinstance(wp_id,str):
            item = self._get_item_from_game_state(wp_id,game_state)
            if isinstance(item,Weapon): return {"damage_dice":item.damage_dice,"attack_bonus":item.attack_bonus,"damage_bonus":item.damage_bonus}
        return {"damage_dice":self.base_damage_dice,"attack_bonus":0,"damage_bonus":0}
    def get_equipped_armor_ac_bonus(self, game_state:'GameState')->int:
        ac_bonus=0
        for slot_type in ["armor","shield"]:
            item_id = self.equipment.get(slot_type)
            if isinstance(item_id,str):
                item = self._get_item_from_game_state(item_id,game_state)
                if isinstance(item,Armor) and ((slot_type=="armor" and item.armor_type!="shield") or (slot_type=="shield" and item.armor_type=="shield")):
                    ac_bonus+=item.ac_bonus
        return ac_bonus
    def get_effective_armor_class(self,game_state:'GameState')->int: return self.base_armor_class + self.get_equipped_armor_ac_bonus(game_state)
    def use_item(self,item_id:str,game_state:'GameState',target:'Character'=None)->tuple[bool,str]:
        if item_id not in self.inventory: return False, f"Item '{item_id}' not in inventory."
        item = self._get_item_from_game_state(item_id,game_state)
        if not item: return False, f"Item data for '{item_id}' not retrieved."
        if not isinstance(item,Consumable): return False, f"'{item.name}' is not consumable."
        tgt = target if target else self
        msgs = [f"{self.name} uses {item.name}."]
        for eff in item.effects:
            eff_type = eff.get("effect_type")
            if eff_type=="heal":
                amt_str = eff.get("amount","0"); roll_amt=0
                try:
                    if 'd' in amt_str:
                        parts=amt_str.split('d'); num_d=int(parts[0]); dice_p=parts[1]; bonus=0
                        if '+' in dice_p: d_sides_str,b_str = dice_p.split('+'); bonus=int(b_str)
                        else: d_sides_str=dice_p
                        roll_amt=roll_dice(int(d_sides_str),num_d)+bonus
                    else: roll_amt=int(amt_str)
                    roll_amt=max(0,roll_amt); tgt.heal(roll_amt)
                    msgs.append(f"{tgt.name} healed for {roll_amt} HP. HP: {tgt.current_hp}/{tgt.max_hp}")
                except ValueError: msgs.append(f"Invalid amount format: {amt_str}"); logging.error(f"Invalid heal amount {item_id}: {amt_str}")
            elif eff_type=="buff":
                stat,mod,dur = eff.get("stat","?"),eff.get("modifier",0),eff.get("duration",0)
                msgs.append(f"{tgt.name} buff to {stat} by {mod} for {dur} (Buffs not fully implemented).")
                logging.info(f"Buff from {item_id} to {tgt.name}: stat {stat}, mod {mod}, dur {dur}")
            else: msgs.append(f"Unknown effect '{eff_type}' for '{item.name}'.")
        self.remove_from_inventory(item_id); notify_dm(". ".join(msgs))
        return True, ". ".join(msgs)
    def add_to_inventory(self,item_id:str):
        if not isinstance(item_id,str): raise TypeError("Item ID string.");
        if not item_id.strip(): raise ValueError("Item ID non-empty.")
        self.inventory.append(item_id)
    def remove_from_inventory(self,item_id:str)->bool:
        if not isinstance(item_id,str): raise TypeError("Item ID string.")
        try: self.inventory.remove(item_id); return True
        except ValueError: return False
    def change_currency(self,gold_d=0,silver_d=0,copper_d=0)->bool:
        if "currency" not in self.equipment or not isinstance(self.equipment["currency"],dict): self.equipment["currency"]={}
        for c_type in ["gold","silver","copper"]:
            if c_type not in self.equipment["currency"]: self.equipment["currency"][c_type]=0
        if gold_d<0 and self.equipment["currency"].get("gold",0)<abs(gold_d): return False
        self.equipment["currency"]["gold"] = self.equipment["currency"].get("gold",0)+gold_d
        self.equipment["currency"]["silver"] = self.equipment["currency"].get("silver",0)+silver_d
        self.equipment["currency"]["copper"] = self.equipment["currency"].get("copper",0)+copper_d
        return True
    def get_ability_modifier(self,ability_name:str)->int:
        score=self.ability_scores.get(ability_name.lower())
        if score is None or not isinstance(score,int): logging.warning(f"Ability '{ability_name.lower()}' invalid for {self.name}. Mod 0."); return 0
        return(score-10)//2
    def perform_skill_check(self,skill_name:str,dc:int)->tuple[bool,int,int,str]:
        skill_norm=skill_name.lower(); roll=roll_dice(20)
        abil_name=SKILL_ABILITY_MAP.get(skill_norm); abil_mod=0; abil_mod_s="N/A"
        if abil_name: abil_mod=self.get_ability_modifier(abil_name); abil_mod_s=str(abil_mod)
        else: logging.warning(f"Skill '{skill_norm}' not in SKILL_ABILITY_MAP for {self.name}.")
        prof_b=0; prof_b_s="0"
        prof_s=self.proficiencies_map.get('skills',[])
        if not isinstance(prof_s,list): prof_s=[]
        if skill_norm in prof_s: prof_b=PROFICIENCY_BONUS; prof_b_s=str(prof_b)
        total=roll+abil_mod+prof_b; success=total>=dc
        breakdown=f"d20({roll})+{abil_name.upper() if abil_name else 'N/A'}_MOD({abil_mod_s})+PROF({prof_b_s})={total} vs DC({dc})"
        return success,roll,total,breakdown
    def cast_spell(self,spell_name:str,game_state:'GameState',target:'Character'=None)->tuple[bool,str]:
        spell=SPELLBOOK.get(spell_name)
        if not spell: return False, f"Spell '{spell_name}' not found."
        actual_t = target if spell.target_type!="self" else self
        if not actual_t and spell.target_type!="self": return False, f"Spell '{spell_name}' needs target."
        if not isinstance(actual_t,Character): return False, "Invalid target type."
        slot_msg_part=""
        if spell.level>0:
            if not self.has_spell_slot(spell.level): return False, f"No L{spell.level} slots for '{spell_name}'."
            if not self.consume_spell_slot(spell.level): logging.error(f"Fail consume slot for '{spell_name}' for {self.name}."); return False, f"Error consume slot for '{spell_name}'."
            slot_msg_part=f", consuming L{spell.level} slot"
        base_val=0; dice_s=""
        if spell.dice_expression:
            try:
                parts=spell.dice_expression.lower().split('d'); num_d,d_sides=1,0
                if len(parts)==2: num_d_s,d_sides_s=parts; d_sides=int(d_sides_s); num_d=int(num_d_s) if num_d_s else 1
                elif len(parts)==1 and parts[0].isdigit(): d_sides=int(parts[0]); num_d=1
                else: raise ValueError("Invalid format.")
                if num_d<=0 or d_sides<=0: raise ValueError("Dice/sides positive.")
                roll_res=roll_dice(d_sides,num_d); base_val+=roll_res; dice_s=f"{spell.dice_expression}({roll_res})"
            except ValueError as e: logging.error(f"Error parse dice spell '{spell_name}': {e}"); return False, f"Error spell '{spell_name}': Invalid dice."
        abil_mod_val=0; mod_s=""
        if spell.stat_modifier_ability: abil_mod_val=self.get_ability_modifier(spell.stat_modifier_ability); mod_s=f" + {spell.stat_modifier_ability[:3].upper()}({abil_mod_val})"
        total_val=max(0,base_val+abil_mod_val); eff_desc=""
        if spell.effect_type=="heal": actual_t.heal(total_val); eff_desc=f"Healed {total_val} HP."
        elif spell.effect_type=="damage": actual_t.take_damage(total_val); eff_desc=f"Dealt {total_val} {spell.name.lower().replace(' ','_')} damage."
        else: eff_desc="Unknown spell effect."; logging.warning(f"Spell '{spell_name}' unknown effect: {spell.effect_type}")
        target_n=actual_t.name
        calc_p=[p for p in [dice_s,mod_s.replace(" + ","",1) if not dice_s else mod_s] if p]; calc_f=" ".join(calc_p)
        if calc_f: calc_f+=f" = {total_val}"
        else: calc_f=str(total_val)
        msg=f"{self.name} casts '{spell_name}' on {target_n}{slot_msg_part}. {eff_desc} ({calc_f})"
        return True,msg
    def has_spell_slot(self,spell_level:int)->bool: return self.spell_slots.get(f"level_{spell_level}",{}).get("current",0)>0
    def consume_spell_slot(self,spell_level:int)->bool:
        if self.has_spell_slot(spell_level): self.spell_slots[f"level_{spell_level}"]["current"]-=1; return True
        return False
    def apply_rewards(self,rewards:dict, game_state: 'GameState')->list[str]:
        msgs=[]
        if "xp" in rewards and isinstance(rewards["xp"],int) and rewards["xp"]>0: self.experience_points+=rewards["xp"]; msgs.append(f"Gained {rewards['xp']} XP.")
        if "items" in rewards and isinstance(rewards["items"],list):
            for item_id in rewards["items"]:
                if isinstance(item_id,str): self.add_to_inventory(item_id); msgs.append(f"Obtained: {item_id}.")
                else: logging.warning(f"Invalid item_id in rewards: {item_id}")
        if "currency" in rewards and isinstance(rewards["currency"],dict):
            for c_type,amt in rewards["currency"].items():
                if isinstance(c_type,str) and isinstance(amt,int) and amt>0:
                    if "currency" not in self.equipment: self.equipment["currency"]={}
                    self.equipment["currency"][c_type]=self.equipment.get("currency",{}).get(c_type,0)+amt
                    msgs.append(f"Received {amt} {c_type}.")
                else: logging.warning(f"Invalid currency rewards: {c_type},{amt}")

        if "faction_rep_changes" in rewards and isinstance(rewards["faction_rep_changes"], list):
            for rep_change in rewards["faction_rep_changes"]:
                if isinstance(rep_change, dict):
                    faction_id = rep_change.get("faction_id")
                    amount = rep_change.get("amount")
                    if faction_id and isinstance(amount, int):
                        self.change_faction_reputation(faction_id, amount, game_state)
                        # The change_faction_reputation method already logs and notifies DM
                    else:
                        logging.warning(f"Player {self.name}: Invalid faction reputation change data in rewards: {rep_change}")
                else:
                    logging.warning(f"Player {self.name}: Invalid entry in faction_rep_changes list: {rep_change}")

        if msgs: notify_dm(f"Rewards for {self.name}: {'. '.join(msgs)}.")
        return msgs
    def accept_quest(self, q_id:str, stage_id:str)->tuple[bool,str]:
        if q_id in self.active_quests: return False, f"Quest '{q_id}' active."
        if q_id in self.completed_quests: return False, f"Quest '{q_id}' completed."
        self.active_quests[q_id]={"current_stage_id":stage_id,"completed_optional_objectives":[]}
        q_obj=ALL_QUESTS.get(q_id); desc="Adventure begins!"
        if q_obj:
            stage=next((s for s in q_obj.stages if s["stage_id"]==stage_id),None)
            if stage and stage.get("status_description"): desc=stage["status_description"]
        notify_dm(f"Quest '{q_id}' ({q_obj.title if q_obj else ''}) accepted by {self.name}. Stage: {stage_id}. {desc}")
        return True, f"Quest '{q_id}' accepted."
    def advance_quest_stage(self,q_id:str,new_stage_id:str)->tuple[bool,str]:
        if q_id in self.active_quests:
            self.active_quests[q_id]["current_stage_id"]=new_stage_id
            q_obj=ALL_QUESTS.get(q_id); desc=f"Player {self.name} advanced to stage '{new_stage_id}'."
            if q_obj:
                stage=next((s for s in q_obj.stages if s["stage_id"]==new_stage_id),None)
                if stage and stage.get("status_description"): desc=stage["status_description"]
            notify_dm(f"Quest '{q_id}' ({q_obj.title if q_obj else ''}) for {self.name} advanced. Stage: {new_stage_id}. {desc}")
            return True, f"Quest '{q_id}' advanced to {new_stage_id}."
        return False, f"Quest '{q_id}' not active."
    def complete_optional_objective(self,q_id:str,opt_id:str)->tuple[bool,str]:
        if q_id in self.active_quests:
            if opt_id not in self.active_quests[q_id]["completed_optional_objectives"]:
                self.active_quests[q_id]["completed_optional_objectives"].append(opt_id)
                q_obj=ALL_QUESTS.get(q_id); desc=f"Player {self.name} completed opt obj '{opt_id}'."
                if q_obj:
                    opt_o=next((o for o in q_obj.optional_objectives if o["objective_id"]==opt_id),None)
                    if opt_o and opt_o.get("status_description"): desc=opt_o["status_description"]
                notify_dm(f"Opt obj '{opt_id}' for quest '{q_id}' ({q_obj.title if q_obj else ''}) done by {self.name}. {desc}")
                return True, f"Opt obj '{opt_id}' for '{q_id}' done."
            return False, f"Opt obj '{opt_id}' already done."
        return False, f"Quest '{q_id}' not active."
    def complete_quest(self,q_id:str)->tuple[bool,str]:
        if q_id in self.active_quests:
            del self.active_quests[q_id]
            if q_id not in self.completed_quests: self.completed_quests.append(q_id)
            q_obj=ALL_QUESTS.get(q_id); desc=f"Quest '{q_id}' done by {self.name}!"
            if q_obj and q_obj.description: desc=f"Player {self.name} completed: {q_obj.title}! {q_obj.description}"
            notify_dm(desc)
            return True, f"Quest '{q_id}' completed."
        return False, f"Quest '{q_id}' not active/already done."

class NPC(Character):
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: dict, base_damage_dice: str, dialogue_responses: dict = None):
        super().__init__(id, name, max_hp, combat_stats, base_damage_dice)
        self.dialogue_responses = dialogue_responses if dialogue_responses else {}
    def get_dialogue_node(self, key: str) -> dict | None: return self.dialogue_responses.get(key)

class GameState:
    player_character: Player
    locations: dict[str, Location]
    items: dict[str, Item]
    npcs: dict[str, NPC]
    factions: dict[str, Faction] # Added type hint for factions
    game_objects: dict[str, dict]
    rag_documents: dict[str, list[dict | str]]
    # ... other attributes might be here or implicitly defined in __init__

    def __init__(self, player_character: Player):
        if not isinstance(player_character, Player): raise TypeError("player_character must be Player.")
        self.player_character = player_character
        self.locations: dict[str, Location] = {}
        self.items: dict[str, Item] = {}
        self.npcs: dict[str, NPC] = {}
        self.factions: dict[str, Faction] = {} # Initialized factions
        self.game_objects: dict[str, dict] = {} # For raw GameObject data
        self.rag_documents: dict[str, list[dict | str]] = {} # For other raw data for RAG

        self.world_data: dict = {} # Legacy, might merge with game_objects or specific RAG docs
        self.world_variables: dict = {}
        self.participants_in_combat: list[Character] = []
        self.current_turn_character_id: str | None = None
        self.turn_order: list[str] = []
        self.is_in_combat = False
        self.current_dialogue_npc_id: str | None = None
        self.current_dialogue_key: str | None = "greetings"

    def load_items(self, items_raw_data: list[dict]):
        for item_data in items_raw_data:
            item_id = item_data.get("id")
            if not item_id:
                logging.warning(f"Item data missing 'id'. Skipping: {item_data.get('name', 'Unknown Item')}")
                continue
            item_type = item_data.get("type")
            try:
                item_instance: Item | None = None
                if item_type == "weapon": item_instance = Weapon(**item_data)
                elif item_type == "armor": item_instance = Armor(**item_data)
                elif item_type == "consumable": item_instance = Consumable(**item_data)
                elif item_type == "key_item": item_instance = KeyItem(**item_data)
                else: # Default to generic Item
                    item_data["item_type"] = "generic" # Ensure type is set
                    item_instance = Item(**item_data)

                if item_instance: self.items[item_instance.id] = item_instance
            except Exception as e:
                logging.error(f"Error loading item '{item_id}': {e}. Data: {item_data}")

    def load_locations(self, locations_raw_data: list[dict]):
        for loc_data in locations_raw_data:
            loc_id = loc_data.get("id")
            if not loc_id:
                logging.warning(f"Location data missing 'id'. Skipping: {loc_data.get('name', 'Unknown Location')}")
                continue
            try:
                self.locations[loc_id] = Location(**loc_data)
            except Exception as e:
                logging.error(f"Error loading location '{loc_id}': {e}. Data: {loc_data}")

    def load_npcs(self, npcs_raw_data: list[dict]):
        for npc_data in npcs_raw_data:
            npc_id = npc_data.get("id")
            if not npc_id:
                logging.warning(f"NPC data missing 'id'. Skipping: {npc_data.get('name', 'Unknown NPC')}")
                continue
            # Use create_npc_from_data from data_loader.py
            npc_instance = create_npc_from_data(npc_data)
            if npc_instance:
                self.npcs[npc_instance.id] = npc_instance
            # create_npc_from_data already logs errors

    def load_factions(self, factions_raw_data: list[dict]):
        for faction_data in factions_raw_data:
            faction_id = faction_data.get("id")
            if not faction_id:
                logging.warning(f"Faction data missing 'id'. Skipping: {faction_data.get('name', 'Unknown Faction')}")
                continue

            try:
                # Core faction data for the Faction object
                faction_name = faction_data.get("name")
                if not faction_name:
                    logging.warning(f"Faction data for id '{faction_id}' missing 'name'. Skipping.")
                    continue

                # The Faction class expects: id, name, description, goals, relationships, members (optional)
                faction_instance = Faction(
                    id=faction_id,
                    name=faction_name,
                    description=faction_data.get("description", ""),
                    goals=faction_data.get("goals", ""),
                    relationships=faction_data.get("relationships", {}),
                    members=faction_data.get("members") # Pass None if not present, Faction class handles default
                )
                self.factions[faction_instance.id] = faction_instance

                # Handle RAG data: store it in self.rag_documents
                # This keeps Faction object cleaner and RAG data centralized.
                if "rag_data" in faction_data and isinstance(faction_data["rag_data"], dict):
                    # Add faction_id to the rag_data for easier linking if needed
                    rag_content = faction_data["rag_data"]
                    rag_content["faction_id_source"] = faction_id # Link back to the faction object

                    # Store under a specific key, e.g., 'Factions_RAG' or append to existing 'Factions' raw data.
                    # For simplicity, let's create/append to a 'Factions_RAG' category.
                    if 'Factions_RAG' not in self.rag_documents:
                        self.rag_documents['Factions_RAG'] = []
                    self.rag_documents['Factions_RAG'].append(rag_content)

                logging.info(f"Faction '{faction_name}' (ID: {faction_id}) loaded.")

            except KeyError as e:
                logging.error(f"Error loading faction '{faction_id}': Missing key {e}. Data: {faction_data}")
            except Exception as e:
                logging.error(f"Error loading faction '{faction_id}': {e}. Data: {faction_data}")

    def initialize_from_raw_data(self, all_raw_data: dict[str, list[dict | str]]):
        self.load_items(all_raw_data.get('Items', []))
        self.load_locations(all_raw_data.get('Regions', []))
        self.load_npcs(all_raw_data.get('NPCs', []))
        self.load_factions(all_raw_data.get('Factions', [])) # Added call

        # Load GameObjects as raw dicts
        raw_game_objects = all_raw_data.get('GameObjects', [])
        for go_dict in raw_game_objects:
            go_id = go_dict.get('id')
            if isinstance(go_id, str): # Ensure id is a string
                self.game_objects[go_id] = go_dict
            elif isinstance(go_dict, dict): # Check if go_dict is a dictionary
                 logging.warning(f"GameObject data missing 'id' or 'id' is not a string: {go_dict.get('name', 'Unknown GameObject')}")
            # If go_dict is not a dict (e.g. if load_raw_data_from_sources put a string there by mistake), skip.
            # load_raw_data_from_sources should only put dicts for JSON files.

        # Store other categories for RAG
        for category, data_list in all_raw_data.items():
            if category not in ["Items", "NPCs", "Regions", "GameObjects"]:
                self.rag_documents[category] = data_list

        # For compatibility, world_data might point to game_objects or specific RAG docs if needed by older functions
        # For now, let's keep world_data separate or decide its fate later.
        # If hidden_clue_details or puzzle_details are in GameObjects, then reveal_clue and operate_puzzle_element
        # should use self.game_objects instead of self.world_data.
        # Let's assume for now self.world_data will be populated from self.game_objects for those functions.
        self.world_data = self.game_objects # Point world_data to the new game_objects dict

    def start_dialogue(self, npc_id: str, initial_key: str = "greetings"):
        if npc_id not in self.npcs: logging.warning(f"Dialogue with non-existent NPC ID: {npc_id}"); return
        self.current_dialogue_npc_id = npc_id; self.current_dialogue_key = initial_key
    def end_dialogue(self): self.current_dialogue_npc_id = None; self.current_dialogue_key = None
    def is_in_dialogue(self) -> bool: return self.current_dialogue_npc_id is not None and self.current_dialogue_npc_id in self.npcs
    def set_dialogue_key(self, key: str): self.current_dialogue_key = key
    def get_current_dialogue_npc(self) -> NPC | None:
        if self.is_in_dialogue(): return self.npcs.get(self.current_dialogue_npc_id)
        return None
    def take_damage(self, amount: int): self.player_character.take_damage(amount)
    def heal(self, amount: int): self.player_character.heal(amount)
    def add_to_inventory(self, item_id: str): self.player_character.add_to_inventory(item_id)
    def remove_from_inventory(self, item_id: str) -> bool: return self.player_character.remove_from_inventory(item_id)
    def get_status(self) -> str:
        pc = self.player_character; inv_names = []
        for item_id in pc.inventory: item_obj=self.items.get(item_id); inv_names.append(item_obj.name if item_obj else item_id)
        inv_s = ', '.join(inv_names) if inv_names else "empty"
        return f"Player: {pc.name}, HP: {pc.current_hp}/{pc.max_hp}, Inv: [{inv_s}]"

def determine_initiative(participants:list[Character])->list[str]:
    if not participants: return []
    rolls=[{'id':p.id,'initiative':roll_dice(20)+p.combat_stats.get('initiative_bonus',0)} for p in participants]
    rolls.sort(key=lambda x:x['initiative'],reverse=True)
    return [e['id'] for e in rolls]

def player_buys_item(player:Player,npc:NPC,item_id:str,game_state:GameState)->tuple[bool,str]:
    item=game_state.items.get(item_id)
    if not item: return False, f"Item ID '{item_id}' not found."
    price=item.value.get("buy") if item.value else 0
    if price is None or price<=0: return False, f"Item '{item.name}' no buy price/not buyable."
    gold=player.equipment.get("currency",{}).get("gold",0)
    if gold<price: return False, f"'{item.name}' needs {price} gold, has {gold}."
    if not player.change_currency(gold_delta=-price): return False, "Currency error."
    player.add_to_inventory(item_id)
    new_gold=player.equipment.get("currency",{}).get("gold",0)
    notify_dm(f"{player.name} bought {item.name} from {npc.name} for {price} gold. Gold left: {new_gold}.")
    return True, f"Bought '{item.name}' for {price} gold."

def player_sells_item(player:Player,npc:NPC,item_id:str,game_state:GameState)->tuple[bool,str]:
    if item_id not in player.inventory:
        item_obj=game_state.items.get(item_id); name=item_obj.name if item_obj else item_id
        return False, f"Player no '{name}' in inventory."
    item=game_state.items.get(item_id)
    if not item: return False, f"Item ID '{item_id}' not in DB."
    price=item.value.get("sell") if item.value else 0
    if price is None or price<=0: return False, f"Item '{item.name}' no sell price/not sellable."
    if not player.remove_from_inventory(item_id): return False, f"'{item.name}' remove fail."
    if not player.change_currency(gold_delta=price): player.add_to_inventory(item_id); return False, f"'{item.name}' sell currency error."
    new_gold=player.equipment.get("currency",{}).get("gold",0)
    notify_dm(f"{player.name} sold {item.name} to {npc.name} for {price} gold. Gold now: {new_gold}.")
    return True, f"Sold '{item.name}' for {price} gold."

def reveal_clue(player:Player,obj_id:str,game_state:GameState)->tuple[bool,str]:
    if not isinstance(player,Player) or not isinstance(game_state,GameState): raise TypeError("Invalid types.")
    obj_data = game_state.game_objects.get(obj_id) # Changed from world_data to game_objects
    if not obj_data: return False, "Target not found."
    clue=obj_data.get("hidden_clue_details")
    if not clue: return False, "No hidden clue."
    if clue.get("revealed",False): return True, f"(Already found): {clue.get('clue_text','No content')}"
    skill,dc=clue.get("required_skill"),clue.get("dc")
    if not skill or dc is None: return False, "Clue info misconfigured."
    succ,_,_,breakdown=player.perform_skill_check(skill,dc)
    obj_name=obj_data.get('name',obj_id)
    if succ:
        text=clue.get("clue_text","Unknown clue."); player.discovered_clues.append(text); clue["revealed"]=True
        notify_dm(f"{player.name} found clue in {obj_name}: '{text}' (Check: {breakdown})")
        return True, text
    else:
        notify_dm(f"{player.name} failed to find clue in {obj_name}. (Check: {breakdown})")
        return False, f"Searched {obj_name}, found nothing special."

def operate_puzzle_element(player:Player,puzzle_id:str,el_id:str,new_state:str,game_state:GameState)->tuple[bool,str]:
    if not isinstance(player,Player) or not isinstance(game_state,GameState): raise TypeError("Invalid types.")
    puzzle_room_data = game_state.game_objects.get(puzzle_id) # Changed from world_data
    if not puzzle_room_data: return False, "Puzzle room not found."
    puzzle=puzzle_room_data.get("puzzle_details")
    if not puzzle or puzzle.get("type")!="lever_sequence": return False, "No lever puzzle here."
    if puzzle.get("is_solved",False): return True, "Puzzle already solved."
    element=next((el for el in puzzle.get("elements",[]) if el.get("id")==el_id),None)
    if not element: return False, f"Puzzle element '{el_id}' not found."
    avail_states=element.get("available_states",[])
    if new_state not in avail_states: return False, f"Cannot set {element.get('name',el_id)} to {new_state}. Available: {', '.join(avail_states)}"
    old_state=element.get("state"); element["state"]=new_state
    el_name=element.get('name',el_id)
    notify_dm(f"{player.name} changed {el_name} from {old_state} to {new_state}.")
    solved,solve_msg=check_puzzle_solution(puzzle_id,game_state,player)
    if solved: return True, solve_msg
    else: return True, f"{el_name} set to {new_state}. Nothing happens yet."

def check_puzzle_solution(puzzle_id:str,game_state:GameState,player:Player)->tuple[bool,str]:
    puzzle_room_data=game_state.game_objects.get(puzzle_id) # Changed from world_data
    if not puzzle_room_data: return False, "Puzzle room data not found."
    puzzle=puzzle_room_data.get("puzzle_details")
    if not puzzle: return False, "Puzzle details not found."
    if puzzle.get("is_solved",False): return True, "Puzzle already solved."
    curr_states={el["id"]:el["state"] for el in puzzle.get("elements",[])}
    sol_seq=puzzle.get("solution_sequence",[])
    match=all(curr_states.get(sol_el["element_id"])==sol_el["target_state"] for sol_el in sol_seq)
    if match:
        puzzle["is_solved"]=True
        succ_msg=puzzle.get("success_message",f"{player.name} solved puzzle in {puzzle_room_data.get('name','room')}!")
        on_solve=puzzle_room_data.get("on_solve_effect")
        if on_solve and "world_variable_to_set" in on_solve:
            var,val=on_solve["world_variable_to_set"],on_solve.get("value",True)
            game_state.world_variables[var]=val; succ_msg+=f" ({var} set to {val})"
        notify_dm(f"{player.name} solved '{puzzle_room_data.get('name',puzzle_id)}' puzzle! {succ_msg}")
        return True, succ_msg
    return False, ""


if __name__ == '__main__':
    print("\n--- GameState Initialization and Interaction Demonstration ---")

    # 1. Load raw data using data_loader
    print("Loading all raw data from sources...")
    all_game_raw_data = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)
    # print(f"Raw data loaded: {json.dumps(all_game_raw_data, indent=2, ensure_ascii=False)}")


    # 2. Initialize Player
    hero_data = {
        "id": "hero001", "name": "TestHero", "max_hp": 50,
        "combat_stats": {'armor_class': 10, 'attack_bonus': 3, 'damage_bonus': 1, 'initiative_bonus': 2},
        "base_damage_dice": "1d4",
        "ability_scores": {"strength": 16, "dexterity": 14, "charisma": 12},
        "inventory": ["healing_potion_small"], # ID of an item expected to be loaded from file
        "equipment": {"weapon": "iron_sword", "currency": {"gold": 150}} # IDs
    }
    player = Player(player_data=hero_data)
    print(f"\nPlayer '{player.name}' initialized.")

    # 3. Initialize GameState and load data into it
    game = GameState(player_character=player)
    print("Initializing GameState with raw data...")
    game.initialize_from_raw_data(all_game_raw_data)

    print(f"\n--- GameState Load Summary ---")
    print(f"Items loaded: {len(game.items)}")
    print(f"Locations loaded: {len(game.locations)}")
    print(f"NPCs loaded: {len(game.npcs)}")
    print(f"Factions loaded: {len(game.factions)}")
    if game.factions:
        first_faction_id = list(game.factions.keys())[0]
        print(f"  Example Faction: {game.factions[first_faction_id].name}")
    print(f"GameObjects loaded: {len(game.game_objects)}")
    print(f"RAG document categories: {list(game.rag_documents.keys())}")
    for cat, docs in game.rag_documents.items():
        print(f"  - {cat}: {len(docs)} documents")
    if 'Factions_RAG' in game.rag_documents:
       print(f"  - Factions_RAG specific count: {len(game.rag_documents['Factions_RAG'])}")

    print(f"\nInitial Player Status: {game.get_status()}")
    print(f"Initial Equipment: {player.equipment}")

    # --- Test Item Interactions (using items loaded from files) ---
    print("\n--- Item Interaction Test (Loaded Data) ---")
    # Player starts with "iron_sword" equipped (defined in hero_data, loaded from iron_sword.json)
    weapon_stats = player.get_equipped_weapon_stats(game)
    print(f"Equipped weapon ('iron_sword') stats: {weapon_stats}")

    # Equip "chainmail_armor" (loaded from chainmail_armor.json)
    player.add_to_inventory("chainmail_armor") # Add its ID to inventory first
    print(f"Inventory before equipping chainmail: {player.inventory}")
    if player.equip_item("chainmail_armor", "armor", game):
        print(f"Equipped Chainmail Armor. Inventory: {player.inventory}")
        ac = player.get_effective_armor_class(game)
        print(f"AC after equipping chainmail: {ac}") # Base 10 + Chainmail's AC bonus (e.g., 4)
    else:
        print(f"Failed to equip Chainmail Armor. Check if 'chainmail_armor' was loaded into game.items: {'chainmail_armor' in game.items}")

    # Use "healing_potion_small" (loaded from healing_potion_small.json)
    player.current_hp = 20
    print(f"Player HP before potion: {player.current_hp}")
    if "healing_potion_small" not in player.inventory: # If it was consumed by initial status or other tests
        player.add_to_inventory("healing_potion_small")
    print(f"Inventory before using potion: {player.inventory}")
    use_success, use_msg = player.use_item("healing_potion_small", game)
    print(use_msg)
    if use_success: print(f"Player HP after potion: {player.current_hp}")

    # --- Test Buying/Selling (with a loaded NPC and loaded items) ---
    print("\n--- Buying/Selling Test (Loaded Data) ---")
    merchant_npc = game.npcs.get("npc_merchant_jane") # Loaded from npc_merchant_jane.json
    if merchant_npc:
        print(f"Trading with: {merchant_npc.name}")
        # Assume 'healing_potion_small' is in merchant's shop_inventory in the JSON
        # Player buys another 'healing_potion_small'
        print(f"Player gold before buying: {player.equipment.get('currency', {}).get('gold')}")
        buy_success, buy_msg = player_buys_item(player, merchant_npc, "healing_potion_small", game)
        print(buy_msg)
        if buy_success: print(f"Player gold after buying: {player.equipment.get('currency', {}).get('gold')}")
        print(f"Player inventory after buying: {player.inventory}")

        # Player sells "old_key" (if they have it and it's sellable, loaded from old_key.json)
        if "old_key" not in player.inventory: player.add_to_inventory("old_key")
        print(f"\nPlayer gold before selling 'old_key': {player.equipment.get('currency', {}).get('gold')}")
        sell_success, sell_msg = player_sells_item(player, merchant_npc, "old_key", game)
        print(sell_msg)
        if sell_success: print(f"Player gold after selling 'old_key': {player.equipment.get('currency', {}).get('gold')}")
    else:
        print("Merchant Jane (npc_merchant_jane) not found in game.npcs. Skipping trade tests.")

    # --- Test NPC Interaction (Attack) ---
    # Find a hostile NPC if any were loaded, or use a known one for testing.
    # For now, we'll just check if merchant is attackable.
    if merchant_npc and merchant_npc.is_alive():
        print(f"\n--- Combat Test (vs {merchant_npc.name}) ---")
        print(f"{player.name} (HP: {player.current_hp}) vs {merchant_npc.name} (HP: {merchant_npc.current_hp})")
        attack_msg_p = player.attack(merchant_npc, game)
        print(attack_msg_p)
        if merchant_npc.is_alive():
            attack_msg_n = merchant_npc.attack(player, game)
            print(attack_msg_n)

    # Test reveal_clue with a game object
    print("\n--- Reveal Clue Test ---")
    # Assume 'sunstone' game object exists from data/GameObjects/sunstone.json
    # and has a hidden_clue_details field.
    # Player needs 'investigation' skill for this example.
    player.skills_list.append("investigation")
    player.proficiencies_map.get("skills", []).append("investigation")
    player.ability_scores["intelligence"] = 16 # Good INT for investigation

    if "sunstone" in game.game_objects:
        clue_success, clue_msg = reveal_clue(player, "sunstone", game)
        print(f"Reveal clue from 'sunstone': {clue_success} - {clue_msg}")
        # Try again (should say already revealed)
        clue_success2, clue_msg2 = reveal_clue(player, "sunstone", game)
        print(f"Reveal clue again: {clue_success2} - {clue_msg2}")
    else:
        print("Game object 'sunstone' not found in game.game_objects. Skipping reveal_clue test.")


    print("\n--- End of GameState Demonstration ---")
