from typing import Dict, Any

class Character:
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: Dict[str, Any], base_damage_dice: str):
        self.id = id
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.combat_stats = combat_stats
        self.base_damage_dice = base_damage_dice

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def take_damage(self, amount: int):
        self.current_hp -= amount
        if self.current_hp < 0:
            self.current_hp = 0

    def attack(self, target: 'Character') -> str:
        # Simple attack logic, can be expanded
        attack_roll = d20() + self.combat_stats.get('attack_bonus', 0)
        armor_class = target.combat_stats.get('armor_class', 10)

        if attack_roll >= armor_class:
            num_dice, dice_sides = map(int, self.base_damage_dice.replace('d', ' ').split())
            dmg_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
            damage = dmg_roll + self.combat_stats.get('damage_bonus', 0)
            target.take_damage(damage)
            return f"{self.name} attacks {target.name} for {damage} damage."
        else:
            return f"{self.name}'s attack misses {target.name}."