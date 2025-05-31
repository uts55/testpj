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
        self.mock_dm_manager = unittest.mock.MagicMock() # Add a mock DM manager for tests

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
        # Corrected call to process_combat_turn
        notification1 = process_combat_turn(self.mock_dm_manager, self.player_state, player_action)
        self.assertIn("Hero passes their turn.", notification1)
        self.assertIn("Next up: GoblinA.", notification1)
        self.assertEqual(self.player_state.current_turn_character_id, "GoblinA")

        # NPC's turn (GoblinA attacks Hero)
        # Mock NPC's attack roll (hit) and damage roll
        # Attack: roll_dice(20) -> 15 (hit: 15+3 > 15 AC)
        # Damage: roll_dice(6,1) -> 4 (damage: 4+1 = 5)
        mock_roll_dice_gs.side_effect = [15, 4]
        initial_player_hp = self.player.current_hp

        # Corrected call to process_combat_turn
        notification2 = process_combat_turn(self.mock_dm_manager, self.player_state, "") # player_action is empty for NPC
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
        # Damage roll sum for 2d6 (e.g., 3+5=8)
        mock_roll_dice.side_effect = [18, 8] # d20 roll, then the sum of 2d6

        target_player = self.player_attacker_unarmed
        initial_player_hp = target_player.current_hp
        damage_roll_sum = 8 # This is the sum mocked for roll_dice
        expected_damage = damage_roll_sum + self.npc_attacker.combat_stats['damage_bonus'] # 8 + 3 = 11

        result_message = self.npc_attacker.attack(target_player)

        self.assertIn("HIT!", result_message)
        # The message will show the sum of dice directly from roll_dice()
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

    @patch('game_state.roll_dice') # Ensure attack hits to reach dice parsing
    def test_attack_invalid_dice_format_raises_error_player(self, mock_roll_dice_gs):
        # Mock the attack roll to ensure a hit, so dice parsing is attempted.
        # Let NPC attacker attack player_attacker_unarmed (AC 10).
        # NPC attack_bonus is 4. A roll of 10 + 4 = 14, which should hit AC 10.
        mock_roll_dice_gs.return_value = 10 # Mocking the d20 roll for the attack

        # This test is primarily for the Character class's parsing, best tested with NPC
        # where base_damage_dice is directly used.

        # Test case 1: "invalid_dice"
        self.npc_attacker.base_damage_dice = "invalid_dice"
        expected_error_regex_invalid = r"Error parsing damage dice 'invalid_dice' for Orc: Invalid format\. Expected XdY or dY\."
        with self.assertRaisesRegex(ValueError, expected_error_regex_invalid):
            self.npc_attacker.attack(self.player_attacker_unarmed)
        mock_roll_dice_gs.assert_called_with(sides=20) # Ensure attack roll was made

        # Test case 2: "1d"
        self.npc_attacker.base_damage_dice = "1d"
        expected_error_regex_1d = r"Error parsing damage dice '1d' for Orc: Dice sides component is missing\."
        with self.assertRaisesRegex(ValueError, expected_error_regex_1d):
             self.npc_attacker.attack(self.player_attacker_unarmed)
        mock_roll_dice_gs.assert_called_with(sides=20)


        # Test case 3: "d"
        self.npc_attacker.base_damage_dice = "d"
        # When input is "d", parts becomes ['', '']. num_dice_str is '', dice_sides_str is ''.
        # The logic `if not dice_sides_str:` will be true.
        expected_error_regex_d = r"Error parsing damage dice 'd' for Orc: Dice sides component is missing\."
        with self.assertRaisesRegex(ValueError, expected_error_regex_d):
            self.npc_attacker.attack(self.player_attacker_unarmed)
        mock_roll_dice_gs.assert_called_with(sides=20)


        # Test case 4: "0d6"
        self.npc_attacker.base_damage_dice = "0d6"
        expected_error_regex_0d6 = r"Error parsing damage dice '0d6' for Orc: Number of dice and sides must be positive\. Got: 0d6"
        with self.assertRaisesRegex(ValueError, expected_error_regex_0d6):
            self.npc_attacker.attack(self.player_attacker_unarmed)
        mock_roll_dice_gs.assert_called_with(sides=20)


        # Test case 5: "1d0"
        self.npc_attacker.base_damage_dice = "1d0"
        expected_error_regex_1d0 = r"Error parsing damage dice '1d0' for Orc: Number of dice and sides must be positive\. Got: 1d0"
        with self.assertRaisesRegex(ValueError, expected_error_regex_1d0):
            self.npc_attacker.attack(self.player_attacker_unarmed)
        mock_roll_dice_gs.assert_called_with(sides=20)


class TestStatusEffects(unittest.TestCase):
    def setUp(self):
        self.char = Character(id="test_char", name="Test Character", max_hp=50,
                              combat_stats={'armor_class': 10, 'attack_bonus': 0, 'damage_bonus': 0, 'initiative_bonus': 0},
                              base_damage_dice="1d4")
        self.player = Player(id="player_char", name="Player Character", max_hp=100,
                             combat_stats={'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2, 'initiative_bonus': 3},
                             base_damage_dice="1d8")
        self.npc = NPC(id="npc_char", name="NPC Character", max_hp=30,
                       combat_stats={'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1, 'initiative_bonus': 1},
                       base_damage_dice="1d6")
        self.player_state = PlayerState(player_character=self.player)


    def test_add_poison_effect(self):
        # Add new effect
        msg1 = self.char.add_status_effect('poison', 3, 2)
        self.assertEqual(len(self.char.status_effects), 1)
        effect = self.char.status_effects[0]
        self.assertEqual(effect['name'], 'poison')
        self.assertEqual(effect['duration'], 3)
        self.assertEqual(effect['potency'], 2)
        self.assertIn(f"{self.char.name} is now poison for 3 turns", msg1)

        # Update existing effect
        msg2 = self.char.add_status_effect('poison', 5, 4)
        self.assertEqual(len(self.char.status_effects), 1) # Should still be one
        effect = self.char.status_effects[0]
        self.assertEqual(effect['duration'], 5) # Duration updated
        self.assertEqual(effect['potency'], 4) # Potency updated
        self.assertIn(f"{self.char.name}'s poison has been refreshed to 5 turns", msg2)

    def test_remove_poison_effect(self):
        self.char.add_status_effect('poison', 3, 2)
        self.assertEqual(len(self.char.status_effects), 1) # Ensure it was added
        self.char.remove_status_effect('poison')
        self.assertEqual(len(self.char.status_effects), 0)
        # Test removing a non-existent effect (should do nothing)
        self.char.remove_status_effect('non_existent_effect')
        self.assertEqual(len(self.char.status_effects), 0)

    def test_poison_tick_damage_duration_and_messages(self):
        self.char.current_hp = 20 # Set specific HP for testing damage
        self.char.add_status_effect('poison', 3, 2)

        # Tick 1
        messages1 = self.char.tick_status_effects()
        self.assertEqual(self.char.current_hp, 18)
        self.assertEqual(self.char.status_effects[0]['duration'], 2)
        self.assertTrue(any("took 2 damage from poison" in msg for msg in messages1))

        # Tick 2
        messages2 = self.char.tick_status_effects()
        self.assertEqual(self.char.current_hp, 16)
        self.assertEqual(self.char.status_effects[0]['duration'], 1)
        self.assertTrue(any("took 2 damage from poison" in msg for msg in messages2))

        # Tick 3 - poison expires
        messages3 = self.char.tick_status_effects()
        self.assertEqual(self.char.current_hp, 14)
        self.assertEqual(len(self.char.status_effects), 0) # Effect removed
        self.assertTrue(any("is no longer poison" in msg for msg in messages3))
        self.assertTrue(any("took 2 damage from poison" in msg for msg in messages3)) # Damage before expiration

    def test_poison_tick_character_death_and_messages(self):
        self.char.current_hp = 1 # Character has 1 HP
        self.char.add_status_effect('poison', 1, 2) # Poison deals 2 damage

        messages = self.char.tick_status_effects()
        self.assertEqual(self.char.current_hp, 0)
        self.assertFalse(self.char.is_alive())
        self.assertTrue(any("took 2 damage from poison" in msg for msg in messages))
        self.assertTrue(any("succumbed to poison" in msg for msg in messages))
        # Poison should also be removed as character is dead (or duration expired)
        # The current tick_status_effects logic might remove it due to duration,
        # or if death stops further processing, it might remain.
        # Per current game_state.py, if char dies, loop breaks.
        # The "is no longer poison" message and effect removal will not happen if death breaks the loop first.
        self.assertFalse(any("is no longer poison" in msg for msg in messages))

        # The effect's duration is NOT decremented because the loop breaks upon death.
        # So, the duration remains what it was (1 in this test case).
        self.assertTrue(len(self.char.status_effects) == 1, "Status effect should remain on character if death breaks loop before duration update.")
        if self.char.status_effects: # Should be true based on above assertion
            self.assertEqual(self.char.status_effects[0]['duration'], 1, "Duration should not change if death breaks loop.")
            self.assertEqual(self.char.status_effects[0]['name'], 'poison')

    def test_add_status_effect_return_messages(self):
        # This test is somewhat redundant given test_add_poison_effect,
        # but it explicitly checks the return messages as requested.
        char = Character(id="msg_char", name="Msg Character", max_hp=10, combat_stats={}, base_damage_dice="1d4")

        msg_new = char.add_status_effect('heal_over_time', 3, 1)
        self.assertIn(f"{char.name} is now heal_over_time for 3 turns", msg_new)

        msg_refresh = char.add_status_effect('heal_over_time', 5, 1) # Potency can be same or different
        self.assertIn(f"{char.name}'s heal_over_time has been refreshed to 5 turns", msg_refresh)

        # Test adding a different effect
        msg_new_other = char.add_status_effect('strength_buff', 2, 2)
        self.assertIn(f"{char.name} is now strength_buff for 2 turns", msg_new_other)
        self.assertEqual(len(char.status_effects), 2)

    @patch('game_state.roll_dice')
    @patch('game_state.random.randint')
    def test_poison_application_on_attack(self, mock_random_randint, mock_roll_dice_gs):
        # Attacker: self.player, Target: self.npc
        # Mock random.randint to ensure poison application (<= 10 for 10% chance)
        mock_random_randint.return_value = 5 # This will make the 10% chance succeed

        # Mock roll_dice:
        # 1. Attack roll (e.g., 20 for a guaranteed hit)
        # 2. Damage roll (e.g., 5 for player's 1d8 base_damage_dice)
        mock_roll_dice_gs.side_effect = [20, 5] # d20 for attack, then damage roll

        # Ensure target has no status effects initially
        self.assertEqual(len(self.npc.status_effects), 0)

        attack_message = self.player.attack(self.npc)

        # Assert that the target now has the 'poison' status effect
        self.assertEqual(len(self.npc.status_effects), 1)
        self.assertEqual(self.npc.status_effects[0]['name'], 'poison')
        self.assertEqual(self.npc.status_effects[0]['duration'], 3) # Default duration from subtask
        self.assertEqual(self.npc.status_effects[0]['potency'], 2) # Default potency

        # Assert that attack_message contains the poison notification
        self.assertIn(f"{self.npc.name} has been poisoned!", attack_message)

        # Verify mocks were called
        mock_random_randint.assert_called_once_with(1, 100)
        self.assertTrue(mock_roll_dice_gs.called)


    @patch('main.notify_dm_event') # Mock the function in main.py where it's defined
    @patch('game_state.roll_dice') # Mock roll_dice for predictable NPC attacks if needed
    @patch('game_state.random.randint') # Mock random.randint for predictable poison application
    def test_process_combat_turn_with_poison_and_dm_notifications(self, mock_gs_randint, mock_gs_roll_dice, mocked_notify_dm_event_func):
        # Setup: Player is poisoned, it's player's turn.
        self.player.current_hp = 10 # Ensure player can take poison damage
        self.player.add_status_effect('poison', 1, 2) # Duration 1, Potency 2
        self.assertEqual(self.player.status_effects[0]['name'], 'poison')


        # Mock DM manager - not strictly needed if notify_dm_event is properly patched,
        # but good for completeness if process_combat_turn expected a real DM object.
        # Based on current process_combat_turn, it needs a dm_manager argument.
        mock_dm_manager = unittest.mock.MagicMock()
        # We'll pass mock_dm_manager to process_combat_turn.
        # The @patch('main.notify_dm_event') handles intercepting the calls.

        # Simulate combat start to set turn order (player first)
        # We need to ensure player_state.participants_in_combat includes the actual objects
        self.player_state.participants_in_combat = [self.player, self.npc]
        self.player_state.turn_order = [self.player.id, self.npc.id]
        self.player_state.current_turn_character_id = self.player.id
        self.player_state.is_in_combat = True


        # Player's turn, player passes
        # dm_manager is passed here
        # Corrected keyword argument
        process_combat_turn(mock_dm_manager, self.player_state, player_action="pass")

        # Assertions for notify_dm_event calls
        self.assertTrue(mocked_notify_dm_event_func.called)

        # Check for poison damage message
        expected_poison_dmg_msg = f"{self.player.name} took 2 damage from poison."
        # Check for poison expiry message
        expected_poison_expiry_msg = f"{self.player.name} is no longer poison."
        # Check for player pass message (this is part of the consolidated return, not separate DM event)
        # player_pass_msg = f"{self.player.name} passes their turn."

        # Extract all messages sent to notify_dm_event
        sent_dm_messages = [call_args[0][1] for call_args in mocked_notify_dm_event_func.call_args_list]
        # print(f"Sent DM Messages: {sent_dm_messages}") # For debugging

        self.assertIn(expected_poison_dmg_msg, sent_dm_messages)
        self.assertIn(expected_poison_expiry_msg, sent_dm_messages)
        # self.assertNotIn(player_pass_msg, sent_dm_messages) # The "pass" message is part of the main turn result, not a separate event here

        self.assertEqual(self.player.current_hp, 8) # 10 - 2 from poison
        self.assertEqual(len(self.player.status_effects), 0) # Poison expired

        # Optional Extension: Test poison application during NPC attack
        mocked_notify_dm_event_func.reset_mock() # Reset for the next part of the test
        self.player.current_hp = 20 # Reset HP
        self.npc.status_effects = [] # Clear NPC effects
        self.player_state.current_turn_character_id = self.npc.id # Set to NPC's turn

        # NPC attacks Player. Mock for poison application (10% chance)
        mock_gs_randint.return_value = 1 # Ensure poison hits
        # Mock NPC attack roll (hit) and damage roll
        # NPC (attack_bonus=3) vs Player (AC=15). Need >12 on d20 for hit.
        # Damage: 1d6 (NPC base) + 1 (NPC damage_bonus)
        mock_gs_roll_dice.side_effect = [15, 4] # Hit roll, damage roll

        # Process NPC turn
        # Corrected keyword argument
        turn_result_npc = process_combat_turn(mock_dm_manager, self.player_state, player_action="")
        # print(f"NPC Turn Result for Player UI: {turn_result_npc}") # Debug

        sent_dm_messages_npc_turn = [call_args[0][1] for call_args in mocked_notify_dm_event_func.call_args_list]
        # print(f"Sent DM Messages (NPC Turn): {sent_dm_messages_npc_turn}") # Debug

        # The attack message itself is sent to notify_dm_event
        # It should contain the poison notification
        self.assertTrue(any(f"{self.player.name} has been poisoned!" in msg for msg in sent_dm_messages_npc_turn))
        self.assertEqual(len(self.player.status_effects), 1)
        self.assertEqual(self.player.status_effects[0]['name'], 'poison')


if __name__ == '__main__':
    unittest.main(verbosity=2)
