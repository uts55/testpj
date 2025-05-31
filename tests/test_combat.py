import unittest
from unittest.mock import patch

# Assuming game_state.py and main.py are in the parent directory or accessible via PYTHONPATH
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_state import PlayerState, determine_initiative, roll_dice, Player, NPC, Character
from main import start_combat, process_combat_turn, check_combat_end_condition


class TestInitiativeCalculation(unittest.TestCase):
    @patch('game_state.roll_dice')
    def test_basic_initiative_order(self, mock_roll_dice_func):
        mock_roll_dice_func.side_effect = [10, 5, 15] # Charlie (15), Alice (10), Bob (5)

        participants = [
            NPC(id="Alice", name="Alice", max_hp=100, combat_stats={'initiative_bonus': 2}, base_damage_dice="1d4"), # Roll 10 -> 12
            NPC(id="Bob", name="Bob", max_hp=100, combat_stats={'initiative_bonus': 5}, base_damage_dice="1d4"),       # Roll 5  -> 10
            NPC(id="Charlie", name="Charlie", max_hp=100, combat_stats={'initiative_bonus': 0}, base_damage_dice="1d4") # Roll 15 -> 15
        ]
        # Expected order: Charlie (15), Alice (12), Bob (10)
        expected_order_ids = ["Charlie", "Alice", "Bob"]
        turn_order_ids = determine_initiative(participants)
        self.assertEqual(turn_order_ids, expected_order_ids)

    def test_empty_participants_list(self):
        participants = []
        turn_order = determine_initiative(participants)
        self.assertEqual(turn_order, [])

    @patch('game_state.roll_dice')
    def test_initiative_tie_breaking_behavior(self, mock_roll_dice_func):
        # Alice rolls 10 (total 12), David rolls 12 (total 12)
        mock_roll_dice_func.side_effect = [10, 12]
        participants = [
            NPC(id="Alice", name="Alice", max_hp=100, combat_stats={'initiative_bonus': 2}, base_damage_dice="1d4"),
            NPC(id="David", name="David", max_hp=100, combat_stats={'initiative_bonus': 0}, base_damage_dice="1d4"),
        ]
        turn_order_ids = determine_initiative(participants)
        # Python's sort is stable. If scores are equal, original order is preserved.
        # Alice (10+2=12), David (12+0=12). Alice is first in list.
        self.assertEqual(turn_order_ids, ["Alice", "David"])


class TestCombatFlow(unittest.TestCase):
    def setUp(self):
        self.player = Player(id="Hero", name="Hero", max_hp=100,
                             combat_stats={'initiative_bonus': 3, 'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2},
                             base_damage_dice="1d8")
        self.npc1 = NPC(id="GoblinA", name="GoblinA", max_hp=50,
                        combat_stats={'initiative_bonus': 1, 'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1},
                        base_damage_dice="1d6")
        self.npc2 = NPC(id="GoblinB", name="GoblinB", max_hp=50,
                        combat_stats={'initiative_bonus': 1, 'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1},
                        base_damage_dice="1d6")
        self.npcs = [self.npc1, self.npc2]
        self.player_state = PlayerState(player_character=self.player)

    @patch('main.determine_initiative') # Patches determine_initiative as used within main.py's start_combat
    def test_start_combat(self, mock_determine_initiative_in_main):
        mock_determine_initiative_in_main.return_value = ["Hero", "GoblinA", "GoblinB"]

        initial_participants_obj_list = [self.player] + self.npcs
        notification = start_combat(self.player, self.npcs, self.player_state)

        self.assertTrue(self.player_state.is_in_combat)
        # Check if actual objects are stored
        self.assertEqual(len(self.player_state.participants_in_combat), 3)
        self.assertIn(self.player, self.player_state.participants_in_combat)
        self.assertIn(self.npc1, self.player_state.participants_in_combat)
        self.assertIn(self.npc2, self.player_state.participants_in_combat)

        self.assertEqual(self.player_state.turn_order, ["Hero", "GoblinA", "GoblinB"])
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")
        self.assertIn("Combat started! Turn order: Hero, GoblinA, GoblinB.", notification)
        self.assertIn("First up: Hero (Hero).", notification)


    @patch('main.determine_initiative')
    @patch('game_state.roll_dice') # For NPC attacks
    def test_process_combat_turn_player_and_npc(self, mock_roll_dice_gs, mock_determine_initiative_main):
        mock_determine_initiative_main.return_value = ["Hero", "GoblinA"] # Simplified for this test
        self.npcs = [self.npc1] # Only one NPC for simpler turn progression
        start_combat(self.player, self.npcs, self.player_state)

        # Player's turn - pass
        player_action = "pass"
        notification1 = process_combat_turn(self.player_state, player_action)
        self.assertIn("Hero passes their turn.", notification1)
        self.assertIn("Next up: GoblinA.", notification1)
        self.assertEqual(self.player_state.current_turn_character_id, "GoblinA")

        # NPC's turn (GoblinA attacks Hero)
        # Mock NPC's attack roll (hit) and damage roll
        # Attack: roll_dice(20) -> 15 (hit: 15+3 > 15 AC)
        # Damage: roll_dice(6,1) -> 4 (damage: 4+1 = 5)
        mock_roll_dice_gs.side_effect = [15, 4]
        initial_player_hp = self.player.current_hp

        notification2 = process_combat_turn(self.player_state, "") # player_action is empty for NPC
        self.assertIn("GoblinA attacks Hero.", notification2)
        self.assertIn("HIT!", notification2)
        self.assertIn("Deals 1d6(4) + DMG Bonus(1) = 5 damage.", notification2)
        self.assertEqual(self.player.current_hp, initial_player_hp - 5)
        self.assertIn(f"Hero HP: {self.player.current_hp}/{self.player.max_hp}", notification2)
        self.assertIn("Next up: Hero.", notification2) # Assuming turn wraps around
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")


    def test_check_combat_end_condition_player_defeat(self):
        with patch('main.determine_initiative', return_value=[self.player.id, self.npc1.id]):
             start_combat(self.player, [self.npc1], self.player_state)

        self.player.take_damage(self.player.max_hp * 2) # Ensure player is defeated
        self.assertTrue(not self.player.is_alive())

        ended, notification = check_combat_end_condition(self.player, [self.npc1], self.player_state)

        self.assertTrue(ended)
        self.assertIn(f"Player {self.player.name} ({self.player.id}) has been defeated! Combat ends.", notification)
        self.assertFalse(self.player_state.is_in_combat)
        self.assertEqual(self.player_state.participants_in_combat, [])
        self.assertIsNone(self.player_state.current_turn_character_id)
        self.assertEqual(self.player_state.turn_order, [])

    def test_check_combat_end_condition_npcs_defeat(self):
        with patch('main.determine_initiative', return_value=[self.player.id, self.npc1.id, self.npc2.id]):
            start_combat(self.player, self.npcs, self.player_state)

        self.npc1.take_damage(self.npc1.max_hp * 2)
        self.npc2.take_damage(self.npc2.max_hp * 2)
        self.assertTrue(not self.npc1.is_alive())
        self.assertTrue(not self.npc2.is_alive())

        ended, notification = check_combat_end_condition(self.player, self.npcs, self.player_state)

        self.assertTrue(ended)
        self.assertIn(f"All NPCs ({self.npc1.name}, {self.npc2.name}) defeated! Combat ends.", notification)
        self.assertFalse(self.player_state.is_in_combat)

    def test_check_combat_end_condition_no_end(self):
        with patch('main.determine_initiative', return_value=[self.player.id] + [n.id for n in self.npcs]):
            start_combat(self.player, self.npcs, self.player_state)

        ended, notification = check_combat_end_condition(self.player, self.npcs, self.player_state)

        self.assertFalse(ended)
        self.assertEqual(notification, "")
        self.assertTrue(self.player_state.is_in_combat)


class TestAttackMethod(unittest.TestCase):
    def setUp(self):
        self.player_attacker = Player(
            id="P1", name="Hero", max_hp=50,
            combat_stats={'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2, 'initiative_bonus': 0},
            base_damage_dice="1d6"
            # equipment={'weapon': {'name': 'Epic Sword', 'damage_dice': '1d100'}} # Player attack currently uses base_damage_dice
        )
        self.npc_target = NPC(
            id="N1", name="Goblin", max_hp=30,
            combat_stats={'armor_class': 13, 'attack_bonus': 3, 'damage_bonus': 1, 'initiative_bonus': 0},
            base_damage_dice="1d4"
        )
        self.npc_attacker = NPC(
            id="N2", name="Orc", max_hp=60,
            combat_stats={'armor_class': 14, 'attack_bonus': 4, 'damage_bonus': 3, 'initiative_bonus': 0},
            base_damage_dice="1d10"
        )

    @patch('game_state.roll_dice')
    def test_player_attack_hits_uses_base_damage_dice(self, mock_roll_dice):
        # Attack roll: 15 (total 15 + 5 = 20 vs AC 13 -> HIT)
        # Damage roll (1d6 for player's base_damage_dice): 4
        mock_roll_dice.side_effect = [15, 4]

        initial_target_hp = self.npc_target.current_hp
        expected_damage = 4 (roll) + self.player_attacker.combat_stats['damage_bonus'] # 4 + 2 = 6

        result_message = self.player_attacker.attack(self.npc_target)

        self.assertIn("Hero attacks Goblin.", result_message)
        self.assertIn("d20(15) + ATK Bonus(5) = 20 vs AC(13). HIT!", result_message)
        self.assertIn(f"Deals 1d6(4) + DMG Bonus(2) = {expected_damage} damage.", result_message)
        self.assertEqual(self.npc_target.current_hp, initial_target_hp - expected_damage)
        self.assertIn(f"Goblin HP: {self.npc_target.current_hp}/{self.npc_target.max_hp}", result_message)

    @patch('game_state.roll_dice')
    def test_attack_misses(self, mock_roll_dice):
        # Attack roll: 5 (total 5 + 5 = 10 vs AC 13 -> MISS)
        mock_roll_dice.return_value = 5

        initial_target_hp = self.npc_target.current_hp
        result_message = self.player_attacker.attack(self.npc_target)

        self.assertIn("Hero attacks Goblin.", result_message)
        self.assertIn("d20(5) + ATK Bonus(5) = 10 vs AC(13). MISS!", result_message)
        self.assertEqual(self.npc_target.current_hp, initial_target_hp) # HP unchanged

    @patch('game_state.roll_dice')
    def test_npc_attack_hits(self, mock_roll_dice):
        # NPC (Orc) attacks Player (Hero)
        # Attack roll: 16 (total 16 + 4 = 20 vs AC 15 -> HIT)
        # Damage roll (1d10 for Orc's base_damage_dice): 7
        mock_roll_dice.side_effect = [16, 7]

        initial_player_hp = self.player_attacker.current_hp # Target is player_attacker here
        expected_damage = 7 (roll) + self.npc_attacker.combat_stats['damage_bonus'] # 7 + 3 = 10

        result_message = self.npc_attacker.attack(self.player_attacker)

        self.assertIn("Orc attacks Hero.", result_message)
        self.assertIn("d20(16) + ATK Bonus(4) = 20 vs AC(15). HIT!", result_message)
        self.assertIn(f"Deals 1d10(7) + DMG Bonus(3) = {expected_damage} damage.", result_message)
        self.assertEqual(self.player_attacker.current_hp, initial_player_hp - expected_damage)
        self.assertIn(f"Hero HP: {self.player_attacker.current_hp}/{self.player_attacker.max_hp}", result_message)

    @patch('game_state.roll_dice')
    def test_attack_damage_parsing_XdY(self, mock_roll_dice):
        self.npc_attacker.base_damage_dice = "2d6"
        # Attack roll: 18 (HIT)
        # Damage rolls (2d6): 3, 5
        mock_roll_dice.side_effect = [18, 3, 5]

        initial_player_hp = self.player_attacker.current_hp
        damage_roll_sum = 3 + 5
        expected_damage = damage_roll_sum + self.npc_attacker.combat_stats['damage_bonus'] # 8 + 3 = 11

        result_message = self.npc_attacker.attack(self.player_attacker)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 2d6({damage_roll_sum}) + DMG Bonus(3) = {expected_damage} damage.", result_message)
        self.assertEqual(self.player_attacker.current_hp, initial_player_hp - expected_damage)

    @patch('game_state.roll_dice')
    def test_attack_damage_parsing_dY_format(self, mock_roll_dice):
        self.npc_attacker.base_damage_dice = "d8" # Should be treated as 1d8
        # Attack roll: 17 (HIT)
        # Damage roll (1d8): 6
        mock_roll_dice.side_effect = [17, 6]

        initial_player_hp = self.player_attacker.current_hp
        expected_damage = 6 + self.npc_attacker.combat_stats['damage_bonus'] # 6 + 3 = 9

        result_message = self.npc_attacker.attack(self.player_attacker)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 1d8(6) + DMG Bonus(3) = {expected_damage} damage.", result_message) # Verifies "1d8"
        self.assertEqual(self.player_attacker.current_hp, initial_player_hp - expected_damage)

    @patch('game_state.roll_dice')
    def test_attack_target_defeated(self, mock_roll_dice):
        self.npc_target.current_hp = 5 # Target has low HP
        # Attack roll: 20 (HIT)
        # Damage roll (1d6 for player): 6
        mock_roll_dice.side_effect = [20, 6]

        expected_damage = 6 + self.player_attacker.combat_stats['damage_bonus'] # 6 + 2 = 8

        result_message = self.player_attacker.attack(self.npc_target)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 1d6(6) + DMG Bonus(2) = {expected_damage} damage.", result_message)
        self.assertEqual(self.npc_target.current_hp, 0) # HP should be 0
        self.assertFalse(self.npc_target.is_alive())
        self.assertIn(f"{self.npc_target.name} HP: 0/{self.npc_target.max_hp}.", result_message)
        self.assertIn(f"{self.npc_target.name} has been defeated!", result_message)

    def test_attack_invalid_dice_format_raises_error(self):
        self.player_attacker.base_damage_dice = "invalid_dice"
        with self.assertRaisesRegex(ValueError, "Invalid base_damage_dice format for Hero: 'invalid_dice'. Expected XdY or dY"):
            self.player_attacker.attack(self.npc_target)

        self.player_attacker.base_damage_dice = "1d" # Missing sides
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '1d' for Hero: invalid literal for int\(\) with base 10: ''"):
             self.player_attacker.attack(self.npc_target)

        self.player_attacker.base_damage_dice = "d" # Missing sides
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice 'd' for Hero: invalid literal for int\(\) with base 10: ''"):
             self.player_attacker.attack(self.npc_target)

        self.player_attacker.base_damage_dice = "0d6" # Zero dice
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '0d6' for Hero: Number of dice and sides must be positive. Got: 0d6"):
             self.player_attacker.attack(self.npc_target)

        self.player_attacker.base_damage_dice = "1d0" # Zero sides
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '1d0' for Hero: Number of dice and sides must be positive. Got: 1d0"):
             self.player_attacker.attack(self.npc_target)


if __name__ == '__main__':
    unittest.main(verbosity=2)
