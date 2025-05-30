import random
import logging

logger = logging.getLogger(__name__)

def roll_dice(sides: int) -> int:
    """Simulates rolling a die with a specified number of sides.

    Args:
        sides: The number of sides on the die (e.g., 6 for a d6, 20 for a d20).

    Returns:
        The result of the roll, an integer between 1 and `sides`.
    """
    if not isinstance(sides, int) or sides <= 0:
        logger.error(f"Invalid number of sides for dice roll: {sides}. Must be a positive integer.")
        # Or raise ValueError("Number of sides must be a positive integer")
        # For now, returning 0 or 1 to indicate error or prevent crashes,
        # but ideally, this should be handled by the caller or via an exception.
        return 1 # Default to 1 if sides is invalid to avoid breaking logic expecting a number.

    roll_result = random.randint(1, sides)
    logger.info(f"Rolled a d{sides}, result: {roll_result}")
    return roll_result
