import unittest
from unittest.mock import patch

# Assuming game_state.py and main.py are in the parent directory or accessible via PYTHONPATH
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game_state import PlayerState, determine_initiative, roll_dice, Player, NPC, Character, ITEM_DATABASE # Added ITEM_DATABASE
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
                             base_damage_dice="1d8", equipment_data=None) # Added equipment_data
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
        self.player_attacker_unarmed = Player(
            id="P_Unarmed", name="Unarmed Hero", max_hp=50,
            combat_stats={'armor_class': 10, 'attack_bonus': 2, 'damage_bonus': 1, 'initiative_bonus': 0}, # Base AC 10
            base_damage_dice="1d4", # Fallback, but get_equipped_weapon_stats should override
            equipment_data=None # No equipment
        )
        self.player_attacker_sword = Player(
            id="P_Sword", name="Sword Hero", max_hp=50,
            combat_stats={'armor_class': 10, 'attack_bonus': 2, 'damage_bonus': 1, 'initiative_bonus': 0}, # Base AC 10
            base_damage_dice="1d4",
            equipment_data={"weapon": "short_sword"} # Equip short_sword (1d6, +1 ATK, +0 DMG)
        )
        self.player_attacker_longsword_armor_shield = Player(
            id="P_FullGear", name="Geared Hero", max_hp=60,
            combat_stats={'armor_class': 10, 'attack_bonus': 3, 'damage_bonus': 2, 'initiative_bonus': 1}, # Base AC 10
            base_damage_dice="1d4",
            equipment_data={
                "weapon": "long_sword",      # 1d8, +1 ATK, +1 DMG
                "armor": "leather_armor",   # +2 AC
                "shield": "wooden_shield"   # +1 AC
            }
        )
        self.npc_target = NPC(
            id="N1", name="Goblin", max_hp=30,
            combat_stats={'armor_class': 13, 'attack_bonus': 3, 'damage_bonus': 1, 'initiative_bonus': 0},
            base_damage_dice="1d4"
        )
        self.npc_attacker = NPC( # Used for attacking players
            id="N2", name="Orc", max_hp=60,
            combat_stats={'armor_class': 14, 'attack_bonus': 4, 'damage_bonus': 3, 'initiative_bonus': 0},
            base_damage_dice="1d10" # Orc uses a 1d10 weapon
        )

    @patch('game_state.roll_dice')
    def test_player_attack_unarmed(self, mock_roll_dice):
        # Unarmed Hero attacks Goblin. Base ATK Bonus: 2, Base DMG Bonus: 1. Unarmed: 1d4, +0 ATK, +0 DMG
        # Total ATK Bonus: 2+0=2. Total DMG Bonus: 1+0=1.
        # Attack roll: 15 (total 15 + 2 = 17 vs AC 13 -> HIT)
        # Damage roll (1d4 for unarmed): 3
        mock_roll_dice.side_effect = [15, 3]

        initial_target_hp = self.npc_target.current_hp
        # Expected damage: 3 (roll) + 1 (player base) + 0 (unarmed) = 4
        expected_damage = 3 + self.player_attacker_unarmed.combat_stats['damage_bonus'] + 0

        result_message = self.player_attacker_unarmed.attack(self.npc_target)

        self.assertIn("Unarmed Hero attacks Goblin.", result_message)
        self.assertIn(f"d20(15) + ATK Bonus(2) = 17 vs AC({self.npc_target.combat_stats['armor_class']}). HIT!", result_message)
        self.assertIn(f"Deals 1d4(3) + DMG Bonus(1) = {expected_damage} damage.", result_message)
        self.assertEqual(self.npc_target.current_hp, initial_target_hp - expected_damage)

    @patch('game_state.roll_dice')
    def test_player_attack_with_weapon_short_sword(self, mock_roll_dice):
        # Sword Hero (Short Sword: 1d6, +1 ATK, +0 DMG) attacks Goblin.
        # Player Base ATK Bonus: 2, Base DMG Bonus: 1.
        # Effective ATK Bonus: 2 (base) + 1 (sword) = 3.
        # Effective DMG Bonus: 1 (base) + 0 (sword) = 1.
        # Attack roll: 15 (total 15 + 3 = 18 vs AC 13 -> HIT)
        # Damage roll (1d6 for short_sword): 4
        mock_roll_dice.side_effect = [15, 4]

        initial_target_hp = self.npc_target.current_hp
        # Expected damage: 4 (roll) + 1 (player base) + 0 (sword) = 5
        expected_damage = 4 + self.player_attacker_sword.combat_stats['damage_bonus'] + ITEM_DATABASE["short_sword"]["damage_bonus"]

        # Calculate effective bonuses for the message
        effective_atk_bonus = self.player_attacker_sword.combat_stats['attack_bonus'] + ITEM_DATABASE["short_sword"]["attack_bonus"]
        effective_dmg_bonus = self.player_attacker_sword.combat_stats['damage_bonus'] + ITEM_DATABASE["short_sword"]["damage_bonus"]

        result_message = self.player_attacker_sword.attack(self.npc_target)

        self.assertIn("Sword Hero attacks Goblin.", result_message)
        self.assertIn(f"d20(15) + ATK Bonus({effective_atk_bonus}) = 18 vs AC({self.npc_target.combat_stats['armor_class']}). HIT!", result_message)
        self.assertIn(f"Deals 1d6(4) + DMG Bonus({effective_dmg_bonus}) = {expected_damage} damage.", result_message)
        self.assertEqual(self.npc_target.current_hp, initial_target_hp - expected_damage)
        self.assertIn(f"Goblin HP: {self.npc_target.current_hp}/{self.npc_target.max_hp}", result_message)

    def test_player_effective_ac_with_equipment(self):
        # P_FullGear: base AC 10. leather_armor (+2 AC), wooden_shield (+1 AC)
        # Expected AC = 10 + 2 + 1 = 13
        expected_ac = self.player_attacker_longsword_armor_shield.base_armor_class + \
                      ITEM_DATABASE["leather_armor"]["ac_bonus"] + \
                      ITEM_DATABASE["wooden_shield"]["ac_bonus"]
        self.assertEqual(self.player_attacker_longsword_armor_shield.get_effective_armor_class(), expected_ac)

        # Test unarmed player AC (no equipment)
        # P_Unarmed: base AC 10. No armor/shield.
        self.assertEqual(self.player_attacker_unarmed.get_effective_armor_class(), self.player_attacker_unarmed.base_armor_class)

    @patch('game_state.roll_dice')
    def test_npc_attack_player_with_equipment(self, mock_roll_dice):
        # Orc (ATK Bonus 4) attacks Geared Hero (AC 13 from base 10 + leather + shield)
        # Attack roll: 10 (total 10 + 4 = 14 vs AC 13 -> HIT)
        # Damage roll (1d10 for Orc): 7
        mock_roll_dice.side_effect = [10, 7]

        target_player = self.player_attacker_longsword_armor_shield
        initial_player_hp = target_player.current_hp
        expected_ac = target_player.get_effective_armor_class() # Should be 13

        # Orc's damage: 7 (roll) + 3 (Orc's damage_bonus) = 10
        expected_damage = 7 + self.npc_attacker.combat_stats['damage_bonus']

        result_message = self.npc_attacker.attack(target_player)

        self.assertIn(f"Orc attacks Geared Hero.", result_message)
        self.assertIn(f"d20(10) + ATK Bonus({self.npc_attacker.combat_stats['attack_bonus']}) = 14 vs AC({expected_ac}). HIT!", result_message)
        self.assertIn(f"Deals 1d10(7) + DMG Bonus({self.npc_attacker.combat_stats['damage_bonus']}) = {expected_damage} damage.", result_message)
        self.assertEqual(target_player.current_hp, initial_player_hp - expected_damage)
        self.assertIn(f"Geared Hero HP: {target_player.current_hp}/{target_player.max_hp}", result_message)

    @patch('game_state.roll_dice')
    def test_attack_misses_player_with_high_ac(self, mock_roll_dice):
        # Sword Hero (ATK Bonus 3) attacks Geared Hero (AC 13)
        # Sword Hero ATK Bonus: 2(base) + 1(short_sword) = 3
        # Attack roll: 5 (total 5 + 3 = 8 vs AC 13 -> MISS)
        mock_roll_dice.return_value = 5 # Only one roll needed for a miss

        target_player = self.player_attacker_longsword_armor_shield
        initial_target_hp = target_player.current_hp
        expected_ac = target_player.get_effective_armor_class()
        attacker_effective_atk_bonus = self.player_attacker_sword.combat_stats['attack_bonus'] + ITEM_DATABASE["short_sword"]["attack_bonus"]


        result_message = self.player_attacker_sword.attack(target_player)

        self.assertIn("Sword Hero attacks Geared Hero.", result_message)
        self.assertIn(f"d20(5) + ATK Bonus({attacker_effective_atk_bonus}) = 8 vs AC({expected_ac}). MISS!", result_message)
        self.assertEqual(target_player.current_hp, initial_target_hp) # HP unchanged


    @patch('game_state.roll_dice')
    def test_npc_attack_hits_unarmored_player(self, mock_roll_dice):
        # NPC (Orc) attacks Player (Unarmed Hero, AC 10)
        # Attack roll: 16 (total 16 + 4 = 20 vs AC 10 -> HIT)
        # Damage roll (1d10 for Orc's base_damage_dice): 7
        mock_roll_dice.side_effect = [16, 7]

        target_player = self.player_attacker_unarmed # Target is player_attacker_unarmed
        initial_player_hp = target_player.current_hp
        expected_ac = target_player.get_effective_armor_class() # Should be 10
        expected_damage = 7 + self.npc_attacker.combat_stats['damage_bonus'] # 7 + 3 = 10

        result_message = self.npc_attacker.attack(target_player)

        self.assertIn("Orc attacks Unarmed Hero.", result_message)
        self.assertIn(f"d20(16) + ATK Bonus(4) = 20 vs AC({expected_ac}). HIT!", result_message)
        self.assertIn(f"Deals 1d10(7) + DMG Bonus(3) = {expected_damage} damage.", result_message)
        self.assertEqual(target_player.current_hp, initial_player_hp - expected_damage)
        self.assertIn(f"Unarmed Hero HP: {target_player.current_hp}/{target_player.max_hp}", result_message)

    @patch('game_state.roll_dice')
    def test_attack_damage_parsing_XdY_npc_attacker(self, mock_roll_dice): # Renamed to be specific
        self.npc_attacker.base_damage_dice = "2d6"
        # Attack roll: 18 (HIT vs Unarmed Hero AC 10)
        # Damage rolls (2d6): 3, 5
        mock_roll_dice.side_effect = [18, 3, 5] # d20 roll, then two d6 rolls

        target_player = self.player_attacker_unarmed
        initial_player_hp = target_player.current_hp
        damage_roll_sum = 3 + 5
        expected_damage = damage_roll_sum + self.npc_attacker.combat_stats['damage_bonus'] # 8 + 3 = 11

        result_message = self.npc_attacker.attack(target_player)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 2d6({damage_roll_sum}) + DMG Bonus(3) = {expected_damage} damage.", result_message)
        self.assertEqual(target_player.current_hp, initial_player_hp - expected_damage)

    @patch('game_state.roll_dice')
    def test_attack_damage_parsing_dY_format_npc_attacker(self, mock_roll_dice): # Renamed
        self.npc_attacker.base_damage_dice = "d8" # Should be treated as 1d8
        # Attack roll: 17 (HIT vs Unarmed Hero AC 10)
        # Damage roll (1d8): 6
        mock_roll_dice.side_effect = [17, 6]

        target_player = self.player_attacker_unarmed
        initial_player_hp = target_player.current_hp
        expected_damage = 6 + self.npc_attacker.combat_stats['damage_bonus'] # 6 + 3 = 9

        result_message = self.npc_attacker.attack(target_player)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 1d8(6) + DMG Bonus(3) = {expected_damage} damage.", result_message) # Verifies "1d8"
        self.assertEqual(target_player.current_hp, initial_player_hp - expected_damage)

    @patch('game_state.roll_dice')
    def test_player_attack_target_defeated_with_weapon(self, mock_roll_dice): # Modified
        self.npc_target.current_hp = 5 # Target has low HP
        # Sword Hero attacks Goblin. ATK Bonus 3 (2 base + 1 sword). DMG Bonus 1 (1 base + 0 sword)
        # Attack roll: 20 (HIT)
        # Damage roll (1d6 for short_sword): 6
        mock_roll_dice.side_effect = [20, 6]

        attacker = self.player_attacker_sword
        effective_atk_bonus = attacker.combat_stats['attack_bonus'] + ITEM_DATABASE["short_sword"]["attack_bonus"]
        effective_dmg_bonus = attacker.combat_stats['damage_bonus'] + ITEM_DATABASE["short_sword"]["damage_bonus"]
        expected_damage = 6 + effective_dmg_bonus # 6 + 1 = 7

        result_message = attacker.attack(self.npc_target)

        self.assertIn("HIT!", result_message)
        self.assertIn(f"Deals 1d6(6) + DMG Bonus({effective_dmg_bonus}) = {expected_damage} damage.", result_message)
        self.assertEqual(self.npc_target.current_hp, 0) # HP should be 0
        self.assertFalse(self.npc_target.is_alive())
        self.assertIn(f"{self.npc_target.name} HP: 0/{self.npc_target.max_hp}.", result_message)
        self.assertIn(f"{self.npc_target.name} has been defeated!", result_message)

    def test_attack_invalid_dice_format_raises_error_player(self): # Modified to use specific player
        attacker = self.player_attacker_unarmed # Using unarmed for simplicity
        attacker.base_damage_dice = "invalid_dice" # This would be used if no weapon equipped that overrides
        # However, player get_equipped_weapon_stats() returns "1d4" for unarmed, so base_damage_dice is not used by player.
        # This test is more relevant for NPC or if player had no weapon AND get_equipped_weapon_stats returned self.base_damage_dice

        # To test this for player, we'd need to ensure get_equipped_weapon_stats uses base_damage_dice
        # Or, we test this path via an NPC. For player, it's harder to trigger this specific error for base_damage_dice
        # if they are unarmed, as it defaults to "1d4" from get_equipped_weapon_stats.
        # Let's assume this is for an NPC to test Character's direct use of base_damage_dice.
        self.npc_attacker.base_damage_dice = "invalid_dice"
        with self.assertRaisesRegex(ValueError, "Invalid damage_dice format for Orc: 'invalid_dice'. Expected XdY or dY"):
            self.npc_attacker.attack(self.player_attacker_unarmed)

        self.npc_attacker.base_damage_dice = "1d"
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '1d' for Orc: invalid literal for int\(\) with base 10: ''"):
             self.npc_attacker.attack(self.player_attacker_unarmed)

        self.npc_attacker.base_damage_dice = "d"
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice 'd' for Orc: invalid literal for int\(\) with base 10: ''"):
            self.npc_attacker.attack(self.player_attacker_unarmed)

        self.npc_attacker.base_damage_dice = "0d6"
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '0d6' for Orc: Number of dice and sides must be positive. Got: 0d6"):
            self.npc_attacker.attack(self.player_attacker_unarmed)

        self.npc_attacker.base_damage_dice = "1d0"
        with self.assertRaisesRegex(ValueError, "Error parsing damage dice '1d0' for Orc: Number of dice and sides must be positive. Got: 1d0"):
            self.npc_attacker.attack(self.player_attacker_unarmed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
