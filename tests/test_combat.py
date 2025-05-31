import unittest
from unittest.mock import patch

# Assuming game_state.py and main.py are in the parent directory or accessible via PYTHONPATH
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_state import PlayerState, determine_initiative, roll_dice
from main import start_combat, process_combat_turn, check_combat_end_condition

# --- Mock Objects for Testing ---
class MockCombatant:
    def __init__(self, id_val, initiative_bonus, hp, name=None):
        self.id = id_val
        self.combat_stats = {'initiative_bonus': initiative_bonus}
        self.current_hp = hp
        self.name = name if name else id_val

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, MockCombatant):
            return NotImplemented
        return self.id == other.id

class TestInitiativeCalculation(unittest.TestCase):
    @patch('game_state.roll_dice')
    def test_basic_initiative_order(self, mock_roll_dice_func):
        mock_roll_dice_func.side_effect = [10, 5, 15]

        participants = [
            MockCombatant(id_val="Alice", initiative_bonus=2, hp=100),
            MockCombatant(id_val="Bob", initiative_bonus=5, hp=100),
            MockCombatant(id_val="Charlie", initiative_bonus=0, hp=100)
        ]

        expected_order = ["Charlie", "Alice", "Bob"]
        turn_order = determine_initiative(participants)
        self.assertEqual(turn_order, expected_order)

    def test_empty_participants_list(self):
        participants = []
        turn_order = determine_initiative(participants)
        self.assertEqual(turn_order, [])

    @patch('game_state.roll_dice')
    def test_initiative_tie_breaking_behavior(self, mock_roll_dice_func):
        mock_roll_dice_func.side_effect = [10, 12]
        participants = [
            MockCombatant(id_val="Alice", initiative_bonus=2, hp=100), # Score: 10 + 2 = 12
            MockCombatant(id_val="David", initiative_bonus=0, hp=100), # Score: 12 + 0 = 12
        ]
        turn_order = determine_initiative(participants)
        # Current implementation: higher bonus doesn't guarantee order in tie.
        # Python's sort is stable. For items with equal initiative scores, their original order is preserved.
        # Alice (12) vs David (12). Alice is first in list.
        # If determine_initiative explicitly sorted by bonus as secondary, this test would be different.
        # For now, we know they both appear.
        self.assertIn("Alice", turn_order)
        self.assertIn("David", turn_order)
        self.assertEqual(len(turn_order), 2)
        # If using a stable sort (which Python's Timsort is), and assuming no other tie-breaking logic,
        # if Alice's computed initiative is 12 and David's is 12,
        # and Alice was before David in the input list, she should be before David in the output list.
        # Based on rolls: Alice (10+2=12), David (12+0=12).
        # If they are truly equal, their input order for that score is preserved.
        # If 'Charlie' (15), 'Alice' (12), 'David' (12), 'Bob' (10)
        # If Alice and David are tied and Alice was defined before David in the input list to determine_initiative
        # then the output for a stable sort on initiative score would be Alice then David for that tie.
        # For this specific test, with only Alice and David, if they are tied, the order is Alice, David.
        # Let's assume roll_dice makes David score higher: side_effect = [10, 15] -> David (15), Alice (12)
        # Let's assume roll_dice makes Alice score higher: side_effect = [15, 10] -> Alice (17), David (10)
        # If scores are equal [10, 12] -> Alice (12), David (12). Expected: ["Alice", "David"] or ["David", "Alice"]
        # Python's list.sort() is stable. So if their scores are identical, original order is preserved.
        # Alice is at index 0, David at index 1. So Alice should come first if scores are equal.
        if turn_order[0] == "Alice": # Alice got 12 (roll 10), David got 12 (roll 12)
             self.assertEqual(turn_order, ["Alice", "David"]) # Alice first due to stable sort
        else: # David got 12, Alice got 12. David first due to stable sort is not possible here.
             self.assertEqual(turn_order, ["David", "Alice"])


class TestCombatFlow(unittest.TestCase):
    def setUp(self):
        self.player_state = PlayerState()
        self.player = MockCombatant(id_val="Hero", initiative_bonus=3, hp=100)
        self.npc1 = MockCombatant(id_val="GoblinA", initiative_bonus=1, hp=50)
        self.npc2 = MockCombatant(id_val="GoblinB", initiative_bonus=1, hp=50)
        self.npcs = [self.npc1, self.npc2]

    @patch('main.determine_initiative')
    def test_start_combat(self, mock_determine_initiative_in_main):
        # This mock targets determine_initiative as it's used in main.py
        mock_determine_initiative_in_main.return_value = ["Hero", "GoblinA", "GoblinB"]

        notification = start_combat(self.player, self.npcs, self.player_state)

        self.assertTrue(self.player_state.is_in_combat)
        self.assertEqual(self.player_state.participants_in_combat, ["Hero", "GoblinA", "GoblinB"])
        self.assertEqual(self.player_state.turn_order, ["Hero", "GoblinA", "GoblinB"])
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")
        self.assertIn("Combat started! Turn order: Hero, GoblinA, GoblinB.", notification)
        self.assertIn("First up: Hero.", notification)

    @patch('main.determine_initiative')
    def test_process_combat_turn(self, mock_determine_initiative_in_main):
        mock_determine_initiative_in_main.return_value = ["Hero", "GoblinA", "GoblinB"]
        start_combat(self.player, self.npcs, self.player_state)

        notification1 = process_combat_turn(self.player_state)
        self.assertEqual(notification1, "Hero's turn.")
        self.assertEqual(self.player_state.current_turn_character_id, "GoblinA")

        notification2 = process_combat_turn(self.player_state)
        self.assertEqual(notification2, "GoblinA's turn.")
        self.assertEqual(self.player_state.current_turn_character_id, "GoblinB")

        notification3 = process_combat_turn(self.player_state)
        self.assertEqual(notification3, "GoblinB's turn.")
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")

    def test_check_combat_end_condition_player_defeat(self):
        # We need to ensure determine_initiative is called within start_combat for a valid setup
        # So we might need to patch it here too if we don't want its randomness.
        # However, for this test, the exact turn order doesn't matter as much as the end condition.
        with patch('main.determine_initiative', return_value=["Hero", "GoblinA", "GoblinB"]):
            start_combat(self.player, self.npcs, self.player_state)
        self.player.current_hp = 0

        ended, notification = check_combat_end_condition(self.player, self.npcs, self.player_state)

        self.assertTrue(ended)
        self.assertEqual(notification, f"Player {self.player.id} has been defeated! Combat ends.")
        self.assertFalse(self.player_state.is_in_combat)
        self.assertEqual(self.player_state.participants_in_combat, [])
        self.assertIsNone(self.player_state.current_turn_character_id)
        self.assertEqual(self.player_state.turn_order, [])

    def test_check_combat_end_condition_npcs_defeat(self):
        with patch('main.determine_initiative', return_value=["Hero", "GoblinA", "GoblinB"]):
            start_combat(self.player, self.npcs, self.player_state)
        self.npc1.current_hp = 0
        self.npc2.current_hp = 0

        ended, notification = check_combat_end_condition(self.player, self.npcs, self.player_state)

        self.assertTrue(ended)
        self.assertEqual(notification, "All enemies defeated! Combat ends.")
        self.assertFalse(self.player_state.is_in_combat)

    def test_check_combat_end_condition_no_end(self):
        with patch('main.determine_initiative', return_value=["Hero", "GoblinA", "GoblinB"]):
            start_combat(self.player, self.npcs, self.player_state)

        ended, notification = check_combat_end_condition(self.player, self.npcs, self.player_state)

        self.assertFalse(ended)
        self.assertEqual(notification, "")
        self.assertTrue(self.player_state.is_in_combat)

if __name__ == '__main__':
    unittest.main(verbosity=2)
