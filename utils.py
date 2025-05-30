# utils.py
import random

# Mapping of skills to their primary ability scores
SKILL_ABILITY_MAP = {
    "athletics": "strength",
    "acrobatics": "dexterity",
    "slight_of_hand": "dexterity",
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

def roll_dice(sides: int) -> int:
    """
    Simulates rolling a single die with a given number of sides.
    Args:
        sides: The number of sides on the die (e.g., 6 for a d6, 20 for a d20).
    Returns:
        A random integer between 1 and `sides` (inclusive).
    Raises:
        ValueError: if sides is less than 1.
    """
    if sides < 1:
        raise ValueError("Number of sides must be at least 1.")
    return random.randint(1, sides)
