import unittest
import os
import json
import tempfile
import logging
from unittest.mock import patch, mock_open # Added mock_open for test_load_empty_json_file
from game_state import GameState, Player, Item, NPC, Location, ALL_QUESTS # Added NPC, ALL_QUESTS

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
        gs.load_game("non_existent_save_file.json")
        mock_logger.info.assert_called_once_with("Save file not found at non_existent_save_file.json. Starting a new game or using default state.")


if __name__ == '__main__':
    unittest.main()
