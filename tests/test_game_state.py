import unittest
import random # random is used by game_state.roll_dice, not directly in tests but good to note
from game_state import PlayerState, roll_dice

class TestPlayerState(unittest.TestCase):
    """Test cases for the PlayerState class."""

    def test_initialization_defaults(self):
        """Test PlayerState initialization with default values."""
        player = PlayerState()
        self.assertEqual(player.current_hp, 100, "Default HP should be 100")
        self.assertEqual(player.max_hp, 100, "Default max_hp should be 100")
        self.assertEqual(player.inventory, [], "Default inventory should be empty")

    def test_initialization_custom(self):
        """Test PlayerState initialization with custom values."""
        player = PlayerState(initial_hp=80, max_hp=120)
        self.assertEqual(player.current_hp, 80, "Custom initial_hp not set correctly")
        self.assertEqual(player.max_hp, 120, "Custom max_hp not set correctly")

    def test_initialization_hp_capped_at_max(self):
        """Test that initial_hp is capped at max_hp if it exceeds it."""
        player = PlayerState(initial_hp=150, max_hp=100)
        self.assertEqual(player.current_hp, 100, "initial_hp should be capped at max_hp")
        self.assertEqual(player.max_hp, 100)

    def test_initialization_invalid_hp_values(self):
        """Test PlayerState initialization with invalid HP values."""
        with self.assertRaisesRegex(ValueError, "initial_hp cannot be negative", msg="Negative initial_hp"):
            PlayerState(initial_hp=-10)
        with self.assertRaisesRegex(ValueError, "max_hp must be a positive integer", msg="Zero max_hp"):
            PlayerState(max_hp=0)
        with self.assertRaisesRegex(ValueError, "max_hp must be a positive integer", msg="Negative max_hp"):
            PlayerState(max_hp=-5)
        with self.assertRaisesRegex(TypeError, "HP values must be integers", msg="String initial_hp"):
            PlayerState(initial_hp="abc")
        with self.assertRaisesRegex(TypeError, "HP values must be integers", msg="String max_hp"):
            PlayerState(max_hp="xyz")

    def test_take_damage(self):
        """Test the take_damage method."""
        player = PlayerState(initial_hp=100, max_hp=100)
        player.take_damage(30)
        self.assertEqual(player.current_hp, 70, "Damage not applied correctly")
        player.take_damage(80) # Damage exceeding current HP
        self.assertEqual(player.current_hp, 0, "HP should be 0 after taking more damage than available")

    def test_take_damage_to_zero(self):
        """Test take_damage reducing HP exactly to zero."""
        player = PlayerState(initial_hp=50)
        player.take_damage(50)
        self.assertEqual(player.current_hp, 0, "HP should be exactly 0")

    def test_take_damage_already_zero(self):
        """Test take_damage when HP is already zero."""
        player = PlayerState(initial_hp=0)
        player.take_damage(20)
        self.assertEqual(player.current_hp, 0, "HP should remain 0 if damage taken at 0 HP")

    def test_take_damage_invalid_amount(self):
        """Test take_damage with invalid amounts."""
        player = PlayerState()
        with self.assertRaisesRegex(TypeError, "Damage amount must be an integer", msg="String damage amount"):
            player.take_damage("abc")
        with self.assertRaisesRegex(ValueError, "Damage amount cannot be negative", msg="Negative damage amount"):
            player.take_damage(-10)

    def test_heal(self):
        """Test the heal method."""
        player = PlayerState(initial_hp=30, max_hp=100)
        player.heal(40)
        self.assertEqual(player.current_hp, 70, "Healing not applied correctly")
        player.heal(50) # Healing exceeding max_hp
        self.assertEqual(player.current_hp, 100, "HP should be max_hp after healing beyond max")

    def test_heal_to_max(self):
        """Test heal restoring HP exactly to max_hp."""
        player = PlayerState(initial_hp=90, max_hp=100)
        player.heal(10)
        self.assertEqual(player.current_hp, 100, "HP should be exactly max_hp")

    def test_heal_already_max(self):
        """Test heal when HP is already at max_hp."""
        player = PlayerState(initial_hp=100, max_hp=100)
        player.heal(20)
        self.assertEqual(player.current_hp, 100, "HP should remain max_hp if healed at max_hp")

    def test_heal_invalid_amount(self):
        """Test heal with invalid amounts."""
        player = PlayerState()
        with self.assertRaisesRegex(TypeError, "Heal amount must be an integer", msg="String heal amount"):
            player.heal("abc")
        with self.assertRaisesRegex(ValueError, "Heal amount cannot be negative", msg="Negative heal amount"):
            player.heal(-10)

    def test_inventory_management(self):
        """Test adding and removing items from inventory."""
        player = PlayerState()
        player.add_to_inventory("sword")
        self.assertIn("sword", player.inventory, "Item 'sword' not added")
        player.add_to_inventory("potion")
        self.assertIn("potion", player.inventory, "Item 'potion' not added")
        self.assertEqual(len(player.inventory), 2, "Inventory size incorrect after additions")

        self.assertTrue(player.remove_from_inventory("sword"), "Removing 'sword' should return True")
        self.assertNotIn("sword", player.inventory, "'sword' still in inventory after removal")
        self.assertEqual(len(player.inventory), 1, "Inventory size incorrect after removal")

        self.assertFalse(player.remove_from_inventory("shield"), "Removing non-existent 'shield' should return False")
        self.assertIn("potion", player.inventory, "'potion' should still be in inventory")

    def test_add_to_inventory_invalid_name(self):
        """Test add_to_inventory with invalid item names."""
        player = PlayerState()
        with self.assertRaisesRegex(TypeError, "Item name must be a string", msg="Integer item name"):
            player.add_to_inventory(123)
        with self.assertRaisesRegex(ValueError, "Item name cannot be empty or just whitespace", msg="Whitespace item name"):
            player.add_to_inventory("  ")
        with self.assertRaisesRegex(ValueError, "Item name cannot be empty or just whitespace", msg="Empty item name"):
            player.add_to_inventory("")

    def test_remove_from_inventory_invalid_name(self):
        """Test remove_from_inventory with invalid item names."""
        player = PlayerState()
        player.add_to_inventory("test_item")
        with self.assertRaisesRegex(TypeError, "Item name must be a string", msg="Integer item name for removal"):
            player.remove_from_inventory(123)
        self.assertIn("test_item", player.inventory, "Item should still be in inventory after invalid removal attempt")

    def test_get_status(self):
        """Test the get_status method output format."""
        player = PlayerState(initial_hp=75, max_hp=110)
        self.assertEqual(player.get_status(), "HP: 75/110, Inventory: [empty]")
        player.add_to_inventory("map")
        self.assertEqual(player.get_status(), "HP: 75/110, Inventory: [map]")
        player.add_to_inventory("torch")
        self.assertEqual(player.get_status(), "HP: 75/110, Inventory: [map, torch]")
        player.inventory = [] # Reset for next check
        self.assertEqual(player.get_status(), "HP: 75/110, Inventory: [empty]")


class TestRollDice(unittest.TestCase):
    """Test cases for the roll_dice function."""

    def test_single_die_roll(self):
        """Test rolling a single die for various sides."""
        for sides in [1, 6, 20, 100]:
            with self.subTest(sides=sides):
                roll = roll_dice(sides)
                self.assertTrue(1 <= roll <= sides, f"Roll {roll} out of range for 1d{sides}")

    def test_single_die_roll_always_one_if_sides_one(self):
        """Test rolling a 1-sided die always results in 1."""
        for _ in range(10): # Repeat to increase confidence
            self.assertEqual(roll_dice(1), 1, "Roll on 1-sided die should always be 1")

    def test_multiple_dice_rolls(self):
        """Test rolling multiple dice."""
        for sides, num_dice in [(6, 2), (10, 3), (4, 5)]:
            with self.subTest(sides=sides, num_dice=num_dice):
                roll = roll_dice(sides, num_dice)
                self.assertTrue(num_dice <= roll <= sides * num_dice,
                                f"Roll {roll} out of range for {num_dice}d{sides}")

    def test_roll_distribution_basic_d6(self):
        """Basic check for d6 roll distribution (not a rigorous statistical test)."""
        sides = 6
        num_rolls = 300 # Increased number of rolls for better chance of seeing all outcomes
        rolls = [roll_dice(sides) for _ in range(num_rolls)]
        unique_rolls = set(rolls)
        # For a d6, with 300 rolls, it's highly probable all outcomes (1-6) appear.
        self.assertEqual(unique_rolls, {1, 2, 3, 4, 5, 6},
                         f"Expected all outcomes (1-6) for d6 in {num_rolls} rolls, got {unique_rolls}")

    def test_roll_distribution_basic_d4(self):
        """Basic check for d4 roll distribution."""
        sides = 4
        num_rolls = 200
        rolls = [roll_dice(sides, num_dice=2) for _ in range(num_rolls)] # 2d4
        # Min sum 2, Max sum 8.
        # Check if a few values in the middle range appear.
        # This is a very loose check.
        seen_values_near_mean = {r for r in rolls if 3 <= r <= 7} # Mean of 2d4 is 5
        self.assertTrue(len(seen_values_near_mean) > 3, # Expect to see a few different values near mean
                        f"Expected some variety near mean for 2d4 rolls, got {seen_values_near_mean}")


    def test_input_validation_roll_dice(self):
        """Test input validation for roll_dice."""
        with self.assertRaisesRegex(TypeError, "Sides and num_dice must be integers", msg="String sides"):
            roll_dice(sides="abc")
        with self.assertRaisesRegex(TypeError, "Sides and num_dice must be integers", msg="String num_dice"):
            roll_dice(sides=6, num_dice="two")
        with self.assertRaisesRegex(ValueError, "Number of sides must be positive", msg="Zero sides"):
            roll_dice(sides=0)
        with self.assertRaisesRegex(ValueError, "Number of sides must be positive", msg="Negative sides"):
            roll_dice(sides=-6)
        with self.assertRaisesRegex(ValueError, "Number of dice to roll must be positive", msg="Zero num_dice"):
            roll_dice(sides=6, num_dice=0)
        with self.assertRaisesRegex(ValueError, "Number of dice to roll must be positive", msg="Negative num_dice"):
            roll_dice(sides=6, num_dice=-3)

if __name__ == '__main__':
    unittest.main()
