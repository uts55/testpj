import os
import json
import typing

if typing.TYPE_CHECKING:
    from game_state import NPC # For type hinting

def load_raw_data_from_sources(document_sources: list[str]) -> dict[str, list[dict | str]]:
    """
    Loads raw data from all specified document sources.
    Iterates through source directories, reads .json and .txt files,
    and organizes them by category (derived from directory names).

    Args:
        document_sources: A list of directory paths to load data from.

    Returns:
        A dictionary where keys are category names (e.g., "NPCs", "Lore")
        and values are lists of loaded file contents.
        JSON files are loaded as dictionaries.
        TXT files are loaded as dictionaries: {"id": filename, "text_content": content, "source_category": category_name}
    """
    all_data: dict[str, list[dict | str]] = {}
    for source_path in document_sources:
        # Derive category name from the directory's basename
        # e.g., './data/NPCs' becomes 'NPCs'
        category_name = os.path.basename(source_path)
        if not category_name: # Handles cases like './data/' if it were passed
            category_name = os.path.basename(os.path.dirname(source_path))

        all_data[category_name] = []

        if os.path.exists(source_path) and os.path.isdir(source_path):
            for filename in os.listdir(source_path):
                filepath = os.path.join(source_path, filename)
                if os.path.isdir(filepath): # Skip subdirectories
                    continue

                if filename.endswith(".json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Ensure the loaded data has an 'id' if it's a dictionary,
                            # otherwise use filename as id. This is helpful for later processing.
                            if isinstance(data, dict) and 'id' not in data:
                                data['id'] = os.path.splitext(filename)[0]
                            elif isinstance(data, list): # If JSON root is a list, try to process items
                                processed_list = []
                                for item in data:
                                    if isinstance(item, dict) and 'id' not in item:
                                        # This might not be ideal if list items don't have natural IDs
                                        # For now, we'll just add them as-is if they are dicts
                                        pass
                                    processed_list.append(item)
                                data = processed_list # Replace data with the list of items
                            all_data[category_name].append(data)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse JSON from {filepath}, skipping.")
                    except Exception as e:
                        print(f"Warning: An unexpected error occurred while processing JSON {filepath}: {e}, skipping.")
                elif filename.endswith(".txt"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Store TXT content in a dictionary for consistency and RAG processing needs
                            all_data[category_name].append({
                                "id": os.path.splitext(filename)[0], # Use filename without extension as ID
                                "text_content": content,
                                "source_category": category_name # Add category for context
                            })
                    except Exception as e:
                        print(f"Warning: An unexpected error occurred while processing TXT {filepath}: {e}, skipping.")
        else:
            print(f"Warning: Source directory '{source_path}' not found or is not a directory.")
    return all_data

def create_npc_from_data(npc_data: dict) -> 'NPC | None':
    """
    Creates an NPC instance from a dictionary of NPC data.
    This function is kept as a utility, potentially for GameState to use
    when instantiating NPCs from the raw data loaded by load_raw_data_from_sources.

    Args:
        npc_data: A dictionary containing the NPC's attributes.
                  Expected keys include 'id', 'name', 'max_hp', 'combat_stats',
                  'base_damage_dice', and optionally 'dialogue_responses',
                  'active_time_periods', 'is_currently_active'.

    Returns:
        A dictionary with validated/processed NPC data if successful, None otherwise.
    """
    try:
        required_keys = ['id', 'name', 'max_hp', 'combat_stats', 'base_damage_dice']
        for key in required_keys:
            if key not in npc_data:
                raise KeyError(f"Missing essential key '{key}'")

        # Prepare a dictionary for NPC instantiation, including optional fields
        processed_data = {
            'id': npc_data['id'],
            'name': npc_data['name'],
            'max_hp': npc_data['max_hp'],
            'combat_stats': npc_data['combat_stats'],
            'base_damage_dice': npc_data['base_damage_dice'],
            'dialogue_responses': npc_data.get("dialogue_responses"),
            'active_time_periods': npc_data.get("active_time_periods"),
            'is_currently_active': npc_data.get("is_currently_active", True) # Default to True
        }
        return processed_data
    except KeyError as e:
        npc_identifier = npc_data.get('name', npc_data.get('id', 'Unknown NPC'))
        print(f"Warning: Missing essential data for NPC '{npc_identifier}'. Details: {e}. Skipping NPC data processing.")
        return None
    except Exception as e:
        npc_identifier = npc_data.get('name', npc_data.get('id', 'Unknown NPC'))
        print(f"Warning: Error processing NPC data for '{npc_identifier}': {e}. Skipping.")
        return None

# Old load_game_data and load_npcs_from_directory are now removed.

if __name__ == '__main__':
    print("--- Running data_loader.py example usage ---")

    # Need to import RAG_DOCUMENT_SOURCES from config
    # For testing, we can define a dummy path or try to import from parent if structure allows
    # Assuming this script is run from the project root for pathing to work as in config.
    try:
        from config import RAG_DOCUMENT_SOURCES

        print(f"\nLoading raw data from configured sources: {RAG_DOCUMENT_SOURCES}")
        raw_data_loaded = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)

        print(f"\n--- Loaded Data Summary ---")
        for category, data_list in raw_data_loaded.items():
            print(f"Category: {category} - Loaded {len(data_list)} files.")
            if data_list:
                # Print details of the first item in each category for a quick check
                first_item = data_list[0]
                item_id = first_item.get('id', 'N/A') if isinstance(first_item, dict) else "N/A (raw string)"
                item_type = type(first_item).__name__
                print(f"  First item example (ID: {item_id}, Type: {item_type}):")
                if isinstance(first_item, dict):
                    # Print a few key-value pairs from the dictionary
                    for i, (key, value) in enumerate(first_item.items()):
                        if i < 3: # Print max 3 key-value pairs
                            print(f"    '{key}': '{str(value)[:50]}{'...' if len(str(value)) > 50 else ''}'")
                        else:
                            break
                elif isinstance(first_item, str): # Should not happen with current .txt handling
                    print(f"    Content (first 50 chars): {first_item[:50]}{'...' if len(first_item) > 50 else ''}")
                print("-" * 20)

        # Example: Accessing specific loaded data
        if "NPCs" in raw_data_loaded and raw_data_loaded["NPCs"]:
            print("\n--- Example: First loaded NPC raw data ---")
            first_npc_data = raw_data_loaded["NPCs"][0]
            if isinstance(first_npc_data, dict): # Should be a dict
                 print(json.dumps(first_npc_data, indent=2))
                 # Test NPC data processing using create_npc_from_data
                 processed_npc_dict = create_npc_from_data(first_npc_data)
                 if processed_npc_dict:
                     print(f"\nSuccessfully processed NPC data for: {processed_npc_dict.get('name')} (ID: {processed_npc_dict.get('id')})")
                     # game_state.py would then do: NPC(**processed_npc_dict)
                 else:
                     print("\nFailed to process NPC data.")
            else:
                print("First NPC data was not a dictionary as expected.")


        if "Lore" in raw_data_loaded and raw_data_loaded["Lore"]:
            print("\n--- Example: First loaded Lore raw data ---")
            first_lore_data = raw_data_loaded["Lore"][0]
            if isinstance(first_lore_data, dict):
                print(json.dumps(first_lore_data, indent=2))
            else:
                print("First Lore data was not a dictionary as expected.") # Should be dict for .txt files too

        if "Items" in raw_data_loaded and raw_data_loaded["Items"]:
            print("\n--- Example: First loaded Item raw data ---")
            first_item_data = raw_data_loaded["Items"][0]
            if isinstance(first_item_data, dict):
                 print(json.dumps(first_item_data, indent=2))
            else:
                print("First Item data was not a dictionary as expected.")

        new_categories_to_check = ["RaceTemplates", "AttributeTraits", "RoleTemplates"]
        for category in new_categories_to_check:
            if category in raw_data_loaded and raw_data_loaded[category]:
                print(f"\n--- Example: First loaded {category} raw data ---")
                # Check if the data is a list (expected for these JSONs)
                if isinstance(raw_data_loaded[category], list) and len(raw_data_loaded[category]) > 0:
                    # The actual data for these categories is the list itself, where each item is a template.
                    # The loader wraps this list inside another list. So raw_data_loaded[category][0] is the list of templates.
                    first_item_list = raw_data_loaded[category][0]
                    if isinstance(first_item_list, list) and len(first_item_list) > 0:
                        first_item_data = first_item_list[0] # Get the first template from the list
                        if isinstance(first_item_data, dict): # Should be a dict
                            print(json.dumps(first_item_data, indent=2, ensure_ascii=False)) # ensure_ascii=False for Korean characters
                        else:
                            print(f"First {category} data item was not a dictionary as expected. Type: {type(first_item_data)}")
                    else:
                        print(f"{category} data content is not a list or is empty. Type: {type(first_item_list)}")
                else:
                    print(f"{category} data structure is not a list or is empty. Type: {type(raw_data_loaded[category])}")
            else:
                print(f"\n--- No data loaded for category: {category} ---")

    except ImportError:
        print("Could not import RAG_DOCUMENT_SOURCES from config.py. Make sure it's accessible.")
    except Exception as e:
        print(f"An error occurred during the test run: {e}")

    print("\n--- data_loader.py example usage complete ---")
