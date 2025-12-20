# --- Configuration Constants ---

# API and Model Configuration
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
# Valid Gemini model names:
# - gemini-1.5-flash-latest (recommended for fast responses)
# - gemini-1.5-flash (stable version)
# - gemini-1.5-pro-latest (more capable, slower)
# - gemini-2.0-flash-exp (experimental, latest features)
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # Standard sentence transformer model
VECTOR_DB_PATH = "./chroma_db" # Path to store ChromaDB persistent data
COLLECTION_NAME = "dnd_game_content" # Name of the collection in ChromaDB

RAG_DOCUMENT_SOURCES = [
    './data/NPCs',
    './data/Items', # Added Items
    './data/Regions', # Was already present
    './data/GameObjects',
    './data/Lore',
    './data/History',
    './data/Factions',
    './data/Technology',
    './data/MagicSystems',
    './data/Races',
    './data/RaceTemplates',
    './data/AttributeTraits',
    './data/RoleTemplates'
]

# Fields to extract text from for RAG embedding.
# 'dialogue_responses' will be handled specially in get_text_from_doc to extract npc_text from nodes.
RAG_TEXT_FIELDS = [
    'name',
    'description',
    'text_content', # Primarily for .txt files and specific JSON fields like in Lore/History
    'dialogue_responses', # Special handling: extract 'npc_text' from dialogue nodes
    # Consider adding other relevant fields from your specific JSON structures if needed:
    # e.g., 'effects.description' if items had detailed effect descriptions,
    # 'exits.description' if exits had descriptive text.
    # For now, keeping it to common and clearly structured text fields.
]

RAG_DOCUMENT_FILTERS = {} # Placeholder for potential future filtering logic

# Text Splitting Configuration (relevant if pre-splitting text before embedding, not used in current direct embedding)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Dialogue Manager Configuration
MAX_HISTORY_ITEMS = 20
MAX_API_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Game Settings
SAVE_GAME_DIR = "./Save/"
SAVE_GAME_FILENAME = "autosave.json"

# Other
INITIAL_PROMPT_TEXT = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다. 플레이어의 첫 행동을 기다리는 상황을 가정하고, 모험의 시작을 알리는 흥미로운 도입부를 묘사해주세요."

PRESET_SCENARIOS = [
    {
        "id": "goblin_cave_escape",
        "name": "Escape from the Goblin Cave",
        "initial_prompt": "You awaken in a damp, dark cave, the stench of goblins filling your nostrils. Your head throbs, and you have no memory of how you got here. A rusty dagger lies beside you. Find a way out!",
        "start_location_id": "goblin_cave_entrance",
        "player_start_setup": {"items": ["rusty_dagger_001"], "hp_modifier": -2}
    },
    {
        "id": "haunted_mansion_investigation",
        "name": "The Haunted Mansion",
        "initial_prompt": "The villagers have spoken of strange noises and ghostly apparitions emanating from the old Blackwood Manor. You've been hired to investigate. You stand before its imposing, creaky gates as dusk settles.",
        "start_location_id": "blackwood_manor_gates"
    },
    {
        "id": "default_adventure_start",
        "name": "A Standard Adventure Start",
        "initial_prompt": INITIAL_PROMPT_TEXT,
        "start_location_id": "default_start_location"
    }
]

USER_EXIT_COMMANDS = ["그만", "종료", "exit"]
