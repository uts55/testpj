import unittest
from unittest.mock import patch, MagicMock # For mocking notify_dm
import sys
import os

# Add project root to sys.path to allow importing game_state
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from game_state import Player, NPC, ITEM_DATABASE, player_buys_item, player_sells_item
# Ensure game_state.py also has from gemini_dm import notify_dm for the functions to use it
# (This is implicitly handled by the project structure and game_state.py's own imports)

class TestEconomySystem(unittest.TestCase):

    def setUp(self):
        # Basic player data for tests
        self.player_data = {
            "id": "test_player", "name": "TestPlayer", "max_hp": 50,
            "combat_stats": {}, "base_damage_dice": "1d4",
            "ability_scores": {}, "skills": [], "proficiencies": {}, # Added to satisfy Player constructor
            "equipment": {"currency": {"gold": 100, "silver": 50, "copper": 20}}
        }
        self.player = Player(self.player_data)

        # Basic NPC data for context in buy/sell functions
        # Note: NPC constructor in game_state.py takes individual args, not a dict.
        self.merchant_npc = NPC(
            id="test_merchant", name="TestMerchant", max_hp=30,
            combat_stats={}, base_damage_dice="1d4",
            dialogue_responses={}
        )
        # Add sells_item_ids directly to the instance for testing purposes
        self.merchant_npc.sells_item_ids = ["test_item_buy", "test_item_expensive"]


        # Store original ITEM_DATABASE items to restore later if necessary,
        # though for these tests, we're mostly adding new ones.
        self._original_item_database_backup = ITEM_DATABASE.copy()

        # Ensure ITEM_DATABASE has items for testing
        ITEM_DATABASE["test_item_buy"] = {"id": "test_item_buy", "name": "Test Buy Item", "type": "misc", "buy_price": 20, "sell_price": 10}
        ITEM_DATABASE["test_item_sell"] = {"id": "test_item_sell", "name": "Test Sell Item", "type": "misc", "buy_price": 30, "sell_price": 15}
        ITEM_DATABASE["test_item_expensive"] = {"id": "test_item_expensive", "name": "Expensive Item", "type": "misc", "buy_price": 200, "sell_price": 100}
        ITEM_DATABASE["test_item_no_price"] = {"id": "test_item_no_price", "name": "No Price Item", "type": "misc"}

    def tearDown(self):
        # Restore ITEM_DATABASE to its original state if changes were made that affect other tests.
        # For this suite, we are adding specific keys, so removing them is cleaner.
        keys_to_remove = ["test_item_buy", "test_item_sell", "test_item_expensive", "test_item_no_price"]
        for key in keys_to_remove:
            if key in ITEM_DATABASE:
                del ITEM_DATABASE[key]
        # If other tests might rely on the exact state of ITEM_DATABASE before these tests,
        # a more robust backup/restore like self._original_item_database_backup would be needed.
        # For now, assuming these test-specific items are okay to remove.


    def test_change_currency_add_gold(self):
        self.player.change_currency(gold_delta=50)
        self.assertEqual(self.player.equipment["currency"]["gold"], 150)

    def test_change_currency_spend_gold_sufficient_funds(self):
        success = self.player.change_currency(gold_delta=-50)
        self.assertTrue(success)
        self.assertEqual(self.player.equipment["currency"]["gold"], 50)

    def test_change_currency_spend_gold_insufficient_funds(self):
        success = self.player.change_currency(gold_delta=-150)
        self.assertFalse(success)
        self.assertEqual(self.player.equipment["currency"]["gold"], 100) # Should not change

    def test_change_currency_initialize_if_missing(self):
        player_no_currency_data = {
            "id": "test_player_nc", "name": "NoCurrencyPlayer", "max_hp": 50,
            "combat_stats": {}, "base_damage_dice": "1d4", "equipment": {},
            "ability_scores": {}, "skills": [], "proficiencies": {} # Added for Player constructor
        }
        player_nc = Player(player_no_currency_data)
        player_nc.change_currency(gold_delta=10)
        self.assertEqual(player_nc.equipment["currency"]["gold"], 10)
        self.assertEqual(player_nc.equipment["currency"]["silver"], 0) # Check initialization
        self.assertEqual(player_nc.equipment["currency"]["copper"], 0) # Check initialization

    @patch('game_state.notify_dm') # Mock notify_dm from where it's used (game_state)
    def test_player_buys_item_successful(self, mock_notify_dm: MagicMock):
        self.player.equipment["currency"]["gold"] = 100 # Ensure enough gold
        success, message = player_buys_item(self.player, self.merchant_npc, "test_item_buy")
        self.assertTrue(success)
        self.assertIn("구매했습니다", message)
        self.assertEqual(self.player.equipment["currency"]["gold"], 80) # 100 - 20
        self.assertIn("test_item_buy", self.player.inventory)
        mock_notify_dm.assert_called_once()
        self.assertIn("구매했습니다", mock_notify_dm.call_args[0][0])

    @patch('game_state.notify_dm')
    def test_player_buys_item_insufficient_funds(self, mock_notify_dm: MagicMock):
        self.player.equipment["currency"]["gold"] = 10 # Not enough for test_item_buy (cost 20)
        success, message = player_buys_item(self.player, self.merchant_npc, "test_item_buy")
        self.assertFalse(success)
        self.assertIn("골드가 부족합니다", message)
        self.assertEqual(self.player.equipment["currency"]["gold"], 10) # Unchanged
        self.assertNotIn("test_item_buy", self.player.inventory)
        mock_notify_dm.assert_not_called()

    def test_player_buys_item_not_found(self):
        success, message = player_buys_item(self.player, self.merchant_npc, "non_existent_item")
        self.assertFalse(success)
        self.assertIn("찾을 수 없습니다", message)

    def test_player_buys_item_no_price(self):
        success, message = player_buys_item(self.player, self.merchant_npc, "test_item_no_price")
        self.assertFalse(success)
        self.assertIn("구매 가격 정보가 없습니다", message)

    @patch('game_state.notify_dm')
    def test_player_sells_item_successful(self, mock_notify_dm: MagicMock):
        self.player.inventory = ["test_item_sell"] # Player has the item
        self.player.equipment["currency"]["gold"] = 50
        success, message = player_sells_item(self.player, self.merchant_npc, "test_item_sell")
        self.assertTrue(success)
        self.assertIn("판매했습니다", message)
        self.assertEqual(self.player.equipment["currency"]["gold"], 65) # 50 + 15 (sell_price)
        self.assertNotIn("test_item_sell", self.player.inventory)
        mock_notify_dm.assert_called_once()
        self.assertIn("판매했습니다", mock_notify_dm.call_args[0][0])

    @patch('game_state.notify_dm')
    def test_player_sells_item_not_in_inventory(self, mock_notify_dm: MagicMock):
        self.player.inventory = [] # Player does not have the item
        success, message = player_sells_item(self.player, self.merchant_npc, "test_item_sell")
        self.assertFalse(success)
        self.assertIn("인벤토리에", message) # "아이템이 없습니다"
        self.assertNotIn("test_item_sell", self.player.inventory) # Still not there
        mock_notify_dm.assert_not_called()

    def test_player_sells_item_no_price(self):
        self.player.inventory = ["test_item_no_price"]
        success, message = player_sells_item(self.player, self.merchant_npc, "test_item_no_price")
        self.assertFalse(success)
        self.assertIn("판매 가격 정보가 없습니다", message)
        # Item should remain in inventory if price check fails before removal
        self.assertIn("test_item_no_price", self.player.inventory)

    def test_item_prices_in_database(self):
        # Check a few standard items that should have prices from previous subtasks
        short_sword_data = ITEM_DATABASE.get("short_sword")
        self.assertIsNotNone(short_sword_data, "Short sword not found in ITEM_DATABASE")
        self.assertIn("buy_price", short_sword_data)
        self.assertIn("sell_price", short_sword_data)
        self.assertGreater(short_sword_data["buy_price"], 0)
        self.assertGreater(short_sword_data["sell_price"], 0)

        leather_armor_data = ITEM_DATABASE.get("leather_armor")
        self.assertIsNotNone(leather_armor_data, "Leather armor not found in ITEM_DATABASE")
        self.assertIn("buy_price", leather_armor_data)
        self.assertIn("sell_price", leather_armor_data)
        self.assertGreater(leather_armor_data["buy_price"], 0)
        self.assertGreater(leather_armor_data["sell_price"], 0)


if __name__ == '__main__':
    unittest.main()
