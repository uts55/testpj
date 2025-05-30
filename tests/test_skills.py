import unittest
from unittest.mock import patch
import random # Required for tests even if random.randint is mocked for specific tests

from game_state import Player # Assuming Player is in game_state.py
from utils import SKILL_ABILITY_MAP, PROFICIENCY_BONUS # Assuming these are in utils.py

class TestPlayerUseSkill(unittest.TestCase):

    def setUp(self):
        # Basic player setup for most tests
        # This player will be loaded from a simplified version of player_template.json
        # or constructed directly with necessary attributes.
        self.player_data = {
            "id": "player_test_1",
            "name": "TestPlayer",
            "inventory": [],
            "skills": ["investigation", "perception", "arcana"], # Player has these skills
            "knowledge_fragments": [],
            "current_location": "test_loc",
            "ability_scores": {
                "strength": 10,
                "dexterity": 12, # Mod +1
                "constitution": 14, # Mod +2
                "intelligence": 16, # Mod +3 (for Investigation, Arcana)
                "wisdom": 8,       # Mod -1 (for Perception)
                "charisma": 13     # Mod +1
            },
            "proficiencies": {
                "skills": ["investigation", "arcana"] # Proficient in Investigation and Arcana
            }
            # Other fields can be omitted if not directly used by use_skill
        }
        self.player = Player.from_dict(self.player_data)

    @patch('random.randint')
    def test_use_skill_proficient(self, mock_randint):
        # Test "investigation" which uses Intelligence (16 -> +3 mod)
        # Player is proficient (+PROFICIENCY_BONUS)
        mock_randint.return_value = 10  # Mocked d20 roll

        expected_d20_roll = 10
        expected_ability_modifier = (16 - 10) // 2  # +3
        expected_proficiency_bonus = PROFICIENCY_BONUS
        expected_total_roll = expected_d20_roll + expected_ability_modifier + expected_proficiency_bonus

        result = self.player.use_skill("investigation")

        self.assertEqual(result["skill"], "investigation")
        self.assertEqual(result["d20_roll"], expected_d20_roll)
        self.assertEqual(result["ability_key"], "intelligence")
        self.assertEqual(result["ability_score"], 16)
        self.assertEqual(result["ability_modifier"], expected_ability_modifier)
        self.assertTrue(result["is_proficient"])
        self.assertEqual(result["applied_proficiency_bonus"], expected_proficiency_bonus)
        self.assertEqual(result["total_roll"], expected_total_roll)
        self.assertIn(f"Result: {expected_total_roll}", result["description"])
        mock_randint.assert_called_once_with(1, 20)

    @patch('random.randint')
    def test_use_skill_not_proficient(self, mock_randint):
        # Test "perception" which uses Wisdom (8 -> -1 mod)
        # Player is NOT proficient (no proficiency bonus)
        mock_randint.return_value = 15  # Mocked d20 roll

        expected_d20_roll = 15
        expected_ability_modifier = (8 - 10) // 2  # -1
        expected_proficiency_bonus = 0 # Not proficient
        expected_total_roll = expected_d20_roll + expected_ability_modifier + expected_proficiency_bonus

        result = self.player.use_skill("perception")

        self.assertEqual(result["skill"], "perception")
        self.assertEqual(result["d20_roll"], expected_d20_roll)
        self.assertEqual(result["ability_key"], "wisdom")
        self.assertEqual(result["ability_score"], 8)
        self.assertEqual(result["ability_modifier"], expected_ability_modifier)
        self.assertFalse(result["is_proficient"])
        self.assertEqual(result["applied_proficiency_bonus"], expected_proficiency_bonus)
        self.assertEqual(result["total_roll"], expected_total_roll)
        self.assertIn(f"Result: {expected_total_roll}", result["description"])
        mock_randint.assert_called_once_with(1, 20)

    def test_use_skill_unknown_skill_in_map(self):
        # Test a skill that's not in SKILL_ABILITY_MAP
        result = self.player.use_skill("baking") # Assuming 'baking' is not in SKILL_ABILITY_MAP

        self.assertIn("error", result)
        self.assertEqual(result["skill"], "baking")
        self.assertTrue("not a recognized skill" in result.get("error", "").lower() or \
                        "not a recognized skill" in result.get("description", "").lower())

    def test_use_skill_missing_ability_score(self):
        # Temporarily remove an ability score the player should have for a known skill
        original_intelligence = self.player.ability_scores.pop("intelligence", None)

        result = self.player.use_skill("arcana") # Arcana uses Intelligence

        self.assertEqual(result["skill"], "arcana")
        # The current implementation defaults to ability score 10 if missing, and logs a warning.
        # Let's test this default behavior.
        # d20 roll will be random here as we are not mocking it for this specific test path,
        # or we can mock it if we want to predict the total_roll.
        # For simplicity, we'll just check that it used the default ability score for modifier calculation.

        expected_default_ability_score = 10
        expected_ability_modifier_default = (expected_default_ability_score - 10) // 2 # Should be 0

        self.assertEqual(result["ability_key"], "intelligence")
        self.assertEqual(result["ability_score"], expected_default_ability_score) # Check it used the default
        self.assertEqual(result["ability_modifier"], expected_ability_modifier_default)
        # Player is proficient in Arcana
        self.assertTrue(result["is_proficient"])
        self.assertEqual(result["applied_proficiency_bonus"], PROFICIENCY_BONUS)

        # Restore ability score for other tests
        if original_intelligence is not None:
            self.player.ability_scores["intelligence"] = original_intelligence

    @patch('random.randint')
    def test_use_skill_case_insensitivity(self, mock_randint):
        # Test "INVESTIGATION" (uppercase) which uses Intelligence (16 -> +3 mod)
        # Player is proficient (+PROFICIENCY_BONUS)
        mock_randint.return_value = 5

        expected_d20_roll = 5
        expected_ability_modifier = (16 - 10) // 2  # +3
        expected_proficiency_bonus = PROFICIENCY_BONUS
        expected_total_roll = expected_d20_roll + expected_ability_modifier + expected_proficiency_bonus

        result = self.player.use_skill("INVESTIGATION") # Uppercase skill name

        self.assertEqual(result["skill"], "INVESTIGATION") # Should probably return original case or consistent case
        self.assertEqual(result["d20_roll"], expected_d20_roll)
        self.assertEqual(result["ability_key"], "intelligence")
        self.assertEqual(result["total_roll"], expected_total_roll)
        mock_randint.assert_called_once_with(1, 20)

    def test_player_does_not_have_skill_but_in_map(self):
        # Player object's `skills` list: ["investigation", "perception", "arcana"]
        # "history" is in SKILL_ABILITY_MAP but not in player's `self.skills`
        # The current `use_skill` implementation doesn't check `self.skills`.
        # It only checks if the skill is in SKILL_ABILITY_MAP and if proficient in self.proficiencies.
        # This test is more about documenting current behavior.
        with patch('random.randint', return_value=12) as mock_rand:
            result = self.player.use_skill("history") # History uses Intelligence (16 -> +3)
                                                     # Player is NOT proficient in History

            expected_d20_roll = 12
            expected_ability_modifier = (16 - 10) // 2  # +3
            expected_proficiency_bonus = 0 # Not proficient
            expected_total_roll = expected_d20_roll + expected_ability_modifier + expected_proficiency_bonus

            self.assertEqual(result["skill"], "history")
            self.assertEqual(result["d20_roll"], expected_d20_roll)
            self.assertEqual(result["ability_key"], "intelligence")
            self.assertEqual(result["ability_score"], 16)
            self.assertEqual(result["ability_modifier"], expected_ability_modifier)
            self.assertFalse(result["is_proficient"]) # Not in self.player_data["proficiencies"]["skills"]
            self.assertEqual(result["applied_proficiency_bonus"], expected_proficiency_bonus)
            self.assertEqual(result["total_roll"], expected_total_roll)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
