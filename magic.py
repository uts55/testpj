class Spell:
    def __init__(self, name: str, level: int, casting_time: str, range_str: str, target_type: str, effect_type: str, dice_expression: str, stat_modifier_ability: str = None):
        self.name = name
        self.level = level
        self.casting_time = casting_time
        self.range_str = range_str
        self.target_type = target_type
        self.effect_type = effect_type
        self.dice_expression = dice_expression
        self.stat_modifier_ability = stat_modifier_ability

SPELLBOOK = {}

# Add Cure Light Wounds
SPELLBOOK["Cure Light Wounds"] = Spell(
    name="Cure Light Wounds",
    level=1,
    casting_time="1 action",
    range_str="Touch",
    target_type="ally",
    effect_type="heal",
    dice_expression="1d4",
    stat_modifier_ability="wisdom"
)

# Add Fire Bolt
SPELLBOOK["Fire Bolt"] = Spell(
    name="Fire Bolt",
    level=1,
    casting_time="1 action",
    range_str="120 feet",
    target_type="enemy",
    effect_type="damage",
    dice_expression="1d6",
    stat_modifier_ability=None
)
