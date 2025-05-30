import unittest
import logging # Optional: configure logging for tests if needed
from game_state import GameState, Player, Location, Item # Adjust import path if necessary

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
        # Ensure the item is not in game_state.items for this specific test case,
        # as acquire_item_from_location checks game_state.items
        # However, the primary check is whether it's in location.items.
        # If it's not in location.items, the function should return False early.
        # For a robust test, ensure it's also not in game_state.items if checking that path.
        # But the prompt's test focuses on "not in location".

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

if __name__ == '__main__':
    # Configure logging to show output from the game logic if desired during tests
    # logging.basicConfig(level=logging.INFO)
    unittest.main()
