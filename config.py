# --- Configuration Constants ---

# API and Model Configuration
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
VECTOR_DB_PATH = "./chroma_db"
COLLECTION_NAME = "dnd_settings"
RAG_DOCUMENT_SOURCES = ['./data/NPCs', './data/GameObjects', './data/Players']
RAG_DOCUMENT_FILTERS = {}
RAG_TEXT_FIELDS = ['description', 'lore_fragments', 'dialogue_responses.artifact_info', 'knowledge_fragments', 'name', 'text_content']

# Text Splitting Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Dialogue Manager Configuration
MAX_HISTORY_ITEMS = 20
MAX_API_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Other
INITIAL_PROMPT_TEXT = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다. 플레이어의 첫 행동을 기다리는 상황을 가정하고, 모험의 시작을 알리는 흥미로운 도입부를 묘사해주세요."
USER_EXIT_COMMANDS = ["그만", "종료", "exit"]
