# Example:
# python rag_system_simulation.py --data_dir ./data --filters '{"type": "npc", "current_location": "엘름 마을 촌장집"}' --query "고대 유물" --text_fields "description,lore_fragments,dialogue_responses.artifact_info"
#
# This searches for NPCs in '엘름 마을 촌장집', queries for '고대 유물' within their description, lore_fragments, 
# and specific dialogue responses related to 'artifact_info'.

import json
import os
import argparse
from pathlib import Path

def load_documents(directory_path: str) -> list[dict]:
    """
    Finds all .json files in the specified directory_path,
    reads each JSON file, and returns a list of Python dictionaries.
    Handles potential errors like invalid JSON format or file not found gracefully.
    Assumes JSON files contain a list of document objects, or a single document object.
    """
    documents = []
    if not os.path.exists(directory_path):
        print(f"Error: Directory not found - {directory_path}")
        return documents

    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list): # Handles files like [{"doc1"}, {"doc2"}] or [{"doc_single"}]
                        documents.extend(data)
                    elif isinstance(data, dict): # Handles files like {"doc_single"}
                        documents.append(data)
                    else:
                        print(f"Warning: Unexpected JSON structure in {filepath}. Expected list or dict at root.")
            except FileNotFoundError:
                print(f"Error: File not found - {filepath}")
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON format in - {filepath}")
            except Exception as e:
                print(f"An unexpected error occurred while processing {filepath}: {e}")
    return documents

def _get_nested_value(doc: dict, key_path: str):
    """Helper function to get a value from a nested dictionary using a dot-separated path."""
    keys = key_path.split('.')
    value = doc
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list): # Attempt to handle list indices if a key is numeric
            try:
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None # Index out of bounds
            except ValueError:
                return None # Key is not a valid index for a list
        else:
            return None # Key not found or value is not a collection
    return value

def filter_documents(documents: list[dict], filters: dict) -> list[dict]:
    """
    Filters a list of document dictionaries based on criteria in the filters dictionary.
    Keys in filters can be dot-separated paths for nested fields.
    """
    filtered_docs = []
    for doc in documents:
        match = True
        for key_path, expected_value in filters.items():
            actual_value = _get_nested_value(doc, key_path)
            if actual_value != expected_value:
                match = False
                break
        if match:
            filtered_docs.append(doc)
    return filtered_docs

def _extract_text_from_value(value) -> list[str]:
    """Helper function to recursively extract string values from various data structures."""
    texts = []
    if isinstance(value, str):
        texts.append(value)
    elif isinstance(value, list):
        for item in value:
            texts.extend(_extract_text_from_value(item))
    elif isinstance(value, dict):
        for sub_value in value.values():
            texts.extend(_extract_text_from_value(sub_value))
    return texts

def extract_text_for_rag(document: dict, text_fields: list[str]) -> str:
    """
    Extracts text content from specified fields in a document.
    Handles dot-separated paths for nested fields.
    Joins lists of strings and concatenates strings from complex objects.
    """
    extracted_texts = []
    for field_path in text_fields:
        value = _get_nested_value(document, field_path)
        if value is not None:
            texts_from_field = _extract_text_from_value(value)
            extracted_texts.extend(texts_from_field)
    
    return " ".join(extracted_texts)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG System Simulation Script")
    parser.add_argument(
        "--data_dir", 
        type=str, 
        default="./data",
        help="Path to the directory containing JSON files (default: ./data)"
    )
    parser.add_argument(
        "--filters", 
        type=str, 
        required=True,
        help="A JSON string representing the metadata filters dictionary (e.g., '{\"type\": \"npc\", \"stats.health\": 50}')"
    )
    parser.add_argument(
        "--query", 
        type=str, 
        default=None,
        help="The natural language query for simulated keyword search (optional)."
    )
    parser.add_argument(
        "--text_fields", 
        type=str, 
        required=True,
        help="A comma-separated string of field names to extract text from for RAG (e.g., \"description,lore_fragments,knowledge_fragments\")"
    )

    args = parser.parse_args()

    # Parse filters JSON string
    try:
        parsed_filters = json.loads(args.filters)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON string for --filters argument: {e}")
        exit(1)

    # Convert comma-separated text_fields to a list
    list_of_text_fields = [field.strip() for field in args.text_fields.split(',')]

    # Load documents
    # Ensure data directory and files (player_1.json, npc_001.json) exist from previous setup
    # For this task, we assume they are already created.
    # To re-create them if missing for testing:
    # Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    # player_1_content = [{"id": "player_001", "name": "에단", "type": "player", "current_location": "엘름 마을", "description": "모험가", "knowledge_fragments": ["유물은 숲에 있다"]}]
    # npc_001_content = [{"id": "npc_001", "name": "엘라라", "type": "npc", "current_location": "엘름 마을 촌장집", "description": "촌장", "lore_fragments": ["고대 유물에 대해 안다"], "dialogue_responses": {"artifact_info": ["유물은 강력하다"]}}]
    # with open(os.path.join(args.data_dir, "player_1.json"), 'w', encoding='utf-8') as f: json.dump(player_1_content, f, ensure_ascii=False, indent=2)
    # with open(os.path.join(args.data_dir, "npc_001.json"), 'w', encoding='utf-8') as f: json.dump(npc_001_content, f, ensure_ascii=False, indent=2)
        
    all_documents = load_documents(args.data_dir)
    if not all_documents:
        print(f"No documents loaded from {args.data_dir}. Ensure JSON files exist and are correctly formatted.")
        # Create dummy files if they don't exist for the purpose of this exercise run
        # This part is mainly for making the script runnable standalone if data isn't pre-populated.
        data_dir_path = Path(args.data_dir)
        data_dir_path.mkdir(parents=True, exist_ok=True)

        player_1_content_default = [
          {
            "id": "player_001", "name": "에단", "type": "player", "current_location": "엘름 마을", 
            "description": "날카로운 눈빛을 가진 젊은 모험가.", 
            "knowledge_fragments": ["엘름 마을 촌장은 밤에만 나타난다.", "고대 유물은 잊혀진 숲 깊은 곳에 숨겨져 있다는 전설이 있다."],
            "skills": [{"name": "강타", "description": "강력한 일격"}, {"name": "패링", "description": "공격 쳐내기"}]
          }
        ]
        npc_001_content_default = [
          {
            "id": "npc_001", "name": "엘라라", "type": "npc", "current_location": "엘름 마을 촌장집", 
            "description": "엘름 마을의 현명한 촌장.", 
            "lore_fragments": ["엘라라는 젊은 시절 뛰어난 마법사였다.", "고대 유물에 대해 잘 알고 있다."],
            "dialogue_responses": {
              "artifact_info": ["고대 유물이라... 그것은 우리 마을의 오랜 전설과 관련이 깊지.", "그 유물은 강력한 힘을 지녔지만, 동시에 위험한 저주도 품고 있다고 전해지네."],
              "greetings": ["엘름 마을에 온 것을 환영하네."]
            }
          }
        ]
        sample_game_obj_content = [
            {
                "id": "ancient_tablet_001",
                "name": "고대의 석판",
                "type": "object",
                "description": "알 수 없는 문자가 새겨진 오래된 석판. 중요한 단서를 담고 있는 듯하다.",
                "location": "잊혀진 숲",
                "properties": {
                    "readable_by": "mage_class_or_scholar",
                    "requires_translation_spell": True
                },
                "lore_text_embedded": "세 개의 달이 정렬될 때, 숨겨진 길이 열리리라...",
                "related_quests": ["quest_001", "quest_003"]
            }
        ]

        with open(data_dir_path / "player_1.json", 'w', encoding='utf-8') as f:
            json.dump(player_1_content_default, f, ensure_ascii=False, indent=2)
        with open(data_dir_path / "npc_001.json", 'w', encoding='utf-8') as f:
            json.dump(npc_001_content_default, f, ensure_ascii=False, indent=2)
        with open(data_dir_path / "game_object_001.json", 'w', encoding='utf-8') as f:
            json.dump(sample_game_obj_content, f, ensure_ascii=False, indent=2)
        print(f"Created sample JSON files in {args.data_dir} for demonstration as it was empty.")
        all_documents = load_documents(args.data_dir)


    # Filter documents
    filtered_documents = filter_documents(all_documents, parsed_filters)

    results = []
    query_keywords = []
    if args.query:
        query_keywords = args.query.lower().split()

    for doc in filtered_documents:
        extracted_text = extract_text_for_rag(doc, list_of_text_fields)
        
        if args.query and query_keywords:
            # Perform case-insensitive keyword search
            text_to_search = extracted_text.lower()
            match = True
            for keyword in query_keywords:
                if keyword not in text_to_search:
                    match = False
                    break
            if match:
                results.append((doc.get("name", doc.get("id", "Unknown ID")), extracted_text))
        else:
            # No query, so add all filtered documents' extracted text
            results.append((doc.get("name", doc.get("id", "Unknown ID")), extracted_text))

    # Print results
    if results:
        print(f"\nFound {len(results)} matching document(s):")
        for name_id, text in results:
            print(f"\n--- Document: {name_id} ---")
            print(text)
            print("--- End of Document ---")
    else:
        print("No documents matched the criteria.")

    print("\nScript finished.")
