import json
import logging

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
    def __init__(self, id: str, name: str, stats: dict, inventory: list[str],  # Changed to list[str] for item IDs
                 skills: list, knowledge_fragments: list, current_location: str):
        self.id = id
        self.name = name
        self.stats = stats if stats is not None else {}
        self.inventory = inventory if inventory is not None else []  # List of item IDs
        self.skills = skills if skills is not None else []
        self.knowledge_fragments = knowledge_fragments if knowledge_fragments is not None else []
        self.current_location = current_location

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'stats': self.stats,
            'inventory': self.inventory,  # Store item IDs directly
            'skills': self.skills,
            'knowledge_fragments': self.knowledge_fragments,
            'current_location': self.current_location,
        }

    @classmethod
    def from_dict(cls, data: dict):
        # Inventory is now a list of strings (item IDs)
        inventory = data.get('inventory', [])
        return cls(
            id=data['id'],
            name=data['name'],
            stats=data.get('stats', {}),
            inventory=inventory,  # Expecting list of item IDs
            skills=data.get('skills', []),
            knowledge_fragments=data.get('knowledge_fragments', []),
            current_location=data['current_location']
        )

    def take_damage(self, amount: int):
        if 'hp' in self.stats:
            self.stats['hp'] -= amount
            logger.info(f"Player {self.name} ({self.id}) took {amount} damage. HP is now {self.stats['hp']}.")
        else:
            logger.warning(f"Player {self.name} ({self.id}) has no 'hp' stat to take damage.")

    def use_skill(self, skill_name: str):
        logger.info(f"Player {self.name} ({self.id}) used skill: {skill_name}.")
        # Placeholder for skill logic

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
        self.world_variables: dict = {}
        self.turn_count: int = 0

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
        player_stats = {'hp': 100, 'mp': 50, 'attack': 10}
        main_player = Player(id=main_player_id,
                             name=default_player_name,
                             stats=player_stats,
                             inventory=[],
                             skills=['basic_attack'],
                             knowledge_fragments=[],
                             current_location=start_location_id)
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
        
        logger.info("New game initialization complete.")


    def save_game(self, filepath: str):
        try:
            data = self.to_dict()
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Game saved successfully to {filepath}")
        except IOError as e:
            logger.error(f"Could not write save file to {filepath}. Error: {e}")
        except Exception as e: 
            logger.error(f"An unexpected error occurred while saving the game to {filepath}. Error: {e}", exc_info=True)
