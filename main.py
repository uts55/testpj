# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
import traceback
import re # 정규 표현식 사용 (문장 분할 등)
import logging

# --- Configuration Constants ---
# API and Model Configuration
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_NAME = "gemini-2.5-pro-exp-03-25" # 사용자가 명시적으로 요구한 모델 사용

# RAG Configuration
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' # 가볍고 성능 좋은 범용 모델
VECTOR_DB_PATH = "./chroma_db" # 로컬 디스크에 벡터 데이터를 저장할 경로
COLLECTION_NAME = "dnd_settings" # ChromaDB 컬렉션 이름

# File Paths
SETTINGS_FILEPATH = "my_personal_settings.txt" # 개인 설정 파일 경로

# Text Splitting Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100 # 청크 간 겹치는 글자 수 (split_text_into_chunks 호출 시 사용)

# Other
INITIAL_PROMPT_TEXT = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다. 플레이어의 첫 행동을 기다리는 상황을 가정하고, 모험의 시작을 알리는 흥미로운 도입부를 묘사해주세요."
USER_EXIT_COMMANDS = ["그만", "종료", "exit"]

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- API 키 로딩 (.env 파일 사용) ---
load_dotenv()
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

# --- 텍스트 분할 함수 정의 ---
def split_text_into_chunks(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """
    텍스트를 지정된 크기와 겹침으로 나누는 함수 (간단 버전)
    Args:
        text (str): 분할할 전체 텍스트
        chunk_size (int): 각 청크의 최대 글자 수
        chunk_overlap (int): 청크 간 겹치는 글자 수
    Returns:
        list[str]: 분할된 텍스트 청크 리스트
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        # 실제 end_index는 텍스트 길이를 넘지 않도록 조정
        actual_end_index = min(end_index, len(text))
        chunks.append(text[start_index:actual_end_index])

        # 다음 시작 위치는 겹침(overlap)을 고려하여 이동
        start_index += chunk_size - chunk_overlap

        # The main while loop condition 'while start_index < len(text):'
        # and the check 'chunk_overlap < chunk_size' (implicitly, due to ValueError)
        # are sufficient to prevent infinite loops and ensure termination.
        # The previous additional break conditions were redundant or could lead to premature termination.

    # 간단한 구현이므로, 마지막 청크가 너무 짧거나 하는 예외 처리는 생략됨
    # 좀 더 정교하게 하려면 문장 경계 등을 고려해야 함
    logger.info(f"Original text length: {len(text)}")
    logger.info(f"Number of chunks created: {len(chunks)}")
    if chunks:
         logger.info(f"Average chunk length: {sum(len(c) for c in chunks) / len(chunks):.2f}")
    return chunks

# --- 모델 이름 정의 ---
# GEMINI_MODEL_NAME은 Configuration Constants 섹션에서 정의됨
logger.info(f"사용할 Gemini 모델: {GEMINI_MODEL_NAME}")
# 주의: 'exp' 모델은 실험적이며 예고 없이 변경되거나 사용이 중단될 수 있습니다.
# Google AI Studio 또는 공식 문서에서 사용 가능한 모델인지, API 키에 접근 권한이 있는지 확인하는 것이 좋습니다.

# --- 모델 객체 생성 ---
try:
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    logger.info("GenerativeModel 객체 생성 완료.")
except Exception as e:
     logger.critical(f"오류: GenerativeModel 생성 중 문제가 발생했습니다.", exc_info=True)
     logger.critical(f"      모델 이름('{GEMINI_MODEL_NAME}')이 유효하지 않거나, 해당 모델에 대한 접근 권한이 없거나, API 키에 문제가 있을 수 있습니다.")
     exit()

# --- SRD 텍스트 로드 및 분할 ---
# SETTINGS_FILEPATH는 Configuration Constants 섹션에서 정의됨
text_chunks = [] # 분할된 청크를 저장할 리스트

try:
    # 파일 형식에 따라 읽는 방식 변경 필요할 수 있음 (예: PDF, DOCX 라이브러리 사용)
    # 여기서는 일반 텍스트 파일(.txt) 또는 마크다운(.md)으로 가정
    with open(SETTINGS_FILEPATH, 'r', encoding='utf-8') as f:
        settings_text = f.read()
    logger.info(f"성공적으로 '{SETTINGS_FILEPATH}' 파일을 읽었습니다.")

    # CHUNK_SIZE와 CHUNK_OVERLAP는 Configuration Constants에서 가져오거나 함수의 기본값을 사용
    text_chunks = split_text_into_chunks(settings_text) # CHUNK_SIZE, CHUNK_OVERLAP 기본값 사용

    if not text_chunks:
        logger.warning("[경고] 텍스트 분할 결과, 생성된 청크가 없습니다.")
        # 청크가 없으면 RAG 진행 불가
        exit() # 또는 다른 처리 로직
    else:
        logger.info(f"\n--- 총 {len(text_chunks)}개의 텍스트 청크 생성 완료 ---")
        # logger.debug(text_chunks[0][:300] + "...") # 첫 청크 확인 (선택적, 디버그 레벨)

except FileNotFoundError:
    logger.critical(f"[오류] 개인 설정 파일 '{SETTINGS_FILEPATH}'을 찾을 수 없습니다.")
    exit()
except Exception as e:
    logger.critical(f"[오류] 개인 설정 파일을 읽거나 분할하는 중 오류 발생:", exc_info=True)
    exit()


# --- RAG: 임베딩 모델 및 벡터 DB 설정 ---
# RAG 기능을 사용하지 않으려면 이 섹션 전체를 주석 처리하거나 건너뛸 수 있음

logger.info("\n--- RAG 설정 시작 ---")
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.utils import embedding_functions # 최신 ChromaDB는 이렇게 임포트할 수 있음
except ImportError as e:
    logger.critical("[오류] RAG 관련 라이브러리(sentence-transformers, chromadb)가 설치되지 않았습니다.", exc_info=True)
    logger.critical("      pip install sentence-transformers chromadb 명령어로 설치해주세요.")
    exit()

# 1. 임베딩 모델 로드
#    EMBEDDING_MODEL_NAME은 Configuration Constants 섹션에서 정의됨
try:
    logger.info(f"임베딩 모델 로딩 중 ('{EMBEDDING_MODEL_NAME}')... (시간이 좀 걸릴 수 있습니다)")
    # embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME) # SentenceTransformer 직접 사용 방식
    
    # ChromaDB 내장 함수 사용 방식 (더 간편할 수 있음)
    chroma_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    logger.info(f"임베딩 모델 '{EMBEDDING_MODEL_NAME}' 로드 완료.")
except Exception as e:
    logger.critical(f"[오류] 임베딩 모델 '{EMBEDDING_MODEL_NAME}' 로딩 실패:", exc_info=True)
    exit()

# 2. ChromaDB 클라이언트 설정
#    VECTOR_DB_PATH는 Configuration Constants 섹션에서 정의됨
try:
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    logger.info(f"ChromaDB 클라이언트 생성 완료 (저장 경로: {VECTOR_DB_PATH})")
except Exception as e:
    logger.critical("[오류] ChromaDB 클라이언트 생성 실패:", exc_info=True)
    exit()

# 3. 컬렉션 생성 또는 가져오기
#    COLLECTION_NAME은 Configuration Constants 섹션에서 정의됨
try:
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=chroma_embedding_function # 여기서 임베딩 함수 지정!
        # metadata={"hnsw:space": "cosine"} # 유사도 측정 방식 지정 (선택적)
    )
    logger.info(f"ChromaDB 컬렉션 '{COLLECTION_NAME}' 준비 완료.")
except Exception as e:
    logger.critical(f"[오류] ChromaDB 컬렉션 '{COLLECTION_NAME}' 생성 또는 가져오기 실패:", exc_info=True)
    exit()

# 4. 데이터 임베딩 및 저장 (컬렉션이 비어 있을 경우에만 실행)
try:
    if collection.count() == 0 and text_chunks:
        logger.info(f"컬렉션 '{COLLECTION_NAME}'이 비어있습니다. 데이터 임베딩 및 저장을 시작합니다...")
        logger.info(f"총 {len(text_chunks)}개의 청크를 처리합니다. (시간이 걸릴 수 있습니다)")

        ids = [f"chunk_{i}" for i in range(len(text_chunks))]
        collection.add(
            documents=text_chunks,
            ids=ids
            # metadatas=[{'source': SETTINGS_FILEPATH}] * len(text_chunks) # 메타데이터 추가 가능
        )
        logger.info(f"데이터 임베딩 및 저장 완료! 총 {collection.count()}개의 벡터가 저장되었습니다.")
    elif text_chunks:
        logger.info(f"컬렉션 '{COLLECTION_NAME}'에 이미 데이터({collection.count()}개)가 존재합니다. 임베딩 과정을 건너<0xEB><0x9B><0x81>니다.")
    else:
         logger.info("저장할 텍스트 청크가 없습니다.")
except Exception as e:
    logger.error("[오류] 데이터 임베딩 또는 저장 중 오류 발생:", exc_info=True)
    # 오류 발생 시 부분적으로 데이터가 저장되었을 수 있음

logger.info("--- RAG 설정 완료 ---")


# --- RAG: 정보 검색 함수 정의 ---
def search_vector_db(query_text, collection, n_results=3):
    """
    벡터 데이터베이스에서 주어진 쿼리와 가장 유사한 텍스트 청크를 검색합니다.
    Args:
        query_text (str): 검색할 사용자 질문 또는 키워드.
        collection (chromadb.Collection): 검색을 수행할 ChromaDB 컬렉션 객체.
        n_results (int): 검색 결과로 반환할 청크의 수.
    Returns:
        list[str]: 검색된 텍스트 청크 리스트 (유사도 순). 없을 경우 빈 리스트.
    """
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=['documents']
        )
        if results and results.get('documents') and results['documents']:
             retrieved_docs = results['documents'][0]
             # logger.debug(f"검색된 문서: {retrieved_docs}") # 디버깅용
             return retrieved_docs
        else:
             # logger.debug(f"검색 결과 없음 또는 documents 키 없음: {results}") # 디버깅용
             return []
    except Exception as e:
        logger.error(f"벡터 DB 검색 중 오류 발생:", exc_info=True)
        return []


# --- Tool 설정 (이전에 성공했던 방식) ---
tools = None
try:
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
    # INITIAL_PROMPT_TEXT는 Configuration Constants 섹션에서 정의됨
    contents_for_request = [
        {"role": "user", "parts": [{"text": INITIAL_PROMPT_TEXT}]}
    ]

    logger.info(f"\nGemini에게 보낼 첫 메시지:\n{INITIAL_PROMPT_TEXT}\n")
    # Use logger for messages that aren't part of the direct DM output stream
    logger.info("Gemini의 응답 (스트리밍 시작):")

    stream = model.generate_content(
        contents_for_request,
        stream=True,
        tools=tools
    )

    for chunk in stream:
        try:
            if chunk.parts:
                 chunk_text = ''.join(part.text for part in chunk.parts if hasattr(part, 'text'))
                 print(chunk_text, end="", flush=True) # Direct print for streaming output
                 full_response += chunk_text
        except Exception as chunk_e:
             logger.error(f"\n스트리밍 중 청크 처리 오류: {chunk_e}", exc_info=True)
             pass # Continue processing other chunks

    print("\n") # Ensure newline after streaming output
    logger.info("스트리밍 완료.")

    conversation_history.append({"role": "user", "parts": [{"text": INITIAL_PROMPT_TEXT}]})
    conversation_history.append({"role": "model", "parts": [{"text": full_response}]})

except Exception as e:
    logger.critical(f"초기 Gemini API 호출 또는 처리 중 문제가 발생했습니다.", exc_info=True)
    logger.critical("초기 호출 실패로 프로그램을 종료합니다.")
    exit()


# --- 상호작용 루프 시작 (RAG 통합) ---
if conversation_history:
    logger.info("\n--- 이제 모험을 시작합니다! ---")

    while True:
        try:
            player_input = input("플레이어: ")
        except EOFError:
             logger.info("\n입력 종료 (EOF). 모험을 종료합니다.")
             break

        if player_input.lower() in USER_EXIT_COMMANDS:
            logger.info("모험을 종료합니다.")
            break

        logger.info("\n[RAG] 관련 정보 검색 중...")
        try:
             retrieved_context = search_vector_db(player_input, collection, n_results=3)
             if retrieved_context:
                  logger.info(f"[RAG] {len(retrieved_context)}개의 관련 정보를 찾았습니다.")
                  # logger.debug(f"검색된 컨텍스트: {retrieved_context}")
             else:
                  logger.info("[RAG] 관련된 추가 정보를 찾지 못했습니다.")
        except NameError:
             logger.warning("[경고] RAG 컬렉션('collection')이 정의되지 않아 검색을 건너<0xEB><0x9B><0x81>니다.")
             retrieved_context = []
        except Exception as search_e:
             logger.error(f"[오류] RAG 검색 중 오류 발생: {search_e}", exc_info=True)
             retrieved_context = []

        # 3a. 검색된 컨텍스트를 프롬프트에 추가할 형태로 가공
        context_prompt_part = ""
        if retrieved_context:
            context_prompt_part += "\n\n[참고 자료 (개인 설정)]\n"
            for i, doc in enumerate(retrieved_context):
                context_prompt_part += f"- 문서 {i+1}: {doc}\n"
            context_prompt_part += "\n위 참고 자료를 바탕으로 답변해주세요.\n" # AI에게 활용하도록 지시

        # 3b. 현재 사용자 입력을 포함한 최종 프롬프트 리스트 구성
        #    주의: conversation_history는 이미 user/model 턴을 포함하고 있음
        #    따라서, 마지막 사용자 입력 전에 참고 자료를 넣는 것이 자연스러울 수 있음
        #    또는, 시스템 메시지처럼 맨 앞에 넣는 방법도 고려 가능
        
        # 방법 1: 마지막 사용자 입력 *전에* 컨텍스트 추가 (컨텍스트 + 최신 질문)
        prompt_for_gemini = conversation_history.copy() # 원본 유지 위해 복사
        # 마지막 사용자 입력(방금 받은 입력)을 임시로 추가하기 전에 컨텍스트 추가
        if context_prompt_part:
             # 컨텍스트 정보를 'user' 역할의 일부로 추가 (다른 역할도 가능)
             prompt_for_gemini.append({"role": "user", "parts": [{"text": context_prompt_part}]})
        # 마지막 사용자 입력을 최종적으로 추가
        prompt_for_gemini.append({"role": "user", "parts": [{"text": player_input}]})
        
        # (디버깅용) 최종 프롬프트 확인
        # logger.debug("\n--- 최종 프롬프트 (Gemini에게 전달) ---")
        # for item in prompt_for_gemini:
        #    logger.debug(f"[{item['role']}]: {item['parts'][0]['text'][:100]}...") # 일부만 출력
        # logger.debug("--------------------------------------")

        # === RAG 통합 끝 ===

        # Use logger for messages that aren't part of the direct DM output stream
        logger.info("\nDM 응답 (스트리밍 시작):")

        try:
            stream = model.generate_content(
                prompt_for_gemini,
                stream=True,
                tools=tools
            )

            current_dm_response = ""
            for chunk in stream:
                try:
                    if chunk.parts:
                        chunk_text = ''.join(part.text for part in chunk.parts if hasattr(part, 'text'))
                        print(chunk_text, end="", flush=True) # Direct print for streaming output
                        current_dm_response += chunk_text
                except Exception as chunk_e:
                    logger.error(f"\n스트리밍 중 청크 처리 오류: {chunk_e}", exc_info=True)
                    pass # Continue processing other chunks

            print("\n") # Ensure newline after streaming output

            # 6. 대화 기록 업데이트 (사용자 입력과 AI 응답 모두 추가)
            #    주의: RAG 컨텍스트는 임시로 프롬프트에만 사용하고,
            #          실제 대화 기록에는 사용자 입력과 모델 응답만 저장하는 것이 일반적임
            #          (컨텍스트까지 저장하면 기록이 너무 길어지고 중복될 수 있음)
            # 대화 기록 업데이트 로직 수정:
            # 1. 사용자 입력을 먼저 기록에 추가한다.
            # 2. API 호출 성공하고 응답이 있으면 모델 응답을 기록에 추가한다.
            # 3. API 호출 실패 또는 빈 응답 시, 이전에는 사용자 입력을 제거했으나,
            #    이제는 사용자 입력을 유지하고, 모델 응답이 없는 상태로 기록하거나
            #    또는 특정 메시지를 모델 응답으로 기록하는 것을 고려할 수 있다.
            #    여기서는 사용자 입력을 유지하고, 빈 모델 응답 시 알림을 로깅하고
            #    모델 응답은 기록에 추가하지 않는 현재 방식을 유지하되, 명시적으로 표현한다.

            conversation_history.append({"role": "user", "parts": [{"text": player_input}]})

            if current_dm_response:
                 conversation_history.append({"role": "model", "parts": [{"text": current_dm_response}]})
            else:
                 logger.info("[알림] DM으로부터 빈 응답을 받았습니다. (사용자 입력은 기록에 유지됩니다)")
                 # conversation_history.append({"role": "model", "parts": [{"text": "<빈 응답>"}]}) # 이렇게 명시적으로 기록도 가능

        except Exception as e:
            logger.error(f"상호작용 중 Gemini API 호출 또는 처리 중 문제가 발생했습니다.", exc_info=True)
            if conversation_history and conversation_history[-1]["role"] == "user" and \
               conversation_history[-1]["parts"][0]["text"] == player_input:
                 conversation_history.pop()
                 logger.info("[알림] 오류 발생으로 마지막 사용자 입력은 처리되지 않았고, 기록에서 제거되었습니다. 다시 시도해주세요.")
            else:
                 logger.warning("[알림] 오류 발생으로 마지막 사용자 입력 처리에 문제가 있었을 수 있습니다. 대화 기록을 확인해주세요.")

else:
     logger.warning("대화 기록이 초기화되지 않아 상호작용 루프를 시작할 수 없습니다.")
     
# --- END OF FILE main.py ---