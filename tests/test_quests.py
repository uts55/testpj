import unittest
from unittest.mock import patch, call
import copy

from game_state import Player
from quests import Quest, ALL_QUESTS
# notify_dm is imported into game_state's namespace, so we patch it there.

# Base player data template for initializing Player objects in tests
initial_player_data_template = {
    "id": "test_player",
    "name": "TestPlayer",
    "experience_points": 0,
    "inventory": [],
    "equipment": {
        "currency": {"gold": 0, "silver": 0, "copper": 0},
        "weapon": None,
        "armor": None,
        "shield": None,
    },
    "active_quests": {},
    "completed_quests": [],
    "max_hp": 50, # Added default
    "combat_stats": {'armor_class': 10, 'attack_bonus': 1, 'damage_bonus': 0, 'initiative_bonus': 2}, # Added defaults
    "base_damage_dice": "1d4", # Added default
    "ability_scores": {"strength": 10, "dexterity": 10, "constitution": 10, "intelligence": 10, "wisdom": 10, "charisma": 10}, # Added defaults
    "skills_list": ["perception", "stealth"], # Added defaults (skills was skills_list in Player init)
    "proficiencies_map": {"skills": ["perception"]}, # Added defaults (proficiencies was proficiencies_map in Player init)
    "spell_slots": {"level_1": {"current": 3, "maximum": 3}}, # Added defaults
    # Ensure all fields required by Player.__init__ are present
    "player_class": "Fighter",
    "level": 1,
    "status_effects": [],
    "feats": [],
    "knowledge_fragments": [],
    "current_location": "test_location",
    "background": "Test Background",
    "alignment": "Neutral",
    "personality_traits": [],
    "ideals": [],
    "bonds": [],
    "flaws": [],
    "notes": ""
}
# Correcting mismatched key names from template to Player.__init__ based on Player class structure
initial_player_data_template["skills"] = initial_player_data_template.pop("skills_list")
initial_player_data_template["proficiencies"] = initial_player_data_template.pop("proficiencies_map")


class TestQuestSystem(unittest.TestCase):

    def setUp(self):
        """Create a fresh Player instance for each test."""
        self.player_data = copy.deepcopy(initial_player_data_template)
        # Player class expects player_data as the first argument, and optionally equipment_data
        # The structure of initial_player_data_template already includes an "equipment" field.
        # So, we don't need to pass equipment_data separately if it's derived from player_data["equipment"].
        self.player = Player(self.player_data)


    @patch('game_state.notify_dm')
    def test_accept_quest(self, mock_notify_dm):
        quest_to_accept = "q001"
        first_stage_id = ALL_QUESTS[quest_to_accept].stages[0]["stage_id"]

        accepted, msg = self.player.accept_quest(quest_to_accept, first_stage_id)
        self.assertTrue(accepted)
        self.assertIn(quest_to_accept, self.player.active_quests)
        self.assertEqual(self.player.active_quests[quest_to_accept]["current_stage_id"], first_stage_id)
        self.assertEqual(self.player.active_quests[quest_to_accept]["completed_optional_objectives"], [])
        mock_notify_dm.assert_called_once()
        # Example of checking call args (can be more specific)
        self.assertIn(quest_to_accept, mock_notify_dm.call_args[0][0])

        # Test accepting already active quest
        accepted_again, msg_again = self.player.accept_quest(quest_to_accept, first_stage_id)
        self.assertFalse(accepted_again)
        self.assertIn("already active", msg_again.lower())
        mock_notify_dm.assert_called_once() # Should not be called again

        # Test accepting completed quest
        self.player.completed_quests.append("q002")
        accepted_completed, msg_completed = self.player.accept_quest("q002", ALL_QUESTS["q002"].stages[0]["stage_id"])
        self.assertFalse(accepted_completed)
        self.assertIn("already been completed", msg_completed.lower())
        mock_notify_dm.assert_called_once() # Should not be called again

    @patch('game_state.notify_dm')
    def test_advance_quest_stage(self, mock_notify_dm):
        quest_id = "q001"
        initial_stage_id = ALL_QUESTS[quest_id].stages[0]["stage_id"]
        second_stage_id = ALL_QUESTS[quest_id].stages[1]["stage_id"]

        self.player.accept_quest(quest_id, initial_stage_id)
        mock_notify_dm.reset_mock() # Reset mock after accept_quest call

        advanced, msg = self.player.advance_quest_stage(quest_id, second_stage_id)
        self.assertTrue(advanced)
        self.assertEqual(self.player.active_quests[quest_id]["current_stage_id"], second_stage_id)
        mock_notify_dm.assert_called_once()
        self.assertIn(second_stage_id, mock_notify_dm.call_args[0][0])

        # Test advancing non-active quest
        advanced_non_active, msg_non_active = self.player.advance_quest_stage("q003", "s1_investigate_corruption")
        self.assertFalse(advanced_non_active)
        self.assertIn("not active", msg_non_active.lower())

    @patch('game_state.notify_dm')
    def test_complete_optional_objective_and_rewards(self, mock_notify_dm):
        quest_id = "q001"
        quest_obj = ALL_QUESTS[quest_id]
        initial_stage_id = quest_obj.stages[0]["stage_id"]
        self.player.accept_quest(quest_id, initial_stage_id) # Call 1 to notify_dm

        optional_objective = quest_obj.optional_objectives[0]
        opt_obj_id = optional_objective["objective_id"]
        opt_obj_rewards = optional_objective["rewards"]

        initial_xp = self.player.experience_points
        initial_gold = self.player.equipment["currency"].get("gold", 0)
        initial_items_count = len(self.player.inventory)

        completed_opt, msg_opt = self.player.complete_optional_objective(quest_id, opt_obj_id) # Call 2 to notify_dm
        self.assertTrue(completed_opt)
        self.assertIn(opt_obj_id, self.player.active_quests[quest_id]["completed_optional_objectives"])

        # Apply rewards
        reward_msgs = self.player.apply_rewards(opt_obj_rewards) # Call 3 to notify_dm
        self.assertTrue(len(reward_msgs) > 0)

        self.assertEqual(self.player.experience_points, initial_xp + opt_obj_rewards["xp"])
        self.assertEqual(self.player.equipment["currency"]["gold"], initial_gold + opt_obj_rewards["currency"]["gold"])
        self.assertEqual(len(self.player.inventory), initial_items_count + len(opt_obj_rewards["items"]))
        for item in opt_obj_rewards["items"]:
            self.assertIn(item, self.player.inventory)

        # Check specific calls to notify_dm
        # Call 1: accept_quest (already happened)
        # Call 2: complete_optional_objective
        # Call 3: apply_rewards
        self.assertEqual(mock_notify_dm.call_count, 3)
        self.assertIn(f"Optional objective '{opt_obj_id}' for quest '{quest_id}'", mock_notify_dm.call_args_list[1][0][0]) # call_args_list[1] is the second call
        self.assertIn("Rewards received", mock_notify_dm.call_args_list[2][0][0]) # call_args_list[2] is the third call


        # Test completing already completed optional objective
        completed_again, msg_again = self.player.complete_optional_objective(quest_id, opt_obj_id)
        self.assertFalse(completed_again)
        self.assertIn("already completed", msg_again.lower())
        self.assertEqual(mock_notify_dm.call_count, 3) # No new notification

    @patch('game_state.notify_dm')
    def test_complete_quest_and_rewards(self, mock_notify_dm):
        quest_id = "q002"
        quest_obj = ALL_QUESTS[quest_id]
        initial_stage_id = quest_obj.stages[0]["stage_id"]
        self.player.accept_quest(quest_id, initial_stage_id) # Call 1 to notify_dm

        initial_xp = self.player.experience_points
        initial_silver = self.player.equipment["currency"].get("silver", 0)
        initial_items_count = len(self.player.inventory)

        completed, msg = self.player.complete_quest(quest_id) # Call 2 to notify_dm
        self.assertTrue(completed)
        self.assertNotIn(quest_id, self.player.active_quests)
        self.assertIn(quest_id, self.player.completed_quests)

        # Apply rewards
        main_rewards = quest_obj.rewards
        reward_msgs = self.player.apply_rewards(main_rewards) # Call 3 to notify_dm
        self.assertTrue(len(reward_msgs) > 0)

        self.assertEqual(self.player.experience_points, initial_xp + main_rewards["xp"])
        self.assertEqual(self.player.equipment["currency"]["silver"], initial_silver + main_rewards["currency"]["silver"])
        self.assertEqual(len(self.player.inventory), initial_items_count + len(main_rewards["items"]))
        for item in main_rewards["items"]:
            self.assertIn(item, self.player.inventory)

        self.assertEqual(mock_notify_dm.call_count, 3)
        self.assertIn(f"Quest '{quest_id}' has been successfully completed", mock_notify_dm.call_args_list[1][0][0])
        self.assertIn("Rewards received", mock_notify_dm.call_args_list[2][0][0])


        # Test completing non-active quest
        completed_non_active, msg_non_active = self.player.complete_quest("q001") # q001 was not accepted here
        self.assertFalse(completed_non_active)
        self.assertIn("not active or already completed", msg_non_active.lower())
        self.assertEqual(mock_notify_dm.call_count, 3) # No new notification


    @patch('game_state.notify_dm')
    def test_apply_rewards_various_types(self, mock_notify_dm):
        initial_xp = self.player.experience_points
        initial_gold = self.player.equipment["currency"].get("gold", 0)
        initial_silver = self.player.equipment["currency"].get("silver", 0)

        rewards_to_apply = {
            "xp": 150,
            "items": ["item_test_sword", "item_test_shield"],
            "currency": {"gold": 75, "silver": 25, "copper": 100}
        }
        self.player.apply_rewards(rewards_to_apply)

        self.assertEqual(self.player.experience_points, initial_xp + 150)
        self.assertIn("item_test_sword", self.player.inventory)
        self.assertIn("item_test_shield", self.player.inventory)
        self.assertEqual(self.player.equipment["currency"]["gold"], initial_gold + 75)
        self.assertEqual(self.player.equipment["currency"]["silver"], initial_silver + 25)
        self.assertEqual(self.player.equipment["currency"]["copper"], 100) # Initial copper was 0

        mock_notify_dm.assert_called_once()
        # The exact string can be fragile, better to check for components
        call_arg_str = mock_notify_dm.call_args[0][0]
        self.assertIn("Gained 150 XP", call_arg_str)
        self.assertIn("Obtained item: item_test_sword", call_arg_str)
        self.assertIn("Obtained item: item_test_shield", call_arg_str)
        self.assertIn("Received 75 gold", call_arg_str)
        self.assertIn("Received 25 silver", call_arg_str)
        self.assertIn("Received 100 copper", call_arg_str)


    @patch('game_state.notify_dm')
    def test_multi_stage_quest_progression(self, mock_notify_dm):
        quest_id = "q003"
        quest_obj = ALL_QUESTS[quest_id]

        # Accept quest
        accepted, _ = self.player.accept_quest(quest_id, quest_obj.stages[0]["stage_id"])
        self.assertTrue(accepted)
        self.assertEqual(mock_notify_dm.call_count, 1)
        self.assertIn(f"Quest '{quest_id}'", mock_notify_dm.call_args[0][0])
        self.assertIn(quest_obj.stages[0]["stage_id"], mock_notify_dm.call_args[0][0])


        # Advance to stage 2
        advanced_s2, _ = self.player.advance_quest_stage(quest_id, quest_obj.stages[1]["stage_id"])
        self.assertTrue(advanced_s2)
        self.assertEqual(self.player.active_quests[quest_id]["current_stage_id"], quest_obj.stages[1]["stage_id"])
        self.assertEqual(mock_notify_dm.call_count, 2)
        self.assertIn(quest_obj.stages[1]["stage_id"], mock_notify_dm.call_args[0][0])


        # Advance to stage 3
        advanced_s3, _ = self.player.advance_quest_stage(quest_id, quest_obj.stages[2]["stage_id"])
        self.assertTrue(advanced_s3)
        self.assertEqual(self.player.active_quests[quest_id]["current_stage_id"], quest_obj.stages[2]["stage_id"])
        self.assertEqual(mock_notify_dm.call_count, 3)
        self.assertIn(quest_obj.stages[2]["stage_id"], mock_notify_dm.call_args[0][0])

        # Complete quest
        completed, _ = self.player.complete_quest(quest_id)
        self.assertTrue(completed)
        self.assertNotIn(quest_id, self.player.active_quests)
        self.assertIn(quest_id, self.player.completed_quests)
        self.assertEqual(mock_notify_dm.call_count, 4)
        self.assertIn(f"Quest '{quest_id}' has been successfully completed", mock_notify_dm.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
