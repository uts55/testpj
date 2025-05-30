import json
import logging
import os
import random # Add this
from utils import SKILL_ABILITY_MAP, PROFICIENCY_BONUS # Add this
from quests import Quest, ALL_QUESTS # Add this
import config # Added

logger = logging.getLogger(__name__)

class Item:
    def __init__(self, id: str, name: str, description: str, effects: dict = None):
        self.id = id
        self.name = name
        self.description = description
        self.effects = effects if effects is not None else {}

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'effects': self.effects,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            effects=data.get('effects', {}),
        )

class Player:
    def __init__(self, id: str, name: str, inventory: list[str],
                 skills: list, knowledge_fragments: list, current_location: str,
                 player_class: str = None, level: int = 1, experience_points: int = 0,
                 ability_scores: dict = None, combat_stats: dict = None, hit_points: dict = None,
                 spell_slots: dict = None, equipment: dict = None, status_effects: list = None,
                 proficiencies: dict = None, feats: list = None, background: str = None,
                 alignment: str = None, personality_traits: list = None, ideals: list = None,
                 bonds: list = None, flaws: list = None, notes: str = None,
                 active_quests: list = None, completed_quests: list = None,
                 quest_status: dict[str, str] = None, quest_progress: dict[str, dict] = None): # Modified
        self.id = id
        self.name = name
        self.inventory = inventory if inventory is not None else []  # List of item IDs
        self.skills = skills if skills is not None else []
        self.knowledge_fragments = knowledge_fragments if knowledge_fragments is not None else []
        self.current_location = current_location

        self.player_class = player_class
        self.level = level
        self.experience_points = experience_points
        
        self.ability_scores = ability_scores if ability_scores is not None else {}
        self.combat_stats = combat_stats if combat_stats is not None else {}
        self.hit_points = hit_points if hit_points is not None else {"current": 0, "maximum": 0, "temporary": 0}
        self.spell_slots = spell_slots if spell_slots is not None else {}
        
        default_currency = {"gold": 0, "silver": 0, "copper": 0}
        default_equipment = {
            "weapon": None, "armor": None, "shield": None, "helmet": None,
            "boots": None, "gloves": None, "amulet": None, "ring1": None, "ring2": None,
            "currency": default_currency
        }
        self.equipment = equipment if equipment is not None else default_equipment
        if 'currency' not in self.equipment or not isinstance(self.equipment['currency'], dict):
            self.equipment['currency'] = default_currency.copy()

        self.status_effects = status_effects if status_effects is not None else []
        self.proficiencies = proficiencies if proficiencies is not None else {}
        self.feats = feats if feats is not None else []
        self.background = background
        self.alignment = alignment
        self.personality_traits = personality_traits if personality_traits is not None else []
        self.ideals = ideals if ideals is not None else []
        self.bonds = bonds if bonds is not None else []
        self.flaws = flaws if flaws is not None else []
        self.notes = notes
        self.active_quests = active_quests if active_quests is not None else []
        self.completed_quests = completed_quests if completed_quests is not None else []
        self.quest_status = quest_status if quest_status is not None else {} # Added
        self.quest_progress = quest_progress if quest_progress is not None else {} # Added

    def to_dict(self) -> dict:
        serializable_quest_progress = {} # Added
        for q_id, prog_data_dict in self.quest_progress.items(): # Added
            serializable_quest_progress[q_id] = { # Added
                'objectives': list(prog_data_dict.get('objectives', [])), # Added
                'completed_objectives': list(prog_data_dict.get('completed_objectives', set())) # Added
            } # Added
        return {
            'id': self.id,
            'name': self.name,
            'inventory': self.inventory,
            'skills': self.skills,
            'knowledge_fragments': self.knowledge_fragments,
            'current_location': self.current_location,
            'player_class': self.player_class,
            'level': self.level,
            'experience_points': self.experience_points,
            'ability_scores': self.ability_scores,
            'combat_stats': self.combat_stats,
            'hit_points': self.hit_points,
            'spell_slots': self.spell_slots,
            'equipment': self.equipment,
            'status_effects': self.status_effects,
            'proficiencies': self.proficiencies,
            'feats': self.feats,
            'background': self.background,
            'alignment': self.alignment,
            'personality_traits': self.personality_traits,
            'ideals': self.ideals,
            'bonds': self.bonds,
            'flaws': self.flaws,
            'notes': self.notes,
            'active_quests': self.active_quests,
            'completed_quests': self.completed_quests,
            'quest_status': self.quest_status, # Added
            'quest_progress': serializable_quest_progress, # Added
        }

    @classmethod
    def from_dict(cls, data: dict):
        inventory = data.get('inventory', [])
        # Ensure default for nested currency if loading older data
        equipment_data = data.get('equipment', {})
        if 'currency' not in equipment_data or not isinstance(equipment_data.get('currency'), dict):
            equipment_data['currency'] = {"gold": 0, "silver": 0, "copper": 0}

        raw_quest_progress = data.get('quest_progress', {}) # Added
        final_quest_progress = {} # Added
        for qid, prog_data_dict in raw_quest_progress.items(): # Added
            final_quest_progress[qid] = { # Added
                'objectives': list(prog_data_dict.get('objectives', [])), # Added
                'completed_objectives': set(prog_data_dict.get('completed_objectives', [])) # Added
            } # Added

        return cls(
            id=data['id'],
            name=data['name'],
            inventory=inventory,
            skills=data.get('skills', []),
            knowledge_fragments=data.get('knowledge_fragments', []),
            current_location=data.get('current_location'), # Make robust for missing current_location
            player_class=data.get('player_class'),
            level=data.get('level', 1),
            experience_points=data.get('experience_points', 0),
            ability_scores=data.get('ability_scores', {}),
            combat_stats=data.get('combat_stats', {}),
            hit_points=data.get('hit_points', {"current": 0, "maximum": 0, "temporary": 0}),
            spell_slots=data.get('spell_slots', {}),
            equipment=equipment_data,
            status_effects=data.get('status_effects', []),
            proficiencies=data.get('proficiencies', {}),
            feats=data.get('feats', []),
            background=data.get('background'),
            alignment=data.get('alignment'),
            personality_traits=data.get('personality_traits', []),
            ideals=data.get('ideals', []),
            bonds=data.get('bonds', []),
            flaws=data.get('flaws', []),
            notes=data.get('notes'),
            active_quests=data.get('active_quests', []),
            completed_quests=data.get('completed_quests', []),
            quest_status=data.get('quest_status', {}), # Added
            quest_progress=final_quest_progress # Added
        )

    def take_damage(self, amount: int):
        if 'current' in self.hit_points:
            self.hit_points['current'] -= amount
            logger.info(f"Player {self.name} ({self.id}) took {amount} damage. HP is now {self.hit_points['current']}.")
        else:
            logger.warning(f"Player {self.name} ({self.id}) has no 'current' HP to take damage.")

    def use_skill(self, skill_name: str) -> dict:
        skill_name_lower = skill_name.lower() # Normalize for lookup
        logger.info(f"Player {self.name} ({self.id}) attempting skill: {skill_name_lower}.")

        if skill_name_lower not in SKILL_ABILITY_MAP:
            logger.warning(f"Skill '{skill_name_lower}' not found in SKILL_ABILITY_MAP for player {self.name}.")
            return {
                "skill": skill_name,
                "error": f"Skill '{skill_name_lower}' is not a recognized skill.",
                "total_roll": 0, # Or some other default
                "description": f"{self.name} attempted to use unknown skill: {skill_name}."
            }

        ability_key = SKILL_ABILITY_MAP[skill_name_lower]
        ability_score = self.ability_scores.get(ability_key)

        if ability_score is None:
            logger.warning(f"Ability score '{ability_key}' not found for player {self.name} when using skill '{skill_name_lower}'. Defaulting to 10.")
            ability_score = 10 # Default or handle as an error

        d20_roll = random.randint(1, 20)
        ability_modifier = (ability_score - 10) // 2

        is_proficient = skill_name_lower in [s.lower() for s in self.proficiencies.get('skills', [])]
        applied_proficiency_bonus = PROFICIENCY_BONUS if is_proficient else 0

        total_roll = d20_roll + ability_modifier + applied_proficiency_bonus

        log_message = (
            f"Skill Check: {skill_name.capitalize()}. Player: {self.name}. "
            f"D20: {d20_roll}, Ability: {ability_key.capitalize()} ({ability_score}, Mod: {ability_modifier}), "
            f"Proficient: {'Yes' if is_proficient else 'No'} (Bonus: {applied_proficiency_bonus}), Total: {total_roll}"
        )
        logger.info(log_message)

        return {
            "skill": skill_name,
            "d20_roll": d20_roll,
            "ability_key": ability_key,
            "ability_score": ability_score,
            "ability_modifier": ability_modifier,
            "is_proficient": is_proficient,
            "applied_proficiency_bonus": applied_proficiency_bonus,
            "total_roll": total_roll,
            "description": f"{self.name} attempts {skill_name}. Result: {total_roll} (d20={d20_roll}, {ability_key[:3].upper()} Mod={ability_modifier}, Prof Bonus={applied_proficiency_bonus})"
        }

    def add_item_to_inventory(self, item_id: str):
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            logger.info(f"Item {item_id} added to Player {self.name}'s ({self.id}) inventory.")
        else:
            logger.info(f"Item {item_id} already in Player {self.name}'s ({self.id}) inventory.")

    def change_location(self, new_location_id: str):
        old_location = self.current_location
        self.current_location = new_location_id
        logger.info(f"Player {self.name} ({self.id}) moved from {old_location} to {new_location_id}.")

    def update_ability_score(self, ability_name: str, new_score: int):
        if ability_name in self.ability_scores:
            self.ability_scores[ability_name] = new_score
            logger.info(f"Player {self.name} ({self.id}) ability score {ability_name} updated to {new_score}.")
            # Note: Recalculating modifiers or dependent stats (like spell save DC) would be done elsewhere or here if specified.
        else:
            logger.warning(f"Player {self.name} ({self.id}) does not have ability score {ability_name}.")

    def change_experience_points(self, points: int):
        self.experience_points += points
        logger.info(f"Player {self.name} ({self.id}) experience points changed by {points}. Total XP: {self.experience_points}.")
        # Note: Level up logic would typically be triggered here or by a separate call.

    def set_weapon(self, item_id: str | None):
        self.equipment['weapon'] = item_id
        logger.info(f"Player {self.name} ({self.id}) weapon set to {item_id}.")

    def set_armor(self, item_id: str | None):
        self.equipment['armor'] = item_id
        logger.info(f"Player {self.name} ({self.id}) armor set to {item_id}.")

    def set_shield(self, item_id: str | None):
        self.equipment['shield'] = item_id
        logger.info(f"Player {self.name} ({self.id}) shield set to {item_id}.")

    def update_currency(self, currency_type: str, amount_change: int):
        if currency_type in self.equipment.get('currency', {}):
            self.equipment['currency'][currency_type] += amount_change
            if self.equipment['currency'][currency_type] < 0:
                self.equipment['currency'][currency_type] = 0 # Prevent negative currency
            logger.info(f"Player {self.name} ({self.id}) currency {currency_type} changed by {amount_change}. New amount: {self.equipment['currency'][currency_type]}.")
        else:
            logger.warning(f"Player {self.name} ({self.id}) does not have currency type {currency_type}.")

    def acquire_item_from_location(self, item_id: str, location: 'Location', game_state: 'GameState') -> bool:
        """Allows the player to acquire an item from a location."""
        if item_id not in location.items:
            logger.warning(f"Item {item_id} not found at {location.name} ({location.id}) for player {self.name} ({self.id}).")
            return False

        # Check if item exists in the master list of items in game_state
        if item_id not in game_state.items:
            logger.error(f"Item {item_id} found in location {location.name} but not in master item list. Data inconsistency.")
            # Even if it's in location, if it's not a known item, it's problematic.
            # Depending on strictness, you might still allow acquiring it from location,
            # but it's better to log an error. For now, we'll prevent acquisition.
            return False

        location.items.remove(item_id)
        self.add_item_to_inventory(item_id) # This method already logs inventory addition
        logger.info(f"Player {self.name} ({self.id}) acquired item {item_id} from {location.name} ({location.id}).")
        return True

    def use_item(self, item_id: str, game_state: 'GameState') -> bool:
        """Allows the player to use an item from their inventory and apply its effects."""
        if item_id not in self.inventory:
            logger.warning(f"Player {self.name} ({self.id}) tried to use item {item_id} but does not possess it.")
            return False

        item = game_state.items.get(item_id)
        if not item:
            logger.error(f"Item {item_id} in inventory for player {self.name} ({self.id}) but not found in game_state.items. Data inconsistency.")
            return False

        effects = item.effects
        item_used_or_effect_attempted = False # Flag to track if any effect was processed or if item was just "used"

        if effects:
            effect_type = effects.get("type")
            if effect_type == "heal":
                if 'current' in self.hit_points and 'maximum' in self.hit_points:
                    amount = effects.get("amount", 0)
                    if amount > 0:
                        healed_amount = min(amount, self.hit_points['maximum'] - self.hit_points['current'])
                        if healed_amount > 0:
                            self.hit_points['current'] += healed_amount
                            logger.info(f"Player {self.name} ({self.id}) used {item.name}. Recovered {healed_amount} HP. Current HP: {self.hit_points['current']}/{self.hit_points['maximum']}.")
                        else:
                            logger.info(f"Player {self.name} ({self.id}) used {item.name}, but HP is already full.")
                        item_used_or_effect_attempted = True
                    else:
                        logger.warning(f"Player {self.name} ({self.id}) used {item.name}, but heal amount is zero or invalid.")
                        item_used_or_effect_attempted = True # Still counts as "used"
                else:
                    logger.warning(f"Player {self.name} ({self.id}) tried to use heal item {item.name}, but HP data is incomplete.")
            # Placeholder for other effect types
            elif effect_type == "some_other_effect_type":
                logger.info(f"Player {self.name} ({self.id}) used {item.name}. Effect type '{effect_type}' not yet implemented.")
                item_used_or_effect_attempted = True
            elif effect_type: # An effect type is specified but not handled
                logger.warning(f"Player {self.name} ({self.id}) used {item.name}, but effect type '{effect_type}' is unknown or not handled.")
                item_used_or_effect_attempted = True
            else: # No effect type specified in effects dict
                logger.info(f"Player {self.name} ({self.id}) used {item.name}, but it has no defined effect type.")
                item_used_or_effect_attempted = True # Counts as "used" even if no specific action
        else:
            logger.info(f"Player {self.name} ({self.id}) used {item.name}, but it has no effects defined.")
            item_used_or_effect_attempted = True # Counts as "used"

        # Assuming the item is consumable if it was used or an effect was attempted.
        # This could be made more granular with an item property like "consumable: true/false" in item.effects
        if item_used_or_effect_attempted:
            if item_id in self.inventory: # Double check, though it should be
                self.inventory.remove(item_id)
                logger.info(f"Item {item.name} ({item_id}) was consumed by player {self.name} ({self.id}).")
            return True

        # If no effects were processed and item wasn't "used" (e.g. item has effects but not of a known type and we decide not to consume)
        # This part of the logic might need refinement based on how unhandled effects should behave regarding consumption.
        # For now, if item_used_or_effect_attempted is False, it means no known effect was triggered.
        # Let's assume if an item is "used", even if its specific effect isn't implemented, it's consumed.
        # The current logic ensures item_used_or_effect_attempted is true if *any* effect dict exists or even if it's empty.

        return False # Should ideally be covered by item_used_or_effect_attempted logic


class NPC:
    def __init__(self, id: str, name: str, current_location: str, description: str, 
                 lore_fragments: list, dialogue_responses: dict, status: str, hp: int = None):
        self.id = id
        self.name = name
        self.current_location = current_location
        self.description = description
        self.lore_fragments = lore_fragments if lore_fragments is not None else []
        self.dialogue_responses = dialogue_responses if dialogue_responses is not None else {}
        self.status = status
        self.hp = hp

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'current_location': self.current_location,
            'description': self.description,
            'lore_fragments': self.lore_fragments,
            'dialogue_responses': self.dialogue_responses,
            'status': self.status,
            'hp': self.hp,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            name=data['name'],
            current_location=data['current_location'],
            description=data['description'],
            lore_fragments=data.get('lore_fragments', []),
            dialogue_responses=data.get('dialogue_responses', {}),
            status=data['status'],
            hp=data.get('hp')
        )

    def take_damage(self, amount: int):
        if self.hp is not None: # Check if NPC has HP attribute
            self.hp -= amount
            if self.hp < 0:
                self.hp = 0 # Prevent negative HP
            logger.info(f"NPC {self.name} ({self.id}) took {amount} damage. HP is now {self.hp}.")
            if self.hp == 0:
                logger.info(f"NPC {self.name} ({self.id}) has been defeated.")
                # Future: Add logic for handling NPC defeat (e.g., changing status, removing from game)
        else:
            logger.warning(f"NPC {self.name} ({self.id}) has no HP to take damage.")
    
    def change_status(self, new_status: str):
        old_status = self.status
        self.status = new_status
        logger.info(f"NPC {self.name} ({self.id}) status changed from {old_status} to {new_status}.")


class Location:
    def __init__(self, id: str, name: str, description: str, exits: dict, 
                 items: list[str], npcs: list[str]): # items is list[str] for item IDs
        self.id = id
        self.name = name
        self.description = description
        self.exits = exits if exits is not None else {}
        self.items = items if items is not None else [] # List of item IDs
        self.npcs = npcs if npcs is not None else [] # List of NPC IDs

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'exits': self.exits,
            'items': self.items, # Store item IDs directly
            'npcs': self.npcs, # Store NPC IDs
        }

    @classmethod
    def from_dict(cls, data: dict):
        # Items are now a list of strings (item IDs)
        items = data.get('items', [])
        npc_ids = data.get('npcs', [])
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            exits=data.get('exits', {}),
            items=items, # Expecting list of item IDs
            npcs=npc_ids 
        )

class GameState:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.npcs: dict[str, NPC] = {}
        self.locations: dict[str, Location] = {}
        self.items: dict[str, Item] = {} # Master list of all items
        self.quests: dict[str, Quest] = {} # Added
        self.world_variables: dict = {}
        self.turn_count: int = 0

    def load_quests(self, quests_data: dict[str, Quest]): # Added
        self.quests = quests_data # Added
        logger.info("Quests loaded into game state.") # Added

    def get_quest(self, quest_id: str) -> Quest | None: # Added
        return self.quests.get(quest_id) # Added

    def accept_quest(self, player_id: str, quest_id: str) -> bool: # Added
        player = self.get_player(player_id) # Added
        if not player: logger.error(f"Player {player_id} not found."); return False # Added
        quest = self.get_quest(quest_id) # Added
        if not quest: logger.error(f"Quest {quest_id} not found."); return False # Added
        if quest_id in player.active_quests or quest_id in player.completed_quests: logger.info(f"Quest {quest_id} already handled for player {player_id}."); return False # Added
        player.active_quests.append(quest_id) # Added
        player.quest_status[quest_id] = quest.status_descriptions.get('accepted', 'accepted') # Added
        player.quest_progress[quest_id] = {'objectives': list(quest.objectives), 'completed_objectives': set()} # Added
        logger.info(f"Player {player_id} accepted quest {quest_id}.") # Added
        return True # Added

    def advance_quest_objective(self, player_id: str, quest_id: str, objective_description: str) -> bool: # Added
        player = self.get_player(player_id) # Added
        if not player: logger.error(f"Player {player_id} not found."); return False # Added
        quest = self.get_quest(quest_id) # Added
        if not quest: logger.error(f"Quest {quest_id} not found."); return False # Added
        if quest_id not in player.active_quests: logger.warning(f"Quest {quest_id} not active for player {player_id}."); return False # Added
        if quest_id not in player.quest_progress: logger.error(f"Quest progress for {quest_id} not found for player {player_id}."); return False # Added
        progress_data = player.quest_progress[quest_id] # Added
        if objective_description in progress_data.get('objectives', []) and objective_description not in progress_data.get('completed_objectives', set()): # Added
            progress_data['completed_objectives'].add(objective_description) # Added
            logger.info(f"Player {player_id} advanced objective '{objective_description}' for quest {quest_id}.") # Added
            # Optional: Update player.quest_status[quest_id] based on objective completion if specific status exists in quest.status_descriptions # Added
            return True # Added
        else: logger.warning(f"Objective '{objective_description}' for quest {quest_id} not advanceable for player {player_id}."); return False # Added

    def complete_quest(self, player_id: str, quest_id: str) -> bool: # Added
        player = self.get_player(player_id) # Added
        if not player: logger.error(f"Player {player_id} not found."); return False # Added
        quest = self.get_quest(quest_id) # Added
        if not quest: logger.error(f"Quest {quest_id} not found."); return False # Added
        if quest_id not in player.active_quests: logger.warning(f"Quest {quest_id} not active for player {player_id} to complete."); return False # Added
        if quest_id not in player.quest_progress: logger.error(f"Quest progress for {quest_id} not found for player {player_id}."); return False # Added
        progress_data = player.quest_progress[quest_id] # Added
        if set(progress_data.get('objectives', [])) == progress_data.get('completed_objectives', set()): # Added
            player.active_quests.remove(quest_id) # Added
            player.completed_quests.append(quest_id) # Added
            player.quest_status[quest_id] = quest.status_descriptions.get('completed', 'completed') # Added
            xp_reward = quest.rewards.get('xp', 0) # Added
            if xp_reward > 0: player.change_experience_points(xp_reward) # Added
            for item_id in quest.rewards.get('items', []): player.add_item_to_inventory(item_id) # Added
            for currency_type, amount in quest.rewards.get('currency', {}).items(): player.update_currency(currency_type, amount) # Added
            logger.info(f"Player {player_id} completed quest {quest_id} and received rewards.") # Added
            return True # Added
        else: logger.info(f"Player {player_id} attempt to complete quest {quest_id} failed: objectives not met."); return False # Added

    def get_player(self, player_id: str) -> Player | None:
        return self.players.get(player_id)

    def get_npcs_in_location(self, location_id: str) -> list[NPC]:
        # This assumes Location.npcs stores NPC IDs.
        # And GameState.npcs stores the NPC objects.
        # This method was asked for in Part 1, but Location.npcs stores NPC IDs.
        # The prompt "Get NPCs in the player's current location using game_state.get_npcs_in_location(player.current_location). List their names."
        # implies this method should return NPC objects.
        
        # Let's assume Location.npcs contains IDs that need to be resolved.
        location = self.locations.get(location_id)
        if not location:
            logger.warning(f"Location {location_id} not found in get_npcs_in_location.")
            return []
        
        npcs_in_loc: list[NPC] = []
        # The Location object itself stores a list of NPC IDs in its `npcs` attribute.
        # We should iterate through these IDs and fetch the NPC objects from `self.npcs`.
        for npc_id in location.npcs: 
            npc = self.npcs.get(npc_id)
            if npc:
                # A more direct interpretation of "NPCs in location" would be to check npc.current_location
                # However, Location.npcs is designed to hold the list of NPCs *supposed* to be in that location.
                # For consistency with that design, we use location.npcs.
                # If an NPC's current_location differs, that's a state inconsistency to be managed elsewhere,
                # or this method could be stricter: if npc.current_location == location_id:
                npcs_in_loc.append(npc)
            else:
                logger.warning(f"NPC with ID {npc_id} listed in location {location_id} not found in master NPC list.")
        return npcs_in_loc

    def apply_event(self, event_data: dict):
        logger.info(f"Applying event: {event_data}")
        # Placeholder for more complex event logic

    def update_npc_location(self, npc_id: str, new_location_id: str):
        npc = self.npcs.get(npc_id)
        if npc:
            old_location = npc.current_location
            npc.current_location = new_location_id
            
            # Also update the old and new location's list of NPCs
            # Remove NPC from old location's list
            if old_location and old_location in self.locations:
                if npc_id in self.locations[old_location].npcs:
                    self.locations[old_location].npcs.remove(npc_id)
            
            # Add NPC to new location's list
            if new_location_id in self.locations:
                if npc_id not in self.locations[new_location_id].npcs:
                    self.locations[new_location_id].npcs.append(npc_id)
            else:
                logger.warning(f"Target location {new_location_id} for NPC {npc_id} not found.")

            logger.info(f"NPC {npc.name} ({npc_id}) location updated from {old_location} to {new_location_id}.")
        else:
            logger.warning(f"NPC {npc_id} not found, cannot update location.")


    def to_dict(self) -> dict:
        return {
            'players': {player_id: player.to_dict() for player_id, player in self.players.items()},
            'npcs': {npc_id: npc.to_dict() for npc_id, npc in self.npcs.items()},
            'locations': {loc_id: loc.to_dict() for loc_id, loc in self.locations.items()},
            'items': {item_id: item.to_dict() for item_id, item in self.items.items()},
            'world_variables': self.world_variables,
            'turn_count': self.turn_count,
        }

    def load_game(self, filepath: str):
        # Store a copy of the current state's critical attributes
        original_players = {pid: p.to_dict() for pid, p in self.players.items()}
        original_npcs = {nid: n.to_dict() for nid, n in self.npcs.items()}
        original_locations = {lid: l.to_dict() for lid, l in self.locations.items()}
        original_items = {iid: i.to_dict() for iid, i in self.items.items()}
        original_world_variables = self.world_variables.copy()
        original_turn_count = self.turn_count
        # Quests are typically static, but if they could be modified during gameplay and saved, include them too.
        # For now, assuming quests are reloaded from ALL_QUESTS consistently.

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Create temporary structures
            temp_items: dict[str, Item] = {}
            temp_npcs: dict[str, NPC] = {}
            temp_locations: dict[str, Location] = {}
            temp_players: dict[str, Player] = {}
            temp_world_variables: dict = {}
            temp_turn_count: int = 0

            # 1. Load items first into temporary structure
            temp_items = {item_id: Item.from_dict(item_data) for item_id, item_data in data.get('items', {}).items()}
            logger.debug(f"Attempting to load {len(temp_items)} items into temporary structure.")

            # 2. Load NPCs into temporary structure
            temp_npcs = {npc_id: NPC.from_dict(npc_data) for npc_id, npc_data in data.get('npcs', {}).items()}
            logger.debug(f"Attempting to load {len(temp_npcs)} NPCs into temporary structure.")

            # 3. Load locations into temporary structure
            temp_locations = {}
            for loc_id, loc_data in data.get('locations', {}).items():
                location = Location.from_dict(loc_data)
                temp_locations[loc_id] = location
            logger.debug(f"Attempting to load {len(temp_locations)} locations into temporary structure.")

            # Validate location items and NPCs within temporary structures
            for loc_id, location in temp_locations.items():
                # Validate items in location
                for item_id in location.items[:]:
                    if item_id not in temp_items:
                        logger.warning(f"Location {location.id} items list contains non-existent item {item_id}. Removing from temp load data.")
                        location.items.remove(item_id)
                # Validate NPCs in location
                for npc_id in location.npcs[:]:
                    if npc_id not in temp_npcs:
                        logger.warning(f"Location {location.id} NPCs list contains non-existent NPC {npc_id}. Removing from temp load data.")
                        location.npcs.remove(npc_id)

            # 4. Load players into temporary structure
            temp_players = {player_id: Player.from_dict(player_data) for player_id, player_data in data.get('players', {}).items()}
            logger.debug(f"Attempting to load {len(temp_players)} players into temporary structure.")

            # Validate player inventory within temporary structures
            for player_id, player in temp_players.items():
                for item_id in player.inventory[:]:
                    if item_id not in temp_items:
                        logger.warning(f"Player {player.id} inventory (in temp load data) contains non-existent item {item_id}. Removing.")
                        player.inventory.remove(item_id)
                # Validate player quest items if they are distinct and need checking against temp_items

            temp_world_variables = data.get('world_variables', {})
            temp_turn_count = data.get('turn_count', 0)

            # Validate and correct entity locations
            entities_to_check = list(temp_players.values()) + list(temp_npcs.values())
            default_location_id_to_use = "default_start_location" # From config.PRESET_SCENARIOS

            for entity in entities_to_check:
                entity_type = "Player" if isinstance(entity, Player) else "NPC"
                is_location_invalid = False

                if entity.current_location is None:
                    is_location_invalid = True
                    logger.warning(f"{entity_type} {entity.id} ({entity.name}) has a None current_location.")
                elif entity.current_location not in temp_locations:
                    is_location_invalid = True
                    logger.warning(f"{entity_type} {entity.id} ({entity.name}) current_location '{entity.current_location}' is invalid or does not exist in loaded locations.")

                if is_location_invalid:
                    chosen_fallback_location = None
                    # Try config.DEFAULT_START_LOCATION_ID (using the one from default scenario)
                    if default_location_id_to_use in temp_locations:
                        chosen_fallback_location = default_location_id_to_use
                        logger.info(f"Attempting to move {entity_type} {entity.id} to default start location '{chosen_fallback_location}'.")
                    # Else, try the first location from temp_locations
                    elif temp_locations:
                        first_available_location = next(iter(temp_locations))
                        chosen_fallback_location = first_available_location
                        logger.info(f"Default start location not available or invalid. Attempting to move {entity_type} {entity.id} to first available location '{chosen_fallback_location}'.")

                    if chosen_fallback_location:
                        entity.current_location = chosen_fallback_location
                        logger.info(f"{entity_type} {entity.id} ({entity.name}) has been moved to fallback location '{chosen_fallback_location}'.")
                    else:
                        logger.critical(f"{entity_type} {entity.id} ({entity.name}) has an invalid location ('{entity.current_location}'), and no valid fallback location could be determined (e.g., temp_locations is empty). Entity may be inaccessible.")

            # If all loading and validation steps are successful, assign to actual instance attributes
            self.items = temp_items
            self.npcs = temp_npcs
            self.locations = temp_locations
            self.players = temp_players
            self.world_variables = temp_world_variables
            self.turn_count = temp_turn_count

            # Load quests (typically static data, loaded after core game objects are confirmed)
            self.load_quests(ALL_QUESTS)

            logger.info(f"Game loaded successfully from {filepath}. Loaded: {len(self.items)} items, {len(self.npcs)} NPCs, {len(self.locations)} locations, {len(self.players)} players.")

        except FileNotFoundError:
            logger.info(f"Save file not found at {filepath}. Game state remains unchanged.")
            # No need to restore original state as it was never modified
        except json.JSONDecodeError as e:
            logger.error(f"Could not decode JSON from {filepath}. Error: {e}. Game state remains unchanged.")
            # No need to restore original state
        except Exception as e: 
            logger.error(f"An unexpected error occurred while loading and validating the game from {filepath}. Error: {e}. Attempting to restore pre-load game state.", exc_info=True)
            # Restore the original state
            self.players = {pid: Player.from_dict(p_data) for pid, p_data in original_players.items()}
            self.npcs = {nid: NPC.from_dict(n_data) for nid, n_data in original_npcs.items()}
            self.locations = {lid: Location.from_dict(l_data) for lid, l_data in original_locations.items()}
            self.items = {iid: Item.from_dict(i_data) for iid, i_data in original_items.items()}
            self.world_variables = original_world_variables
            self.turn_count = original_turn_count
            # Consider re-calling load_quests if it was part of the original state that needs restoring.
            # However, if ALL_QUESTS is static, it might not be necessary unless quests can be dynamically altered and saved.
            logger.info("Successfully restored game state to pre-load attempt.")


    def _ensure_location_exists(self, location_id: str, location_name: str = None, description: str = None):
        if location_id not in self.locations:
            self.locations[location_id] = Location(
                id=location_id,
                name=location_name or location_id.replace('_', ' ').title(),
                description=description or f"A location: {location_id.replace('_', ' ').title()}.",
                exits={},
                items=[],
                npcs=[]
            )
            logger.info(f"Created placeholder location: {location_id}")
            return True # Indicates location was created
        return False # Indicates location already existed

    def _ensure_item_exists(self, item_id: str, item_name: str = None, description: str = None):
        if item_id not in self.items:
            self.items[item_id] = Item(
                id=item_id,
                name=item_name or item_id.replace('_', ' ').title(),
                description=description or "A scenario starting item."
            )
            logger.info(f"Created placeholder item: {item_id}")
            return True # Indicates item was created
        return False # Indicates item already existed

    def initialize_new_game(self, main_player_id: str, default_player_name: str,
                            start_location_id: str, scenario_data: dict = None): # Modified signature

        effective_start_location_id = start_location_id
        player_initial_inventory = []
        player_hp_modifier = 0

        if scenario_data:
            logger.info(f"Initializing new game with scenario: {scenario_data.get('name', 'Unnamed Scenario')}")
            effective_start_location_id = scenario_data['start_location_id']

            # Ensure scenario start location exists
            self._ensure_location_exists(effective_start_location_id, scenario_data.get('name', effective_start_location_id)) # Use scenario name for location if available

            # Handle player_start_setup if present
            player_setup = scenario_data.get('player_start_setup', {})
            if 'items' in player_setup:
                for item_id in player_setup['items']:
                    self._ensure_item_exists(item_id) # Create placeholder if not existing
                    player_initial_inventory.append(item_id)
            if 'hp_modifier' in player_setup:
                player_hp_modifier = player_setup['hp_modifier']
        else:
            logger.info(f"Initializing new game with default settings for player ID {main_player_id} at {start_location_id}.")

        # Clear existing game data
        self.players.clear()
        self.npcs.clear()
        self.locations.clear()
        self.items.clear()
        self.world_variables.clear()
        
        # Create main player
        main_player = Player(
            id=main_player_id,
            name=default_player_name,
            inventory=player_initial_inventory, # Use potentially scenario-defined inventory
            skills=['basic_attack'],
            knowledge_fragments=[],
            current_location=effective_start_location_id, # Use scenario or default start location
            # Default values for new Player attributes
            player_class="Adventurer", 
            level=1, 
            experience_points=0,
            ability_scores={"strength": 10, "dexterity": 10, "constitution": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
            combat_stats={"armor_class": 10, "initiative_bonus": 0, "speed": 30},
            hit_points={"current": 10, "maximum": 10, "temporary": 0}, # HP modifier applied after this
            spell_slots={},
            equipment={
                "weapon": None, "armor": None, "shield": None, "helmet": None,
                "boots": None, "gloves": None, "amulet": None, "ring1": None, "ring2": None,
                "currency": {"gold": 10, "silver": 0, "copper": 0}
            },
            status_effects=[],
            proficiencies={"saving_throws": [], "skills": []},
            feats=[],
            background="Commoner",
            alignment="Neutral",
            personality_traits=[],
            ideals=[],
            bonds=[],
            flaws=[],
            notes="",
            active_quests=[],
            completed_quests=[],
            quest_status={}, # Added
            quest_progress={} # Added
        )
        self.players[main_player_id] = main_player

        # Apply HP modifier if any
        if player_hp_modifier != 0:
            main_player.hit_points['current'] += player_hp_modifier
            if main_player.hit_points['current'] < 1:
                main_player.hit_points['current'] = 1 # Ensure HP doesn't go below 1
            if main_player.hit_points['current'] > main_player.hit_points['maximum']: # Also ensure current HP does not exceed max due to modifier
                main_player.hit_points['current'] = main_player.hit_points['maximum']

        logger.info(f"Created player {default_player_name} ({main_player_id}) at {effective_start_location_id} with HP {main_player.hit_points['current']}.")

        # --- Default Content Creation (runs for both scenario and default game) ---
        # This section populates the world with some baseline content.
        # Scenarios can override or exist alongside this.
        
        # Default locations (ensure they don't overwrite scenario-specified locations if IDs clash)
        # The original start_location_id passed to the function is used for default setup.
        # If a scenario is used, effective_start_location_id will be different.
        default_loc1_id = start_location_id # This is the original parameter, used for default setup
        default_loc2_id = "north_road"

        # Only create default locations if they weren't already created by scenario logic (or ensure they are distinct)
        self._ensure_location_exists(default_loc1_id, "Village Square", "The center of a quiet village. Paths lead in several directions.")
        self._ensure_location_exists(default_loc2_id, "North Road", "A dusty road leading out of the village, heading north.")
        
        # Setup exits for default locations, being careful not to break scenario-defined exits if IDs overlap.
        # This is a bit tricky if scenario locations have same IDs as default.
        # A robust way is to only add exits if the location was newly created by _ensure_location_exists or if exits are empty.
        if default_loc1_id in self.locations and not self.locations[default_loc1_id].exits:
             self.locations[default_loc1_id].exits['north'] = default_loc2_id
        if default_loc2_id in self.locations and not self.locations[default_loc2_id].exits:
             self.locations[default_loc2_id].exits['south'] = default_loc1_id

        logger.info(f"Ensured default locations are present: {default_loc1_id}, {default_loc2_id}.")

        # Default item (ensure it doesn't overwrite scenario-specified items if IDs clash)
        default_item_id = "note_001"
        self._ensure_item_exists(default_item_id, "Mysterious Note", "A crumpled piece of paper with faded writing.")
        logger.info(f"Ensured default item is present: {default_item_id}.")

        # Place default item in its default location, if that location exists and item not already there
        if default_loc1_id in self.locations and default_item_id not in self.locations[default_loc1_id].items:
            self.locations[default_loc1_id].items.append(default_item_id)
            logger.info(f"Placed default item {default_item_id} in default location {default_loc1_id}.")

        # Add a sample healing item
        healing_potion_id = "item_healing_potion_minor"
        self._ensure_item_exists(
            healing_potion_id,
            item_name="Minor Healing Potion",
            description="A common potion that restores a small amount of health."
        )
        # Now, directly access the item from self.items and set its effects
        if healing_potion_id in self.items:
            self.items[healing_potion_id].effects = {"type": "heal", "amount": 10}

        # Place this healing potion in a starting location.
        if default_loc1_id in self.locations and healing_potion_id not in self.locations[default_loc1_id].items:
            self.locations[default_loc1_id].items.append(healing_potion_id)
            logger.info(f"Placed healing potion {healing_potion_id} in {default_loc1_id}.")

        # Default NPC (ensure it doesn't overwrite scenario-specified NPCs if IDs clash)
        default_npc_id = "npc_001"
        if default_npc_id not in self.npcs: # Only create if not existing (e.g. from a scenario)
            old_villager = NPC(id=default_npc_id,
                               name="Old Villager",
                               current_location=default_loc1_id, # Default NPC in default start location
                               description="A friendly-looking villager with wise eyes.",
                               lore_fragments=["Heard tales of a hidden cave nearby..."],
                               dialogue_responses={'greeting': "Welcome, traveler!", 'farewell': "Safe travels!"},
                               status="neutral",
                               hp=30)
            self.npcs[default_npc_id] = old_villager
            logger.info(f"Created default NPC: {default_npc_id} ({old_villager.name}).")

            # Add default NPC to its default location, if that location exists and NPC not already there
            if default_loc1_id in self.locations and default_npc_id not in self.locations[default_loc1_id].npcs:
                self.locations[default_loc1_id].npcs.append(default_npc_id)
                logger.info(f"Placed default NPC {default_npc_id} in default location {default_loc1_id}.")

        # Create "Bob the Bartender" NPC
        bob_bartender_id = "npc_bartender_001"
        if bob_bartender_id not in self.npcs: # Only create if not existing
            bob_dialogue = {
                "greetings": [
                    "Welcome to the Prancing Pony! What can I get for ya?",
                    "Well met, traveler! Pull up a stool.",
                    "Need a drink or perhaps some local news?"
                ],
                "local_rumors": [
                    "I've heard whispers of strange lights up on Weathertop hill...",
                    "Some say old Farmer Giles found a peculiar ring in his fields."
                ]
            }
            bob_bartender = NPC(
                id=bob_bartender_id,
                name="Bob the Bartender",
                current_location=default_loc1_id, # Place Bob in the default start location
                description="A jolly-looking bartender with a friendly smile, always ready to chat or offer a drink.",
                lore_fragments=[
                    "Bob has worked at the Prancing Pony Inn for twenty years.",
                    "He claims to make the best ale in the region."
                ],
                dialogue_responses=bob_dialogue,
                status="neutral",
                hp=50
            )
            self.npcs[bob_bartender.id] = bob_bartender
            logger.info(f"Created default NPC: {bob_bartender.id} ({bob_bartender.name}).")

            # Add Bob to the default start location's NPC list
            if default_loc1_id in self.locations:
                if bob_bartender.id not in self.locations[default_loc1_id].npcs:
                    self.locations[default_loc1_id].npcs.append(bob_bartender.id)
                    logger.info(f"Placed default NPC {bob_bartender.id} in default location {default_loc1_id}.")
            else:
                logger.warning(f"Default start location {default_loc1_id} not found when trying to place {bob_bartender.id}.")

        # Set turn count and world variables
        self.turn_count = 0
        self.world_variables = {'time_of_day': 'noon', 'weather': 'clear'} # These can be generic
        logger.info("Turn count set to 0. World variables initialized.")
        self.load_quests(ALL_QUESTS)
        logger.info("New game initialization complete.")

    def save_game(self, filepath: str):
        try:
            data = self.to_dict()
            save_dir = os.path.dirname(filepath)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Game saved successfully to {filepath}")
        except IOError as e:
            logger.error(f"Could not write save file to {filepath}. Error: {e}")
        except Exception as e: 
            logger.error(f"An unexpected error occurred while saving the game to {filepath}. Error: {e}", exc_info=True)
