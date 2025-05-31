import unittest
from game_state import GameState, Player, Item # Assuming Item is needed for inventory if quests give items
from factions import Faction
from quests import Quest, ALL_QUESTS # To get the test quest
import logging

# Suppress most logging output during tests for cleaner results, unless specifically testing logging.
# logging.disable(logging.CRITICAL) # Option: Or set to a higher level like ERROR

class TestFactions(unittest.TestCase):

    def setUp(self):
        # Basic player data for initializing a Player instance
        self.player_data = {
            "id": "test_player", "name": "Test Player", "max_hp": 100,
            "combat_stats": {}, "base_damage_dice": "1d4",
            "faction_reputations": {}, "inventory": [], "equipment": {}
        }
        self.player = Player(self.player_data)

        # Initialize GameState with the player
        self.game_state = GameState(player_character=self.player)

        # Define some factions for testing
        self.faction1_data = {
            "id": "wardens", "name": "Forest Wardens", "description": "Protectors of the woods.",
            "goals": "Guard nature.", "relationships": {"hand": "enemy"}, "members": ["npc1"]
        }
        self.faction2_data = {
            "id": "hand", "name": "Shadow Hand", "description": "Seekers of dark power.",
            "goals": "Gain power.", "relationships": {"wardens": "enemy"}, "members": ["npc2"]
        }
        self.faction1 = Faction(**self.faction1_data)
        self.faction2 = Faction(**self.faction2_data)

        # Add factions to game_state for some tests
        self.game_state.factions[self.faction1.id] = self.faction1
        self.game_state.factions[self.faction2.id] = self.faction2

        # Ensure the test quest q_verdant_wardens_aid is in ALL_QUESTS
        # For this test, we'll use its actual ID 'q_verdant_wardens_aid'
        # and assume its structure matches what was defined, especially the rewards.
        self.test_quest_id = "q_verdant_wardens_aid"
        if self.test_quest_id not in ALL_QUESTS:
            # Fallback: Define a minimal quest for testing if not found (though it should be)
            ALL_QUESTS[self.test_quest_id] = Quest(
                id=self.test_quest_id, title="Test Aid Wardens", description="Help them.",
                stages=[{"stage_id": "s1", "description": "Do something.", "completion_condition": "true", "next_stage_id": None}],
                optional_objectives=[],
                rewards={
                    'xp': 10,
                    'faction_rep_changes': [{"faction_id": "verdant_wardens", "amount": 25}]
                }
            )
        self.verdant_wardens_id = "verdant_wardens" # Actual ID from faction data files
         # Add the actual Verdant Wardens faction if not already for the quest test
        if self.verdant_wardens_id not in self.game_state.factions:
             self.game_state.factions[self.verdant_wardens_id] = Faction(id=self.verdant_wardens_id, name="The Verdant Wardens", description="", goals="", relationships={})


    def test_faction_creation(self):
        self.assertEqual(self.faction1.name, "Forest Wardens")
        self.assertEqual(self.faction1.id, "wardens")
        self.assertEqual(self.faction1.relationships, {"hand": "enemy"})
        self.assertIsNotNone(Faction(id="test", name="Test F", description="", goals="", relationships={}, members=[]))
        self.assertIsNotNone(Faction(id="test2", name="Test F2", description="", goals="", relationships={})) # Test optional members

    def test_add_faction_to_game_state(self):
        self.assertIn("wardens", self.game_state.factions)
        self.assertEqual(self.game_state.factions["wardens"].name, "Forest Wardens")

    def test_player_initial_faction_reputation(self):
        self.assertEqual(self.player.faction_reputations, {})

    def test_change_faction_reputation_basic(self):
        # Using faction1 ("wardens") which is in self.game_state.factions
        self.player.change_faction_reputation("wardens", 10, self.game_state)
        self.assertEqual(self.player.faction_reputations.get("wardens"), 10)

        self.player.change_faction_reputation("wardens", -5, self.game_state)
        self.assertEqual(self.player.faction_reputations.get("wardens"), 5)

    def test_change_faction_reputation_clamping(self):
        # Using faction2 ("hand") which is in self.game_state.factions
        self.player.change_faction_reputation("hand", 150, self.game_state)
        self.assertEqual(self.player.faction_reputations.get("hand"), 100) # Should clamp to +100

        self.player.change_faction_reputation("hand", -50, self.game_state) # From 100 to 50
        self.assertEqual(self.player.faction_reputations.get("hand"), 50)

        self.player.change_faction_reputation("hand", -200, self.game_state) # From 50, try to go to -150
        self.assertEqual(self.player.faction_reputations.get("hand"), -100) # Should clamp to -100

        # Test starting from 0 and going very low
        self.player.change_faction_reputation("new_faction_test", -1000, self.game_state)
        # Need to add "new_faction_test" to game_state.factions for name lookup in change_faction_reputation
        self.game_state.factions["new_faction_test"] = Faction(id="new_faction_test", name="New Faction", description="", goals="", relationships={})
        self.assertEqual(self.player.faction_reputations.get("new_faction_test"), -100)


    def test_change_faction_reputation_unknown_faction_id_for_message(self):
        # Test that it doesn't crash if faction_id for message is not in game_state.factions
        # The change_faction_reputation method should use a default name like "Unknown Faction"
        # We're mostly checking for no exceptions here.
        # The actual reputation change should still occur.
        initial_rep = self.player.faction_reputations.get("non_existent_faction", 0)
        try:
            self.player.change_faction_reputation("non_existent_faction", 10, self.game_state)
            self.assertEqual(self.player.faction_reputations.get("non_existent_faction"), initial_rep + 10)
        except Exception as e:
            self.fail(f"change_faction_reputation raised an exception with unknown faction ID: {e}")


    def test_apply_rewards_faction_reputation(self):
        quest_to_test = ALL_QUESTS.get(self.test_quest_id)
        self.assertIsNotNone(quest_to_test, f"Quest {self.test_quest_id} not found in ALL_QUESTS.")

        rewards_data = quest_to_test.rewards

        # Ensure the target faction for the quest reward exists in player's reputations (or starts at 0)
        target_faction_id_from_quest = rewards_data["faction_rep_changes"][0]["faction_id"]
        amount_from_quest = rewards_data["faction_rep_changes"][0]["amount"]

        # Check initial reputation for the target faction (should be 0 or not exist)
        initial_rep = self.player.faction_reputations.get(target_faction_id_from_quest, 0)

        self.player.apply_rewards(rewards_data, self.game_state)

        expected_rep = initial_rep + amount_from_quest
        # Clamp if necessary, though 25 shouldn't exceed limits from 0
        expected_rep = max(-100, min(100, expected_rep))

        self.assertEqual(self.player.faction_reputations.get(target_faction_id_from_quest), expected_rep)

    def test_apply_rewards_multiple_faction_reputations(self):
        rewards_data = {
            'xp': 50,
            'faction_rep_changes': [
                {"faction_id": "wardens", "amount": 15},
                {"faction_id": "hand", "amount": -10}
            ]
        }
        initial_wardens_rep = self.player.faction_reputations.get("wardens", 0)
        initial_hand_rep = self.player.faction_reputations.get("hand", 0)

        self.player.apply_rewards(rewards_data, self.game_state)

        self.assertEqual(self.player.faction_reputations.get("wardens"), initial_wardens_rep + 15)
        self.assertEqual(self.player.faction_reputations.get("hand"), initial_hand_rep - 10)

if __name__ == '__main__':
    unittest.main()
