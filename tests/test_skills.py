import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Assuming the project structure is:
# project_root/
#   game_state.py
#   utils.py
#   tests/
#     test_skills.py
#     __init__.py

# This adds the project_root to sys.path for imports if running tests from tests/ directory directly
# For many test runners (like 'python -m unittest discover'), this might not be strictly necessary
# if they handle path discovery, but it's a good safeguard.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_state import Player
from utils import PROFICIENCY_BONUS, SKILL_ABILITY_MAP # SKILL_ABILITY_MAP is used by Player, not directly in test logic much here

class TestPlayerSkills(unittest.TestCase):

    def test_get_ability_modifier(self):
        player_data_abilities = {
            "id": "player_abs", "name": "AbilityTester", "max_hp": 10,
            "combat_stats": {}, "base_damage_dice": "1d4", "equipment": {},
            "ability_scores": {
                "strength": 7,
                "dexterity": 10,
                "constitution": 14,
                "intelligence": 15,
                "wisdom": 8,
                "charisma": 13
            },
            "skills": [], "proficiencies": {"skills": []}
        }
        player = Player(player_data=player_data_abilities)

        self.assertEqual(player.get_ability_modifier("strength"), -2)  # (7 - 10) // 2
        self.assertEqual(player.get_ability_modifier("dexterity"), 0)   # (10 - 10) // 2
        self.assertEqual(player.get_ability_modifier("constitution"), 2) # (14 - 10) // 2
        self.assertEqual(player.get_ability_modifier("intelligence"), 2) # (15 - 10) // 2
        self.assertEqual(player.get_ability_modifier("wisdom"), -1)     # (8 - 10) // 2
        self.assertEqual(player.get_ability_modifier("charisma"), 1)   # (13 - 10) // 2

        # Test with a non-existent ability
        # Expected to log a warning and return 0
        # To check logs, we would need to configure logging and use self.assertLogs,
        # but for this subtask, focusing on return value is primary.
        self.assertEqual(player.get_ability_modifier("luck"), 0)

        # Test with mixed case
        self.assertEqual(player.get_ability_modifier("sTrEnGtH"), -2)

    # Patching 'game_state.roll_dice' because Player class in game_state.py imports roll_dice from utils
    # and calls it as 'roll_dice()'. So we patch where it's looked up (in game_state module scope).
    @patch('game_state.roll_dice')
    def test_perform_skill_check(self, mock_roll_dice: MagicMock):
        player_data_for_skills = {
            "id": "skill_test_player", "name": "Skill Tester", "max_hp": 10,
            "combat_stats": {}, "base_damage_dice": "1d4", "equipment": {},
            "ability_scores": {"dexterity": 16, "charisma": 14, "strength": 10, "wisdom": 12},
            "skills": ["lockpicking", "persuasion", "athletics", "perception", "unknown_skill_in_list"],
            "proficiencies": {
                "skills": ["lockpicking", "athletics"] # Proficient in lockpicking (DEX) and athletics (STR)
            }
        }
        player = Player(player_data=player_data_for_skills)

        # Scenario 1: Proficient Skill Success
        # Lockpicking (DEX 16 -> +3 mod), Proficient (+PROFICIENCY_BONUS)
        # DC = 15. Mock roll = 10. Total = 10 (roll) + 3 (DEX) + PROFICIENCY_BONUS
        mock_roll_dice.return_value = 10
        expected_total_s1 = 10 + 3 + PROFICIENCY_BONUS
        dc_s1 = 15
        success, d20_roll, total_value, breakdown_str = player.perform_skill_check("lockpicking", dc_s1)

        self.assertEqual(d20_roll, 10)
        self.assertEqual(total_value, expected_total_s1)
        self.assertEqual(success, expected_total_s1 >= dc_s1)
        self.assertIn(f"d20(10)", breakdown_str)
        self.assertIn(f"DEXTERITY_MOD(3)", breakdown_str) # Relies on SKILL_ABILITY_MAP
        self.assertIn(f"PROF_BONUS({PROFICIENCY_BONUS})", breakdown_str)
        self.assertIn(f"= {expected_total_s1}", breakdown_str)
        self.assertIn(f"vs DC({dc_s1})", breakdown_str)

        # Scenario 2: Non-Proficient Skill Failure
        # Persuasion (CHA 14 -> +2 mod), Not Proficient
        # DC = 18. Mock roll = 8. Total = 8 (roll) + 2 (CHA)
        mock_roll_dice.return_value = 8
        expected_total_s2 = 8 + 2
        dc_s2 = 18
        success, d20_roll, total_value, breakdown_str = player.perform_skill_check("persuasion", dc_s2)

        self.assertEqual(d20_roll, 8)
        self.assertEqual(total_value, expected_total_s2)
        self.assertEqual(success, expected_total_s2 >= dc_s2) # Should be False
        self.assertFalse(success)
        self.assertIn(f"d20(8)", breakdown_str)
        self.assertIn(f"CHARISMA_MOD(2)", breakdown_str) # Relies on SKILL_ABILITY_MAP
        self.assertIn(f"PROF_BONUS(0)", breakdown_str)
        self.assertIn(f"= {expected_total_s2}", breakdown_str)
        self.assertIn(f"vs DC({dc_s2})", breakdown_str)

        # Scenario 3: Skill not in SKILL_ABILITY_MAP (uses "unknown_skill_in_list" which is in player's skills but not in SKILL_ABILITY_MAP)
        # DC = 10. Mock roll = 10. Total = 10 (roll) + 0 (no ability) + 0 (not proficient by this name)
        mock_roll_dice.return_value = 10
        expected_total_s3 = 10
        dc_s3 = 10
        # Note: "unknown_skill_in_list" is not in SKILL_ABILITY_MAP, so no ability mod.
        # It's also not in proficiencies by that name.
        success, d20_roll, total_value, breakdown_str = player.perform_skill_check("unknown_skill_in_list", dc_s3)

        self.assertEqual(d20_roll, 10)
        self.assertEqual(total_value, expected_total_s3)
        self.assertEqual(success, expected_total_s3 >= dc_s3) # Should be True
        self.assertTrue(success)
        self.assertIn(f"d20(10)", breakdown_str)
        self.assertIn(f"N/A_MOD(N/A)", breakdown_str) # No ability associated
        self.assertIn(f"PROF_BONUS(0)", breakdown_str)
        self.assertIn(f"= {expected_total_s3}", breakdown_str)

        # Scenario 4: Edge case - Total equals DC
        # Athletics (STR 10 -> +0 mod), Proficient (+PROFICIENCY_BONUS)
        # DC = 12. Mock roll needs to be 12 - PROFICIENCY_BONUS. Total = (12 - PROFICIENCY_BONUS) + 0 + PROFICIENCY_BONUS = 12.
        roll_for_boundary = 12 - PROFICIENCY_BONUS
        mock_roll_dice.return_value = roll_for_boundary
        expected_total_s4 = roll_for_boundary + 0 + PROFICIENCY_BONUS
        dc_s4 = 12
        success, d20_roll, total_value, breakdown_str = player.perform_skill_check("athletics", dc_s4)

        self.assertEqual(d20_roll, roll_for_boundary)
        self.assertEqual(total_value, expected_total_s4) # Should be dc_s4
        self.assertEqual(total_value, dc_s4)
        self.assertEqual(success, expected_total_s4 >= dc_s4) # Should be True
        self.assertTrue(success)
        self.assertIn(f"d20({roll_for_boundary})", breakdown_str)
        self.assertIn(f"STRENGTH_MOD(0)", breakdown_str)
        self.assertIn(f"PROF_BONUS({PROFICIENCY_BONUS})", breakdown_str)
        self.assertIn(f"= {expected_total_s4}", breakdown_str)

        # Scenario 5: Skill uses an ability score not present in the player's ability_scores
        # Perception (WIS), but let's test with a player who doesn't have Wisdom defined.
        player_data_no_wisdom = {
            "id": "player_no_wis", "name": "NoWisdomTester", "max_hp": 10,
            "combat_stats": {}, "base_damage_dice": "1d4", "equipment": {},
            "ability_scores": {"dexterity": 10}, # No wisdom
            "skills": ["perception"], # Has perception skill
            "proficiencies": {"skills": []} # Not proficient
        }
        player_no_wisdom = Player(player_data=player_data_no_wisdom)
        mock_roll_dice.return_value = 11
        expected_total_s5 = 11 + 0 + 0 # Roll + 0 (WIS mod because missing) + 0 (not proficient)
        dc_s5 = 10
        success, d20_roll, total_value, breakdown_str = player_no_wisdom.perform_skill_check("perception", dc_s5)

        self.assertEqual(d20_roll, 11)
        self.assertEqual(total_value, expected_total_s5)
        self.assertTrue(success)
        self.assertIn(f"d20(11)", breakdown_str)
        self.assertIn(f"WISDOM_MOD(0)", breakdown_str) # Modifier defaults to 0 if ability not found
        self.assertIn(f"PROF_BONUS(0)", breakdown_str)
        self.assertIn(f"= {expected_total_s5}", breakdown_str)


if __name__ == '__main__':
    unittest.main()
