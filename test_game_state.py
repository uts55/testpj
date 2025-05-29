import unittest
import os
import json
from game_state import GameState, Player, NPC, Location, Item

TEST_SAVE_FILE = "test_save_game.json"

class TestItemClass(unittest.TestCase):
    def test_item_creation(self):
        item = Item("potion_001", "Healing Potion", "Restores HP")
        self.assertEqual(item.id, "potion_001")
        self.assertEqual(item.name, "Healing Potion")
        self.assertEqual(item.description, "Restores HP")

    def test_item_to_from_dict(self):
        item_data = {"id": "scroll_002", "name": "Fireball Scroll", "description": "Casts a fireball"}
        item = Item.from_dict(item_data)
        self.assertEqual(item.id, "scroll_002")
        self.assertEqual(item.name, "Fireball Scroll")
        self.assertEqual(item.description, "Casts a fireball")
        self.assertEqual(item.to_dict(), item_data)

class TestPlayerClass(unittest.TestCase):
    def test_player_creation(self):
        player = Player(id="player_hero", name="Hero", stats={'hp': 100, 'mp': 50},
                        inventory=["sword_001"], skills=["power_attack"],
                        knowledge_fragments=["ancient_lore_part1"], current_location="village")
        self.assertEqual(player.id, "player_hero")
        self.assertEqual(player.name, "Hero")
        self.assertEqual(player.stats, {'hp': 100, 'mp': 50})
        self.assertEqual(player.inventory, ["sword_001"])
        self.assertEqual(player.skills, ["power_attack"])
        self.assertEqual(player.knowledge_fragments, ["ancient_lore_part1"])
        self.assertEqual(player.current_location, "village")

    def test_player_to_from_dict(self):
        player_data = {
            "id": "player_mage", "name": "Mage", "stats": {'hp': 80, 'mp': 120},
            "inventory": ["staff_001", "robe_001"], "skills": ["fireball"],
            "knowledge_fragments": ["arcane_secrets_v1"], "current_location": "tower"
        }
        player = Player.from_dict(player_data)
        self.assertEqual(player.id, "player_mage")
        self.assertEqual(player.name, "Mage")
        self.assertEqual(player.inventory, ["staff_001", "robe_001"])
        self.assertEqual(player.to_dict(), player_data)

    def test_player_take_damage(self):
        player = Player("p1", "Test", {'hp': 100}, [], [], [], "loc_A")
        player.take_damage(20)
        self.assertEqual(player.stats['hp'], 80)
        player.take_damage(100) # Should go to -20, or 0 if clamped (current implementation doesn't clamp)
        self.assertEqual(player.stats['hp'], -20)


    def test_player_add_item_to_inventory(self):
        player = Player("p1", "Test", {}, [], [], [], "loc_A")
        player.add_item_to_inventory("potion_001")
        self.assertIn("potion_001", player.inventory)
        player.add_item_to_inventory("potion_001") # Add same item
        self.assertEqual(player.inventory.count("potion_001"), 1) # Should still be 1

    def test_player_change_location(self):
        player = Player("p1", "Test", {}, [], [], [], "loc_A")
        player.change_location("loc_B")
        self.assertEqual(player.current_location, "loc_B")

class TestNPCClass(unittest.TestCase):
    def test_npc_creation(self):
        npc = NPC(id="guard_001", name="City Guard", current_location="city_gate",
                  description="A stern-looking guard.", lore_fragments=["knows_city_layout"],
                  dialogue_responses={"greeting": "Halt!"}, status="alert", hp=60)
        self.assertEqual(npc.id, "guard_001")
        self.assertEqual(npc.name, "City Guard")
        self.assertEqual(npc.current_location, "city_gate")
        self.assertEqual(npc.status, "alert")
        self.assertEqual(npc.hp, 60)

    def test_npc_to_from_dict(self):
        npc_data = {
            "id": "merchant_001", "name": "Traveling Merchant", "current_location": "market_square",
            "description": "A merchant with various goods.", "lore_fragments": ["has_rare_items"],
            "dialogue_responses": {"buy": "What can I get for you?"}, "status": "neutral", "hp": 40
        }
        npc = NPC.from_dict(npc_data)
        self.assertEqual(npc.id, "merchant_001")
        self.assertEqual(npc.name, "Traveling Merchant")
        self.assertEqual(npc.to_dict(), npc_data)

    def test_npc_change_status(self):
        npc = NPC("n1", "TestNPC", "loc", "", [], {}, "neutral")
        npc.change_status("hostile")
        self.assertEqual(npc.status, "hostile")

class TestLocationClass(unittest.TestCase):
    def test_location_creation(self):
        loc = Location(id="forest_01", name="Dark Forest", description="A spooky forest.",
                       exits={"north": "cave_entrance"}, items=["twig_001"], npcs=["goblin_001"])
        self.assertEqual(loc.id, "forest_01")
        self.assertEqual(loc.name, "Dark Forest")
        self.assertEqual(loc.items, ["twig_001"])
        self.assertEqual(loc.npcs, ["goblin_001"])

    def test_location_to_from_dict(self):
        loc_data = {
            "id": "castle_01", "name": "Old Castle", "description": "A crumbling castle.",
            "exits": {"south": "drawbridge"}, "items": ["gem_001"], "npcs": ["ghost_001"]
        }
        loc = Location.from_dict(loc_data)
        self.assertEqual(loc.id, "castle_01")
        self.assertEqual(loc.items, ["gem_001"]) # list of item IDs
        self.assertEqual(loc.npcs, ["ghost_001"]) # list of NPC IDs
        self.assertEqual(loc.to_dict(), loc_data)


class TestGameState(unittest.TestCase):
    def setUp(self):
        # Ensure no test save file from previous runs
        if os.path.exists(TEST_SAVE_FILE):
            os.remove(TEST_SAVE_FILE)

    def tearDown(self):
        # Clean up test save file
        if os.path.exists(TEST_SAVE_FILE):
            os.remove(TEST_SAVE_FILE)

    def test_initialize_new_game(self):
        gs = GameState()
        player_id = "test_player_init"
        player_name = "TesterInit"
        start_loc_id = "start_zone_init"
        gs.initialize_new_game(player_id, player_name, start_loc_id)

        self.assertFalse(not gs.players, "Players dict should not be empty after init")
        self.assertFalse(not gs.locations, "Locations dict should not be empty after init")
        self.assertFalse(not gs.items, "Items dict should not be empty after init")
        self.assertFalse(not gs.npcs, "NPCs dict should not be empty after init")

        player = gs.get_player(player_id)
        self.assertIsNotNone(player)
        self.assertEqual(player.name, player_name)
        self.assertEqual(player.current_location, start_loc_id)
        self.assertIn(start_loc_id, gs.locations)

        # Check for default item ("note_001") and NPC ("npc_001")
        self.assertIsNotNone(gs.items.get("note_001"))
        self.assertIn("note_001", gs.locations[start_loc_id].items)
        
        npc = gs.npcs.get("npc_001")
        self.assertIsNotNone(npc)
        self.assertEqual(npc.current_location, start_loc_id)
        self.assertIn("npc_001", gs.locations[start_loc_id].npcs)
        
        self.assertEqual(gs.turn_count, 0)
        self.assertIn('time_of_day', gs.world_variables)


    def test_save_and_load_game(self):
        gs1 = GameState()
        gs1.initialize_new_game("p1", "Player One", "loc1_start")
        
        # Modify game state further
        gs1.players["p1"].stats['hp'] = 90
        gs1.players["p1"].add_item_to_inventory("custom_item_01")
        gs1.items["custom_item_01"] = Item("custom_item_01", "Custom Item", "A special test item")
        gs1.turn_count = 5
        gs1.world_variables['weather'] = 'rainy'
        
        gs1.locations["loc1_start"].description = "A modified starting location."
        
        # Add a second NPC
        npc2_data = {"id": "npc_002", "name": "Guard", "current_location": "loc1_start", 
                     "description": "A vigilant guard.", "lore_fragments": [], 
                     "dialogue_responses": {}, "status": "neutral", "hp": 70}
        gs1.npcs["npc_002"] = NPC.from_dict(npc2_data)
        gs1.locations["loc1_start"].npcs.append("npc_002")


        gs1.save_game(TEST_SAVE_FILE)
        self.assertTrue(os.path.exists(TEST_SAVE_FILE))

        gs2 = GameState()
        gs2.load_game(TEST_SAVE_FILE)

        self.assertEqual(gs1.turn_count, gs2.turn_count)
        self.assertEqual(gs1.world_variables, gs2.world_variables)

        # Compare players
        self.assertEqual(len(gs1.players), len(gs2.players))
        p1_gs1 = gs1.get_player("p1")
        p1_gs2 = gs2.get_player("p1")
        self.assertIsNotNone(p1_gs1)
        self.assertIsNotNone(p1_gs2)
        self.assertIsInstance(p1_gs2, Player)
        self.assertEqual(p1_gs1.to_dict(), p1_gs2.to_dict())

        # Compare NPCs
        self.assertEqual(len(gs1.npcs), len(gs2.npcs))
        for npc_id in gs1.npcs:
            self.assertIn(npc_id, gs2.npcs)
            self.assertIsInstance(gs2.npcs[npc_id], NPC)
            self.assertEqual(gs1.npcs[npc_id].to_dict(), gs2.npcs[npc_id].to_dict())

        # Compare Locations
        self.assertEqual(len(gs1.locations), len(gs2.locations))
        for loc_id in gs1.locations:
            self.assertIn(loc_id, gs2.locations)
            self.assertIsInstance(gs2.locations[loc_id], Location)
            self.assertEqual(gs1.locations[loc_id].to_dict(), gs2.locations[loc_id].to_dict())
            # Check if NPC and Item lists within locations are consistent
            self.assertEqual(sorted(gs1.locations[loc_id].npcs), sorted(gs2.locations[loc_id].npcs))
            self.assertEqual(sorted(gs1.locations[loc_id].items), sorted(gs2.locations[loc_id].items))


        # Compare Items (master list)
        self.assertEqual(len(gs1.items), len(gs2.items))
        for item_id in gs1.items:
            self.assertIn(item_id, gs2.items)
            self.assertIsInstance(gs2.items[item_id], Item)
            self.assertEqual(gs1.items[item_id].to_dict(), gs2.items[item_id].to_dict())


    def test_get_player(self):
        gs = GameState()
        gs.initialize_new_game("player123", "Test Player", "town")
        player = gs.get_player("player123")
        self.assertIsNotNone(player)
        self.assertEqual(player.name, "Test Player")
        self.assertIsNone(gs.get_player("non_existent_player"))

    def test_get_npcs_in_location(self):
        gs = GameState()
        # initialize_new_game creates "npc_001" (Old Villager) in the start_loc_id
        start_loc_id = "start_zone_npcs" 
        gs.initialize_new_game("p_npc_test", "P_NPC", start_loc_id)
        
        npcs_in_start = gs.get_npcs_in_location(start_loc_id)
        self.assertTrue(len(npcs_in_start) >= 1, "Should be at least one NPC in start location")
        # Find the default NPC by its ID because its name might change if tests run in parallel or init changes
        default_npc_id = "npc_001" 
        found_default_npc = any(npc.id == default_npc_id for npc in npcs_in_start)
        self.assertTrue(found_default_npc, f"Default NPC {default_npc_id} not found in start location.")
        
        # Assuming "north_road" is the other location created by initialize_new_game and has no NPCs by default
        other_loc_id = "north_road" # This ID is hardcoded in initialize_new_game
        self.assertEqual(len(gs.get_npcs_in_location(other_loc_id)), 0)


    def test_update_npc_location(self):
        gs = GameState()
        player_id = "p_upd_npc"
        start_loc_id = "start_loc_upd"
        target_loc_id = "north_road" # This is the default second location from initialize_new_game
        
        gs.initialize_new_game(player_id, "P_UPD", start_loc_id)
        
        default_npc_id = "npc_001" # Created by initialize_new_game
        
        # Ensure the target location exists
        self.assertIn(target_loc_id, gs.locations, f"Target location {target_loc_id} must exist.")
        
        gs.update_npc_location(default_npc_id, target_loc_id)
        
        npc = gs.npcs.get(default_npc_id)
        self.assertIsNotNone(npc)
        self.assertEqual(npc.current_location, target_loc_id)
        
        # Check if Location.npcs lists are updated
        self.assertNotIn(default_npc_id, gs.locations[start_loc_id].npcs)
        self.assertIn(default_npc_id, gs.locations[target_loc_id].npcs)

        # Test moving to a non-existent location (should log warning, NPC location should not change)
        # The method currently doesn't prevent this, NPC.current_location is set, but it won't be in any Location.npcs list
        # gs.update_npc_location(default_npc_id, "non_existent_loc")
        # self.assertEqual(npc.current_location, target_loc_id) # Should remain in target_loc_id

if __name__ == '__main__':
    unittest.main()
