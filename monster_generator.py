import random
import uuid # For generating unique IDs
from generated_monster import GeneratedMonster
from typing import Any, Dict, List, Optional
from character import Character

# Helper function to safely get nested dictionary values
def get_nested_value(data_dict: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    current = data_dict
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current

class MonsterGenerator:
    def __init__(self, race_templates: List[Dict[str, Any]],
                 attribute_templates: List[Dict[str, Any]],
                 role_templates: List[Dict[str, Any]]):
        self.race_templates = {r['id']: r for r in race_templates}
        self.attribute_templates = {a['id']: a for a in attribute_templates}
        self.role_templates = {r['id']: r for r in role_templates}

    def _select_race(self, race_id: Optional[str] = None) -> Dict[str, Any]:
        if race_id and race_id in self.race_templates:
            return self.race_templates[race_id]
        return random.choice(list(self.race_templates.values()))

    def _select_attributes(self, selected_race: Dict[str, Any],
                           attribute_ids: Optional[List[str]] = None,
                           difficulty_level: Optional[int] = None) -> List[Dict[str, Any]]:
        selected_attributes = []
        if attribute_ids:
            for attr_id in attribute_ids:
                if attr_id in self.attribute_templates:
                    selected_attributes.append(self.attribute_templates[attr_id])
            return selected_attributes

        possible_tags = get_nested_value(selected_race, ['possible_attribute_tags'], [])
        if not possible_tags:
            return []

        num_attributes = 1
        if difficulty_level:
            if difficulty_level >= 7:
                num_attributes = random.randint(2, 3)
            elif difficulty_level >= 4:
                num_attributes = random.randint(1, 2)

        eligible_attributes = [attr for attr in self.attribute_templates.values() if attr['id'] in possible_tags]
        if not eligible_attributes:
             eligible_attributes = list(self.attribute_templates.values())

        k = min(num_attributes, len(eligible_attributes))
        return random.sample(eligible_attributes, k)

    def _select_role(self, selected_race: Dict[str, Any],
                     role_id: Optional[str] = None,
                     difficulty_level: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if role_id and role_id in self.role_templates:
            return self.role_templates[role_id]

        possible_tags = get_nested_value(selected_race, ['possible_role_tags'], [])
        if not possible_tags:
            return random.choice(list(self.role_templates.values())) if self.role_templates else None

        eligible_roles = [role for role in self.role_templates.values() if role['id'] in possible_tags]
        if not eligible_roles:
            return random.choice(list(self.role_templates.values())) if self.role_templates else None

        return random.choice(eligible_roles)

    def _generate_name(self, race: Dict[str, Any], attributes: List[Dict[str, Any]], role: Optional[Dict[str, Any]]) -> str:
        parts = []
        for attr in attributes:
            if 'name_prefix_kr' in attr:
                parts.append(attr['name_prefix_kr'])

        parts.append(race.get('name_kr', '알 수 없는 종족'))

        if role and 'name_kr' in role:
            parts.append(role['name_kr'])

        for attr in attributes:
            if 'name_suffix_kr' in attr:
                parts.append(attr['name_suffix_kr'])

        return " ".join(parts)

    def _generate_description(self, race: Dict[str, Any], attributes: List[Dict[str, Any]], role: Optional[Dict[str, Any]]) -> str:
        desc_parts = [race.get('description_base', "정체를 알 수 없는 존재입니다.")]

        for attr in attributes:
            if 'description_fragment' in attr:
                desc_parts.append(attr['description_fragment'])

        if role and 'description_fragment' in role:
            desc_parts.append(role['description_fragment'])

        if len(desc_parts) > 1:
            base = desc_parts[0]
            modifiers = " ".join(desc_parts[1:])
            return f"{base} {modifiers}"
        return desc_parts[0]

    def _calculate_combat_stats(self, race: Dict[str, Any], attributes: List[Dict[str, Any]], role: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], int, str]:
        final_stats = {k: v for k, v in get_nested_value(race, ['base_combat_stats'], {}).items()}

        final_stats.setdefault('hp', 10)
        final_stats.setdefault('ac', 10)
        final_stats.setdefault('attack_bonus', 0)
        final_stats.setdefault('damage_bonus', 0)
        final_stats.setdefault('speed', 30)

        base_damage_dice = final_stats.pop('damage_dice', race.get('base_combat_stats', {}).get('damage_dice', '1d4'))
        max_hp = final_stats.pop('hp')

        for attr in attributes:
            modifiers = get_nested_value(attr, ['stat_modifiers'], {})
            if 'hp_multiplier' in modifiers:
                max_hp = int(max_hp * modifiers['hp_multiplier'])
            if 'hp_add' in modifiers:
                max_hp += modifiers['hp_add']
            if 'ac_add' in modifiers:
                final_stats['ac'] += modifiers['ac_add']
            if 'attack_bonus_add' in modifiers:
                final_stats['attack_bonus'] += modifiers['attack_bonus_add']
            if 'damage_bonus_add' in modifiers:
                final_stats['damage_bonus'] += modifiers['damage_bonus_add']
            if 'speed_add' in modifiers:
                final_stats['speed'] += modifiers['speed_add']

        if role:
            modifiers = get_nested_value(role, ['stat_modifiers'], {})
            if 'hp_multiplier' in modifiers:
                max_hp = int(max_hp * modifiers['hp_multiplier'])
            if 'hp_add' in modifiers:
                max_hp += modifiers['hp_add']
            if 'ac_add' in modifiers:
                final_stats['ac'] += modifiers['ac_add']
            if 'ac_shield_bonus_add' in modifiers:
                final_stats['ac'] += modifiers['ac_shield_bonus_add']
            if 'attack_bonus_add' in modifiers:
                final_stats['attack_bonus'] += modifiers['attack_bonus_add']
            if 'attack_bonus_melee_add' in modifiers:
                final_stats['attack_bonus'] += modifiers['attack_bonus_melee_add']
            if 'attack_bonus_ranged_add' in modifiers:
                final_stats['attack_bonus'] += modifiers['attack_bonus_ranged_add']
            if 'damage_bonus_add' in modifiers:
                 final_stats['damage_bonus'] += modifiers['damage_bonus_add']
            if 'speed_add' in modifiers:
                final_stats['speed'] += modifiers['speed_add']

        if 'ac' in final_stats:
            final_stats['armor_class'] = final_stats.pop('ac')

        return final_stats, max_hp, base_damage_dice

    def _collect_abilities_etc(self, race: Dict[str, Any], attributes: List[Dict[str, Any]], role: Optional[Dict[str, Any]]) -> tuple[List[str], List[str], List[str]]:
        special_abilities = get_nested_value(race, ['inherent_abilities'], [])[:]
        resistances = get_nested_value(race, ['inherent_resistances'], [])[:]
        vulnerabilities = get_nested_value(race, ['inherent_vulnerabilities'], [])[:]

        for attr in attributes:
            special_abilities.extend(get_nested_value(attr, ['added_abilities'], []))
            resistances.extend(get_nested_value(attr, ['added_resistances'], []))
            vulnerabilities.extend(get_nested_value(attr, ['added_vulnerabilities'], []))

        if role:
            special_abilities.extend(get_nested_value(role, ['abilities'], []))

        return list(set(special_abilities)), list(set(resistances)), list(set(vulnerabilities))

    def _determine_loot_tags(self, race: Dict[str, Any], attributes: List[Dict[str, Any]], role: Optional[Dict[str, Any]]) -> List[str]:
        tags = []
        tags.extend(get_nested_value(race, ['loot_tags'], []))
        for attr in attributes:
            tags.extend(get_nested_value(attr, ['loot_tags'], []))
        if role:
            tags.extend(get_nested_value(role, ['loot_tags'], []))

        tags.append(f"race_{race.get('id','unknown')}")
        for attr in attributes:
            tags.append(f"attr_{attr.get('id','unknown')}")
        if role:
            tags.append(f"role_{role.get('id','unknown')}")

        return list(set(tags))

    def _generate_unique_id(self, name_parts: List[str]) -> str:
        base_name = "_".join(part.lower() for part in name_parts if part)
        return f"gen_{base_name}_{uuid.uuid4().hex[:6]}"

    def generate_monster(self, race_id: Optional[str] = None,
                         attribute_ids: Optional[List[str]] = None,
                         role_id: Optional[str] = None,
                         difficulty_level: Optional[int] = None) -> Optional[GeneratedMonster]:

        selected_race = self._select_race(race_id)
        if not selected_race: return None

        selected_attributes = self._select_attributes(selected_race, attribute_ids, difficulty_level)
        selected_role = self._select_role(selected_race, role_id, difficulty_level)

        monster_name_kr = self._generate_name(selected_race, selected_attributes, selected_role)
        monster_description_kr = self._generate_description(selected_race, selected_attributes, selected_role)

        combat_stats, max_hp, base_damage_dice = self._calculate_combat_stats(selected_race, selected_attributes, selected_role)

        special_abilities, resistances, vulnerabilities = self._collect_abilities_etc(selected_race, selected_attributes, selected_role)

        type_parts = ["monster_generated"]
        type_parts.append(selected_race.get('id', 'unknown'))
        if selected_role:
             type_parts.append(selected_role.get('id', 'unknown'))
        monster_type = "_".join(type_parts)

        loot_table_tags = self._determine_loot_tags(selected_race, selected_attributes, selected_role)

        name_id_parts = [selected_race.get('id')]
        if selected_role: name_id_parts.append(selected_role.get('id'))
        monster_id = self._generate_unique_id(name_id_parts)

        threat_level = (max_hp / 10) + combat_stats.get('attack_bonus',0) + (combat_stats.get('armor_class',10) / 2)
        combat_stats['threat_level'] = round(threat_level, 1)

        return GeneratedMonster(
            id=monster_id,
            name_kr=monster_name_kr,
            description_kr=monster_description_kr,
            combat_stats=combat_stats,
            max_hp=max_hp,
            base_damage_dice=base_damage_dice,
            special_abilities=special_abilities,
            resistances=resistances,
            vulnerabilities=vulnerabilities,
            monster_type=monster_type,
            loot_table_tags=loot_table_tags
        )

if __name__ == '__main__':
    RACES = [
        {"id": "orc", "name_kr": "오크", "description_base": "녹색 피부의 호전적인", "base_combat_stats": {"hp": 60, "ac": 13, "attack_bonus": 5, "damage_dice": "1d12+3", "speed": 30}, "inherent_abilities": ["강인함"], "possible_attribute_tags": ["strong", "swift"], "possible_role_tags": ["warrior", "brute"]},
        {"id": "goblin", "name_kr": "고블린", "description_base": "작고 비열한", "base_combat_stats": {"hp": 20, "ac": 12, "attack_bonus": 3, "damage_dice": "1d6+1", "speed": 30}, "inherent_abilities": ["매복"], "possible_attribute_tags": ["swift", "sly"], "possible_role_tags": ["scout", "archer"]}
    ]
    ATTRIBUTES = [
        {"id": "swift", "name_prefix_kr": "재빠른", "description_fragment": "날렵한 움직임의", "stat_modifiers": {"speed_add": 10, "ac_add": 1}, "added_abilities": ["회피 기동"]},
        {"id": "strong", "name_prefix_kr": "강력한", "description_fragment": "엄청난 힘을 지닌", "stat_modifiers": {"hp_add": 10, "damage_bonus_add": 2}, "added_abilities": ["파워 어택"]},
        {"id": "sly", "name_prefix_kr": "교활한", "description_fragment": "음흉한 계략을 꾸미는", "stat_modifiers": {"attack_bonus_add": 1}, "added_abilities": ["기만 전술"]}
    ]
    ROLES = [
        {"id": "warrior", "name_kr": "전사", "description_fragment": "용맹한 전사.", "stat_modifiers": {"hp_add": 10, "attack_bonus_melee_add": 2}, "abilities": ["방패 올리기"]},
        {"id": "scout", "name_kr": "척후병", "description_fragment": "민첩한 척후병.", "stat_modifiers": {"speed_add": 5, "initiative_bonus_add": 2}, "abilities": ["은신"]}
    ]

    generator = MonsterGenerator(race_templates=RACES, attribute_templates=ATTRIBUTES, role_templates=ROLES)

    print("--- Generating Random Monster (No Params) ---")
    random_monster = generator.generate_monster()
    if random_monster:
        print(f"ID: {random_monster.id}, Name: {random_monster.name}, HP: {random_monster.max_hp}, AC: {random_monster.combat_stats.get('armor_class')}")
        print(f"Desc: {random_monster.description_kr}")
        print(f"Abilities: {random_monster.special_abilities}")
        print(f"Stats: {random_monster.combat_stats}")
        print(f"Threat: {random_monster.combat_stats.get('threat_level')}")

    print("\n--- Generating Orc Warrior (Specific IDs) ---")
    orc_warrior = generator.generate_monster(race_id="orc", attribute_ids=["strong"], role_id="warrior")
    if orc_warrior:
        print(f"ID: {orc_warrior.id}, Name: {orc_warrior.name}, HP: {orc_warrior.max_hp}, AC: {orc_warrior.combat_stats.get('armor_class')}")
        print(f"Desc: {orc_warrior.description_kr}")
        print(f"Abilities: {orc_warrior.special_abilities}")
        print(f"Stats: {orc_warrior.combat_stats}")
        print(f"Threat: {orc_warrior.combat_stats.get('threat_level')}")

    print("\n--- Generating Goblin Scout (High Difficulty) ---")
    goblin_scout_hard = generator.generate_monster(race_id="goblin", role_id="scout", difficulty_level=8)
    if goblin_scout_hard:
        print(f"ID: {goblin_scout_hard.id}, Name: {goblin_scout_hard.name}, HP: {goblin_scout_hard.max_hp}, AC: {goblin_scout_hard.combat_stats.get('armor_class')}")
        print(f"Desc: {goblin_scout_hard.description_kr}")
        print(f"Abilities: {goblin_scout_hard.special_abilities}")
        print(f"Attributes used: {len(goblin_scout_hard.loot_table_tags) - 2}")
        print(f"Stats: {goblin_scout_hard.combat_stats}")
        print(f"Threat: {goblin_scout_hard.combat_stats.get('threat_level')}")

    print("\n--- Generating Monster with only race (ensure it works) ---")
    orc_only = generator.generate_monster(race_id="orc", attribute_ids=[], role_id=None)
    if orc_only:
        print(f"ID: {orc_only.id}, Name: {orc_only.name}, HP: {orc_only.max_hp}, AC: {orc_only.combat_stats.get('armor_class')}")
        print(f"Desc: {orc_only.description_kr}")
        print(f"Abilities: {orc_only.special_abilities}")
        print(f"Stats: {orc_only.combat_stats}")
