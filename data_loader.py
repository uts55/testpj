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

if __name__ == '__main__':
    # Example usage:
    print("--- Running data_loader.py example usage ---")

    print("\nLoading game data from default directories...")
    game_data = load_game_data()

    print(f"\nLoaded {len(game_data['npcs'])} NPCs:")
    if game_data['npcs']:
        for npc in game_data['npcs']:
            print(f"  - {npc.get('name', 'Unnamed NPC')} (Description: {npc.get('description', 'N/A')[:30]}...)")
    else:
        print("  No NPCs loaded.")

    print(f"\nLoaded {len(game_data['game_objects'])} GameObjects:")
    if game_data['game_objects']:
        for obj in game_data['game_objects']:
            print(f"  - {obj.get('name', 'Unnamed Object')} (Description: {obj.get('description', 'N/A')[:30]}...)")
    else:
        print("  No GameObjects loaded.")

    print("\n--- Testing with non-existent directories ---")
    non_existent_data = load_game_data(npc_dir="data/NonExistentNPCs", game_object_dir="data/NonExistentObjects")
    print(f"NPCs loaded from non-existent dirs: {len(non_existent_data['npcs'])}")
    print(f"GameObjects loaded from non-existent dirs: {len(non_existent_data['game_objects'])}")

    # The malformed.json file in data/NPCs/ should have triggered a warning during the default loading.
    print("\n--- data_loader.py example usage complete ---")
