# --- START OF FILE main.py ---

import google.generativeai as genai
from google.generativeai import types
import os
from dotenv import load_dotenv
import traceback
import re # 정규 표현식 사용 (문장 분할 등)


# --- API 키 로딩 (.env 파일 사용) ---
# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()
# 로드된 환경 변수에서 API 키를 읽습니다.
api_key = os.getenv("GOOGLE_API_KEY") # Colab과 달리 .env 파일 기준 GOOGLE_API_KEY 사용

if not api_key:
    print("오류: GOOGLE_API_KEY 환경 변수를 찾을 수 없습니다.")
    print("프로젝트 루트 디렉토리에 `.env` 파일이 있고, 그 안에 GOOGLE_API_KEY='YOUR_API_KEY' 형식으로 키가 저장되어 있는지 확인해주세요.")
    exit()

# API 키 설정 (이전 작동 방식 유지)
try:
    genai.configure(api_key=api_key)
    print("API 키 설정 완료 (configure 방식).")
except Exception as e:
     print(f"오류: API 키 설정 중 문제가 발생했습니다: {e}")
     exit()

# --- 텍스트 분할 함수 정의 ---
def split_text_into_chunks(text, chunk_size=1000, chunk_overlap=200):
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

        # 만약 마지막 청크가 생성되었고, 그 시작점이 텍스트 끝에 도달했다면 루프 종료
        if start_index >= len(text):
             break
        # 또는 마지막 청크를 생성한 후 다음 시작 위치가 이전 시작위치와 같다면 무한루프 방지
        if start_index <= (actual_end_index - chunk_size + chunk_overlap) and start_index != 0 :
             # print(f"Loop break condition met: start_index={start_index}") # Debug
             break


    # 간단한 구현이므로, 마지막 청크가 너무 짧거나 하는 예외 처리는 생략됨
    # 좀 더 정교하게 하려면 문장 경계 등을 고려해야 함
    print(f"Original text length: {len(text)}")
    print(f"Number of chunks created: {len(chunks)}")
    if chunks:
         print(f"Average chunk length: {sum(len(c) for c in chunks) / len(chunks):.2f}")
    return chunks

# --- 모델 이름 정의 ---
# 사용자가 명시적으로 요구한 모델 사용
model_name = "gemini-2.5-pro-exp-03-25"
print(f"사용할 모델: {model_name}")
# 주의: 'exp' 모델은 실험적이며 예고 없이 변경되거나 사용이 중단될 수 있습니다.
# Google AI Studio 또는 공식 문서에서 사용 가능한 모델인지, API 키에 접근 권한이 있는지 확인하는 것이 좋습니다.

# --- 모델 객체 생성 ---
try:
    model = genai.GenerativeModel(model_name)
    print("GenerativeModel 객체 생성 완료.")
except Exception as e:
     print(f"\n오류: GenerativeModel 생성 중 문제가 발생했습니다.")
     traceback.print_exc() # 더 자세한 오류 출력
     print(f"      모델 이름('{model_name}')이 유효하지 않거나, 해당 모델에 대한 접근 권한이 없거나, API 키에 문제가 있을 수 있습니다.")
     exit()

# --- SRD 텍스트 로드 및 분할 ---
settings_filepath = "my_personal_settings.txt"
text_chunks = [] # 분할된 청크를 저장할 리스트

try:
    # 파일 형식에 따라 읽는 방식 변경 필요할 수 있음 (예: PDF, DOCX 라이브러리 사용)
    # 여기서는 일반 텍스트 파일(.txt) 또는 마크다운(.md)으로 가정
    with open(settings_filepath, 'r', encoding='utf-8') as f:
        settings_text = f.read()
    print(f"성공적으로 '{settings_filepath}' 파일을 읽었습니다.")

    text_chunks = split_text_into_chunks(settings_text, chunk_size=1000, chunk_overlap=100)

    if not text_chunks:
        print("[경고] 텍스트 분할 결과, 생성된 청크가 없습니다.")
        # 청크가 없으면 RAG 진행 불가
        exit()
    else:
        print(f"\n--- 총 {len(text_chunks)}개의 텍스트 청크 생성 완료 ---")
        # print(text_chunks[0][:300] + "...") # 첫 청크 확인 (선택적)
        # print("---------------------------------")

except FileNotFoundError:
    print(f"[오류] 개인 설정 파일 '{settings_filepath}'을 찾을 수 없습니다.")
    exit()
except Exception as e:
    print(f"[오류] 개인 설정 파일을 읽거나 분할하는 중 오류 발생:")
    traceback.print_exc()
    exit()



# --- RAG: 임베딩 모델 및 벡터 DB 설정 ---
# RAG 기능을 사용하지 않으려면 이 섹션 전체를 주석 처리하거나 건너뛸 수 있음

print("\n--- RAG 설정 시작 ---")
# 필요한 라이브러리 임포트 (파일 상단으로 옮겨도 좋습니다)
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.utils import embedding_functions # 최신 ChromaDB는 이렇게 임포트할 수 있음
except ImportError:
    print("[오류] RAG 관련 라이브러리(sentence-transformers, chromadb-client)가 설치되지 않았습니다.")
    print("      pip install sentence-transformers chromadb-client 명령어로 설치해주세요.")
    exit()

# 1. 임베딩 모델 로드
#    'all-MiniLM-L6-v2'는 가볍고 성능 좋은 범용 모델입니다.
#    다른 모델(예: 한국어 특화 모델 'jhgan/ko-sroberta-multitask') 사용도 가능합니다.
try:
    print("임베딩 모델 로딩 중... (시간이 좀 걸릴 수 있습니다)")
    embedding_model_name = 'all-MiniLM-L6-v2'
    # embedding_model = SentenceTransformer(embedding_model_name) # SentenceTransformer 직접 사용 방식
    
    # ChromaDB 내장 함수 사용 방식 (더 간편할 수 있음)
    # SentenceTransformer 라이브러리가 내부적으로 필요합니다.
    chroma_embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=embedding_model_name
    )
    print(f"임베딩 모델 '{embedding_model_name}' 로드 완료.")
except Exception as e:
    print(f"[오류] 임베딩 모델 '{embedding_model_name}' 로딩 실패:")
    traceback.print_exc()
    exit()

# 2. ChromaDB 클라이언트 설정
#    로컬 디스크에 벡터 데이터를 저장합니다 ('./chroma_db' 폴더 생성됨).
try:
    vector_db_path = "./chroma_db"
    client = chromadb.PersistentClient(path=vector_db_path)
    print(f"ChromaDB 클라이언트 생성 완료 (저장 경로: {vector_db_path})")
except Exception as e:
    print("[오류] ChromaDB 클라이언트 생성 실패:")
    traceback.print_exc()
    exit()

# 3. 컬렉션 생성 또는 가져오기
#    컬렉션은 데이터를 담는 테이블과 유사합니다.
#    주의: embedding_function을 지정해야 해당 함수로 벡터를 생성/검색합니다.
collection_name = "dnd_settings" # 컬렉션 이름 (원하는 대로 변경 가능)
try:
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=chroma_embedding_function # 여기서 임베딩 함수 지정!
        # metadata={"hnsw:space": "cosine"} # 유사도 측정 방식 지정 (선택적)
    )
    print(f"ChromaDB 컬렉션 '{collection_name}' 준비 완료.")
except Exception as e:
    print(f"[오류] ChromaDB 컬렉션 '{collection_name}' 생성 또는 가져오기 실패:")
    traceback.print_exc()
    exit()

# 4. 데이터 임베딩 및 저장 (컬렉션이 비어 있을 경우에만 실행)
#    이미 데이터가 있다면 이 과정은 건너뛰어 시간과 리소스를 절약합니다.
try:
    if collection.count() == 0 and text_chunks:
        print(f"\n컬렉션 '{collection_name}'이 비어있습니다. 데이터 임베딩 및 저장을 시작합니다...")
        print(f"총 {len(text_chunks)}개의 청크를 처리합니다. (시간이 걸릴 수 있습니다)")

        # 청크 ID 생성 (간단하게 인덱스 사용)
        ids = [f"chunk_{i}" for i in range(len(text_chunks))]

        # ChromaDB의 add 함수는 내부적으로 임베딩 함수를 사용하여 벡터를 생성합니다.
        # 따라서 직접 embedding_model.encode()를 호출할 필요가 없습니다.
        collection.add(
            documents=text_chunks, # 원본 텍스트 청크 리스트
            ids=ids                 # 각 청크의 고유 ID 리스트
            # metadatas=[{'source': settings_filepath}] * len(text_chunks) # 메타데이터 추가 가능
        )

        print(f"\n데이터 임베딩 및 저장 완료! 총 {collection.count()}개의 벡터가 저장되었습니다.")

    elif text_chunks:
        print(f"\n컬렉션 '{collection_name}'에 이미 데이터({collection.count()}개)가 존재합니다. 임베딩 과정을 건너<0xEB><0x9B><0x81>니다.")
    else:
         print("\n[정보] 저장할 텍스트 청크가 없습니다.")

except Exception as e:
    print("[오류] 데이터 임베딩 또는 저장 중 오류 발생:")
    traceback.print_exc()
    # 오류 발생 시 부분적으로 데이터가 저장되었을 수 있음

print("--- RAG 설정 완료 ---")


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
        # collection.query()는 내부적으로 설정된 임베딩 함수를 사용하여 query_text를 벡터로 변환합니다.
        results = collection.query(
            query_texts=[query_text], # 검색할 텍스트 리스트 (하나만 검색)
            n_results=n_results,     # 가져올 결과 수
            include=['documents']    # 결과에 원본 문서(텍스트 청크) 포함
            # include=['documents', 'distances'] # 필요시 유사도 거리 포함 가능
        )

        # 결과 구조는 {'ids': [...], 'embeddings': None, 'documents': [[청크1, 청크2, ...]], 'metadatas': [[...]], 'distances': [[...]]} 형태일 수 있음
        # 'documents' 키 아래의 첫 번째 리스트([0])를 반환
        if results and results.get('documents') and results['documents']:
             retrieved_docs = results['documents'][0]
             # print(f"[DEBUG] 검색된 문서: {retrieved_docs}") # 디버깅용
             return retrieved_docs
        else:
             # print(f"[DEBUG] 검색 결과 없음 또는 documents 키 없음: {results}") # 디버깅용
             return []

    except Exception as e:
        print(f"[오류] 벡터 DB 검색 중 오류 발생:")
        traceback.print_exc()
        return [] # 오류 발생 시 빈 리스트 반환


# --- Tool 설정 (이전에 성공했던 방식) ---
tools = None # 기본값 None
try:
    # 이전 성공 방식: GoogleSearchRetrieval 사용
    search_retrieval_config = types.GoogleSearchRetrieval()
    search_tool = types.Tool(google_search_retrieval=search_retrieval_config)
    tools = [search_tool]
    print("[Info] Google Search Tool 설정 완료 (GoogleSearchRetrieval 방식).")
except AttributeError as e:
    # GoogleSearchRetrieval 조차 없는 아주 오래된 버전이거나 다른 문제
    print(f"\n[경고] Google Search Tool({type(e).__name__}: {e}) 설정 중 오류 발생. 라이브러리 버전 문제일 수 있습니다.")
    print("      Tool 기능 없이 진행합니다.")
    tools = None # 오류 시 비활성화
except Exception as tool_error:
    print(f"\n[경고] Tool 설정 중 예기치 않은 오류 발생 ({type(tool_error).__name__}). Tool 기능 없이 진행합니다.")
    tools = None


# --- (변수 초기화) ---
full_response = "" # 첫 API 호출 전 초기화
conversation_history = []

# --- 첫 번째 API 호출 ---
try:
    # AI에게 보낼 첫 메시지 (딕셔너리 형태 - 이전 성공 방식)
    initial_prompt_text = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다. 플레이어의 첫 행동을 기다리는 상황을 가정하고, 모험의 시작을 알리는 흥미로운 도입부를 묘사해주세요."
    contents_for_request = [
        {"role": "user", "parts": [{"text": initial_prompt_text}]}
    ]

    print(f"\nGemini에게 보낼 첫 메시지:\n{initial_prompt_text}\n")
    print("Gemini의 응답 (스트리밍):")

    # 스트리밍 호출 (model.generate_content 사용)
    stream = model.generate_content(
        contents_for_request,
        stream=True,
        tools=tools # 설정된 도구 전달
        # generation_config=... # 필요시 추가
    )

    # 스트리밍 응답 처리 (안전한 방식)
    for chunk in stream:
        try:
            # parts가 있는 경우에만 텍스트 추출 시도
            if chunk.parts:
                 chunk_text = ''.join(part.text for part in chunk.parts if hasattr(part, 'text'))
                 print(chunk_text, end="", flush=True)
                 full_response += chunk_text
            # else:
                 # print("\n[DEBUG] Received chunk without parts:", chunk) # 디버깅용
                 pass
        except Exception as chunk_e:
             # print(f"\n[DEBUG] Error processing chunk: {chunk_e}")
             pass

    print("\n\n스트리밍 완료.")

    # 첫 대화 내용을 기록에 추가 (딕셔너리 형태)
    conversation_history.append({"role": "user", "parts": [{"text": initial_prompt_text}]})
    conversation_history.append({"role": "model", "parts": [{"text": full_response}]})

except Exception as e:
    print(f"\n오류 발생: 초기 Gemini API 호출 또는 처리 중 문제가 발생했습니다.")
    traceback.print_exc()
    print("\n초기 호출 실패로 프로그램을 종료합니다.")
    exit()


# --- 상호작용 루프 시작 (RAG 통합) ---
if conversation_history:
    print("\n--- 이제 모험을 시작합니다! ---")

    # 시스템 프롬프트 정의 (루프 밖에서 정의하여 매번 반복 생성 방지)
    # 이 프롬프트는 실제 API 요청 시 conversation_history 앞에 추가될 수 있습니다.
    # (현재 구조에서는 conversation_history에 첫 user/model 턴으로 역할 부여)
    # system_prompt = "당신은 Dungeons & Dragons 5판 게임의 숙련된 던전 마스터입니다..."

    while True:
        # 1. 사용자 입력 받기
        try:
            player_input = input("플레이어: ")
        except EOFError:
             print("\n입력 종료. 모험을 종료합니다.")
             break

        if player_input.lower() in ["그만", "종료", "exit"]:
            print("모험을 종료합니다.")
            break

        # === RAG 통합 시작 ===
        # 2. 벡터 DB 검색 (사용자 입력을 쿼리로 사용)
        print("\n[RAG] 관련 정보 검색 중...")
        # collection 객체가 정의되어 있어야 함 (이전 코드에서 생성/가져옴)
        try:
             # 검색할 결과 수 조절 가능 (예: n_results=2)
             retrieved_context = search_vector_db(player_input, collection, n_results=3)
             if retrieved_context:
                  print(f"[RAG] {len(retrieved_context)}개의 관련 정보를 찾았습니다.")
                  # print(f"[DEBUG] 검색된 컨텍스트: {retrieved_context}") # 디버깅용
             else:
                  print("[RAG] 관련된 추가 정보를 찾지 못했습니다.")
        except NameError: # collection 객체가 정의되지 않은 경우
             print("[경고] RAG 컬렉션('collection')이 정의되지 않아 검색을 건너<0xEB><0x9B><0x81>니다.")
             retrieved_context = [] # 검색 결과를 빈 리스트로 처리
        except Exception as search_e:
             print(f"[오류] RAG 검색 중 오류 발생: {search_e}")
             retrieved_context = [] # 오류 시 빈 리스트로 처리

        # 3. 프롬프트 구성 (대화 기록 + 검색된 컨텍스트 + 사용자 입력)
        #    Gemini에게 전달할 최종 입력 내용을 구성합니다.

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
        # print("\n--- 최종 프롬프트 (Gemini에게 전달) ---")
        # for item in prompt_for_gemini:
        #    print(f"[{item['role']}]: {item['parts'][0]['text'][:100]}...") # 일부만 출력
        # print("--------------------------------------")

        # === RAG 통합 끝 ===

        print("\nDM 응답 (스트리밍):")

        # 4. 업데이트된 프롬프트로 Gemini API 호출 (스트리밍)
        try:
            stream = model.generate_content(
                # conversation_history 대신 강화된 프롬프트 전달
                prompt_for_gemini,
                stream=True,
                tools=tools # 설정된 도구 전달
            )

            # 5. 스트리밍 응답 처리 및 전체 응답 저장
            current_dm_response = ""
            # ... (스트리밍 처리 로직은 이전과 동일) ...
            for chunk in stream:
                try:
                    if chunk.parts:
                        chunk_text = ''.join(part.text for part in chunk.parts if hasattr(part, 'text'))
                        print(chunk_text, end="", flush=True)
                        current_dm_response += chunk_text
                    # else: pass
                except Exception as chunk_e: pass

            print("\n") # 응답 출력 후 줄바꿈

            # 6. 대화 기록 업데이트 (사용자 입력과 AI 응답 모두 추가)
            #    주의: RAG 컨텍스트는 임시로 프롬프트에만 사용하고,
            #          실제 대화 기록에는 사용자 입력과 모델 응답만 저장하는 것이 일반적임
            #          (컨텍스트까지 저장하면 기록이 너무 길어지고 중복될 수 있음)
            conversation_history.append({"role": "user", "parts": [{"text": player_input}]})
            if current_dm_response:
                 conversation_history.append({"role": "model", "parts": [{"text": current_dm_response}]})
            else:
                 print("[알림] DM으로부터 빈 응답을 받았습니다.")
                 # 빈 응답 시 직전 사용자 입력 제거
                 if conversation_history and conversation_history[-1]["role"] == "user":
                      conversation_history.pop()

        except Exception as e:
            print(f"\n오류 발생: 상호작용 중 문제가 발생했습니다.")
            traceback.print_exc()
            # 오류 발생 시, 방금 추가한 사용자 입력을 기록에서 제거 (컨텍스트는 기록 안됨)
            if conversation_history and conversation_history[-1]["role"] == "user":
                 conversation_history.pop()
                 print("[알림] 오류 발생으로 마지막 사용자 입력은 처리되지 않았습니다. 다시 시도해주세요.")

else:
     print("\n대화 기록이 초기화되지 않아 상호작용 루프를 시작할 수 없습니다.")
     
# --- END OF FILE main.py ---