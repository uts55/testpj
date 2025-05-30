import json
import logging
import os
import random # Add this
from utils import SKILL_ABILITY_MAP, PROFICIENCY_BONUS # Add this
from quests import Quest, ALL_QUESTS # Add this

logger = logging.getLogger(__name__)

class Item:
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
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
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.items = {item_id: Item.from_dict(item_data) for item_id, item_data in data.get('items', {}).items()}
            
            # Player.from_dict now expects inventory to be list of item IDs
            self.players = {player_id: Player.from_dict(player_data) for player_id, player_data in data.get('players', {}).items()}

            self.npcs = {npc_id: NPC.from_dict(npc_data) for npc_id, npc_data in data.get('npcs', {}).items()}
            
            self.locations = {}
            for loc_id, loc_data in data.get('locations', {}).items():
                location = Location.from_dict(loc_data)
                self.locations[loc_id] = location

            self.world_variables = data.get('world_variables', {})
            self.turn_count = data.get('turn_count', 0)
            self.load_quests(ALL_QUESTS) # Added
            logger.info(f"Game loaded successfully from {filepath}")

        except FileNotFoundError:
            logger.info(f"Save file not found at {filepath}. Starting a new game or using default state.")
        except json.JSONDecodeError as e:
            logger.error(f"Could not decode JSON from {filepath}. Error: {e}")
        except Exception as e: 
            logger.error(f"An unexpected error occurred while loading the game from {filepath}. Error: {e}", exc_info=True)

    def initialize_new_game(self, main_player_id: str, default_player_name: str, start_location_id: str):
        logger.info(f"Initializing new game with player ID {main_player_id} at {start_location_id}.")

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
            inventory=[],
            skills=['basic_attack'],
            knowledge_fragments=[],
            current_location=start_location_id,
            # Default values for new Player attributes
            player_class="Adventurer", 
            level=1, 
            experience_points=0,
            ability_scores={"strength": 10, "dexterity": 10, "constitution": 10, "intelligence": 10, "wisdom": 10, "charisma": 10},
            combat_stats={"armor_class": 10, "initiative_bonus": 0, "speed": 30},
            hit_points={"current": 10, "maximum": 10, "temporary": 0},
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
        logger.info(f"Created player {default_player_name} ({main_player_id}).")

        # Create locations
        loc1_id = start_location_id
        loc2_id = "north_road"

        location1 = Location(id=loc1_id,
                             name="Village Square",
                             description="The center of a quiet village. Paths lead in several directions.",
                             exits={'north': loc2_id},
                             items=[],
                             npcs=[])
        
        location2 = Location(id=loc2_id,
                             name="North Road",
                             description="A dusty road leading out of the village, heading north.",
                             exits={'south': loc1_id},
                             items=[],
                             npcs=[])
        
        self.locations[loc1_id] = location1
        self.locations[loc2_id] = location2
        logger.info(f"Created locations: {loc1_id}, {loc2_id}.")

        # Create item
        item_id = "note_001"
        mysterious_note = Item(id=item_id,
                               name="Mysterious Note",
                               description="A crumpled piece of paper with faded writing.")
        self.items[item_id] = mysterious_note
        logger.info(f"Created item: {item_id} ({mysterious_note.name}).")

        # Place item in starting location
        self.locations[loc1_id].items.append(item_id)
        logger.info(f"Placed item {item_id} in location {loc1_id}.")

        # Create NPC
        npc_id = "npc_001"
        old_villager = NPC(id=npc_id,
                           name="Old Villager",
                           current_location=loc1_id,
                           description="A friendly-looking villager with wise eyes.",
                           lore_fragments=["Heard tales of a hidden cave nearby..."],
                           dialogue_responses={'greeting': "Welcome, traveler!", 'farewell': "Safe travels!"},
                           status="neutral",
                           hp=30)
        self.npcs[npc_id] = old_villager
        logger.info(f"Created NPC: {npc_id} ({old_villager.name}).")

        # Add NPC to starting location
        self.locations[loc1_id].npcs.append(npc_id)
        logger.info(f"Placed NPC {npc_id} in location {loc1_id}.")
        
        # Set turn count and world variables
        self.turn_count = 0
        self.world_variables = {'time_of_day': 'noon', 'weather': 'clear'}
        logger.info("Turn count set to 0. World variables initialized.")
        self.load_quests(ALL_QUESTS) # Added
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
