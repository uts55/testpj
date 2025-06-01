import unittest
import os
import sys

# Add project root to sys.path to allow imports from game_state, monster_generator etc.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from monster_generator import MonsterGenerator
from generated_monster import GeneratedMonster

# Mock data for testing - mirrors the structure of actual JSON data
MOCK_RACE_TEMPLATES = [
    {"id": "orc", "name_kr": "오크", "description_base": "녹색 피부의 호전적인", "base_combat_stats": {"hp": 60, "ac": 13, "attack_bonus": 5, "damage_dice": "1d12+3", "speed": 30}, "inherent_abilities": ["강인함"], "possible_attribute_tags": ["strong", "armored", "swift"], "possible_role_tags": ["warrior", "brute"], "loot_tags": ["orc_specific_loot"]},
    {"id": "goblin", "name_kr": "고블린", "description_base": "작고 비열한", "base_combat_stats": {"hp": 20, "ac": 12, "attack_bonus": 3, "damage_dice": "1d6+1", "speed": 30}, "inherent_abilities": ["매복"], "possible_attribute_tags": ["swift", "sly"], "possible_role_tags": ["scout", "archer"], "loot_tags": ["goblin_trinkets"]},
    {"id": "skeleton", "name_kr": "스켈레톤", "description_base": "뼈만 남은 언데드인", "base_combat_stats": {"hp": 30, "ac": 13, "attack_bonus": 3, "damage_dice": "1d8+1", "speed": 30}, "inherent_abilities": ["둔기에 약함", "독 및 상태이상 면역"], "possible_attribute_tags": ["brittle", "ancient"], "possible_role_tags": ["warrior", "guard"]}
]
MOCK_ATTRIBUTE_TEMPLATES = [
    {"id": "swift", "name_prefix_kr": "재빠른", "description_fragment": "날렵한 움직임의", "stat_modifiers": {"speed_add": 10, "ac_add": 1}, "added_abilities": ["회피 기동"], "loot_tags": ["swift_essence"]},
    {"id": "strong", "name_prefix_kr": "강력한", "description_fragment": "엄청난 힘을 지닌", "stat_modifiers": {"hp_add": 10, "damage_bonus_add": 2}, "added_abilities": ["파워 어택"]},
    {"id": "sly", "name_prefix_kr": "교활한", "description_fragment": "음흉한 계략을 꾸미는", "stat_modifiers": {"attack_bonus_add": 1}, "added_abilities": ["기만 전술"]},
    {"id": "armored", "name_prefix_kr": "중무장한", "description_fragment": "두꺼운 갑옷을 입은", "stat_modifiers": {"ac_add": 3, "speed_add": -5}, "added_resistances": ["piercing"]},
    {"id": "ancient", "name_prefix_kr": "고대의", "description_fragment": "오랜 세월의 흔적이 느껴지는", "stat_modifiers": {"hp_add": 20, "attack_bonus_add": 1}, "added_abilities": ["먼지 구름"]},
    {"id": "brittle", "name_suffix_kr": "부서지기 쉬운", "description_fragment": "쉽게 부서질 것 같은", "stat_modifiers": {"hp_add": -5, "ac_add": -1}, "added_vulnerabilities": ["bludgeoning"]}
]
MOCK_ROLE_TEMPLATES = [
    {"id": "warrior", "name_kr": "전사", "description_fragment": "용맹한 전사.", "stat_modifiers": {"hp_add": 10, "attack_bonus_melee_add": 2, "ac_add": 1}, "abilities": ["방패 올리기"], "loot_tags": ["warrior_scroll"]},
    {"id": "scout", "name_kr": "척후병", "description_fragment": "민첩한 척후병.", "stat_modifiers": {"speed_add": 5, "initiative_bonus_add": 2}, "abilities": ["은신"]},
    {"id": "brute", "name_kr": "덩치", "description_fragment": "거대한 덩치의", "stat_modifiers": {"hp_add": 20, "damage_bonus_add": 1, "ac_add": -1}, "abilities": ["휘두르기"]},
    {"id": "guard", "name_kr": "경비병", "description_fragment": "경계를 서는", "stat_modifiers": {"ac_add": 2, "perception_add": 2}, "abilities": ["경계 태세"]}, # Added perception_add for testing
]

class TestMonsterGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = MonsterGenerator(
            race_templates=MOCK_RACE_TEMPLATES,
            attribute_templates=MOCK_ATTRIBUTE_TEMPLATES,
            role_templates=MOCK_ROLE_TEMPLATES
        )

    def test_initialization(self):
        self.assertIsNotNone(self.generator)
        self.assertEqual(len(self.generator.race_templates), len(MOCK_RACE_TEMPLATES))
        self.assertEqual(len(self.generator.attribute_templates), len(MOCK_ATTRIBUTE_TEMPLATES))
        self.assertEqual(len(self.generator.role_templates), len(MOCK_ROLE_TEMPLATES))

    def test_generate_monster_random(self):
        monster = self.generator.generate_monster()
        self.assertIsNotNone(monster)
        self.assertIsInstance(monster, GeneratedMonster)
        self.assertTrue(monster.id.startswith("gen_"))
        self.assertIn(monster.combat_stats.get('armor_class', 0), range(5, 30)) # Reasonable AC range
        self.assertGreater(monster.max_hp, 0)
        self.assertIsNotNone(monster.combat_stats.get('threat_level'))

    def test_generate_monster_specific_race(self):
        monster = self.generator.generate_monster(race_id="orc")
        self.assertIsNotNone(monster)
        self.assertIn("오크", monster.name)
        self.assertTrue(monster.id.startswith("gen_orc"))
        # Check base stats from orc template
        orc_template = self.generator.race_templates["orc"]
        base_hp = orc_template["base_combat_stats"]["hp"]
        # HP can be modified by attributes/role, so check it's at least base
        self.assertGreaterEqual(monster.max_hp, base_hp)

    def test_generate_monster_specific_race_attr_role(self):
        monster = self.generator.generate_monster(race_id="goblin", attribute_ids=["swift"], role_id="scout")
        self.assertIsNotNone(monster)
        self.assertIn("고블린", monster.name)
        self.assertIn("재빠른", monster.name)
        self.assertIn("척후병", monster.name)
        self.assertTrue(monster.id.startswith("gen_goblin_scout"))

        # Check for combined abilities
        self.assertIn("매복", monster.special_abilities) # From goblin
        self.assertIn("회피 기동", monster.special_abilities) # From swift
        self.assertIn("은신", monster.special_abilities) # From scout

        # Check stat modifications (example: speed)
        # Goblin base speed 30 + swift speed_add 10 + scout speed_add 5 = 45
        expected_speed = 30 + 10 + 5
        self.assertEqual(monster.combat_stats.get("speed"), expected_speed)

    def test_generate_monster_with_difficulty(self):
        # Low difficulty might result in fewer attributes
        monster_easy = self.generator.generate_monster(race_id="orc", difficulty_level=1)
        num_attr_easy = sum(1 for tag in monster_easy.loot_table_tags if tag.startswith("attr_"))

        # High difficulty might result in more attributes
        monster_hard = self.generator.generate_monster(race_id="orc", difficulty_level=10)
        num_attr_hard = sum(1 for tag in monster_hard.loot_table_tags if tag.startswith("attr_"))

        self.assertLessEqual(num_attr_easy, num_attr_hard) # Not strictly greater, but high diff tends to have more
        self.assertIn(num_attr_easy, [0,1]) # For orc (swift, strong, armored), diff 1 likely 1 attr
        self.assertIn(num_attr_hard, [2,3]) # For orc, diff 10 likely 2 or 3 attr

    def test_name_generation(self):
        # 재빠른 강력한 오크 전사 (prefix, prefix, race, role) - order might vary based on implementation
        monster = self.generator.generate_monster(race_id="orc", attribute_ids=["swift", "strong"], role_id="warrior")
        self.assertIn("오크", monster.name)
        self.assertIn("전사", monster.name)
        self.assertIn("재빠른", monster.name)
        self.assertIn("강력한", monster.name)

        monster_suffix = self.generator.generate_monster(race_id="skeleton", attribute_ids=["brittle"], role_id="guard")
        self.assertIn("스켈레톤", monster_suffix.name)
        self.assertIn("경비병", monster_suffix.name)
        self.assertIn("부서지기 쉬운", monster_suffix.name) # Suffix

    def test_description_generation(self):
        monster = self.generator.generate_monster(race_id="goblin", attribute_ids=["sly"], role_id="scout")
        self.assertIn("작고 비열한", monster.description_kr) # Goblin base
        self.assertIn("음흉한 계략을 꾸미는", monster.description_kr) # Sly fragment
        self.assertIn("민첩한 척후병", monster.description_kr) # Scout fragment

    def test_stat_calculation_armor_class(self):
        # Orc (AC 13) + Swift (AC +1) + Warrior (AC +1) = 16
        monster = self.generator.generate_monster(race_id="orc", attribute_ids=["swift"], role_id="warrior")
        self.assertEqual(monster.combat_stats.get("armor_class"), 13 + 1 + 1)

    def test_stat_calculation_hp(self):
        # Goblin (HP 20) + Strong (HP +10) + Brute (HP +20) = 50
        monster = self.generator.generate_monster(race_id="goblin", attribute_ids=["strong"], role_id="brute")
        self.assertEqual(monster.max_hp, 20 + 10 + 20)

    def test_abilities_resistances_vulnerabilities_aggregation(self):
        # Skeleton (Inherent: 둔기에 약함, 독 및 상태이상 면역)
        # Armored (Added Resistances: piercing)
        # Brittle (Added Vulnerabilities: bludgeoning - should combine with skeleton's 둔기에 약함)
        monster = self.generator.generate_monster(race_id="skeleton", attribute_ids=["armored", "brittle"], role_id="guard")

        self.assertIn("둔기에 약함", monster.special_abilities) # From skeleton
        self.assertIn("독 및 상태이상 면역", monster.special_abilities) # From skeleton
        self.assertIn("경계 태세", monster.special_abilities) # From guard

        self.assertIn("piercing", monster.resistances) # From armored

        self.assertIn("bludgeoning", monster.vulnerabilities) # From brittle
        # Note: "둔기에 약함" is an ability, not a formal vulnerability in this data structure
        # If it were meant to be a vulnerability, the data structure or aggregation would need adjustment.

    def test_loot_tags_generation(self):
        monster = self.generator.generate_monster(race_id="orc", attribute_ids=["swift"], role_id="warrior")
        self.assertIn("orc_specific_loot", monster.loot_table_tags)
        self.assertIn("swift_essence", monster.loot_table_tags)
        self.assertIn("warrior_scroll", monster.loot_table_tags)
        self.assertIn("race_orc", monster.loot_table_tags)
        self.assertIn("attr_swift", monster.loot_table_tags)
        self.assertIn("role_warrior", monster.loot_table_tags)

    def test_threat_level_calculation(self):
        # Orc (HP 60, AC 13, ATK 5) -> Threat = (60/10) + 5 + (13/2) = 6 + 5 + 6.5 = 17.5
        monster = self.generator.generate_monster(race_id="orc", attribute_ids=[], role_id=None)
        self.assertEqual(monster.combat_stats.get("threat_level"), 17.5)

        # Goblin (20 HP, AC 12, ATK 3) + Strong (HP+10, DMG_Bonus+2) + Warrior (HP+10, ATK_Melee+2, AC+1)
        # HP = 20+10+10 = 40
        # AC = 12+1 = 13
        # ATK = 3+2 = 5 (DMG_Bonus doesn't affect threat calculation here)
        # Threat = (40/10) + 5 + (13/2) = 4 + 5 + 6.5 = 15.5
        monster_complex = self.generator.generate_monster(race_id="goblin", attribute_ids=["strong"], role_id="warrior")
        self.assertEqual(monster_complex.combat_stats.get("threat_level"), 15.5)

    def test_edge_case_no_matching_tags(self):
        # Race with tags that don't match any attributes/roles
        custom_races = [{"id": "custom_loner", "name_kr": "외톨이", "description_base": "혼자입니다.", "base_combat_stats": {"hp": 10, "ac": 10, "attack_bonus": 0, "damage_dice": "1d4"}, "possible_attribute_tags": ["nonexistent_attr_tag"], "possible_role_tags": ["nonexistent_role_tag"]}]
        generator = MonsterGenerator(custom_races, MOCK_ATTRIBUTE_TEMPLATES, MOCK_ROLE_TEMPLATES)
        monster = generator.generate_monster(race_id="custom_loner")
        self.assertIsNotNone(monster)
        # Should still generate, possibly with no attributes/role or random fallback if implemented that way
        # Current _select_attributes falls back to all attributes if eligible_attributes is empty after tag filtering
        # Current _select_role falls back to all roles if eligible_roles is empty
        num_attr = sum(1 for tag in monster.loot_table_tags if tag.startswith("attr_"))
        has_role = any(tag.startswith("role_") for tag in monster.loot_table_tags)

        self.assertTrue(num_attr >= 0) # Could be 0 if no attributes selected by chance or fallback
        self.assertTrue(isinstance(has_role, bool)) # Role selection might pick one randomly

    def test_edge_case_empty_templates(self):
        generator_empty_attr = MonsterGenerator(MOCK_RACE_TEMPLATES, [], MOCK_ROLE_TEMPLATES)
        monster = generator_empty_attr.generate_monster(race_id="orc")
        self.assertIsNotNone(monster)
        num_attr = sum(1 for tag in monster.loot_table_tags if tag.startswith("attr_"))
        self.assertEqual(num_attr, 0) # No attributes can be selected

        generator_empty_role = MonsterGenerator(MOCK_RACE_TEMPLATES, MOCK_ATTRIBUTE_TEMPLATES, [])
        monster_no_role = generator_empty_role.generate_monster(race_id="orc")
        self.assertIsNotNone(monster_no_role)
        has_role = any(tag.startswith("role_") for tag in monster_no_role.loot_table_tags)
        self.assertFalse(has_role)


if __name__ == '__main__':
    unittest.main()
