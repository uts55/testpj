from game_state import Character

class GeneratedMonster(Character):
    def __init__(self, id: str, name_kr: str, description_kr: str,
                 combat_stats: dict, special_abilities: list[str] | None = None,
                 resistances: list[str] | None = None, vulnerabilities: list[str] | None = None,
                 monster_type: str | None = None, loot_table_tags: list[str] | None = None,
                 max_hp: int = 10, base_damage_dice: str = "1d4"):
        super().__init__(id=id, name=name_kr, max_hp=max_hp,
                         combat_stats=combat_stats, base_damage_dice=base_damage_dice)
        self.description_kr = description_kr
        self.special_abilities = special_abilities if special_abilities is not None else []
        self.resistances = resistances if resistances is not None else []
        self.vulnerabilities = vulnerabilities if vulnerabilities is not None else []
        self.monster_type = monster_type
        self.loot_table_tags = loot_table_tags if loot_table_tags is not None else []

    def __repr__(self):
        return (f"<GeneratedMonster(id='{self.id}', name='{self.name}', "
                f"type='{self.monster_type}', hp='{self.current_hp}/{self.max_hp}')>")

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    sample_combat_stats_monster = {
        "armor_class": 15,
        "attack_bonus": 5,
        "damage_bonus": 2,
        "speed": 30,
        "initiative_bonus": 1,
    }
    monster = GeneratedMonster(
        id="gen_orc_001",
        name_kr="강력한 오크 전사",
        description_kr="매우 강력해 보이는 오크 전사입니다. 그의 눈에서 살기가 느껴집니다.",
        combat_stats=sample_combat_stats_monster,
        special_abilities=["분노", "강타"],
        resistances=["독"],
        vulnerabilities=["냉기"],
        monster_type="monster_generated_orc_warrior",
        loot_table_tags=["orc_common", "warrior_equipment"],
        max_hp=75,
        base_damage_dice="1d10+2"
    )
    print(f"Created Monster: {monster}")
    print(f"Name: {monster.name}")
    print(f"Description: {monster.description_kr}")
    print(f"HP: {monster.current_hp}/{monster.max_hp}")
    print(f"AC: {monster.combat_stats.get('armor_class')}")
    print(f"Attack Bonus: {monster.combat_stats.get('attack_bonus')}")
    print(f"Base Damage: {monster.base_damage_dice}")
    print(f"Special Abilities: {monster.special_abilities}")
    print(f"Resistances: {monster.resistances}")
    print(f"Vulnerabilities: {monster.vulnerabilities}")
    print(f"Type: {monster.monster_type}")
    print(f"Loot Tags: {monster.loot_table_tags}")
    print(f"Status Effects: {monster.status_effects}")

    monster.take_damage(10)
    print(f"HP after 10 damage: {monster.current_hp}")
    print(f"Is alive: {monster.is_alive()}")
    monster.heal(5)
    print(f"HP after 5 healing: {monster.current_hp}")
    print(monster.add_status_effect("맹독", 3, 2))
    print(f"Status Effects after adding: {monster.status_effects}")

    class DummyTarget(Character):
        def __init__(self, id="dummy", name="Dummy", max_hp=20, ac=10, dmg_dice="1d4"):
            super().__init__(id, name, max_hp, {"armor_class": ac, "attack_bonus": 0, "damage_bonus": 0}, dmg_dice)

    class DummyGameState:
        pass

    dummy_target = DummyTarget(ac=12)
    dummy_game_state = DummyGameState()

    print("\n--- Attack Demo ---")
    print(f"{monster.name} attacks {dummy_target.name} (AC: {dummy_target.combat_stats.get('armor_class')})")
    attack_result = monster.attack(dummy_target, dummy_game_state)
    print(attack_result)
    print(f"{dummy_target.name} HP after attack: {dummy_target.current_hp}/{dummy_target.max_hp}")

    print("\n--- Testing None for optional lists ---")
    monster_none_lists = GeneratedMonster(
        id="gen_gob_001",
        name_kr="초라한 고블린",
        description_kr="별 볼일 없어 보이는 고블린.",
        combat_stats={"armor_class": 10, "attack_bonus": 1, "speed": 30},
        max_hp=10,
        base_damage_dice="1d4",
        special_abilities=None,
        resistances=None,
        vulnerabilities=None,
        monster_type="monster_generated_goblin_common",
        loot_table_tags=None
    )
    print(f"Monster with None lists: {monster_none_lists}")
    print(f"Special Abilities: {monster_none_lists.special_abilities}")
    print(f"Resistances: {monster_none_lists.resistances}")
    print(f"Vulnerabilities: {monster_none_lists.vulnerabilities}")
    print(f"Loot Tags: {monster_none_lists.loot_table_tags}")
