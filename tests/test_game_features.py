import unittest
from unittest.mock import MagicMock, patch

import sys
import os

# Add project root to sys.path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_state import Player, PlayerState, reveal_clue, operate_puzzle_element, check_puzzle_solution
# Assuming ITEM_DATABASE and other necessary components are accessible or can be mocked.
# For simplicity, we'll define mock data directly in tests.

# Mock player data for tests
BASE_PLAYER_DATA = {
    "id": "test_player", "name": "Tester", "max_hp": 10,
    "combat_stats": {}, "base_damage_dice": "1d4", "equipment": {},
    "ability_scores": {"investigation": 16, "strength": 10}, # Assuming investigation is an ability for simplicity
    "skills": ["investigation"], "proficiencies": {"skills": ["investigation"]},
    "spell_slots": {}, "inventory": [], "currency": {},
    "active_quests": {}, "completed_quests": []
}

# Mock proficiency bonus if needed by skill checks, assuming utils.PROFICIENCY_BONUS
# If utils.SKILL_ABILITY_MAP is used by perform_skill_check, ensure 'investigation' is mapped.
# We might need to patch these if they are not easily available or configured for 'investigation'.
# For now, let's assume perform_skill_check can run with 'investigation'.
# In game_state.Player.perform_skill_check, SKILL_ABILITY_MAP is used.
# Let's mock it for the 'investigation' skill.

MOCK_SKILL_ABILITY_MAP = {
    "investigation": "investigation" # Mocking that 'investigation' skill uses 'investigation' ability
}
MOCK_PROFICIENCY_BONUS = 2


class TestRevealClue(unittest.TestCase):

    def setUp(self):
        self.player = Player(player_data=BASE_PLAYER_DATA.copy())
        self.game_state = PlayerState(player_character=self.player)
        self.game_state.world_data = {} # Reset for each test

        # Mock ancient_tablet for clue tests
        self.tablet_id = "ancient_tablet_001"
        self.clue_text = "The secret is 'sword'."
        self.tablet_data_with_clue = {
            "id": self.tablet_id,
            "name": "Ancient Tablet",
            "hidden_clue_details": {
                "clue_text": self.clue_text,
                "required_skill": "investigation",
                "dc": 15,
                "revealed": False
            }
        }
        self.game_state.world_data[self.tablet_id] = self.tablet_data_with_clue

    @patch('game_state.notify_dm') # Patches notify_dm in the game_state module
    @patch('game_state.SKILL_ABILITY_MAP', MOCK_SKILL_ABILITY_MAP)
    @patch('game_state.PROFICIENCY_BONUS', MOCK_PROFICIENCY_BONUS)
    @patch('game_state.roll_dice') # Patches roll_dice used by perform_skill_check
    def test_reveal_clue_success(self, mock_roll_dice, mock_notify_dm):
        # Player DEX 16 (+3), Proficient (+2). Total mod = +5. DC 15. Need roll of 10.
        mock_roll_dice.return_value = 10 # Ensures success (10 + 5 = 15)

        success, message = reveal_clue(self.player, self.tablet_id, self.game_state)

        self.assertTrue(success)
        self.assertEqual(message, self.clue_text)
        self.assertIn(self.clue_text, self.player.discovered_clues)
        self.assertTrue(self.game_state.world_data[self.tablet_id]["hidden_clue_details"]["revealed"])
        mock_notify_dm.assert_called() # Check if DM was notified

    @patch('game_state.notify_dm')
    @patch('game_state.SKILL_ABILITY_MAP', MOCK_SKILL_ABILITY_MAP)
    @patch('game_state.PROFICIENCY_BONUS', MOCK_PROFICIENCY_BONUS)
    @patch('game_state.roll_dice')
    def test_reveal_clue_failure_skill_check(self, mock_roll_dice, mock_notify_dm):
        mock_roll_dice.return_value = 9 # Ensures failure (9 + 5 = 14 vs DC 15)

        success, message = reveal_clue(self.player, self.tablet_id, self.game_state)

        self.assertFalse(success)
        self.assertNotIn(self.clue_text, self.player.discovered_clues)
        self.assertFalse(self.game_state.world_data[self.tablet_id]["hidden_clue_details"]["revealed"])
        self.assertEqual(message, f"{self.tablet_data_with_clue['name']}을(를) 조사했지만 특별한 것을 찾지 못했습니다.")
        mock_notify_dm.assert_called()

    @patch('game_state.notify_dm')
    def test_reveal_clue_already_revealed(self, mock_notify_dm):
        self.game_state.world_data[self.tablet_id]["hidden_clue_details"]["revealed"] = True
        self.player.discovered_clues.append(self.clue_text) # Assume it was added previously

        success, message = reveal_clue(self.player, self.tablet_id, self.game_state)

        self.assertTrue(success) # Still true, but message indicates already found
        self.assertEqual(message, f"(이미 발견된 단서): {self.clue_text}")
        # No DM notification expected by default for "already revealed" in current reveal_clue logic
        # mock_notify_dm.assert_not_called() # or called with a specific "already found" message if implemented

    def test_reveal_clue_no_clue_details(self):
        tablet_no_clue = {"id": "tablet_no_clue", "name": "Blank Tablet"}
        self.game_state.world_data["tablet_no_clue"] = tablet_no_clue
        success, message = reveal_clue(self.player, "tablet_no_clue", self.game_state)
        self.assertFalse(success)
        self.assertEqual(message, "이 대상에는 숨겨진 단서가 없는 것 같습니다.")

    def test_reveal_clue_target_not_found(self):
        success, message = reveal_clue(self.player, "non_existent_id", self.game_state)
        self.assertFalse(success)
        self.assertEqual(message, "조사할 대상을 찾을 수 없습니다.")

    @patch('game_state.notify_dm')
    @patch('game_state.SKILL_ABILITY_MAP', MOCK_SKILL_ABILITY_MAP)
    @patch('game_state.PROFICIENCY_BONUS', MOCK_PROFICIENCY_BONUS)
    @patch('game_state.roll_dice')
    def test_reveal_clue_misconfigured_dc(self, mock_roll_dice, mock_notify_dm):
        misconfigured_tablet = self.tablet_id + "_misconfig"
        self.game_state.world_data[misconfigured_tablet] = {
            "id": misconfigured_tablet, "name": "Misconfigured Tablet",
            "hidden_clue_details": {"clue_text": "text", "required_skill": "investigation", "revealed": False } # Missing DC
        }
        mock_roll_dice.return_value = 20 # High roll, shouldn't matter
        success, message = reveal_clue(self.player, misconfigured_tablet, self.game_state)
        self.assertFalse(success)
        self.assertEqual(message, "단서의 정보가 잘못 설정되어 조사할 수 없습니다.")


class TestPuzzleInteraction(unittest.TestCase):

    def setUp(self):
        self.player = Player(player_data=BASE_PLAYER_DATA.copy())
        self.game_state = PlayerState(player_character=self.player)
        self.game_state.world_data = {}
        self.game_state.world_variables = {}

        self.puzzle_room_id = "north_tower_puzzle_room"
        self.puzzle_data = {
            "id": self.puzzle_room_id,
            "name": "북쪽 탑의 비밀 방",
            "type": "location",
            "puzzle_details": {
                "type": "lever_sequence",
                "elements": [
                    {"id": "lever1", "name": "첫 번째 레버", "state": "neutral", "available_states": ["up", "neutral", "down"]},
                    {"id": "lever2", "name": "두 번째 레버", "state": "neutral", "available_states": ["up", "neutral", "down"]},
                    {"id": "lever3", "name": "세 번째 레버", "state": "neutral", "available_states": ["up", "neutral", "down"]}
                ],
                "solution_sequence": [
                    {"element_id": "lever1", "target_state": "down"},
                    {"element_id": "lever3", "target_state": "up"},
                    {"element_id": "lever2", "target_state": "down"}
                ],
                "is_solved": False,
                "success_message": "레버를 올바른 순서로 조작하자, 벽의 일부가 움직이며 숨겨진 통로가 드러났습니다!",
                "failure_message": "레버를 조작했지만, 아무 일도 일어나지 않았습니다." # Currently not directly used by check_puzzle_solution for return
            },
            "on_solve_effect": {
                "world_variable_to_set": "north_tower_secret_passage_unlocked",
                "value": True
            }
        }
        self.game_state.world_data[self.puzzle_room_id] = self.puzzle_data

    @patch('game_state.notify_dm')
    def test_operate_puzzle_element_state_change(self, mock_notify_dm):
        op_success, msg = operate_puzzle_element(self.player, self.puzzle_room_id, "lever1", "down", self.game_state)
        self.assertTrue(op_success)
        self.assertEqual(self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][0]["state"], "down")
        self.assertIn("첫 번째 레버 레버를 neutral 상태에서 down 상태로 변경했습니다.", mock_notify_dm.call_args_list[0][0][0]) # Check DM notification
        self.assertIn("첫 번째 레버 레버를 down(으)로 설정했습니다. 아직 아무 일도 일어나지 않았습니다.", msg)

    @patch('game_state.notify_dm')
    def test_operate_puzzle_element_invalid_state(self, mock_notify_dm):
        op_success, msg = operate_puzzle_element(self.player, self.puzzle_room_id, "lever1", "sideways", self.game_state)
        self.assertFalse(op_success)
        self.assertIn("'첫 번째 레버' 레버를 'sideways' 상태로 설정할 수 없습니다.", msg)
        self.assertEqual(self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][0]["state"], "neutral") # State should not change

    @patch('game_state.notify_dm')
    def test_puzzle_solve_correct_sequence(self, mock_notify_dm):
        # Apply correct sequence
        operate_puzzle_element(self.player, self.puzzle_room_id, "lever1", "down", self.game_state)
        mock_notify_dm.reset_mock() # Reset mock for the next call
        operate_puzzle_element(self.player, self.puzzle_room_id, "lever3", "up", self.game_state)
        mock_notify_dm.reset_mock()
        # Last operation should trigger solve
        op_success, msg = operate_puzzle_element(self.player, self.puzzle_room_id, "lever2", "down", self.game_state)

        self.assertTrue(op_success)
        self.assertTrue(self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["is_solved"])
        self.assertTrue(self.game_state.world_variables.get("north_tower_secret_passage_unlocked"))
        expected_success_msg = self.puzzle_data["puzzle_details"]["success_message"]
        self.assertIn(expected_success_msg, msg) # operate_puzzle_element returns the success message

        # Check DM notification for solving
        solve_dm_call_found = False
        for call_args in mock_notify_dm.call_args_list:
            if "퍼즐을 해결했습니다!" in call_args[0][0]:
                solve_dm_call_found = True
                break
        self.assertTrue(solve_dm_call_found, "DM notification for solving the puzzle not found.")


    @patch('game_state.notify_dm')
    def test_puzzle_incorrect_sequence_not_solved(self, mock_notify_dm):
        operate_puzzle_element(self.player, self.puzzle_room_id, "lever1", "up", self.game_state) # Incorrect
        operate_puzzle_element(self.player, self.puzzle_room_id, "lever2", "down", self.game_state)
        op_success, msg = operate_puzzle_element(self.player, self.puzzle_room_id, "lever3", "neutral", self.game_state)

        self.assertTrue(op_success) # Operation itself is successful
        self.assertFalse(self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["is_solved"])
        self.assertFalse(self.game_state.world_variables.get("north_tower_secret_passage_unlocked", False))
        self.assertNotIn(self.puzzle_data["puzzle_details"]["success_message"], msg)


    def test_check_puzzle_solution_already_solved(self):
        self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["is_solved"] = True
        # Directly call check_puzzle_solution
        solved, msg = check_puzzle_solution(self.puzzle_room_id, self.game_state, self.player)
        self.assertTrue(solved)
        self.assertEqual(msg, "이미 해결된 퍼즐입니다.")

    def test_operate_puzzle_element_on_solved_puzzle(self):
        # First, solve the puzzle
        self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][0]["state"] = "down" # lever1
        self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][2]["state"] = "up"   # lever3
        self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][1]["state"] = "down" # lever2
        self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["is_solved"] = True

        op_success, msg = operate_puzzle_element(self.player, self.puzzle_room_id, "lever1", "neutral", self.game_state)
        self.assertTrue(op_success)
        self.assertEqual(msg, "이미 해결된 퍼즐입니다.")
        # Ensure state of lever1 did not change because puzzle is already solved
        self.assertEqual(self.game_state.world_data[self.puzzle_room_id]["puzzle_details"]["elements"][0]["state"], "down")

if __name__ == '__main__':
    unittest.main()
