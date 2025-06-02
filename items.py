import logging

class Item:
    """ Base class for all items. """
    def __init__(self, id: str, name: str, item_type: str, description: str = "",
                 weight: float = 0.0, value: dict = None, lore_keywords: list[str] = None):
        if not id or not isinstance(id, str): raise ValueError("Item ID must be a non-empty string.")
        if not name or not isinstance(name, str): raise ValueError("Item name must be a non-empty string.")
        self.id = id
        self.name = name
        self.item_type = item_type
        self.description = description
        self.weight = weight
        self.value = value if value is not None else {"buy": 0, "sell": 0}
        self.lore_keywords = lore_keywords if lore_keywords is not None else []
    def __repr__(self): return f"<Item(id='{self.id}', name='{self.name}', type='{self.item_type}')>"

class Weapon(Item):
    """ Weapon item. """
    def __init__(self, id: str, name: str, damage_dice: str, description: str = "",
                 attack_bonus: int = 0, damage_bonus: int = 0,
                 weapon_type: str = "sword", weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, "weapon", description, weight, value, lore_keywords)
        if not damage_dice or not isinstance(damage_dice, str): raise ValueError("Weapon damage_dice must be a non-empty string.")
        self.damage_dice = damage_dice
        self.attack_bonus = attack_bonus
        self.damage_bonus = damage_bonus
        self.weapon_type = weapon_type
    def __repr__(self): return f"<Weapon(id='{self.id}', name='{self.name}', damage='{self.damage_dice}')>"

class Armor(Item):
    """ Armor item. """
    def __init__(self, id: str, name: str, ac_bonus: int, description: str = "",
                 armor_type: str = "medium",
                 weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, "armor", description, weight, value, lore_keywords)
        if not isinstance(ac_bonus, int): raise ValueError("Armor ac_bonus must be an integer.")
        self.ac_bonus = ac_bonus
        self.armor_type = armor_type
    def __repr__(self): return f"<Armor(id='{self.id}', name='{self.name}', ac_bonus='{self.ac_bonus}')>"

class Consumable(Item):
    """ Consumable item. """
    def __init__(self, id: str, name: str, effects: list[dict], description: str = "",
                 weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, "consumable", description, weight, value, lore_keywords)
        if not isinstance(effects, list): raise ValueError("Consumable effects must be a list.")
        self.effects = effects
    def __repr__(self): return f"<Consumable(id='{self.id}', name='{self.name}', effects_count='{len(self.effects)}')>"

class KeyItem(Item):
    """ Key item. """
    def __init__(self, id: str, name: str, item_type: str = "key_item", description: str = "", # item_type default for KeyItem
                 unlocks: list[str] = None, weight: float = 0.0, value: dict = None,
                 lore_keywords: list[str] = None):
        super().__init__(id, name, item_type, description, weight, value, lore_keywords)
        self.unlocks = unlocks if unlocks is not None else []
    def __repr__(self): return f"<KeyItem(id='{self.id}', name='{self.name}')>"

# ITEM_DATABASE definition - this was originally in game_state.py
# If Player class (now in characters.py) or other modules need direct access
# to a global item registry, it could be defined and populated here or in game_state.py.
# For now, GameState will own the primary registry of items (self.items).
# If Player class directly used a global ITEM_DATABASE, that would need careful handling.
# The current Player class uses _get_item_from_game_state(item_id, game_state) which is better.
# So, a global ITEM_DATABASE in items.py is probably not needed.
# The test_combat.py uses an ITEM_DATABASE import from game_state. This will need to be addressed.
# For now, I'll define it here as empty, and tests might need adjustment or game_state.py needs to provide it.
ITEM_DATABASE: dict[str, Item] = {}
