# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
# traceback removed
import re # 정규 표현식 사용 (문장 분할 등)
import logging
# import json # No longer needed directly here, handled by data_loader

# Import project modules
import config # Global configuration constants
from data_loader import load_documents, filter_documents, extract_text_for_rag, split_text_into_chunks
from rag_manager import RAGManager
from gemini_dm import GeminiDialogueManager

# --- Logging Configuration ---
# Basic config should be set up early, but specific logger instance for this file.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        try:
            player_input = input("Player: ")
        except EOFError:
            logger.info("\nEOF detected. Ending adventure.")
            break
        
        if player_input.lower() in config.USER_EXIT_COMMANDS:
            logger.info("Exit command received. Ending adventure.")
            break

        retrieved_context_docs = []
        if rag_mgr.collection and rag_mgr.collection.count() > 0 : # Only search if collection exists and has items
            logger.info("\n[RAG] Searching for relevant context...")
            try:
                retrieved_context_docs = rag_mgr.search(player_input, n_results=3)
                if retrieved_context_docs:
                    logger.info(f"[RAG] Found {len(retrieved_context_docs)} context snippets.")
                else:
                    logger.info("[RAG] No additional relevant context found.")
            except Exception as e: # Catch errors during RAG search
                logger.error(f"[RAG] Error during search: {e}", exc_info=True)
                retrieved_context_docs = [] # Ensure it's empty on error
        else:
            logger.info("[RAG] Skipping search as collection is empty or not available.")


        context_for_gemini = None
        if retrieved_context_docs:
            context_for_gemini = "\n".join([f"- {doc}" for doc in retrieved_context_docs])
            
        logger.info("\nDM's Turn (Streaming response):")
        try:
            dm_response = gemini_dm.send_message(
                user_prompt_text=player_input,
                rag_context=context_for_gemini # Pass the formatted string or None
            )
            # send_message handles printing and history
            if "Error:" in dm_response and gemini_dm.model is None: # Should not happen if initial call succeeded
                 logger.error(f"DM response indicates model error. Response: {dm_response}")
                 # Potentially break or handle this state
        except Exception as e:
            logger.error(f"Error during interaction with Gemini: {e}", exc_info=True)
            # Decide if to break or continue after an error
            print("\nAn error occurred. Please try again.") # User-facing message

    logger.info("--- Adventure Ended ---")

# --- END OF FILE main.py ---