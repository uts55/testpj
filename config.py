# --- Configuration Constants ---

# API and Model Configuration
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
VECTOR_DB_PATH = "./chroma_db"
COLLECTION_NAME = "dnd_settings"
RAG_DOCUMENT_SOURCES = [
    './data/NPCs',
    './data/GameObjects',
    './data/Lore',
    './data/History',
    './data/Regions',
    './data/Factions',
    './data/Technology',
    './data/MagicSystems',
    './data/Races'
]
RAG_DOCUMENT_FILTERS = {}
RAG_TEXT_FIELDS = ['description', 'lore_fragments', 'dialogue_responses.artifact_info', 'knowledge_fragments', 'name', 'text_content']

# Text Splitting Configuration
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
