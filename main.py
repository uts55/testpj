# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
# traceback removed
import re # 정규 표현식 사용 (문장 분할 등)
import logging
import json # For load_documents and other functions

# --- Configuration Constants ---
# API and Model Configuration
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_NAME = "gemini-2.5-pro-exp-03-25"

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
VECTOR_DB_PATH = "./chroma_db"
COLLECTION_NAME = "dnd_settings"
RAG_DOCUMENT_SOURCES = ['./data']
RAG_DOCUMENT_FILTERS = {}
RAG_TEXT_FIELDS = ['description', 'lore_fragments', 'dialogue_responses.artifact_info', 'knowledge_fragments', 'name']

# Text Splitting Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Other
INITIAL_PROMPT_TEXT = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다. 플레이어의 첫 행동을 기다리는 상황을 가정하고, 모험의 시작을 알리는 흥미로운 도입부를 묘사해주세요."
USER_EXIT_COMMANDS = ["그만", "종료", "exit"]

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Function Definitions ---
def split_text_into_chunks(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    if chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")
    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        actual_end_index = min(end_index, len(text))
        chunks.append(text[start_index:actual_end_index])
        start_index += chunk_size - chunk_overlap
    # Removed logging from here to keep function focused on its core task
    return chunks

def load_documents(source_paths: list[str]) -> list[dict]:
    documents = []
    for path in source_paths:
        if os.path.isfile(path):
            if path.endswith(".json"):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            documents.extend(data)
                        elif isinstance(data, dict):
                            documents.append(data)
                        else:
                            logger.warning(f"Unexpected JSON structure in {path}. Expected list or dict at root.")
                except FileNotFoundError:
                    logger.error(f"File not found - {path}") # Keep logger for errors
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON format in - {path}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing {path}: {e}")
            else:
                logger.warning(f"Skipping non-JSON file: {path}")
        elif os.path.isdir(path):
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                if os.path.isfile(filepath) and filename.endswith(".json"):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                documents.extend(data)
                            elif isinstance(data, dict):
                                documents.append(data)
                            else:
                                logger.warning(f"Unexpected JSON structure in {filepath}. Expected list or dict at root.")
                    except FileNotFoundError: 
                        logger.error(f"File not found - {filepath}")
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON format in - {filepath}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred while processing {filepath}: {e}")
                elif os.path.isfile(filepath): 
                    logger.warning(f"Skipping non-JSON file: {filepath}") # Log skipping non-JSONs in directory
        else:
            logger.warning(f"Source path not found or invalid, skipping: {path}")
    return documents

def _get_nested_value(doc: dict, key_path: str):
    keys = key_path.split('.')
    value = doc
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list): 
            try:
                idx = int(key)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None 
            except ValueError: # Not an integer index
                return None 
        else: # Key not found or value is not a collection
            return None 
    return value

def filter_documents(documents: list[dict], filters: dict) -> list[dict]:
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
    extracted_texts = []
    for field_path in text_fields:
        value = _get_nested_value(document, field_path)
        if value is not None:
            texts_from_field = _extract_text_from_value(value)
            extracted_texts.extend(texts_from_field)
    return " ".join(extracted_texts)

# Comment removed

if __name__ == "__main__":
    # --- API 키 로딩 (.env 파일 사용) ---
    load_dotenv() # Loads environment variables from .env
    api_key = os.getenv(GOOGLE_API_KEY_ENV)

    if not api_key:
        logger.critical(f"오류: {GOOGLE_API_KEY_ENV} 환경 변수를 찾을 수 없습니다.")
        logger.critical(f"프로젝트 루트 디렉토리에 `.env` 파일이 있고, 그 안에 {GOOGLE_API_KEY_ENV}='YOUR_API_KEY' 형식으로 키가 저장되어 있는지 확인해주세요.")
        exit()

    try:
        genai.configure(api_key=api_key)
        logger.info("API 키 설정 완료 (configure 방식).")
    except Exception as e:
         logger.critical(f"오류: API 키 설정 중 문제가 발생했습니다: {e}", exc_info=True)
         exit()
    
    # --- 모델 객체 생성 ---
    logger.info(f"사용할 Gemini 모델: {GEMINI_MODEL_NAME}")
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        logger.info("GenerativeModel 객체 생성 완료.")
    except Exception as e:
         logger.critical(f"오류: GenerativeModel 생성 중 문제가 발생했습니다.", exc_info=True)
         logger.critical(f"      모델 이름('{GEMINI_MODEL_NAME}')이 유효하지 않거나, 해당 모델에 대한 접근 권한이 없거나, API 키에 문제가 있을 수 있습니다.")
         exit()

    # --- RAG Document Loading and Processing ---
    logger.info("--- RAG 문서 로딩 및 처리 시작 ---")
    # These variables are defined here as they are primarily used in the main execution flow
    text_chunks = []
    document_ids = []
    document_metadatas = []

    try:
        all_documents = load_documents(RAG_DOCUMENT_SOURCES) # Uses the global load_documents
        logger.info(f"총 {len(all_documents)}개의 문서를 {RAG_DOCUMENT_SOURCES}에서 로드했습니다.")

        if RAG_DOCUMENT_FILTERS:
            logger.info(f"다음 필터를 사용하여 문서 필터링: {RAG_DOCUMENT_FILTERS}")
            processed_documents = filter_documents(all_documents, RAG_DOCUMENT_FILTERS) # Uses global filter_documents
            logger.info(f"필터링 후 {len(processed_documents)}개의 문서가 남았습니다.")
        else:
            processed_documents = all_documents
            logger.info("문서 필터가 설정되지 않았습니다. 모든 로드된 문서를 처리합니다.")

        for i, doc in enumerate(processed_documents):
            extracted_text = extract_text_for_rag(doc, RAG_TEXT_FIELDS) # Uses global extract_text_for_rag
            if extracted_text:
                chunks_from_doc = split_text_into_chunks(extracted_text) # Uses global split_text_into_chunks
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
                if chunks_from_doc: # Log only if chunks were actually created
                     logger.debug(f"문서 ID '{doc_id_base}'에서 {len(chunks_from_doc)}개의 텍스트 조각 추출 및 분할 완료.")
            else:
                logger.warning(f"문서 ID '{doc.get('id', f'doc_{i}')}'에서 추출된 텍스트가 없습니다 (필드: {RAG_TEXT_FIELDS}).")

        if text_chunks:
            logger.info(f"--- 총 {len(text_chunks)}개의 텍스트 조각을 RAG 시스템에 추가할 준비가 되었습니다 ---")
        else:
            logger.warning("[경고] 처리 후 RAG 시스템에 추가할 텍스트 조각이 없습니다.")
            # Consider if an exit() is needed if no text chunks are available for RAG
    except Exception as e: # Catch any exception during document processing
        logger.critical(f"[오류] RAG 문서 로딩 또는 처리 중 오류 발생:", exc_info=True)
        exit()
    # --- End of RAG Document Loading and Processing ---

    # --- RAG: 임베딩 모델 및 벡터 DB 설정 ---
    # This section includes imports specific to RAG setup.
    logger.info("\n--- RAG 설정 시작 ---")
    try:
        from sentence_transformers import SentenceTransformer
        import chromadb
        from chromadb.utils import embedding_functions # For SentenceTransformerEmbeddingFunction
    except ImportError as e:
        logger.critical("[오류] RAG 관련 라이브러리(sentence-transformers, chromadb)가 설치되지 않았습니다.", exc_info=True)
        logger.critical("      pip install sentence-transformers chromadb 명령어로 설치해주세요.")
        exit()

    try:
        logger.info(f"임베딩 모델 로딩 중 ('{EMBEDDING_MODEL_NAME}')... (시간이 좀 걸릴 수 있습니다)")
        chroma_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME
        )
        logger.info(f"임베딩 모델 '{EMBEDDING_MODEL_NAME}' 로드 완료.")
    except Exception as e:
        logger.critical(f"[오류] 임베딩 모델 '{EMBEDDING_MODEL_NAME}' 로딩 실패:", exc_info=True)
        exit()

    try:
        client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        logger.info(f"ChromaDB 클라이언트 생성 완료 (저장 경로: {VECTOR_DB_PATH})")
    except Exception as e:
        logger.critical("[오류] ChromaDB 클라이언트 생성 실패:", exc_info=True)
        exit()

    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=chroma_embedding_function
        )
        logger.info(f"ChromaDB 컬렉션 '{COLLECTION_NAME}' 준비 완료.")
    except Exception as e:
        logger.critical(f"[오류] ChromaDB 컬렉션 '{COLLECTION_NAME}' 생성 또는 가져오기 실패:", exc_info=True)
        exit()

    try:
        if collection.count() == 0 and text_chunks: # Only add if collection is empty AND there are chunks
            logger.info(f"컬렉션 '{COLLECTION_NAME}'이 비어있습니다. 데이터 임베딩 및 저장을 시작합니다...")
            logger.info(f"총 {len(text_chunks)}개의 텍스트 조각을 처리합니다. (시간이 걸릴 수 있습니다)")
            collection.add(
                documents=text_chunks,
                ids=document_ids, # Ensure these are correctly populated
                metadatas=document_metadatas # Ensure these are correctly populated
            )
            logger.info(f"데이터 임베딩 및 저장 완료! 총 {collection.count()}개의 벡터가 저장되었습니다.")
        elif text_chunks: # If text_chunks exist but collection is not empty
            logger.info(f"컬렉션 '{COLLECTION_NAME}'에 이미 데이터({collection.count()}개)가 존재합니다. 임베딩 과정을 건너<0xEB><0x9B><0x81>니다.")
        else: # No text_chunks to add
             logger.info("RAG를 위해 저장할 텍스트 조각이 없습니다.")
    except Exception as e: # Catch any exception during embedding/saving
        logger.error("[오류] 데이터 임베딩 또는 저장 중 오류 발생:", exc_info=True)
        # Depending on severity, might consider an exit() here
    logger.info("--- RAG 설정 완료 ---")

    # --- RAG: 정보 검색 함수 정의 (specific to main execution as it uses 'collection') ---
    def search_vector_db_main(query_text, n_results=3): # Renamed to avoid conflict if global one exists
        """
        벡터 데이터베이스에서 주어진 쿼리와 가장 유사한 텍스트 청크를 검색합니다.
        Uses 'collection' defined within this __main__ block.
        """
        # Ensure 'collection' is available in this scope
        if 'collection' not in locals() and 'collection' not in globals():
            logger.error("RAG 컬렉션('collection')이 search_vector_db_main 내에서 접근 불가능합니다.")
            return []
        try:
            results = collection.query( # Uses the 'collection' from the main block
                query_texts=[query_text],
                n_results=n_results,
                include=['documents']
            )
            if results and results.get('documents') and results['documents'][0]:
                 retrieved_docs = results['documents'][0]
                 return retrieved_docs
            else:
                 return []
        except Exception as e:
            logger.error(f"벡터 DB 검색 중 오류 발생 (search_vector_db_main):", exc_info=True)
            return []

    # --- Tool 설정 ---
    tools = None
    try:
        # Ensure 'types' is available if not imported globally or re-import if necessary
        # from google.generativeai import types # Could be here if only for main
        search_retrieval_config = types.GoogleSearchRetrieval()
        search_tool = types.Tool(google_search_retrieval=search_retrieval_config)
        tools = [search_tool]
        logger.info("Google Search Tool 설정 완료 (GoogleSearchRetrieval 방식).")
    except AttributeError as e:
        logger.warning(f"Google Search Tool ({type(e).__name__}: {e}) 설정 중 오류 발생. 라이브러리 버전 문제일 수 있습니다.")
        logger.warning("Tool 기능 없이 진행합니다.")
        tools = None
    except Exception as tool_error:
        logger.warning(f"Tool 설정 중 예기치 않은 오류 발생 ({type(tool_error).__name__}). Tool 기능 없이 진행합니다.", exc_info=True)
        tools = None
    
    # --- (변수 초기화) ---
    full_response = ""
    conversation_history = []

    # --- 첫 번째 API 호출 ---
    try:
        contents_for_request = [
            {"role": "user", "parts": [{"text": INITIAL_PROMPT_TEXT}]}
        ]
        logger.info(f"\nGemini에게 보낼 첫 메시지:\n{INITIAL_PROMPT_TEXT}\n")
        logger.info("Gemini의 응답 (스트리밍 시작):") # Log before print
        stream = model.generate_content( # Uses 'model' from the main block
            contents_for_request,
            stream=True,
            tools=tools # Uses 'tools' from the main block
        )
        for stream_chunk in stream:
            try:
                if stream_chunk.parts:
                     # Ensure part.text exists before joining
                     chunk_text = ''.join(part.text for part in stream_chunk.parts if hasattr(part, 'text'))
                     print(chunk_text, end="", flush=True)
                     full_response += chunk_text
            except Exception as chunk_processing_error: # More specific variable name
                 logger.error(f"\n스트리밍 중 청크 처리 오류: {chunk_processing_error}", exc_info=True)
                 pass # Attempt to continue with other chunks
        print("\n") # Newline after streaming is complete
        logger.info("스트리밍 완료.") # Log after streaming
        conversation_history.append({"role": "user", "parts": [{"text": INITIAL_PROMPT_TEXT}]})
        conversation_history.append({"role": "model", "parts": [{"text": full_response}]})
    except Exception as e: # Catch any exception during initial API call
        logger.critical(f"초기 Gemini API 호출 또는 처리 중 문제가 발생했습니다.", exc_info=True)
        logger.critical("초기 호출 실패로 프로그램을 종료합니다.")
        exit()

    # --- 상호작용 루프 시작 (RAG 통합) ---
    if conversation_history: # Check if initial call was successful
        logger.info("\n--- 이제 모험을 시작합니다! ---")
        while True:
            try:
                player_input = input("플레이어: ")
            except EOFError: # Handle Ctrl+D
                 logger.info("\n입력 종료 (EOF). 모험을 종료합니다.")
                 break # Exit loop
            if player_input.lower() in USER_EXIT_COMMANDS:
                logger.info("모험을 종료합니다.")
                break # Exit loop

            logger.info("\n[RAG] 관련 정보 검색 중...")
            try:
                 # Uses 'search_vector_db_main' which uses 'collection' from this block
                 retrieved_context = search_vector_db_main(player_input, n_results=3) 
                 if retrieved_context:
                      logger.info(f"[RAG] {len(retrieved_context)}개의 관련 정보를 찾았습니다.")
                 else:
                      logger.info("[RAG] 관련된 추가 정보를 찾지 못했습니다.")
            # Removed NameError catch as search_vector_db_main checks for 'collection'
            except Exception as search_e:
                 logger.error(f"[오류] RAG 검색 중 오류 발생: {search_e}", exc_info=True)
                 retrieved_context = [] # Ensure it's an empty list on error

            context_prompt_part = ""
            if retrieved_context: # Check if context was actually retrieved
                context_prompt_part += "\n\n[참고 자료 (RAG 시스템 제공)]\n"
                for i, doc_text in enumerate(retrieved_context): # Iterate over list of strings
                    context_prompt_part += f"- 정보 {i+1}: {doc_text}\n"
                context_prompt_part += "\n위 참고 자료를 바탕으로 답변해주세요.\n"
            
            prompt_for_gemini = conversation_history.copy() # Start with existing history
            if context_prompt_part: # Add context if available
                 prompt_for_gemini.append({"role": "user", "parts": [{"text": context_prompt_part}]})
            prompt_for_gemini.append({"role": "user", "parts": [{"text": player_input}]}) # Add current player input
            
            logger.info("\nDM 응답 (스트리밍 시작):") # Log before print
            try:
                stream = model.generate_content( # Uses 'model' from this block
                    prompt_for_gemini,
                    stream=True,
                    tools=tools # Uses 'tools' from this block
                )
                current_dm_response = ""
                for stream_chunk_interaction in stream:
                    try:
                        if stream_chunk_interaction.parts:
                            # Ensure part.text exists
                            chunk_text = ''.join(part.text for part in stream_chunk_interaction.parts if hasattr(part, 'text'))
                            print(chunk_text, end="", flush=True)
                            current_dm_response += chunk_text
                    except Exception as chunk_interaction_processing_error: # More specific variable name
                        logger.error(f"\n스트리밍 중 청크 처리 오류: {chunk_interaction_processing_error}", exc_info=True)
                        pass # Attempt to continue
                print("\n") # Newline after streaming
                
                # Update conversation history
                conversation_history.append({"role": "user", "parts": [{"text": player_input}]})
                if current_dm_response: # Check if there was a response
                     conversation_history.append({"role": "model", "parts": [{"text": current_dm_response}]})
                else:
                     logger.info("[알림] DM으로부터 빈 응답을 받았습니다. (사용자 입력은 기록에 유지됩니다)")

            except Exception as e: # Catch any exception during interaction API call
                logger.error(f"상호작용 중 Gemini API 호출 또는 처리 중 문제가 발생했습니다.", exc_info=True)
                # Rollback last user input if error occurred during model's response generation for that input
                if conversation_history and conversation_history[-1]["role"] == "user" and \
                   conversation_history[-1]["parts"][0]["text"] == player_input:
                     # This implies the immediately preceding user input might not have gotten a model response
                     # However, we already added the user input. If the goal is to remove it on error,
                     # it should be done carefully. For now, logging is good.
                     logger.warning("[알림] 오류 발생으로 마지막 사용자 입력에 대한 모델 응답 처리에 문제가 있었을 수 있습니다.")
    else: # If conversation_history is empty (initial call failed)
         logger.warning("대화 기록이 초기화되지 않아 상호작용 루프를 시작할 수 없습니다.")

# --- END OF FILE main.py ---