import unittest
import os
import json
import tempfile
import logging
import copy # Added for deepcopy
from unittest.mock import patch, mock_open
from game_state import GameState, Player, Item, NPC, Location, ALL_QUESTS, Quest # Added Quest for ALL_QUESTS typing
import config as game_config # To access any config constants if needed, though game_state.py uses a hardcoded default loc

# Configure logging to be quiet during tests by default
# You can increase level to INFO or DEBUG for specific test debugging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger('game_state') # Get the specific logger used in game_state.py

class TestItemInteractions(unittest.TestCase):

    def setUp(self):
        """Set up a fresh GameState and entities for each test."""
        self.game_state = GameState()
        # It's easier to initialize a minimal game state for tests
        # than relying on initialize_new_game, to have more control.

        # Create a test player
        self.player_id = "test_player"
        self.player = Player(id=self.player_id, name="Test Player", inventory=[], skills=[], knowledge_fragments=[], current_location="test_room", hit_points={"current": 10, "maximum": 20})
        self.game_state.players[self.player_id] = self.player

        # Create a test location
        self.location_id = "test_room"
        self.location = Location(id=self.location_id, name="Test Room", description="A room for testing.", exits={}, items=[], npcs=[])
        self.game_state.locations[self.location_id] = self.location

        # Create a test healing item and add to game_state.items
        self.heal_item_id = "potion_heal_test"
        self.heal_item = Item(id=self.heal_item_id, name="Test Healing Potion", description="Heals HP.", effects={"type": "heal", "amount": 5})
        self.game_state.items[self.heal_item_id] = self.heal_item

        # Create a non-healing item
        self.generic_item_id = "generic_item_test"
        self.generic_item = Item(id=self.generic_item_id, name="Test Generic Item", description="A generic item.", effects={})
        self.game_state.items[self.generic_item_id] = self.generic_item


    def test_acquire_item_successfully(self):
        """Test player acquiring an item from a location."""
        # Place item in location
        self.location.items.append(self.heal_item_id)

        acquired = self.player.acquire_item_from_location(self.heal_item_id, self.location, self.game_state)

        self.assertTrue(acquired)
        self.assertIn(self.heal_item_id, self.player.inventory)
        self.assertNotIn(self.heal_item_id, self.location.items)

    def test_acquire_item_not_in_location(self):
        """Test acquiring an item that is not in the location."""
        non_existent_item_id = "non_existent_potion"
        acquired = self.player.acquire_item_from_location(non_existent_item_id, self.location, self.game_state)

        self.assertFalse(acquired)
        self.assertNotIn(non_existent_item_id, self.player.inventory)

    def test_use_healing_item_successfully(self):
        """Test using a healing item and HP changes."""
        self.player.inventory.append(self.heal_item_id)
        self.player.hit_points["current"] = 5 # Player needs healing

        used = self.player.use_item(self.heal_item_id, self.game_state)

        self.assertTrue(used)
        self.assertEqual(self.player.hit_points["current"], 10) # 5 (initial) + 5 (heal_item amount)
        self.assertNotIn(self.heal_item_id, self.player.inventory) # Item consumed

    def test_use_healing_item_at_full_hp(self):
        """Test using a healing item when HP is full."""
        self.player.inventory.append(self.heal_item_id)
        self.player.hit_points["current"] = self.player.hit_points["maximum"] # Player is at full HP

        used = self.player.use_item(self.heal_item_id, self.game_state)

        self.assertTrue(used)
        self.assertEqual(self.player.hit_points["current"], self.player.hit_points["maximum"]) # HP remains at max
        self.assertNotIn(self.heal_item_id, self.player.inventory)

    def test_use_healing_item_overheal(self):
        """Test healing item does not heal beyond max HP."""
        self.player.inventory.append(self.heal_item_id)
        self.player.hit_points["current"] = 18 # Max HP is 20, heal is 5

        used = self.player.use_item(self.heal_item_id, self.game_state)

        self.assertTrue(used)
        self.assertEqual(self.player.hit_points["current"], 20) # Healed up to max
        self.assertNotIn(self.heal_item_id, self.player.inventory)

    def test_use_item_not_in_inventory(self):
        """Test using an item the player does not have."""
        used = self.player.use_item(self.heal_item_id, self.game_state) # Player doesn't have it

        self.assertFalse(used)

    def test_use_item_not_in_game_state_master_list(self):
        """Test using an item in inventory but not in game_state.items (data inconsistency)."""
        rogue_item_id = "rogue_potion"
        self.player.inventory.append(rogue_item_id) # Item in inventory
        # ... but rogue_item_id is NOT added to self.game_state.items

        used = self.player.use_item(rogue_item_id, self.game_state)

        self.assertFalse(used) # Should fail as item definition is missing
        self.assertIn(rogue_item_id, self.player.inventory) # Item should remain as it wasn't 'defined' to be used

    def test_use_non_healing_item(self):
        """Test using an item with no defined 'heal' effect (should still be consumed)."""
        self.player.inventory.append(self.generic_item_id)
        initial_hp = self.player.hit_points["current"]

        used = self.player.use_item(self.generic_item_id, self.game_state)

        self.assertTrue(used) # Item is "used" even if no specific effect is implemented yet
        self.assertEqual(self.player.hit_points["current"], initial_hp) # HP unchanged
        self.assertNotIn(self.generic_item_id, self.player.inventory) # Consumed


class TestGameStateSaveLoad(unittest.TestCase):

    def setUp(self):
        self.game_state = GameState()
        self.player1_id = "player1"
        self.item1_id = "item1"
        self.npc1_id = "npc1"
        self.loc1_id = "loc1"

        # Make sure ALL_QUESTS is populated for loading
        if not ALL_QUESTS:
            ALL_QUESTS["quest1"] = type("MockQuest", (), {"id": "quest1", "name": "Test Quest", "description": "A test quest.", "objectives": [], "rewards": {}, "status_descriptions": {}})()


    def tearDown(self):
        # Clean up temporary files if any were created and not explicitly closed by name
        pass

    def _create_basic_gamestate(self) -> GameState:
        gs = GameState()
        item1 = Item(id=self.item1_id, name="Sword of Testing", description="A pointy sword.")
        gs.items[self.item1_id] = item1

        loc1 = Location(id=self.loc1_id, name="Test Room", description="A room for tests.", exits={}, items=[self.item1_id], npcs=[self.npc1_id])
        gs.locations[self.loc1_id] = loc1

        player1 = Player(id=self.player1_id, name="Tester", inventory=[self.item1_id], skills=[], knowledge_fragments=[], current_location=self.loc1_id)
        gs.players[self.player1_id] = player1

        npc1 = NPC(id=self.npc1_id, name="Test NPC", current_location=self.loc1_id, description="An NPC for testing.", lore_fragments=[], dialogue_responses={}, status="neutral")
        gs.npcs[self.npc1_id] = npc1
        gs.load_quests(ALL_QUESTS) # Ensure quests are loaded
        return gs

    def test_save_load_basic_integrity(self):
        gs_original = self._create_basic_gamestate()

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name

        try:
            gs_original.save_game(save_filepath)

            gs_loaded = GameState()
            gs_loaded.load_game(save_filepath)

            self.assertEqual(len(gs_original.players), len(gs_loaded.players))
            self.assertEqual(len(gs_original.items), len(gs_loaded.items))
            self.assertEqual(len(gs_original.locations), len(gs_loaded.locations))
            self.assertEqual(len(gs_original.npcs), len(gs_loaded.npcs))

            loaded_player = gs_loaded.players[self.player1_id]
            original_player = gs_original.players[self.player1_id]
            self.assertEqual(loaded_player.name, original_player.name)
            self.assertEqual(loaded_player.inventory, original_player.inventory)
            self.assertEqual(loaded_player.current_location, original_player.current_location)

            loaded_location = gs_loaded.locations[self.loc1_id]
            original_location = gs_original.locations[self.loc1_id]
            self.assertEqual(loaded_location.name, original_location.name)
            self.assertEqual(loaded_location.items, original_location.items)
            self.assertEqual(loaded_location.npcs, original_location.npcs)

            loaded_npc = gs_loaded.npcs[self.npc1_id]
            original_npc = gs_original.npcs[self.npc1_id]
            self.assertEqual(loaded_npc.name, original_npc.name)
            self.assertEqual(loaded_npc.current_location, original_npc.current_location)

            # Check quests (assuming ALL_QUESTS is simple and serializable for this test)
            self.assertTrue(hasattr(gs_loaded, 'quests'))
            self.assertEqual(len(gs_loaded.quests), len(ALL_QUESTS))
            # Ensure quest objects are also loaded correctly if they have more complex structure
            if ALL_QUESTS and gs_loaded.quests:
                 self.assertIsInstance(list(gs_loaded.quests.values())[0], Quest)


        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_with_dangling_item_in_player_inventory(self, mock_logger):
        game_data = {
            "items": {}, # No items defined
            "players": {
                self.player1_id: {
                    "id": self.player1_id, "name": "Tester", "inventory": ["non_existent_item"],
                    "skills": [], "knowledge_fragments": [], "current_location": self.loc1_id,
                    # Add other required fields for Player.from_dict
                    "player_class": "Fighter", "level": 1, "experience_points": 0,
                    "ability_scores": {}, "combat_stats": {},
                    "hit_points": {"current": 10, "maximum": 10, "temporary": 0},
                    "spell_slots": {}, "equipment": {"currency": {"gold":0}}, "status_effects": [],
                    "proficiencies": {}, "feats": [], "background": "", "alignment": "",
                    "personality_traits": [], "ideals": [], "bonds": [], "flaws": [], "notes": ""
                }
            },
            "locations": { # Need a valid location for the player
                 self.loc1_id: {"id": self.loc1_id, "name": "Valid Room", "description": "", "exits": {}, "items": [], "npcs": []}
            },
            "npcs": {}
        }
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            json.dump(game_data, tmp_file)

        try:
            gs_loaded = GameState()
            gs_loaded.load_game(save_filepath)
            loaded_player = gs_loaded.players[self.player1_id]
            self.assertEqual(loaded_player.inventory, [])
            mock_logger.warning.assert_any_call(f"Player {self.player1_id} inventory contains non-existent item non_existent_item. Removing.")
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_with_dangling_references_in_location(self, mock_logger):
        game_data = {
            "items": {},
            "npcs": {},
            "locations": {
                self.loc1_id: {
                    "id": self.loc1_id, "name": "Haunted Room", "description": "boo",
                    "exits": {}, "items": ["ghost_item"], "npcs": ["ghost_npc"]
                }
            },
            "players": {}
        }
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            json.dump(game_data, tmp_file)

        try:
            gs_loaded = GameState()
            gs_loaded.load_game(save_filepath)
            loaded_location = gs_loaded.locations[self.loc1_id]
            self.assertEqual(loaded_location.items, [])
            self.assertEqual(loaded_location.npcs, [])
            mock_logger.warning.assert_any_call(f"Location {self.loc1_id} items list contains non-existent item ghost_item. Removing.")
            mock_logger.warning.assert_any_call(f"Location {self.loc1_id} NPCs list contains non-existent NPC ghost_npc. Removing.")
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_with_invalid_entity_current_location(self, mock_logger):
        invalid_loc_id = "invalid_loc"
        game_data = {
            "items": {},
            "npcs": {
                self.npc1_id: {
                    "id": self.npc1_id, "name": "Lost NPC", "current_location": invalid_loc_id,
                    "description": "", "lore_fragments": [], "dialogue_responses": {}, "status": "neutral"
                }
            },
            "locations": {
                 self.loc1_id: {"id": self.loc1_id, "name": "Valid Room", "description": "", "exits": {}, "items": [], "npcs": []}
            }, # No invalid_loc_id defined
            "players": {
                self.player1_id: {
                    "id": self.player1_id, "name": "Lost Player", "inventory": [],
                    "skills": [], "knowledge_fragments": [], "current_location": invalid_loc_id,
                    "player_class": "Fighter", "level": 1, "experience_points": 0,
                    "ability_scores": {}, "combat_stats": {},
                    "hit_points": {"current": 10, "maximum": 10, "temporary": 0},
                    "spell_slots": {}, "equipment": {"currency": {"gold":0}}, "status_effects": [],
                    "proficiencies": {}, "feats": [], "background": "", "alignment": "",
                    "personality_traits": [], "ideals": [], "bonds": [], "flaws": [], "notes": ""
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            json.dump(game_data, tmp_file)

        try:
            gs_loaded = GameState()
            gs_loaded.load_game(save_filepath)
            mock_logger.warning.assert_any_call(f"Player {self.player1_id} current location {invalid_loc_id} is invalid or does not exist. Player may be stranded.")
            mock_logger.warning.assert_any_call(f"NPC {self.npc1_id} current location {invalid_loc_id} is invalid or does not exist. NPC may be inaccessible.")
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    def test_load_older_save_format_with_missing_optional_field(self):
        # Player.from_dict defaults 'feats' to [] if missing
        player_data_missing_feats = {
            "id": self.player1_id, "name": "Tester Missing Feats", "inventory": [],
            "skills": [], "knowledge_fragments": [], "current_location": self.loc1_id,
            "player_class": "Fighter", "level": 1, "experience_points": 0,
            "ability_scores": {}, "combat_stats": {},
            "hit_points": {"current": 10, "maximum": 10, "temporary": 0},
            "spell_slots": {}, "equipment": {"currency": {"gold":0}}, "status_effects": [],
            "proficiencies": {}, # "feats" is missing
            "background": "", "alignment": "", "personality_traits": [], "ideals": [],
            "bonds": [], "flaws": [], "notes": ""
        }
        game_data = {
            "items": {}, "npcs": {},
            "locations": {
                 self.loc1_id: {"id": self.loc1_id, "name": "Valid Room", "description": "", "exits": {}, "items": [], "npcs": []}
            },
            "players": {self.player1_id: player_data_missing_feats}
        }

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            json.dump(game_data, tmp_file)

        try:
            gs_loaded = GameState()
            gs_loaded.load_game(save_filepath)
            loaded_player = gs_loaded.players[self.player1_id]
            self.assertEqual(loaded_player.feats, []) # Check for default value
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_corrupted_json_file(self, mock_logger):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            tmp_file.write("This is not valid JSON {")

        try:
            gs = GameState()
            # Store initial state of players (empty)
            initial_players_state = gs.players.copy()
            gs.load_game(save_filepath)
            # Check that players state hasn't changed due to partial load
            self.assertEqual(gs.players, initial_players_state)
            mock_logger.error.assert_called_once()
            # Check that the error message contains specific substrings
            args, _ = mock_logger.error.call_args
            self.assertIn("Could not decode JSON", args[0])
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_empty_json_file(self, mock_logger):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
            # File is empty

        try:
            gs = GameState()
            gs.load_game(save_filepath)
            # Depending on json.load behavior with empty file, it might be JSONDecodeError or custom
            # For an empty file, json.load('') raises JSONDecodeError: Expecting value
            mock_logger.error.assert_called_once()
            args, _ = mock_logger.error.call_args
            self.assertIn("Could not decode JSON", args[0]) # Or specific error for empty content
        finally:
            if os.path.exists(save_filepath):
                os.remove(save_filepath)

    @patch('game_state.logger')
    def test_load_file_not_found(self, mock_logger):
        gs = GameState()
        # Test the case where the load_game method itself is expected to handle the FileNotFoundError
        # and log an info message, without raising an unhandled exception.
        # The current implementation in game_state.py catches FileNotFoundError and logs.
        initial_state_dict = gs.to_dict()
        gs.load_game("non_existent_save_file.json")
        final_state_dict = gs.to_dict()

        # Assert that game state remains unchanged.
        self.assertEqual(initial_state_dict, final_state_dict, "Game state should not change if file not found.")

        mock_logger.info.assert_called_once_with("Save file not found at non_existent_save_file.json. Game state remains unchanged.")
        mock_logger.error.assert_not_called() # Ensure no error was logged for this expected case.

    @patch('game_state.logger')
    def test_load_game_atomic_operation_on_failure(self, mock_logger):
        gs_initial = self._create_basic_gamestate()
        # Add a specific player for this test to ensure it's part of the copy
        gs_initial.players["atomic_test_player"] = Player.from_dict({
            "id": "atomic_test_player", "name": "Atomic", "inventory": [], "skills": [],
            "knowledge_fragments": [], "current_location": self.loc1_id, "player_class": "TestClass",
            "level": 1, "experience_points": 0, "ability_scores": {}, "combat_stats": {},
            "hit_points": {"current": 10, "maximum": 10, "temporary": 0},
            "spell_slots": {}, "equipment": {"currency": {"gold": 0}}, "status_effects": [],
            "proficiencies": {}, "feats": [], "background": "", "alignment": "",
            "personality_traits": [], "ideals": [], "bonds": [], "flaws": [], "notes": ""
        })

        initial_players_copy = copy.deepcopy(gs_initial.players)
        initial_items_copy = copy.deepcopy(gs_initial.items)
        initial_locations_copy = copy.deepcopy(gs_initial.locations)
        initial_npcs_copy = copy.deepcopy(gs_initial.npcs)
        initial_world_vars_copy = copy.deepcopy(gs_initial.world_variables)
        initial_turn_count_copy = gs_initial.turn_count

        # Prepare a save file that is valid JSON but will cause Player.from_dict to fail
        # The content of the save file itself needs to be valid enough to pass json.load
        # and initial item/location/npc loading if Player.from_dict is the failure point.
        save_data_for_failure = gs_initial.to_dict() # Use a valid current state as base
        # Modify something minor that Player.from_dict might process, or rely on the patch.
        # For this test, the patch is the primary failure mechanism.

        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            json.dump(save_data_for_failure, tmp_file)
            corrupted_save_filepath = tmp_file.name

        self.addCleanup(os.remove, corrupted_save_filepath)

        # Patch Player.from_dict to raise an error during the loading of players
        with patch('game_state.Player.from_dict', side_effect=ValueError("Simulated player load error")):
            gs_initial.load_game(corrupted_save_filepath)

        # Verify that the game state attributes are still deeply equal to their original states
        self.assertEqual(gs_initial.players, initial_players_copy)
        self.assertEqual(gs_initial.items, initial_items_copy)
        self.assertEqual(gs_initial.locations, initial_locations_copy)
        self.assertEqual(gs_initial.npcs, initial_npcs_copy)
        self.assertEqual(gs_initial.world_variables, initial_world_vars_copy)
        self.assertEqual(gs_initial.turn_count, initial_turn_count_copy)

        # Ensure logger.error (for the exception) and logger.info (for rollback) were called
        mock_logger.error.assert_called()
        # Check that the error message contains specific substrings from the exception
        error_args, _ = mock_logger.error.call_args
        self.assertIn("An unexpected error occurred while loading and validating the game", error_args[0])
        self.assertIn("Simulated player load error", error_args[0])

        mock_logger.info.assert_any_call("Successfully restored game state to pre-load attempt.")


    @patch('game_state.logger')
    def test_load_entities_with_invalid_location_moved_to_default(self, mock_logger):
        # game_state.py uses "default_start_location" hardcoded as a fallback.
        # config.py also has PRESET_SCENARIOS with "default_start_location".
        # We will use this known ID.
        default_loc_id = "default_start_location"
        other_valid_loc_id = "other_valid_loc"

        player_invalid_loc_id = "player_invalid_loc"
        npc_invalid_loc_id = "npc_invalid_loc"

        save_data = {
            "locations": {
                default_loc_id: {"id": default_loc_id, "name": "Default Start", "description": "", "exits": {}, "items": [], "npcs": []},
                other_valid_loc_id: {"id": other_valid_loc_id, "name": "Other Room", "description": "", "exits": {}, "items": [], "npcs": []}
            },
            "players": {
                "p1": Player(id="p1", name="Player LostInSpace", inventory=[], skills=[], knowledge_fragments=[], current_location=player_invalid_loc_id).to_dict()
            },
            "npcs": {
                "n1": NPC(id="n1", name="NPC Adrift", current_location=npc_invalid_loc_id, description="", lore_fragments=[], dialogue_responses={}, status="neutral").to_dict()
            },
            "items": {},
            "world_variables": {},
            "turn_count": 0
        }
        # Ensure player dict has all required fields for from_dict
        save_data["players"]["p1"].update({
            "player_class": "Warrior", "level": 1, "experience_points": 0,
            "ability_scores": {}, "combat_stats": {}, "hit_points": {"current":10, "maximum":10, "temporary":0},
            "spell_slots": {}, "equipment": {"currency":{}}, "status_effects": [], "proficiencies": {}, "feats": [],
            "background": "", "alignment": "", "personality_traits": [], "ideals": [], "bonds": [], "flaws": [], "notes": ""
        })


        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            json.dump(save_data, tmp_file)
            save_filepath = tmp_file.name
        self.addCleanup(os.remove, save_filepath)

        gs = GameState()
        gs.load_game(save_filepath)

        loaded_player = gs.players["p1"]
        loaded_npc = gs.npcs["n1"]

        self.assertEqual(loaded_player.current_location, default_loc_id)
        self.assertEqual(loaded_npc.current_location, default_loc_id)

        mock_logger.warning.assert_any_call(f"Player p1 ({loaded_player.name}) current_location '{player_invalid_loc_id}' is invalid or does not exist in loaded locations.")
        mock_logger.info.assert_any_call(f"Attempting to move Player p1 to default start location '{default_loc_id}'.")
        mock_logger.info.assert_any_call(f"Player p1 ({loaded_player.name}) has been moved to fallback location '{default_loc_id}'.")

        mock_logger.warning.assert_any_call(f"NPC n1 ({loaded_npc.name}) current_location '{npc_invalid_loc_id}' is invalid or does not exist in loaded locations.")
        mock_logger.info.assert_any_call(f"Attempting to move NPC n1 to default start location '{default_loc_id}'.")
        mock_logger.info.assert_any_call(f"NPC n1 ({loaded_npc.name}) has been moved to fallback location '{default_loc_id}'.")

    def test_save_load_complex_state_deep_comparison(self):
        gs_original = GameState()
        gs_original.load_quests(ALL_QUESTS) # Load static quests

        # Populate with complex data
        gs_original.items = {
            "item_sword": Item(id="item_sword", name="DragonSlayer", description="Kills dragons.", effects={"damage_bonus": 5}),
            "item_potion": Item(id="item_potion", name="Mega Potion", description="Heals a lot.", effects={"type": "heal", "amount": 50})
        }
        gs_original.locations = {
            "loc_castle": Location(id="loc_castle", name="Dragon's Castle", description="A scary place.", exits={"south": "loc_village"}, items=["item_sword"], npcs=["npc_dragon"]),
            "loc_village": Location(id="loc_village", name="Quiet Village", description="A peaceful place.", exits={"north": "loc_castle"}, items=["item_potion"], npcs=[])
        }
        gs_original.npcs = {
            "npc_dragon": NPC(id="npc_dragon", name="Smaug", current_location="loc_castle", description="A big red dragon.", lore_fragments=["Rich!"], dialogue_responses={"threaten": "ROAR!"}, status="hostile", hp=100)
        }

        player_data = {
            'id': "player_hero", 'name': "Hero", 'inventory': ["item_potion"],
            'skills': ["swordsmanship", "lockpicking"], 'knowledge_fragments': ["dragon_weakness"],
            'current_location': "loc_village", 'player_class': "Paladin", 'level': 10, 'experience_points': 10000,
            'ability_scores': {"strength": 18, "dexterity": 14, "constitution": 16, "intelligence": 10, "wisdom": 12, "charisma": 15},
            'combat_stats': {"armor_class": 20, "initiative_bonus": 2, "speed": 30},
            'hit_points': {"current": 90, "maximum": 100, "temporary": 5},
            'spell_slots': {"level1": 4, "level2": 3},
            'equipment': {
                "weapon": "item_sword", "armor": "plate_armor_id", "shield": "shield_id", "helmet": "helmet_id",
                "boots": "boots_id", "gloves": "gloves_id", "amulet": "amulet_id", "ring1": "ring_id1", "ring2": "ring_id2",
                "currency": {"gold": 1000, "silver": 500, "copper": 200}
            },
            'status_effects': ["blessed"], 'proficiencies': {"skills": ["athletics", "perception"], "saving_throws": ["wisdom", "charisma"]},
            'feats': ["tough", "great_weapon_master"], 'background': "Noble", 'alignment': "Lawful Good",
            'personality_traits': ["brave", "honorable"], 'ideals': ["justice"], 'bonds': ["my_kingdom"], 'flaws': ["overconfident"],
            'notes': "Ready for adventure!",
            'active_quests': ["quest1"],
            'completed_quests': [],
            'quest_status': {"quest1": "accepted"},
            'quest_progress': {"quest1": {'objectives': ['obj1', 'obj2'], 'completed_objectives': set(['obj1'])}}
        }
        gs_original.players["player_hero"] = Player.from_dict(player_data)

        gs_original.world_variables = {"time_of_day": "dusk", "weather": "stormy"}
        gs_original.turn_count = 123

        # Save
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp_file:
            save_filepath = tmp_file.name
        self.addCleanup(os.remove, save_filepath)
        gs_original.save_game(save_filepath)

        # Load
        gs_loaded = GameState()
        gs_loaded.load_game(save_filepath) # This will also call load_quests

        # High-level comparison using to_dict()
        # Need to ensure quest_progress sets are compared correctly if to_dict doesn't handle them as sorted lists
        original_dict = gs_original.to_dict()
        loaded_dict = gs_loaded.to_dict()

        # Convert sets in quest_progress to sorted lists for consistent comparison
        for p_id, p_data in original_dict['players'].items():
            if 'quest_progress' in p_data:
                for q_id, q_prog in p_data['quest_progress'].items():
                    if 'completed_objectives' in q_prog and isinstance(q_prog['completed_objectives'], set):
                        q_prog['completed_objectives'] = sorted(list(q_prog['completed_objectives']))
        for p_id, p_data in loaded_dict['players'].items():
            if 'quest_progress' in p_data:
                for q_id, q_prog in p_data['quest_progress'].items():
                    if 'completed_objectives' in q_prog and isinstance(q_prog['completed_objectives'], set):
                         q_prog['completed_objectives'] = sorted(list(q_prog['completed_objectives']))


        self.maxDiff = None # Show full diff on failure
        self.assertEqual(original_dict, loaded_dict)

        # More granular checks (optional, but good for verifying specifics like set conversion in quest_progress)
        self.assertEqual(gs_loaded.players["player_hero"].quest_progress["quest1"]["completed_objectives"], set(['obj1']))
        self.assertEqual(gs_loaded.turn_count, 123)
        self.assertEqual(gs_loaded.world_variables, {"time_of_day": "dusk", "weather": "stormy"})
        self.assertIn("item_sword", gs_loaded.items)
        self.assertEqual(gs_loaded.items["item_sword"].effects, {"damage_bonus": 5})
        self.assertEqual(gs_loaded.locations["loc_castle"].npcs, ["npc_dragon"])
        self.assertEqual(gs_loaded.npcs["npc_dragon"].hp, 100)


if __name__ == '__main__':
    unittest.main()
