# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
# traceback removed
import re # 정규 표현식 사용 (문장 분할 등)
import logging
import os # Added for checking file existence
# import json # No longer needed directly here, handled by data_loader

# Import project modules
import config # Global configuration constants
from data_loader import load_documents, filter_documents, extract_text_for_rag, split_text_into_chunks
from rag_manager import RAGManager
from gemini_dm import GeminiDialogueManager
from game_state import GameState, Player, NPC, Location, Item # Added for game state management

# --- Logging Configuration ---
# Basic config should be set up early, but specific logger instance for this file.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SAVE_GAME_FILENAME = "save_game.json"
MAIN_PLAYER_ID = "player_001"
DEFAULT_START_LOCATION_ID = "default_start_location"

if __name__ == "__main__":
    # --- Environment and API Key Setup ---
    load_dotenv()
    api_key = os.getenv(config.GOOGLE_API_KEY_ENV)
    if not api_key:
        logger.critical(f"Error: {config.GOOGLE_API_KEY_ENV} environment variable not found.")
        logger.critical(f"Ensure a `.env` file exists in the project root with {config.GOOGLE_API_KEY_ENV}='YOUR_API_KEY'.")
        exit()
    logger.info("API key loaded successfully.")

    # --- RAG Setup and Document Processing ---
    logger.info("--- Initializing RAG Manager ---")
    try:
        rag_mgr = RAGManager(
            embedding_model_name=config.EMBEDDING_MODEL_NAME,
            vector_db_path=config.VECTOR_DB_PATH,
            collection_name=config.COLLECTION_NAME
        )
        if not rag_mgr.collection: # Check if RAG manager failed to initialize its collection
             logger.critical("RAG Manager's collection is not initialized. Exiting.")
             exit()
    except Exception as e:
        logger.critical(f"Failed to initialize RAGManager: {e}", exc_info=True)
        exit()
    
    logger.info("--- RAG Document Loading and Processing ---")
    text_chunks = []
    document_ids = []
    document_metadatas = []

    try:
        all_documents = load_documents(config.RAG_DOCUMENT_SOURCES)
        logger.info(f"Loaded {len(all_documents)} documents from {config.RAG_DOCUMENT_SOURCES}.")

        if config.RAG_DOCUMENT_FILTERS:
            logger.info(f"Filtering documents with: {config.RAG_DOCUMENT_FILTERS}")
            processed_documents = filter_documents(all_documents, config.RAG_DOCUMENT_FILTERS)
            logger.info(f"{len(processed_documents)} documents remaining after filtering.")
        else:
            processed_documents = all_documents
            logger.info("No document filters set. Processing all loaded documents.")

        for i, doc in enumerate(processed_documents):
            extracted_text = extract_text_for_rag(doc, config.RAG_TEXT_FIELDS)
            if extracted_text:
                chunks_from_doc = split_text_into_chunks(extracted_text) # Uses CHUNK_SIZE, CHUNK_OVERLAP from config via data_loader
                doc_id_base = doc.get('id', f'doc_{i}')
                for chunk_idx, chunk_content in enumerate(chunks_from_doc):
                    text_chunks.append(chunk_content)
                    document_ids.append(f"{doc_id_base}_chunk_{chunk_idx}")
                    document_metadatas.append({
                        'source_id': doc.get('id', 'unknown'),
                        'name': doc.get('name', 'Unnamed Document'),
                        'original_doc_idx': i,
                        'chunk_idx_in_doc': chunk_idx
                    })
                if chunks_from_doc:
                    logger.debug(f"Processed document ID '{doc_id_base}', created {len(chunks_from_doc)} chunks.")
            else:
                logger.warning(f"No text extracted for document ID '{doc.get('id', f'doc_{i}')}' (fields: {config.RAG_TEXT_FIELDS}).")
        
        if text_chunks:
            logger.info(f"Total {len(text_chunks)} text chunks prepared for RAG system.")
            rag_mgr.add_documents_to_collection(text_chunks, document_ids, document_metadatas)
        else:
            logger.warning("No text chunks available to add to RAG system.")

    except Exception as e:
        logger.critical(f"Error during RAG document loading or processing: {e}", exc_info=True)
        exit()
    logger.info("--- RAG Document Loading and Processing Finished ---")

    logger.info("--- Initializing Gemini Dialogue Manager ---")
    tools_list_for_gemini = None
    try:
        # Configure Google Search tool (optional)
        search_retrieval_config = types.GoogleSearchRetrieval()
        search_tool = types.Tool(google_search_retrieval=search_retrieval_config)
        tools_list_for_gemini = [search_tool]
        logger.info("Google Search Tool configured.")
    except AttributeError as e: # Specific error if types.GoogleSearchRetrieval is not found (e.g. older library)
        logger.warning(f"Could not configure Google Search Tool (AttributeError: {e}). This might be due to an outdated library version. Proceeding without tools.")
    except Exception as e:
        logger.warning(f"An unexpected error occurred during Google Search Tool setup: {e}. Proceeding without tools.", exc_info=True)

    try:
        dm_system_instruction = (
            "You are a Dungeon Master for a Dungeons & Dragons 5th Edition game. "
            "Your primary role is to describe the world, narrate events, roleplay non-player characters (NPCs), "
            "and adjudicate the rules of the game. Be descriptive, engaging, and fair. "
            "Use the information provided by the RAG system to answer rule questions or provide context. "
            "If asked to perform an action that requires a tool (like a Google Search), "
            "initiate the tool use and incorporate its results into your response."
        )
        logger.info("System instruction for Dialogue Manager defined.")

        gemini_dm = GeminiDialogueManager(
            api_key=api_key,
            gemini_model_name=config.GEMINI_MODEL_NAME,
            tools=tools_list_for_gemini,
            system_instruction_text=dm_system_instruction,
            max_history_items=config.MAX_HISTORY_ITEMS,
            max_retries=config.MAX_API_RETRIES,
            initial_backoff_seconds=config.INITIAL_BACKOFF_SECONDS
        )
        if not gemini_dm.model: # Check if Gemini DM failed to initialize its model
            logger.critical("Gemini Dialogue Manager's model is not initialized. Exiting.")
            exit()
    except Exception as e:
        logger.critical(f"Failed to initialize GeminiDialogueManager: {e}", exc_info=True)
        exit()
    logger.info("Gemini Dialogue Manager initialized.")

    # --- Game State Initialization and Loading ---
    logger.info("--- Initializing Game State ---")
    game_state = GameState()
    
    save_file_exists = os.path.exists(SAVE_GAME_FILENAME)
    
    game_state.load_game(SAVE_GAME_FILENAME) # This method prints its own detailed status
    
    if save_file_exists:
        # game_state.load_game would have printed success or specific error.
        # If it was a critical error, we might not reach here.
        # This log indicates that a save file was present and processed.
        logger.info(f"Attempted to load saved game from '{SAVE_GAME_FILENAME}'. Check console for details from GameState.")
    else:
        # game_state.load_game would have printed "file not found".
        logger.info(f"No saved game file found at '{SAVE_GAME_FILENAME}'. Starting a new game.")
    
    # General message that initialization is done, regardless of loading a save or starting fresh.
    # logger.info("Game state manager initialized.") # Moved this log message

    # --- Check Load Status and Initialize New Game if Necessary ---
    game_loaded_successfully_and_player_exists = False
    if save_file_exists:
        if game_state.get_player(MAIN_PLAYER_ID) is not None:
            logger.info(f"Successfully loaded saved game including main player {MAIN_PLAYER_ID} from '{SAVE_GAME_FILENAME}'.")
            game_loaded_successfully_and_player_exists = True
        else:
            # Save file existed but was perhaps empty, corrupt, or didn't have our player.
            # game_state.load_game() would have logged specific file errors.
            logger.warning(f"Save file '{SAVE_GAME_FILENAME}' found, but main player {MAIN_PLAYER_ID} is missing or data is incomplete.")
    else:
        # This message is already logged by game_state.load_game(), but good for main.py context too.
        logger.info(f"No saved game file found at '{SAVE_GAME_FILENAME}'.")

    if not game_loaded_successfully_and_player_exists:
        logger.info("No valid saved game for the main player found. Starting new game setup...")
        # DEFAULT_START_LOCATION_ID is "default_start_location" as defined at the top of main.py
        # The initialize_new_game method will use this ID to create the starting location.
        game_state.initialize_new_game(MAIN_PLAYER_ID, "Adventurer", DEFAULT_START_LOCATION_ID)
        # game_state.initialize_new_game() logs its own completion message.
    
    logger.info("Game state manager ready.") # Final status

    # --- Initial API Call ---
    logger.info("\n--- Starting conversation with Initial Prompt ---")
    try:
        initial_response = gemini_dm.send_message(config.INITIAL_PROMPT_TEXT)
        if "Error:" in initial_response and gemini_dm.model is None : # Check if model initialization failed within send_message
             logger.critical(f"Initial message failed because Gemini model is not available in DM. Response: {initial_response}")
             exit()
        elif not initial_response and not gemini_dm.history: # If initial response is empty and history is not even populated
            logger.critical("Initial response was empty and conversation history was not initiated. This could indicate a problem with the API or model. Exiting.")
            exit()
        # send_message already prints the stream and updates history
    except Exception as e:
        logger.critical(f"Critical error during initial message to Gemini: {e}", exc_info=True)
        exit()
    
    if not gemini_dm.history or len(gemini_dm.history) < 2:
        logger.critical("Conversation history not properly initialized after initial prompt. Exiting.")
        exit()

    # --- Interaction Loop ---
    logger.info("\n--- Adventure Begins! Type '그만', '종료', or 'exit' to end. ---")
    while True:
        # --- Generate Current State Summary ---
        player = game_state.get_player(MAIN_PLAYER_ID)
        current_state_summary = ""
        if player:
            player_name = player.name
            player_hp = player.stats.get('hp', 'N/A')
            location_id = player.current_location
            location_obj = game_state.locations.get(location_id)
            location_name = location_obj.name if location_obj else location_id
            
            npcs_in_loc_objs = game_state.get_npcs_in_location(location_id)
            npc_names = [npc.name for npc in npcs_in_loc_objs] if npcs_in_loc_objs else ["None"]
            
            current_state_summary = (
                f"\n[현재 상태]\n"
                f"플레이어: {player_name}\n"
                f"위치: {location_name}\n"
                f"HP: {player_hp}\n"
                f"주변 NPC: {', '.join(npc_names)}\n"
                f"인벤토리: {', '.join(player.inventory) if player.inventory else 'Empty'}\n"
            )
            logger.info(f"Current State Summary generated for player {MAIN_PLAYER_ID}:\n{current_state_summary}")
        else:
            current_state_summary = "[현재 상태]\nPlayer data not available.\n"
            logger.warning(f"Player {MAIN_PLAYER_ID} not found for state summary generation.")

        try:
            player_input_original = input(f"{current_state_summary}\nPlayer: ")
        except EOFError:
            logger.info("\nEOF detected. Ending adventure.")
            game_state.save_game(SAVE_GAME_FILENAME) # Save on EOF
            break
        
        if player_input_original.lower() in config.USER_EXIT_COMMANDS:
            logger.info("Exit command received. Saving game before ending adventure...")
            game_state.save_game(SAVE_GAME_FILENAME) 
            logger.info("Game saved. Ending adventure.")
            break
        
        elif player_input_original.lower() == "save":
            logger.info("Save command received. Saving game state...")
            game_state.save_game(SAVE_GAME_FILENAME)
            logger.info("Game saved.") 
            continue

        # --- Basic Player Input Parsing and State Update ---
        player_command_processed = False
        player_for_action = game_state.get_player(MAIN_PLAYER_ID)

        if player_for_action:
            if player_input_original.lower().startswith("go "):
                direction = player_input_original.lower().split(" ", 1)[1]
                if player_for_action.current_location:
                    current_loc_obj = game_state.locations.get(player_for_action.current_location)
                    if current_loc_obj and direction in current_loc_obj.exits:
                        new_location_id = current_loc_obj.exits[direction]
                        player_for_action.change_location(new_location_id)
                        # GameState's update_npc_location might be relevant if NPCs also move between locations due to player actions.
                        # For now, only player moves.
                        logger.info(f"Player {player_for_action.name} moved from {current_loc_obj.id} to {new_location_id} via command.")
                    else:
                        logger.info(f"Cannot go {direction} from {player_for_action.current_location}.")
                player_command_processed = True # Command was 'go', even if failed.
            
            elif "take sword" in player_input_original.lower():
                # This is a placeholder. A real system would check if "sword_001" is in the current location.
                # And if GameState.items has "sword_001" defined.
                SWORD_ID = "sword_001" 
                if SWORD_ID not in game_state.items: # Create dummy item if not in master list
                    game_state.items[SWORD_ID] = Item(id=SWORD_ID, name="Basic Sword", description="A simple steel sword.")
                    logger.info(f"Dummy item {SWORD_ID} created in GameState.items for 'take sword' command.")

                player_for_action.add_item_to_inventory(SWORD_ID)
                # Potentially remove item from Location.items list if that's modeled.
                # current_loc_obj = game_state.locations.get(player_for_action.current_location)
                # if current_loc_obj and SWORD_ID in current_loc_obj.items:
                #    current_loc_obj.items.remove(SWORD_ID)
                logger.info(f"Player {player_for_action.name} picked up a sword (assumed {SWORD_ID}).")
                player_command_processed = True

        # Prepare prompt for Gemini
        # If a command was processed locally, we might not need to send it to Gemini,
        # or we might send a confirmation/result. For now, always send.
        prompt_for_gemini = player_input_original
        if current_state_summary: # Prepend summary if available
             prompt_for_gemini = f"{current_state_summary}\nPlayer's Action: {player_input_original}"


        retrieved_context_docs = []
        if rag_mgr.collection and rag_mgr.collection.count() > 0 : 
            logger.info("\n[RAG] Searching for relevant context based on original input...")
            try:
                # Use original input for RAG search, not the summary-prepended one.
                retrieved_context_docs = rag_mgr.search(player_input_original, n_results=3) 
                if retrieved_context_docs:
                    logger.info(f"[RAG] Found {len(retrieved_context_docs)} context snippets for '{player_input_original}'.")
                else:
                    logger.info(f"[RAG] No additional relevant context found for '{player_input_original}'.")
            except Exception as e: 
                logger.error(f"[RAG] Error during search for '{player_input_original}': {e}", exc_info=True)
                retrieved_context_docs = [] 
        else:
            logger.info("[RAG] Skipping search as RAG collection is empty or not available.")

        rag_context_for_gemini = None
        if retrieved_context_docs:
            rag_context_for_gemini = "\n".join([f"- {doc}" for doc in retrieved_context_docs])
            
        logger.info("\nDM's Turn (Streaming response):")
        try:
            # Pass the potentially summary-prepended prompt to Gemini
            dm_response = gemini_dm.send_message(
                user_prompt_text=prompt_for_gemini, 
                rag_context=rag_context_for_gemini 
            )
            # send_message handles printing and history

            # --- Basic Gemini Response Parsing and State Update ---
            if player_for_action: # Ensure player exists for actions
                if "you take 5 damage" in dm_response.lower(): # dm_response is the streamed string output
                    logger.info("DM response indicates player takes 5 damage. Updating state.")
                    player_for_action.take_damage(5)
                    game_state.apply_event({'type': 'damage', 'target': MAIN_PLAYER_ID, 'amount': 5, 'source': 'gemini_response'})
                # Add more response parsing here as needed

            if "Error:" in dm_response and gemini_dm.model is None: 
                 logger.error(f"DM response indicates model error. Response: {dm_response}")
        except Exception as e:
            logger.error(f"Error during interaction with Gemini: {e}", exc_info=True)
            print("\nAn error occurred with the DM. Please try again.")

    logger.info("--- Adventure Ended ---")

# --- END OF FILE main.py ---