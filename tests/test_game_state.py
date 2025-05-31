import unittest
import os # For path manipulation in main, if needed
import json # For main block example printing, if used

# Import classes and functions from game_state
from game_state import (
    GameState, Player, NPC, Character,
    Item, Weapon, Armor, Consumable, KeyItem, Location,
    player_buys_item, player_sells_item,
    determine_initiative, reveal_clue # Added reveal_clue for testing
)
# Import functions/data needed for GameState initialization in tests
from data_loader import load_raw_data_from_sources, create_npc_from_data
# RAG_DOCUMENT_SOURCES might be needed if we test loading from actual files in some specific GameState tests,
# but for unit tests, it's better to use mock raw data.
# For the __main__ block in game_state.py, it uses RAG_DOCUMENT_SOURCES directly.

class TestItemClasses(unittest.TestCase):
    """Test cases for Item and its subclasses."""
    def test_item_creation(self):
        item = Item(id="gem", name="Shining Gem", description="A bright, worthless gem.", item_type="generic", weight=0.1, value={"buy": 1, "sell": 0})
        self.assertEqual(item.name, "Shining Gem")
        self.assertEqual(item.item_type, "generic")

    def test_weapon_creation(self):
        weapon = Weapon(id="ws001", name="Iron Dagger", description="A simple dagger.",
                        damage_dice="1d4", attack_bonus=1, damage_bonus=0, weapon_type="dagger", weight=1.0, value={"buy":10, "sell":3})
        self.assertEqual(weapon.name, "Iron Dagger")
        self.assertEqual(weapon.item_type, "weapon")
        self.assertEqual(weapon.damage_dice, "1d4")
        self.assertEqual(weapon.attack_bonus, 1)

    def test_armor_creation(self):
        armor = Armor(id="am001", name="Leather Tunic", description="Basic leather armor.",
                      ac_bonus=2, armor_type="light", weight=5.0, value={"buy":20, "sell":5})
        self.assertEqual(armor.name, "Leather Tunic")
        self.assertEqual(armor.item_type, "armor")
        self.assertEqual(armor.ac_bonus, 2)
        self.assertEqual(armor.armor_type, "light")

    def test_shield_creation(self):
        shield = Armor(id="sh001", name="Wooden Shield", description="A simple wooden shield.",
                       ac_bonus=1, armor_type="shield", weight=6.0, value={"buy":15, "sell":4})
        self.assertEqual(shield.name, "Wooden Shield")
        self.assertEqual(shield.item_type, "armor") # Shields are a type of Armor
        self.assertEqual(shield.ac_bonus, 1)
        self.assertEqual(shield.armor_type, "shield")


    def test_consumable_creation(self):
        effects = [{"effect_type": "heal", "amount": "2d4+2"}]
        consumable = Consumable(id="pot001", name="Healing Potion", description="Restores health.",
                                effects=effects, weight=0.5, value={"buy":50, "sell":15})
        self.assertEqual(consumable.name, "Healing Potion")
        self.assertEqual(consumable.item_type, "consumable")
        self.assertEqual(len(consumable.effects), 1)
        self.assertEqual(consumable.effects[0]["amount"], "2d4+2")

    def test_keyitem_creation(self):
        key = KeyItem(id="key001", name="Rusty Key", description="Opens an old chest.",
                      unlocks=["chest_north_tower"], weight=0.1, value={"buy":5, "sell":1})
        self.assertEqual(key.name, "Rusty Key")
        self.assertEqual(key.item_type, "key_item")
        self.assertIn("chest_north_tower", key.unlocks)


class TestLocationClass(unittest.TestCase):
    """Test cases for the Location class."""
    def test_location_creation(self):
        loc = Location(id="town_square", name="Town Square", description="A bustling place.",
                       exits={"north": "market_street", "south": "inn"},
                       item_ids=["potion1"], npc_ids=["guard1"], game_object_ids=["fountain"])
        self.assertEqual(loc.name, "Town Square")
        self.assertEqual(loc.exits["north"], "market_street")
        self.assertIn("potion1", loc.item_ids)
        self.assertIn("guard1", loc.npc_ids)
        self.assertIn("fountain", loc.game_object_ids)

class TestGameState(unittest.TestCase):
    """Test cases for the GameState class and its interactions."""

    def setUp(self):
        """Set up a basic Player and GameState for each test."""
        self.player_data = {
            "id": "test_player", "name": "Hero", "max_hp": 100,
            "combat_stats": {'armor_class': 10, 'attack_bonus': 2, 'damage_bonus': 1}, # Base AC for player
            "base_damage_dice": "1d4", # Unarmed
            "ability_scores": {"strength": 12, "dexterity": 14, "intelligence": 10},
            "inventory": [],
            "equipment": {"currency": {"gold": 50}}
        }
        self.player = Player(self.player_data)
        self.game_state = GameState(player_character=self.player)

        # Sample raw data for initializing GameState
        self.sample_raw_items = [
            {"id": "sword001", "name": "Steel Sword", "type": "weapon", "damage_dice": "1d8", "value": {"buy": 30, "sell": 10}},
            {"id": "leather001", "name": "Leather Armor", "type": "armor", "ac_bonus": 2, "armor_type": "light", "value": {"buy": 25, "sell": 8}},
            {"id": "potion_heal_1", "name": "Minor Healing Potion", "type": "consumable", "effects": [{"effect_type": "heal", "amount": "1d8+1"}], "value": {"buy": 20, "sell": 5}},
            {"id": "key_jail", "name": "Jail Key", "type": "key_item", "unlocks": ["jail_door_01"], "value": {"buy":0,"sell":0}}
        ]
        self.sample_raw_locations = [
            {"id": "loc001", "name": "Starting Room", "description": "A plain room.", "exits": {"north": "loc002"}},
            {"id": "loc002", "name": "Corridor", "description": "A long corridor.", "exits": {"south": "loc001"}}
        ]
        self.sample_raw_npcs = [
            {"id": "npc001", "name": "Old Man", "max_hp": 30, "combat_stats": {}, "base_damage_dice": "1d4", "dialogue_responses": {"greet": "Hello"}}
        ]
        self.sample_raw_game_objects = [
            {"id": "obj001", "name": "Mysterious Chest", "description": "It's locked."}
        ]
        self.sample_raw_lore = [ # Example of a .txt file loaded by data_loader
            {"id": "lore_intro", "text_content": "In the beginning...", "source_category": "Lore"}
        ]

        self.all_sample_raw_data = {
            "Items": self.sample_raw_items,
            "Regions": self.sample_raw_locations, # Note: data_loader uses directory name 'Regions'
            "NPCs": self.sample_raw_npcs,
            "GameObjects": self.sample_raw_game_objects,
            "Lore": self.sample_raw_lore
        }
        self.game_state.initialize_from_raw_data(self.all_sample_raw_data)


    def test_gamestate_initialization(self):
        """Test GameState initialization with a player character."""
        self.assertEqual(self.game_state.player_character.name, "Hero")
        self.assertTrue(len(self.game_state.items) > 0, "Items should be loaded")
        self.assertTrue(len(self.game_state.locations) > 0, "Locations should be loaded")
        self.assertTrue(len(self.game_state.npcs) > 0, "NPCs should be loaded")

    def test_initialize_from_raw_data(self):
        """Test the main data initialization method."""
        self.assertEqual(len(self.game_state.items), len(self.sample_raw_items))
        self.assertIn("sword001", self.game_state.items)
        self.assertIsInstance(self.game_state.items["sword001"], Weapon)

        self.assertEqual(len(self.game_state.locations), len(self.sample_raw_locations))
        self.assertIn("loc001", self.game_state.locations)
        self.assertIsInstance(self.game_state.locations["loc001"], Location)

        self.assertEqual(len(self.game_state.npcs), len(self.sample_raw_npcs))
        self.assertIn("npc001", self.game_state.npcs)
        self.assertIsInstance(self.game_state.npcs["npc001"], NPC)

        self.assertEqual(len(self.game_state.game_objects), len(self.sample_raw_game_objects))
        self.assertIn("obj001", self.game_state.game_objects)
        self.assertEqual(self.game_state.game_objects["obj001"]["name"], "Mysterious Chest")

        self.assertIn("Lore", self.game_state.rag_documents)
        self.assertEqual(len(self.game_state.rag_documents["Lore"]), len(self.sample_raw_lore))
        self.assertEqual(self.game_state.rag_documents["Lore"][0]["text_content"], "In the beginning...")


    def test_player_equip_unequip_item(self):
        """Test equipping and unequipping items for the Player."""
        self.player.add_to_inventory("sword001")
        self.assertTrue(self.player.equip_item("sword001", "weapon", self.game_state))
        self.assertEqual(self.player.equipment.get("weapon"), "sword001")
        self.assertNotIn("sword001", self.player.inventory)

        # Test get_equipped_weapon_stats
        weapon_stats = self.player.get_equipped_weapon_stats(self.game_state)
        self.assertEqual(weapon_stats["damage_dice"], "1d8")

        # Unequip
        unequipped_id = self.player.unequip_item("weapon", self.game_state)
        self.assertEqual(unequipped_id, "sword001")
        self.assertIsNone(self.player.equipment.get("weapon"))
        self.assertIn("sword001", self.player.inventory)

        # Check unarmed stats
        unarmed_stats = self.player.get_equipped_weapon_stats(self.game_state)
        self.assertEqual(unarmed_stats["damage_dice"], "1d4") # Player's base_damage_dice

    def test_player_armor_and_ac(self):
        """Test equipping armor and shield, and AC calculation."""
        initial_ac = self.player.get_effective_armor_class(self.game_state) # Base AC
        self.assertEqual(initial_ac, self.player_data["combat_stats"]['armor_class'])

        self.player.add_to_inventory("leather001")
        self.player.equip_item("leather001", "armor", self.game_state)
        ac_with_armor = self.player.get_effective_armor_class(self.game_state)
        self.assertEqual(ac_with_armor, initial_ac + self.game_state.items["leather001"].ac_bonus)

        # Add a shield for testing
        shield_data = {"id": "shield001", "name": "Iron Shield", "type": "armor", "ac_bonus": 2, "armor_type": "shield"}
        self.game_state.items["shield001"] = Armor(**shield_data) # Manually add to game_state for this test
        self.player.add_to_inventory("shield001")
        self.player.equip_item("shield001", "shield", self.game_state)

        ac_with_shield = self.player.get_effective_armor_class(self.game_state)
        expected_ac = initial_ac + self.game_state.items["leather001"].ac_bonus + self.game_state.items["shield001"].ac_bonus
        self.assertEqual(ac_with_shield, expected_ac)

    def test_player_use_consumable(self):
        """Test using a consumable item."""
        self.player.current_hp = 50
        self.player.add_to_inventory("potion_heal_1")

        success, msg = self.player.use_item("potion_heal_1", self.game_state)
        self.assertTrue(success)
        self.assertIn("healed for", msg)
        self.assertNotIn("potion_heal_1", self.player.inventory)
        self.assertTrue(self.player.current_hp > 50) # HP should have increased

    def test_player_buy_sell_items(self):
        """Test player buying and selling items."""
        npc_trader = self.game_state.npcs.get("npc001") # Use the Old Man as a trader for test
        initial_gold = self.player.equipment["currency"]["gold"]

        # Player buys "sword001" (assuming it's available from NPC or world, for test we check price from item itself)
        # For a real buy, item should be in NPC's inventory. Here, we test the transaction mechanism.
        # Let's assume "sword001" has a buy price.
        item_to_buy = self.game_state.items["sword001"]

        # Ensure player doesn't have it and can afford it
        if item_to_buy.id in self.player.inventory: self.player.remove_from_inventory(item_to_buy.id)
        self.player.equipment["currency"]["gold"] = item_to_buy.value["buy"] # Ensure player has exact gold

        success_buy, msg_buy = player_buys_item(self.player, npc_trader, item_to_buy.id, self.game_state)
        self.assertTrue(success_buy)
        self.assertIn(item_to_buy.id, self.player.inventory)
        self.assertEqual(self.player.equipment["currency"]["gold"], 0)

        # Player sells "sword001"
        success_sell, msg_sell = player_sells_item(self.player, npc_trader, item_to_buy.id, self.game_state)
        self.assertTrue(success_sell)
        self.assertNotIn(item_to_buy.id, self.player.inventory)
        self.assertEqual(self.player.equipment["currency"]["gold"], item_to_buy.value["sell"])

        # Restore initial gold for other tests if needed, though each test should be isolated.
        self.player.equipment["currency"]["gold"] = initial_gold


    def test_combat_player_vs_npc(self):
        """Test a round of combat: player attacks NPC."""
        self.player.equip_item("sword001", "weapon", self.game_state) # Ensure player is armed
        target_npc = self.game_state.npcs["npc001"]
        initial_npc_hp = target_npc.current_hp

        attack_message = self.player.attack(target_npc, self.game_state)
        self.assertIsInstance(attack_message, str)
        if "HIT!" in attack_message:
            self.assertTrue(target_npc.current_hp < initial_npc_hp or not target_npc.is_alive())
        else: # Miss
            self.assertEqual(target_npc.current_hp, initial_npc_hp)

    def test_reveal_clue_from_game_object(self):
        """Test revealing a clue from a game object."""
        # Add a sample game object with a clue to game_state.game_objects
        # Note: initialize_from_raw_data already populates game_objects using self.sample_raw_game_objects
        # We need to ensure one of them has hidden_clue_details

        test_obj_id = "obj_clue_test"
        self.game_state.game_objects[test_obj_id] = {
            "id": test_obj_id, "name": "Dusty Scroll",
            "description": "An old scroll, perhaps containing secrets.",
            "hidden_clue_details": {
                "clue_text": "The password is 'OpenSesame'",
                "required_skill": "investigation",
                "dc": 12,
                "revealed": False
            }
        }
        # Player needs investigation skill
        self.player.ability_scores["intelligence"] = 15 # Modifier +2
        self.player.proficiencies_map["skills"].append("investigation")

        success, message = reveal_clue(self.player, test_obj_id, self.game_state)

        # For this test, we can't guarantee success due to dice roll.
        # Instead, we check if the logic runs and returns appropriate type of message.
        if success:
            self.assertEqual(message, "The password is 'OpenSesame'")
            self.assertIn("The password is 'OpenSesame'", self.player.discovered_clues)
            self.assertTrue(self.game_state.game_objects[test_obj_id]["hidden_clue_details"]["revealed"])
        else:
            self.assertIn("found nothing special", message)
            self.assertFalse(self.game_state.game_objects[test_obj_id]["hidden_clue_details"]["revealed"])


if __name__ == '__main__':
    unittest.main()
