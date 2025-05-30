# utils.py

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
