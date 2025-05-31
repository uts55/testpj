import os
import json

def load_game_data(npc_dir: str = "data/NPCs", game_object_dir: str = "data/GameObjects") -> dict:
    """
    Loads all NPC and GameObject data from JSON files in specified directories.

    Args:
        npc_dir: The directory path containing NPC JSON files.
        game_object_dir: The directory path containing GameObject JSON files.

    Returns:
        A dictionary with two keys:
        'npcs': A list of NPC data (each item is a dictionary parsed from JSON).
        'game_objects': A list of GameObject data (similarly, dictionaries from JSON).
        Returns empty lists for categories if directories don't exist or no files are found.
    """
    data = {"npcs": [], "game_objects": []}

    # Load NPCs
    if os.path.exists(npc_dir) and os.path.isdir(npc_dir):
        for filename in os.listdir(npc_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(npc_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        loaded_json_content = json.load(f)
                        if isinstance(loaded_json_content, list):
                            if len(loaded_json_content) == 1 and isinstance(loaded_json_content[0], dict):
                                data["npcs"].append(loaded_json_content[0]) # Extract the single dict
                            elif not loaded_json_content: # Empty list
                                print(f"Warning: JSON file {filepath} contains an empty list, skipping.")
                            else: # List with multiple items or non-dict items
                                print(f"Warning: JSON file {filepath} contains a list with multiple items or non-dict items. Skipping.")
                        elif isinstance(loaded_json_content, dict):
                            data["npcs"].append(loaded_json_content) # Append the dict directly
                        else:
                            print(f"Warning: JSON file {filepath} does not contain a dictionary or a list with a single dictionary. Skipping.")
                except FileNotFoundError:
                    # Using print for logging as per environment constraints
                    print(f"Warning: File not found {filepath}, skipping.")
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON from {filepath}, skipping. Check JSON validity.")
                except Exception as e:
                    print(f"Warning: An unexpected error occurred while processing {filepath}: {e}, skipping.")
    else:
        print(f"Warning: NPC directory '{npc_dir}' not found. No NPCs will be loaded from here.")

    # Load GameObjects
    if os.path.exists(game_object_dir) and os.path.isdir(game_object_dir):
        for filename in os.listdir(game_object_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(game_object_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        loaded_json_content = json.load(f)
                        if isinstance(loaded_json_content, list):
                            if len(loaded_json_content) == 1 and isinstance(loaded_json_content[0], dict):
                                data["game_objects"].append(loaded_json_content[0]) # Extract the single dict
                            elif not loaded_json_content: # Empty list
                                print(f"Warning: JSON file {filepath} contains an empty list, skipping.")
                            else: # List with multiple items or non-dict items
                                print(f"Warning: JSON file {filepath} contains a list with multiple items or non-dict items. Skipping.")
                        elif isinstance(loaded_json_content, dict):
                            data["game_objects"].append(loaded_json_content) # Append the dict directly
                        else:
                            print(f"Warning: JSON file {filepath} does not contain a dictionary or a list with a single dictionary. Skipping.")
                except FileNotFoundError:
                    print(f"Warning: File not found {filepath}, skipping.")
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse JSON from {filepath}, skipping. Check JSON validity.")
                except Exception as e:
                    print(f"Warning: An unexpected error occurred while processing {filepath}: {e}, skipping.")
    else:
        print(f"Warning: GameObject directory '{game_object_dir}' not found. No GameObjects will be loaded from here.")

    return data

# It's assumed that the NPC class is imported here if it's not already.
# from game_state import NPC # This line would be needed if NPC class is used directly here.
# For now, we'll add it conceptually. If game_state.py is not accessible here,
# this function might live in a different file or NPC class needs to be passed.
# Let's assume for the task that we can import NPC.
from game_state import NPC # Added for NPC class usage

def create_npc_from_data(npc_data: dict) -> NPC | None:
    """
    Creates an NPC instance from a dictionary of NPC data.

    Args:
        npc_data: A dictionary containing the NPC's attributes.
                  Expected keys include 'id', 'name', 'max_hp', 'combat_stats',
                  'base_damage_dice', and optionally 'dialogue_responses'.

    Returns:
        An NPC object if creation is successful, None otherwise.
    """
    try:
        return NPC(
            id=npc_data['id'],
            name=npc_data['name'],
            max_hp=npc_data['max_hp'],
            combat_stats=npc_data['combat_stats'],
            base_damage_dice=npc_data['base_damage_dice'],
            # Pass dialogue_responses, defaults to None if not present
            dialogue_responses=npc_data.get("dialogue_responses")
        )
    except KeyError as e:
        print(f"Warning: Missing essential key '{e}' in NPC data for '{npc_data.get('name', 'Unknown NPC')}'. Skipping NPC creation.")
        return None
    except Exception as e:
        print(f"Warning: Error creating NPC from data for '{npc_data.get('name', 'Unknown NPC')}': {e}. Skipping.")
        return None

def load_npcs_from_directory(npc_dir_path: str = "data/NPCs") -> list[NPC]:
    """
    Loads all NPCs from a directory, instantiating them into NPC objects.

    Args:
        npc_dir_path: The directory path containing NPC JSON files.

    Returns:
        A list of NPC objects.
    """
    raw_data = load_game_data(npc_dir=npc_dir_path, game_object_dir="data/NonExistentPath") # Only load NPCs

    npcs_list = []
    for npc_data_item in raw_data.get("npcs", []):
        npc_instance = create_npc_from_data(npc_data_item)
        if npc_instance:
            npcs_list.append(npc_instance)
    return npcs_list


if __name__ == '__main__':
    # Example usage:
    print("--- Running data_loader.py example usage ---")

    # Example for load_game_data (original functionality)
    print("\nLoading raw game data from default directories...")
    game_data = load_game_data()
    print(f"Loaded {len(game_data['npcs'])} raw NPC data entries.")
    if game_data['npcs']:
        for npc_raw in game_data['npcs']:
            print(f"  - Raw: {npc_raw.get('name', 'Unnamed NPC')} (Dialogue present: {'dialogue_responses' in npc_raw})")

    print(f"\nLoaded {len(game_data['game_objects'])} raw GameObject data entries.")
    # ... (rest of game_object printing)

    # Example for new load_npcs_from_directory
    print("\n--- Loading and Instantiating NPCs ---")
    instantiated_npcs = load_npcs_from_directory()
    print(f"Successfully instantiated {len(instantiated_npcs)} NPC objects:")
    for npc_obj in instantiated_npcs:
        print(f"  - Object: {npc_obj.name} (ID: {npc_obj.id}), HP: {npc_obj.max_hp}")
        if npc_obj.dialogue_responses:
            print(f"    Dialogue Keys: {list(npc_obj.dialogue_responses.keys())}")
        else:
            print("    No dialogue responses.")

    # Test with a specific NPC that should have dialogue (npc_001.json - Ellara)
    ellara_npc = next((n for n in instantiated_npcs if n.id == "npc_001"), None)
    if ellara_npc:
        print(f"\nTesting Ellara (npc_001) dialogue loading:")
        greeting_node = ellara_npc.get_dialogue_node("greetings")
        if greeting_node:
            print(f"  Greeting NPC Text: {greeting_node.get('npc_text')}")
            print(f"  Greeting Player Choices: {len(greeting_node.get('player_choices', []))}")
        else:
            print("  Could not get 'greetings' node for Ellara.")
    else:
        print("\nEllara (npc_001) not found among instantiated NPCs.")


    print("\n--- Testing with non-existent directories (for raw data loading) ---")
    non_existent_data = load_game_data(npc_dir="data/NonExistentNPCs", game_object_dir="data/NonExistentObjects")
    print(f"Raw NPCs loaded from non-existent dirs: {len(non_existent_data['npcs'])}")
    print(f"Raw GameObjects loaded from non-existent dirs: {len(non_existent_data['game_objects'])}")

    # The malformed.json file in data/NPCs/ should have triggered a warning during the default loading.
    # And also during the instantiation attempt by load_npcs_from_directory.
    print("\n--- data_loader.py example usage complete ---")
