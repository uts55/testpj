# utils.py
import random

# Mapping of skills to their primary ability scores
SKILL_ABILITY_MAP = {
    "athletics": "strength",
    "acrobatics": "dexterity",
    "slight_of_hand": "dexterity",
    "lockpicking": "dexterity",
    "stealth": "dexterity",
    "arcana": "intelligence",
    "history": "intelligence",
    "investigation": "intelligence",
    "nature": "intelligence",
    "religion": "intelligence",
    "animal_handling": "wisdom",
    "insight": "wisdom",
    "medicine": "wisdom",
    "perception": "wisdom",
    "survival": "wisdom",
    "deception": "charisma",
    "intimidation": "charisma",
    "performance": "charisma",
    "persuasion": "charisma",
    # Add more skills as needed
}

# Default proficiency bonus (can be adjusted based on level later)
PROFICIENCY_BONUS = 2

# Ability score abbreviations if needed elsewhere
ABILITY_ABBREVIATIONS = {
    "strength": "STR",
    "dexterity": "DEX",
    "constitution": "CON",
    "intelligence": "INT",
    "wisdom": "WIS",
    "charisma": "CHA",
}

def roll_dice(sides: int, num_dice: int = 1) -> int:
    """
    Simulates rolling one or more dice with a specified number of sides.

    Args:
        sides: The number of sides on each die (e.g., 6 for a d6).
        num_dice: The number of dice to roll. Defaults to 1.

    Returns:
        The sum of the rolls from all dice.

    Raises:
        TypeError: If sides or num_dice are not integers.
        ValueError: If sides or num_dice are not positive.
    """
    if not isinstance(sides, int) or not isinstance(num_dice, int):
        raise TypeError("Sides and num_dice must be integers.")
    if sides <= 0:
        raise ValueError("Number of sides must be positive.")
    if num_dice <= 0:
        raise ValueError("Number of dice to roll must be positive.")

    total_roll = 0
    for _ in range(num_dice):
        total_roll += random.randint(1, sides)
    return total_roll
