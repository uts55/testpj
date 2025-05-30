import unittest
import os
import json
from game_state import GameState, Player
from quests import Quest, ALL_QUESTS # Assuming ALL_QUESTS is populated in quests.py

class TestQuestSystem(unittest.TestCase):

    def setUp(self):
        self.game_state = GameState()
        # Manually load quests for testing, similar to how it would be in initialize_new_game or load_game
        self.game_state.load_quests(ALL_QUESTS)

        # Create a dummy player for testing
        self.player_id = "test_player_1"
        self.player = Player(
            id=self.player_id,
            name="Test Player",
            inventory=[],
            skills=[],
            knowledge_fragments=[],
            current_location="test_location",
            active_quests=[],
            completed_quests=[],
            quest_status={},
            quest_progress={}
        )
        self.game_state.players[self.player_id] = self.player

        # Define sample quest IDs from ALL_QUESTS for easier access
        self.quest1_id = "q001" # The Lost Sword
        self.quest2_id = "q002" # The Alchemist's Request

        # Ensure these quests exist in ALL_QUESTS for tests to be valid
        self.assertIn(self.quest1_id, self.game_state.quests)
        self.assertIn(self.quest2_id, self.game_state.quests)

    def test_quest_loading(self):
        self.assertIsNotNone(self.game_state.get_quest(self.quest1_id))
        self.assertEqual(self.game_state.get_quest(self.quest1_id).title, "The Lost Sword")
        self.assertGreater(len(self.game_state.quests), 0)

    def test_accept_quest(self):
        accepted = self.game_state.accept_quest(self.player_id, self.quest1_id)
        self.assertTrue(accepted)
        self.assertIn(self.quest1_id, self.player.active_quests)
        self.assertEqual(self.player.quest_status.get(self.quest1_id), ALL_QUESTS[self.quest1_id].status_descriptions.get('accepted'))

        quest1_obj = self.game_state.get_quest(self.quest1_id)
        self.assertIn(self.quest1_id, self.player.quest_progress)
        self.assertEqual(set(self.player.quest_progress[self.quest1_id]['objectives']), set(quest1_obj.objectives))
        self.assertEqual(len(self.player.quest_progress[self.quest1_id]['completed_objectives']), 0)

        # Try to accept again
        accepted_again = self.game_state.accept_quest(self.player_id, self.quest1_id)
        self.assertFalse(accepted_again)

    def test_advance_quest_objective(self):
        self.game_state.accept_quest(self.player_id, self.quest1_id)

        quest1 = self.game_state.get_quest(self.quest1_id)
        objective_to_advance = quest1.objectives[0] # "Find the Elder's Sword."

        advanced = self.game_state.advance_quest_objective(self.player_id, self.quest1_id, objective_to_advance)
        self.assertTrue(advanced)
        self.assertIn(objective_to_advance, self.player.quest_progress[self.quest1_id]['completed_objectives'])

        # Try to advance an already completed objective
        advanced_again = self.game_state.advance_quest_objective(self.player_id, self.quest1_id, objective_to_advance)
        self.assertFalse(advanced_again) # Should not advance again if already completed

        # Try to advance a non-existent objective
        advanced_non_existent = self.game_state.advance_quest_objective(self.player_id, self.quest1_id, "NonExistentObjective")
        self.assertFalse(advanced_non_existent)

    def test_complete_quest_prematurely(self):
        self.game_state.accept_quest(self.player_id, self.quest1_id)
        # Only one objective (or none) might be complete here
        completed = self.game_state.complete_quest(self.player_id, self.quest1_id)
        self.assertFalse(completed)
        self.assertIn(self.quest1_id, self.player.active_quests)
        self.assertNotIn(self.quest1_id, self.player.completed_quests)

    def test_complete_quest_successfully(self):
        self.game_state.accept_quest(self.player_id, self.quest1_id)
        quest1 = self.game_state.get_quest(self.quest1_id)

        # Manually advance all objectives for q001
        for objective in quest1.objectives:
            self.game_state.advance_quest_objective(self.player_id, self.quest1_id, objective)

        # Store pre-completion stats
        initial_xp = self.player.experience_points
        initial_gold = self.player.equipment['currency'].get('gold', 0)

        completed = self.game_state.complete_quest(self.player_id, self.quest1_id)
        self.assertTrue(completed)

        self.assertNotIn(self.quest1_id, self.player.active_quests)
        self.assertIn(self.quest1_id, self.player.completed_quests)
        self.assertEqual(self.player.quest_status.get(self.quest1_id), quest1.status_descriptions.get('completed'))

        # Check rewards for q001
        self.assertEqual(self.player.experience_points, initial_xp + quest1.rewards.get('xp',0))
        for item_id in quest1.rewards.get('items', []):
            self.assertIn(item_id, self.player.inventory)
        for currency_type, amount in quest1.rewards.get('currency', {}).items():
            if currency_type == 'gold':
                 self.assertEqual(self.player.equipment['currency'].get(currency_type), initial_gold + amount)
            else:
                 self.assertEqual(self.player.equipment['currency'].get(currency_type), amount)


    def test_save_and_load_with_quests(self):
        # Accept a quest and advance one objective
        self.game_state.accept_quest(self.player_id, self.quest2_id)
        quest2 = self.game_state.get_quest(self.quest2_id)
        objective_to_advance = quest2.objectives[0]
        self.game_state.advance_quest_objective(self.player_id, self.quest2_id, objective_to_advance)

        # Save game state
        save_file = "test_save_game_quests.json"
        self.game_state.save_game(save_file)

        # Create a new game state and load
        new_game_state = GameState()
        new_game_state.load_game(save_file) # This also calls load_quests(ALL_QUESTS) internally

        # Clean up save file
        if os.path.exists(save_file):
            os.remove(save_file)

        # Check loaded player and quest states
        loaded_player = new_game_state.get_player(self.player_id)
        self.assertIsNotNone(loaded_player)

        self.assertIn(self.quest2_id, loaded_player.active_quests)
        self.assertEqual(loaded_player.quest_status.get(self.quest2_id), quest2.status_descriptions.get('accepted')) # Or specific status if advanced

        self.assertIn(self.quest2_id, loaded_player.quest_progress)
        self.assertIn(objective_to_advance, loaded_player.quest_progress[self.quest2_id]['completed_objectives'])
        self.assertEqual(len(loaded_player.quest_progress[self.quest2_id]['completed_objectives']), 1)
        self.assertEqual(set(loaded_player.quest_progress[self.quest2_id]['objectives']), set(quest2.objectives))


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
