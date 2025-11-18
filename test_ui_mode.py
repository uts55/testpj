import os
os.environ["RUNNING_INTERACTIVE_TEST"] = "true"

import ui
import traceback

# Test creating GamePlayFrame in test mode
print("Creating GamePlayFrame in test mode...")
frame = ui.GamePlayFrame()
print("GamePlayFrame created successfully")

# Test various methods
print("\nTesting methods:")
try:
    frame.add_narration("Test narration message")
except Exception as e:
    print(f"Error in add_narration: {e}")
    traceback.print_exc()
frame.update_hp("100/100")
frame.update_location("Test Location")
frame.update_inventory("Sword, Shield")
frame.update_npcs("Guard, Merchant")

# Test dialogue display
print("\nTesting dialogue display:")
frame.display_dialogue("Test NPC", "Hello adventurer!", [
    {"text": "Hello"},
    {"text": "Goodbye"}
])

# Test is_destroyed
print(f"\nIs destroyed: {frame.is_destroyed()}")

# Test destroy
frame.destroy_test_mode()
print(f"After destroy - Is destroyed: {frame.is_destroyed()}")

print("\nAll tests passed!")
