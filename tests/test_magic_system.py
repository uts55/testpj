import unittest
from unittest.mock import patch

# Assuming the project structure allows these imports directly
# If 'PYTHONPATH' issues arise in a real environment, this might need adjustment
# e.g. by adding '..' to sys.path or using a test runner that handles it.
import sys
import os
# Add project root to sys.path to allow direct imports of game modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_state import Player, Character
from magic import Spell, SPELLBOOK # SPELLBOOK should be populated on import
# from utils import roll_dice # We will mock this, so direct import not strictly needed for tests using mock

class TestMagicSystem(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures for each test method."""
        self.player_data = {
            "id": "player_test_id", "name": "TestHero", "max_hp": 50,
            "combat_stats": {'armor_class': 10, 'attack_bonus': 0, 'damage_bonus': 0, 'initiative_bonus': 0},
            "base_damage_dice": "1d4", # For Character base class
            "ability_scores": {"wisdom": 14, "intelligence": 10}, # WIS +2, INT +0
            "spell_slots": {
                "level_1": {"current": 2, "maximum": 2}
            },
            # Ensure skills and proficiencies are present, even if empty, as Player constructor might expect them
            "skills": [],
            "proficiencies": {"skills": []}
        }
        self.player = Player(self.player_data)
        # Make sure player starts with full HP for consistent testing
        self.player.current_hp = self.player.max_hp

        self.target_dummy = Character(id="dummy", name="Dummy", max_hp=50, combat_stats={}, base_damage_dice="1d4")
        self.target_dummy.current_hp = self.target_dummy.max_hp

        # Ensure SPELLBOOK is populated (it should be by importing magic)
        # For robustness, could add a check here, but typically not needed if magic.py is correct.
        if "Cure Light Wounds" not in SPELLBOOK or "Fire Bolt" not in SPELLBOOK:
            # This indicates an issue with magic.py or test setup, but let's log if it happens.
            # In a real CI, this might fail the test run earlier.
            print("Warning: SPELLBOOK might not be correctly populated before tests.")
            # Potentially add them manually if really needed for isolated testing,
            # but it's better if the module handles its state.
            # SPELLBOOK["Cure Light Wounds"] = Spell(...)
            # SPELLBOOK["Fire Bolt"] = Spell(...)


    def test_player_initial_spell_slots(self):
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 2)

    def test_has_spell_slot(self):
        self.assertTrue(self.player.has_spell_slot(1))
        self.assertFalse(self.player.has_spell_slot(2)) # Level 2 slots not defined in setUp

    def test_consume_spell_slot(self):
        self.assertTrue(self.player.consume_spell_slot(1), "First consumption should succeed.")
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 1, "Slot count should be 1 after first consumption.")

        self.assertTrue(self.player.consume_spell_slot(1), "Second consumption should succeed.")
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 0, "Slot count should be 0 after second consumption.")

        self.assertFalse(self.player.consume_spell_slot(1), "Third consumption should fail (no slots left).")
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 0, "Slot count should still be 0.")

        self.assertFalse(self.player.consume_spell_slot(2), "Consumption of undefined level 2 slot should fail.")

    def test_cast_spell_no_slots(self):
        # Consume all level 1 slots first
        self.player.consume_spell_slot(1)
        self.player.consume_spell_slot(1)

        success, message = self.player.cast_spell("Cure Light Wounds", target=self.player)
        self.assertFalse(success)
        self.assertIn("no level 1 spell slots available", message.lower())

    def test_cast_spell_unknown_spell(self):
        success, message = self.player.cast_spell("Unknown Spell", target=self.player)
        self.assertFalse(success)
        self.assertIn("spell 'unknown spell' not found", message.lower())

    @patch('utils.roll_dice')
    def test_cast_spell_cure_light_wounds_on_self(self, mock_roll_dice):
        mock_roll_dice.return_value = 3 # 1d4 roll

        self.player.take_damage(10) # Player HP is 50, so current_hp becomes 40
        hp_after_damage = self.player.current_hp
        self.assertEqual(hp_after_damage, 40)

        success, message = self.player.cast_spell("Cure Light Wounds", target=self.player)

        self.assertTrue(success, f"Casting failed: {message}")

        # Expected healing: 3 (dice) + 2 (Wisdom mod from 14 WIS) = 5
        expected_hp = min(self.player.max_hp, hp_after_damage + 5)
        self.assertEqual(self.player.current_hp, expected_hp)

        self.assertIn(f"casts 'cure light wounds' on {self.player.name.lower()}", message.lower())
        self.assertIn("healed 5 hp", message.lower())
        # Check for dice roll and modifier in the message. Regex might be more robust.
        self.assertIn("1d4(3)", message) # Exact dice roll
        self.assertIn("wis(2)", message.lower()) # Wisdom modifier
        self.assertIn("= 5", message) # Total effect

        # Assuming this was one of the two slots
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 1)

    @patch('utils.roll_dice')
    def test_cast_spell_fire_bolt_on_target(self, mock_roll_dice):
        mock_roll_dice.return_value = 4 # 1d6 roll

        initial_target_hp = self.target_dummy.current_hp # Should be 50

        success, message = self.player.cast_spell("Fire Bolt", target=self.target_dummy)
        self.assertTrue(success, f"Casting failed: {message}")

        # Expected damage: 4 (dice) + 0 (Fire Bolt has no stat_modifier_ability in SPELLBOOK setup) = 4
        expected_hp_after_damage = initial_target_hp - 4
        self.assertEqual(self.target_dummy.current_hp, expected_hp_after_damage)

        self.assertIn(f"casts 'fire bolt' on {self.target_dummy.name.lower()}", message.lower())
        self.assertIn("dealt 4 fire_bolt damage", message.lower()) # Spell name slugified as damage type
        self.assertIn("1d6(4)", message) # Exact dice roll
        self.assertIn("= 4", message) # Total effect, no modifier string part for this spell

        # Check slot consumption (Fire Bolt is level 1 as per magic.py setup)
        self.assertEqual(self.player.spell_slots["level_1"]["current"], 1) # Started with 2, one used by this spell

    def test_cast_spell_requires_target_missing(self):
        # Fire Bolt requires a target, but it's not "self" target type.
        # The cast_spell method checks if target is None AND spell.target_type is not "self".
        success, message = self.player.cast_spell("Fire Bolt") # No target provided
        self.assertFalse(success)
        self.assertIn("requires a target", message.lower())

    @patch('utils.roll_dice')
    def test_cast_spell_target_invalid_type(self, mock_roll_dice):
        mock_roll_dice.return_value = 3 # Arbitrary roll
        # Test with a non-Character target
        not_a_character = {"name": "NotACharacter"}
        success, message = self.player.cast_spell("Fire Bolt", target=not_a_character)
        self.assertFalse(success)
        self.assertIn("invalid target type", message.lower())

    @patch('utils.roll_dice')
    def test_cast_spell_dice_parsing_errors(self, mock_roll_dice):
        # Temporarily add a spell with bad dice expression to SPELLBOOK for this test
        original_spellbook_copy = SPELLBOOK.copy() # Shallow copy is enough if Spell objects are not modified
        SPELLBOOK["Bad Dice Spell"] = Spell("Bad Dice Spell", 1, "1 action", "30 feet", "enemy", "damage", "1dNaN", None)

        success, message = self.player.cast_spell("Bad Dice Spell", target=self.target_dummy)
        self.assertFalse(success)
        self.assertIn("invalid dice expression", message.lower())

        # Restore SPELLBOOK
        SPELLBOOK.clear()
        SPELLBOOK.update(original_spellbook_copy)


if __name__ == '__main__':
    unittest.main()
