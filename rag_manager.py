from data_loader import load_game_data

# GAME_DATA placeholder is now removed, data will be loaded by load_game_data()

def retrieve_context(player_input: str, data: dict) -> str:
    """
    Retrieves relevant context from game data based on player input.

    Args:
        player_input: The string input from the player.
        data: A dictionary containing game data (NPCs, GameObjects).

    Returns:
        A string containing any relevant information found, or a predefined
        message if no context is found.
    """
    relevant_context = []
    keywords = player_input.lower().split()

    # Check NPCs
    for npc in data.get("npcs", []):
        # Debug: Print type of npc
        # print(f"DEBUG: NPC item type: {type(npc)}, content: {npc}")
        if not isinstance(npc, dict):
            print(f"Warning: Expected NPC item to be a dict, but got {type(npc)}. Skipping item: {npc}")
            continue
        npc_name_lower = npc.get("name", "").lower()
        npc_desc_lower = npc.get("description", "").lower()
        if any(keyword in npc_name_lower or keyword in npc_desc_lower for keyword in keywords):
            relevant_context.append(f"NPC: {npc.get('name', 'Unnamed NPC')} - {npc.get('description', 'No description')}")

    # Check GameObjects
    for game_object in data.get("game_objects", []):
        # Debug: Print type of game_object
        # print(f"DEBUG: GameObject item type: {type(game_object)}, content: {game_object}")
        if not isinstance(game_object, dict):
            print(f"Warning: Expected GameObject item to be a dict, but got {type(game_object)}. Skipping item: {game_object}")
            continue
        obj_name_lower = game_object.get("name", "").lower()
        obj_desc_lower = game_object.get("description", "").lower()
        if any(keyword in obj_name_lower or keyword in obj_desc_lower for keyword in keywords):
            relevant_context.append(f"Object: {game_object.get('name', 'Unnamed Object')} - {game_object.get('description', 'No description')}")

    if not relevant_context:
        return "No specific context found for your input."

    return "\n".join(relevant_context)

if __name__ == '__main__':
    print("--- Running example usage of retrieve_context with loaded data ---")

    # Load game data using the new loader function
    print("\nLoading game data via data_loader...")
    actual_game_data = load_game_data()
    # The data_loader will print warnings, e.g., for malformed.json

    if not actual_game_data["npcs"] and not actual_game_data["game_objects"]:
        print("\nWarning: No game data was loaded. Context retrieval might not find anything.")
        print("Please ensure JSON files exist in data/NPCs and data/GameObjects directories.")

    print(f"\n--- Test Case 1: Sunstone and Woods ---")
    test_input_1 = "Tell me about the Sunstone in the Whispering Woods"
    context_1 = retrieve_context(test_input_1, data=actual_game_data)
    print(f"Player Input: \"{test_input_1}\"")
    print(f"Retrieved Context:\n{context_1}")

    print(f"\n--- Test Case 2: Hemlock ---")
    test_input_2 = "What do you know about Hemlock?"
    context_2 = retrieve_context(test_input_2, data=actual_game_data)
    print(f"Player Input: \"{test_input_2}\"")
    print(f"Retrieved Context:\n{context_2}")

    print(f"\n--- Test Case 3: Bakery (expected no context) ---")
    test_input_3 = "Any news from the bakery?"
    context_3 = retrieve_context(test_input_3, data=actual_game_data)
    print(f"Player Input: \"{test_input_3}\"")
    print(f"Retrieved Context:\n{context_3}")

    # This specific example of custom_data is less relevant now that we load real data,
    # but testing with an empty dataset is still valuable.
    print(f"\n--- Test Case 4: Empty data (simulating no data loaded) ---")
    empty_data = {"npcs": [], "game_objects": []}
    test_input_4 = "anything"
    context_4 = retrieve_context(test_input_4, data=empty_data)
    print(f"Player Input (with empty data): \"{test_input_4}\"")
    print(f"Retrieved Context:\n{context_4}")

    print("\n--- rag_manager.py example usage finished ---")
