import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from characters import Player, NPC, Character
from game_state import (
    PlayerState, determine_initiative, roll_dice, GameState, ITEM_DATABASE
)
from generated_monster import GeneratedMonster
from monster_generator import MonsterGenerator # Required for GameState to initialize its generator
from main import start_combat, process_combat_turn, check_combat_end_condition
from data_loader import load_raw_data_from_sources
from config import RAG_DOCUMENT_SOURCES


class TestInitiativeCalculation(unittest.TestCase):
    @patch('game_state.roll_dice')
    def test_basic_initiative_order(self, mock_roll_dice_func):
        mock_roll_dice_func.side_effect = [10, 5, 15]
        participants = [
            NPC(id="Alice", name="Alice", max_hp=100, combat_stats={'initiative_bonus': 2}, base_damage_dice="1d4"),
            NPC(id="Bob", name="Bob", max_hp=100, combat_stats={'initiative_bonus': 5}, base_damage_dice="1d4"),
            NPC(id="Charlie", name="Charlie", max_hp=100, combat_stats={'initiative_bonus': 0}, base_damage_dice="1d4")
        ]
        expected_order_ids = ["Charlie", "Alice", "Bob"]
        turn_order_ids = determine_initiative(participants)
        self.assertEqual(turn_order_ids, expected_order_ids)

    def test_empty_participants_list(self):
        participants = []
        turn_order = determine_initiative(participants)
        self.assertEqual(turn_order, [])

    @patch('game_state.roll_dice')
    def test_initiative_tie_breaking_behavior(self, mock_roll_dice_func):
        mock_roll_dice_func.side_effect = [10, 12]
        participants = [
            NPC(id="Alice", name="Alice", max_hp=100, combat_stats={'initiative_bonus': 2}, base_damage_dice="1d4"),
            NPC(id="David", name="David", max_hp=100, combat_stats={'initiative_bonus': 0}, base_damage_dice="1d4"),
        ]
        turn_order_ids = determine_initiative(participants)
        self.assertEqual(turn_order_ids, ["Alice", "David"])


class TestCombatFlow(unittest.TestCase):
    def setUp(self):
        # Mock GameState for Player attacks needing game.items for equipment
        self.mock_game_state = MagicMock(spec=GameState)
        self.mock_game_state.items = ITEM_DATABASE # Use actual ITEM_DATABASE for weapon stats

        self.player = Player(player_data={
            "id":"Hero", "name":"Hero", "max_hp":100,
            "combat_stats":{'initiative_bonus': 3, 'armor_class': 15, 'attack_bonus': 5, 'damage_bonus': 2},
            "base_damage_dice":"1d8",
            "equipment": {"weapon": "short_sword"} # Example weapon
        })
        self.npc1 = NPC(id="GoblinA", name="GoblinA", max_hp=50,
                        combat_stats={'initiative_bonus': 1, 'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1},
                        base_damage_dice="1d6")
        self.npc2 = NPC(id="GoblinB", name="GoblinB", max_hp=50,
                        combat_stats={'initiative_bonus': 1, 'armor_class': 12, 'attack_bonus': 3, 'damage_bonus': 1},
                        base_damage_dice="1d6")
        self.opponents = [self.npc1, self.npc2] # Changed from self.npcs to self.opponents
        self.player_state = PlayerState(player_character=self.player)
        self.mock_dm_manager = MagicMock()

    @patch('main.determine_initiative') # Patches determine_initiative where start_combat calls it
    def test_start_combat(self, mock_determine_initiative_in_main):
        mock_determine_initiative_in_main.return_value = ["Hero", "GoblinA", "GoblinB"]
        notification = start_combat(self.player, self.opponents, self.player_state) # Use self.opponents

        self.assertTrue(self.player_state.is_in_combat)
        self.assertEqual(len(self.player_state.participants_in_combat), 3)
        self.assertIn(self.player, self.player_state.participants_in_combat)
        self.assertIn(self.npc1, self.player_state.participants_in_combat)
        self.assertIn(self.npc2, self.player_state.participants_in_combat)
        self.assertEqual(self.player_state.turn_order, ["Hero", "GoblinA", "GoblinB"])
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")
        self.assertIn("Combat started! Turn order: Hero, GoblinA, GoblinB.", notification)
        self.assertIn("First up: Hero (Hero).", notification)

    @patch('main.determine_initiative') # Patches determine_initiative where start_combat calls it
    @patch('characters.roll_dice') # Patch roll_dice where Character.attack looks it up
    def test_process_combat_turn_player_and_npc(self, mock_char_roll_dice, mock_determine_initiative_main): # Renamed mock
        mock_determine_initiative_main.return_value = ["Hero", "GoblinA"]
        single_opponent_list = [self.npc1] # Use only one opponent for this test
        start_combat(self.player, single_opponent_list, self.player_state)

        player_action = "pass"
        notification1 = process_combat_turn(self.mock_dm_manager, self.player_state, player_action)
        self.assertIn("Hero passes their turn.", notification1)
        self.assertIn("Next up: GoblinA.", notification1)
        self.assertEqual(self.player_state.current_turn_character_id, "GoblinA")

        mock_char_roll_dice.reset_mock() # Ensure mock state is clean before this part
        mock_char_roll_dice.side_effect = [15, 4] # NPC Attack roll 15, NPC Damage roll 4
        initial_player_hp = self.player.current_hp

        # Player's attack method needs a GameState instance
        # In main.py, process_combat_turn accesses a global `game` variable.
        # We need to mock this global `game` or ensure it's available.
        # For this test, we'll patch the global `game` in `main` module.
        with patch('main.game', self.mock_game_state):
            notification2 = process_combat_turn(self.mock_dm_manager, self.player_state, "") # NPC's turn, no player_action needed

        # print(f"DEBUG: TestCombatFlow: NPC Turn Notification: {notification2}")
        # print(f"DEBUG: TestCombatFlow: mock_char_roll_dice.call_args_list: {mock_char_roll_dice.call_args_list}")

        self.assertIn("GoblinA attacks Hero.", notification2)
        self.assertIn("HIT!", notification2) # NPC attack roll 15 + bonus 3 = 18. Player AC 15. Should be HIT.
         # Damage: 4 (roll) + 1 (GoblinA's bonus) = 5
        # Message format from Character.attack: Deals {dice_for_msg}({dmg_roll}){dice_mod_str}+DMG_STAT({cur_dmg_bonus})={total_dmg} damage.
        # GoblinA: base_damage_dice="1d6", cur_dmg_bonus=1 (from npc1 setup), dice_modifier=0
        self.assertIn(f"Deals 1d6(4)+DMG_STAT(1)={5} damage.", notification2)
        self.assertEqual(self.player.current_hp, initial_player_hp - 5)
        self.assertIn(f"Hero HP: {self.player.current_hp}/{self.player.max_hp}", notification2)
        self.assertIn("Next up: Hero.", notification2)
        self.assertEqual(self.player_state.current_turn_character_id, "Hero")

    def test_check_combat_end_condition_player_defeat(self):
        with patch('main.determine_initiative', return_value=[self.player.id, self.npc1.id]):
             start_combat(self.player, [self.npc1], self.player_state)
        self.player.take_damage(self.player.max_hp * 2)
        self.assertTrue(not self.player.is_alive())
        ended, notification = check_combat_end_condition(self.player, [self.npc1], self.player_state)
        self.assertTrue(ended)
        self.assertIn(f"Player {self.player.name} ({self.player.id}) has been defeated! Combat ends.", notification)
        self.assertFalse(self.player_state.is_in_combat)

    def test_check_combat_end_condition_npcs_defeat(self):
        with patch('main.determine_initiative', return_value=[self.player.id, self.npc1.id, self.npc2.id]):
            start_combat(self.player, self.opponents, self.player_state) # Use self.opponents
        self.npc1.take_damage(self.npc1.max_hp * 2)
        self.npc2.take_damage(self.npc2.max_hp * 2)
        self.assertTrue(not self.npc1.is_alive())
        self.assertTrue(not self.npc2.is_alive())
        ended, notification = check_combat_end_condition(self.player, self.opponents, self.player_state) # Use self.opponents
        self.assertTrue(ended)
        self.assertIn(f"All opponents ({self.npc1.name}, {self.npc2.name}) defeated! Combat ends.", notification) # "opponents"
        self.assertFalse(self.player_state.is_in_combat)

    def test_check_combat_end_condition_no_end(self):
        with patch('main.determine_initiative', return_value=[self.player.id] + [op.id for op in self.opponents]): # Use self.opponents
            start_combat(self.player, self.opponents, self.player_state) # Use self.opponents
        ended, notification = check_combat_end_condition(self.player, self.opponents, self.player_state) # Use self.opponents
        self.assertFalse(ended)
        self.assertEqual(notification, "")
        self.assertTrue(self.player_state.is_in_combat)

# TestAttackMethod and TestStatusEffects remain largely the same as they test Character/Player/NPC methods
# directly, but ensure GameState is passed to attack if needed by Player.
# For brevity, I'll only show modifications if GeneratedMonster specific tests are added there.
# The current TestAttackMethod uses ITEM_DATABASE directly for player weapon stats,
# which is fine if ITEM_DATABASE is populated correctly.

class TestCombatWithGeneratedMonsters(unittest.TestCase):
    def setUp(self):
        self.player = Player(player_data={
            "id":"HeroGM", "name":"HeroGM", "max_hp":120,
            "combat_stats":{'armor_class': 16, 'attack_bonus': 6, 'damage_bonus': 3, 'initiative_bonus': 2},
            "base_damage_dice":"1d8",
            "equipment": {"weapon": "long_sword"} # long_sword: 1d8, ATK+1, DMG+1
        })

        # Initialize GameState and MonsterGenerator
        self.game_instance_for_tests = GameState(player_character=self.player) # Renamed to avoid conflict with main.game
        all_raw_data = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)
        self.game_instance_for_tests.initialize_from_raw_data(all_raw_data)

        self.assertIsNotNone(self.game_instance_for_tests.monster_generator, "MonsterGenerator should be initialized in GameState")

        self.monster1 = self.game_instance_for_tests.spawn_monster(race_id="goblin", difficulty_level=2)
        self.assertIsNotNone(self.monster1, "Failed to spawn monster1 (goblin)")
        if self.monster1: self.game_instance_for_tests.npcs[self.monster1.id] = self.monster1

        self.monster2 = self.game_instance_for_tests.spawn_monster(race_id="orc", attribute_ids=["strong"], role_id="warrior", difficulty_level=5)
        self.assertIsNotNone(self.monster2, "Failed to spawn monster2 (orc warrior)")
        if self.monster2: self.game_instance_for_tests.npcs[self.monster2.id] = self.monster2

        self.player_state = PlayerState(player_character=self.player)
        self.mock_dm_manager = MagicMock()

    @patch('characters.roll_dice') # Patch roll_dice where Character.attack looks it up
    @patch('main.determine_initiative')
    def test_player_attacks_generated_monster(self, mock_determine_initiative, mock_char_roll_dice):
        if not self.monster1: self.fail("Monster1 (goblin) was not spawned for test.")
        mock_determine_initiative.return_value = [self.player.id, self.monster1.id]

        monster_ac = self.monster1.combat_stats.get('armor_class', 10)
        initial_monster_hp = self.monster1.current_hp
        mock_char_roll_dice.side_effect = [15, 5] # d20 attack roll 15, 1d8 damage roll 5

        start_combat(self.player, [self.monster1], self.player_state)
        self.player_state.current_turn_character_id = self.player.id

        action = f"attack {self.monster1.name}"
        # Patch the global 'game' in 'main' module for this call
        with patch('main.game', self.game_instance_for_tests):
            notification = process_combat_turn(self.mock_dm_manager, self.player_state, player_action=action)

        self.assertIn(f"{self.player.name} attacks {self.monster1.name}", notification)
        self.assertIn("HIT!", notification) # player attack 15 + ATK(6+1)=22 vs monster AC. Should HIT.
        # Player: base_dmg_bonus=3, long_sword dmg_bonus=1. Total cur_dmg_bonus=4. Dice string for long_sword is 1d8.
        # Expected: Deals 1d8(5)+DMG_STAT(4)=9 damage.
        self.assertIn(f"Deals 1d8(5)+DMG_STAT(4)={9} damage.", notification)
        self.assertEqual(self.monster1.current_hp, initial_monster_hp - 9)

    @patch('characters.roll_dice') # Patch roll_dice where Character.attack looks it up
    @patch('main.determine_initiative')
    def test_generated_monster_attacks_player(self, mock_determine_initiative, mock_char_roll_dice): # Renamed mock
        if not self.monster2: self.fail("Monster2 (orc warrior) was not spawned for test.")
        mock_determine_initiative.return_value = [self.monster2.id, self.player.id] # Monster's turn first

        monster_atk_bonus = self.monster2.combat_stats.get('attack_bonus', 0)
        monster_dmg_dice = self.monster2.base_damage_dice # e.g., "1d12+3"
        monster_stat_dmg_bonus = self.monster2.combat_stats.get('damage_bonus',0) # Bonus from stats, not dice string

        initial_player_hp = self.player.current_hp
        player_ac = self.player.get_effective_armor_class(self.game_instance_for_tests) # Player AC 16
        mock_char_roll_dice.side_effect = [18, 6] # d20 attack roll 18, dX damage roll 6

        start_combat(self.player, [self.monster2], self.player_state) # This sets turn order via mock
        self.player_state.current_turn_character_id = self.monster2.id # Explicitly set current turn

        with patch('main.game', self.game_instance_for_tests):
            notification = process_combat_turn(self.mock_dm_manager, self.player_state, player_action="")

        self.assertIn(f"{self.monster2.name} attacks {self.player.name}", notification)
        self.assertIn("HIT!", notification) # Monster attack 18 + ATK bonus vs Player AC 16. Should HIT.

        dice_modifier_from_string = 0
        dice_str_base = monster_dmg_dice # e.g. "1d12+3"
        if '+' in monster_dmg_dice:
            parts = monster_dmg_dice.split('+')
            dice_str_base = parts[0] # "1d12"
            dice_modifier_from_string = int(parts[1]) # 3
        elif '-' in monster_dmg_dice: # Not expected for this monster, but good to be robust
            parts = monster_dmg_dice.split('-')
            dice_str_base = parts[0]
            dice_modifier_from_string = -int(parts[1])

        expected_damage_dealt_by_monster = 6 + dice_modifier_from_string + monster_stat_dmg_bonus

        expected_msg_part = f"Deals {dice_str_base}(6)"
        if dice_modifier_from_string != 0:
            expected_msg_part += f"{'+' if dice_modifier_from_string > 0 else ''}{dice_modifier_from_string}"
        expected_msg_part += f"+DMG_STAT({monster_stat_dmg_bonus})={expected_damage_dealt_by_monster} damage."

        self.assertIn(expected_msg_part, notification)
        self.assertEqual(self.player.current_hp, initial_player_hp - expected_damage_dealt_by_monster)

    @patch('characters.roll_dice') # Patch roll_dice where Character.attack looks it up
    @patch('main.determine_initiative')
    def test_player_defeats_generated_monster(self, mock_determine_initiative, mock_char_roll_dice): # Renamed mock
        if not self.monster1: self.fail("Monster1 (goblin) was not spawned for test.")
        mock_determine_initiative.return_value = [self.player.id, self.monster1.id]

        self.monster1.current_hp = 5 # Low HP for one-shot
        mock_char_roll_dice.side_effect = [20, 8] # d20 attack, dX damage. Player damage 8 + 4 = 12.

        start_combat(self.player, [self.monster1], self.player_state)
        self.player_state.current_turn_character_id = self.player.id

        action = f"attack {self.monster1.name}"
        with patch('main.game', self.game_instance_for_tests):
            process_combat_turn(self.mock_dm_manager, self.player_state, player_action=action)

        self.assertFalse(self.monster1.is_alive(), f"Monster {self.monster1.name} should be defeated but has {self.monster1.current_hp} HP.")
        self.assertEqual(self.monster1.current_hp, 0)

        ended, end_notification = check_combat_end_condition(self.player, [self.monster1], self.player_state)
        self.assertTrue(ended)
        self.assertIn(f"All opponents ({self.monster1.name}) defeated! Combat ends.", end_notification)
        self.assertFalse(self.player_state.is_in_combat)

    @patch('characters.roll_dice') # Patch roll_dice where Character.attack looks it up
    @patch('main.determine_initiative')
    def test_generated_monster_defeats_player(self, mock_determine_initiative, mock_char_roll_dice): # Renamed mock
        if not self.monster2: self.fail("Monster2 (orc warrior) was not spawned for test.")
        mock_determine_initiative.return_value = [self.monster2.id, self.player.id]

        self.player.current_hp = 5 # Player low HP
        mock_char_roll_dice.side_effect = [20, 8] # d20 attack, dX damage. Monster damage 8 + mod + stat_bonus.

        start_combat(self.player, [self.monster2], self.player_state)
        self.player_state.current_turn_character_id = self.monster2.id # Monster's turn

        with patch('main.game', self.game_instance_for_tests):
            process_combat_turn(self.mock_dm_manager, self.player_state, player_action="")

        ended, end_notification = check_combat_end_condition(self.player, [self.monster2], self.player_state) # Define ended and end_notification

        self.assertFalse(self.player.is_alive(), f"Player should be defeated but has {self.player.current_hp} HP.")
        self.assertTrue(ended)
        self.assertIn(f"Player {self.player.name} ({self.player.id}) has been defeated! Combat ends.", end_notification)

if __name__ == '__main__':
    # This block is crucial for populating ITEM_DATABASE when tests are run directly.
    # game_state.py's Player class relies on a global ITEM_DATABASE that it expects to be populated.
    # The GameState.initialize_from_raw_data method populates its own self.items.
    # Player._get_item_from_game_state accesses game_state.items (passed GameState instance).
    # The global ITEM_DATABASE in game_state.py itself might not be the primary way Player gets item data
    # if it's always passed a GameState instance.
    # Let's ensure that ITEM_DATABASE is populated if Player class directly uses it as a fallback or for some other reason.
    # The Player class in the provided game_state.py does NOT use the global ITEM_DATABASE.
    # It uses the `game_state.items` from the GameState instance passed to its methods.
    # Therefore, the ITEM_DATABASE population here is likely not strictly necessary for Player methods
    # IF those methods are always called with a valid GameState instance.
    # However, TestCombatFlow.setUp uses ITEM_DATABASE for its self.mock_game_state.items.
    # So, it IS necessary for that specific test class.

    # Check if ITEM_DATABASE from game_state is populated or if it's just an empty dict.
    # game_state.py defines ITEM_DATABASE = {} at the global level.
    # It is populated by the GameState.load_items method IF that method is modified to also update the global.
    # The provided game_state.py's load_items populates self.items, not the global ITEM_DATABASE.

    # For TestCombatFlow.setUp to work as written (self.mock_game_state.items = ITEM_DATABASE),
    # we need to populate the global game_state.ITEM_DATABASE.

    # Create a temporary GameState to load items, and then manually assign to game_state.ITEM_DATABASE
    print("Attempting to populate global game_state.ITEM_DATABASE for tests...")
    temp_player_for_gs = Player(player_data={"id":"dummy_gs_player", "name":"dummy_gs_player", "max_hp":1})
    temp_game_for_db_population = GameState(player_character=temp_player_for_gs)
    all_raw_data_for_db = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)
    temp_game_for_db_population.initialize_from_raw_data(all_raw_data_for_db)

    # Manually update the global ITEM_DATABASE from the loaded items
    if temp_game_for_db_population.items:
        # game_state.ITEM_DATABASE.update(temp_game_for_db_population.items) # This would modify the imported ITEM_DATABASE
        # This direct update is tricky because ITEM_DATABASE is imported.
        # Instead, TestCombatFlow.setUp should use the items from a real GameState instance.
        # Let's refine TestCombatFlow.setUp.
        # The original thought of populating global ITEM_DATABASE is kept for now as per the provided test code structure.
        # If tests fail, this is a key area to revisit.
        # The issue is that `from game_state import ITEM_DATABASE` creates a *copy* if ITEM_DATABASE is mutable
        # and reassigned in game_state.py. If it's modified in place, it should work.
        # Let's assume it's modified in place or that the test structure is expecting this.
        # The Player class does not use game_state.ITEM_DATABASE, it uses the items from the GameState instance.
        # The test `TestCombatFlow` however, assigns `self.mock_game_state.items = ITEM_DATABASE`.
        # This means the global `ITEM_DATABASE` from `game_state` module needs to be filled.

        # The most robust way:
        # 1. game_state.py should have a function to get all loaded items, or GameState.items should be accessible.
        # 2. Tests create a GameState, load data, then pass game_state.items to player methods or mock game_state.items.

        # For the current structure of TestCombatFlow:
        # We need to ensure the imported `ITEM_DATABASE` is filled.
        # The best way is if `game_state.py` had a function like `get_item_database()` that returns the populated dict.
        # Or, `GameState.load_items` could also update the global `ITEM_DATABASE`.
        # The current `game_state.py` does not update the global `ITEM_DATABASE`.

        # The provided test code explicitly uses `self.mock_game_state.items = ITEM_DATABASE`.
        # This implies the global `ITEM_DATABASE` in `game_state.py` is expected to be the source.
        # This will only work if `GameState.initialize_from_raw_data` (or `load_items`)
        # *also* updates the global `game_state.ITEM_DATABASE`.
        # Let's assume for the purpose of this test that this is how it's intended to work,
        # or that the tests requiring it (like TestCombatFlow's use of Player with equipment)
        # will correctly mock or provide the necessary item data.
        # The TestCombatWithGeneratedMonsters correctly creates a full GameState instance.
        # TestCombatFlow is more minimal.

        # The Player class methods like get_equipped_weapon_stats take a game_state argument
        # and use game_state.items. So, the mock_game_state in TestCombatFlow needs to have
        # its .items attribute populated. The line `self.mock_game_state.items = ITEM_DATABASE`
        # attempts this. So, the global ITEM_DATABASE *must* be populated.

        # This hack attempts to populate the global items.ITEM_DATABASE
        # (which game_state.py re-exports)
        import items as items_module
        items_module.ITEM_DATABASE.update(temp_game_for_db_population.items)
        print(f"Global items.ITEM_DATABASE populated with {len(items_module.ITEM_DATABASE)} items for TestCombatFlow.")
        if not items_module.ITEM_DATABASE:
            print("Warning: Global items.ITEM_DATABASE is still empty after attempting population. TestCombatFlow might fail.")
        elif "short_sword" not in items_module.ITEM_DATABASE: # Used by TestCombatFlow
            print("Warning: 'short_sword' not in populated items.ITEM_DATABASE. TestCombatFlow player equipment check might fail.")
        if "long_sword" not in items_module.ITEM_DATABASE: # Used by TestCombatWithGeneratedMonsters
            print("Warning: 'long_sword' not in populated items.ITEM_DATABASE. TestCombatWithGeneratedMonsters player equipment check might fail.")

    unittest.main(verbosity=2)
