from typing import Dict, Any, TYPE_CHECKING
from utils import roll_dice

if TYPE_CHECKING:
    from game_state import GameState

class Character:
    def __init__(self, id: str, name: str, max_hp: int, combat_stats: Dict[str, Any], base_damage_dice: str):
        self.id = id
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.combat_stats = combat_stats
        self.base_damage_dice = base_damage_dice
        self.status_effects = []

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def take_damage(self, amount: int):
        self.current_hp -= amount
        if self.current_hp < 0:
            self.current_hp = 0

    def heal(self, amount: int):
        """HP 회복"""
        self.current_hp = min(self.current_hp + amount, self.max_hp)

    def apply_status_effect(self, effect: dict):
        """상태 효과 적용"""
        self.status_effects.append(effect)

    def tick_status_effects(self) -> list[str]:
        """상태 효과 처리"""
        messages = []
        effects_to_remove = []
        
        for effect in self.status_effects:
            # 효과 처리 로직
            effect['duration'] -= 1
            if effect['duration'] <= 0:
                effects_to_remove.append(effect)
        
        for effect in effects_to_remove:
            self.status_effects.remove(effect)
        
        return messages

    def attack(self, target: 'Character') -> str:
        # Simple attack logic, can be expanded
        attack_roll = roll_dice(20) + self.combat_stats.get('attack_bonus', 0)
        armor_class = target.combat_stats.get('armor_class', 10)

        if attack_roll >= armor_class:
            # Parse dice notation (e.g., "2d6" -> num_dice=2, dice_sides=6)
            dice_parts = self.base_damage_dice.split('d')
            num_dice = int(dice_parts[0])
            dice_sides = int(dice_parts[1])
            dmg_roll = roll_dice(sides=dice_sides, num_dice=num_dice)
            damage = dmg_roll + self.combat_stats.get('damage_bonus', 0)
            target.take_damage(damage)
            return f"{self.name} attacks {target.name} for {damage} damage."
        else:
            return f"{self.name}'s attack misses {target.name}."