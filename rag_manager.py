import os
import json
import logging # Using logging for messages

# Attempt to import RAG-specific libraries
try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    RAG_LIBRARIES_AVAILABLE = True
except ImportError:
    RAG_LIBRARIES_AVAILABLE = False
    logging.warning(
        "RAG libraries (sentence-transformers, chromadb) not found. "
        "RAG functionalities (initialize_vector_db, query_vector_db) will not work. "
        "Falling back to basic keyword search if enabled."
    )
    # Define dummy classes/functions if libraries are not available, so the rest of the file can be parsed
    class SentenceTransformer: pass
    class chromadb:
        class PersistentClient:
            def __init__(self, path): pass
            def get_or_create_collection(self, name, embedding_function=None): return None # Simplified
        def Documents(): pass # Placeholder
        def Embeddings(): pass # Placeholder
        def Metadatas(): pass # Placeholder


from data_loader import load_raw_data_from_sources # Corrected import
from config import RAG_DOCUMENT_SOURCES, RAG_TEXT_FIELDS, EMBEDDING_MODEL_NAME, VECTOR_DB_PATH, COLLECTION_NAME


def get_text_from_doc(doc: dict, text_fields: list[str]) -> str:
    """
    Extracts and concatenates text from specified fields in a document dictionary.
    Handles 'dialogue_responses' as a special case to extract 'npc_text' from dialogue nodes.

    Args:
        doc: The document dictionary (e.g., item, NPC, location data).
        text_fields: A list of field names to extract text from.

    Returns:
        A single string containing all extracted text, joined by spaces.
    """
    texts = []
    if not isinstance(doc, dict):
        logging.warning(f"Document is not a dictionary, cannot extract text. Doc: {str(doc)[:100]}")
        return ""

    for field in text_fields:
        if field == 'dialogue_responses':
            dialogue_data = doc.get(field)
            if isinstance(dialogue_data, dict):
                for _node_key, node_content in dialogue_data.items():
                    if isinstance(node_content, dict) and 'npc_text' in node_content:
                        texts.append(str(node_content['npc_text']))
        else:
            field_value = doc.get(field)
            if field_value is not None:
                texts.append(str(field_value))

    return " ".join(filter(None, texts)).strip()


def initialize_vector_db(
    all_raw_data: dict[str, list[dict | str]],
    text_fields: list[str],
    embedding_model_name: str,
    vector_db_path: str,
    collection_name: str
):
    """
    Initializes and populates a ChromaDB vector database with game content.

    Args:
        all_raw_data: Data loaded by data_loader.load_raw_data_from_sources().
        text_fields: List of fields to extract text from for embedding.
        embedding_model_name: Name of the SentenceTransformer model.
        vector_db_path: Path to store ChromaDB data.
        collection_name: Name of the ChromaDB collection.
    """
    if not RAG_LIBRARIES_AVAILABLE:
        logging.error("Cannot initialize vector DB: RAG libraries are not available.")
        return False

    logging.info(f"Initializing vector database. Model: {embedding_model_name}, Path: {vector_db_path}, Collection: {collection_name}")

    try:
        model = SentenceTransformer(embedding_model_name)
        client = chromadb.PersistentClient(path=vector_db_path)
        # Using a simple default embedding function for the collection as we provide embeddings directly.
        # ChromaDB's default (SentenceTransformer all-MiniLM-L6-v2) is often okay if not providing embeddings.
        # However, to ensure consistency with the model used for generating embeddings,
        # it's good practice to either pass pre-calculated embeddings or configure
        # the collection with a matching embedding function if it were to do it internally.
        # For this implementation, we generate embeddings and pass them directly.
        collection = client.get_or_create_collection(
            name=collection_name
            # metadata={"hnsw:space": "cosine"} # Example: specify distance function if needed
        )
    except Exception as e:
        logging.error(f"Error initializing SentenceTransformer model or ChromaDB client: {e}")
        return False

    doc_ids_to_add = []
    embeddings_to_add = []
    metadatas_to_add = []
    documents_to_add = [] # Text that was embedded

    total_docs_processed = 0
    for category_name, docs_list in all_raw_data.items():
        logging.info(f"Processing category: {category_name} ({len(docs_list)} documents)")
        for idx, doc_dict in enumerate(docs_list):
            if not isinstance(doc_dict, dict):
                logging.warning(f"Skipping non-dictionary document in {category_name}: {str(doc_dict)[:100]}")
                continue

            doc_id_val = doc_dict.get('id', f"missingid_{idx}")
            unique_id = f"{category_name}_{doc_id_val}"

            text_for_embedding = get_text_from_doc(doc_dict, text_fields)
            if not text_for_embedding:
                logging.warning(f"No text extracted for document ID '{unique_id}' in category '{category_name}'. Skipping.")
                continue

            try:
                embedding = model.encode(text_for_embedding).tolist()
            except Exception as e:
                logging.error(f"Error encoding document ID '{unique_id}': {e}. Text was: '{text_for_embedding[:100]}...'")
                continue

            doc_ids_to_add.append(unique_id)
            embeddings_to_add.append(embedding)
            metadatas_to_add.append({
                "category": category_name,
                "id": str(doc_id_val), # Original ID within its category
                "name": str(doc_dict.get('name', '')),
                # Storing the full original document as a JSON string in metadata can be too large for some DBs
                # or might be inefficient. Let's store key fields and the text used for embedding.
                # "original_doc_json": json.dumps(doc_dict) # Option: store full doc
            })
            documents_to_add.append(text_for_embedding) # Store the text that was actually embedded
            total_docs_processed += 1

    if doc_ids_to_add:
        try:
            logging.info(f"Adding {len(doc_ids_to_add)} documents to ChromaDB collection '{collection_name}'...")
            # Batch add documents. Chunking might be needed for very large datasets.
            # Max batch size for Chroma is around 41666.
            batch_size = 5000
            for i in range(0, len(doc_ids_to_add), batch_size):
                collection.add(
                    ids=doc_ids_to_add[i:i+batch_size],
                    embeddings=embeddings_to_add[i:i+batch_size],
                    metadatas=metadatas_to_add[i:i+batch_size],
                    documents=documents_to_add[i:i+batch_size]
                )
            logging.info(f"Successfully added {len(doc_ids_to_add)} documents to ChromaDB.")
        except Exception as e:
            logging.error(f"Error adding documents to ChromaDB: {e}")
            return False
    else:
        logging.info("No documents to add to ChromaDB.")

    return True


def query_vector_db(
    query_text: str,
    vector_db_path: str,
    collection_name: str,
    embedding_model_name: str,
    n_results: int = 5,
    filter_metadata: dict = None
) -> list[dict]:
    """
    Queries the ChromaDB vector database for relevant documents.

    Args:
        query_text: The query string.
        vector_db_path: Path to ChromaDB data.
        collection_name: Name of the ChromaDB collection.
        embedding_model_name: Name of the SentenceTransformer model.
        n_results: Number of results to retrieve.
        filter_metadata: Optional dictionary for metadata filtering (e.g., {"category": "NPCs"}).

    Returns:
        A list of retrieved document data (usually from metadatas), or an empty list if error.
    """
    if not RAG_LIBRARIES_AVAILABLE:
        logging.error("Cannot query vector DB: RAG libraries are not available.")
        return []

    try:
        model = SentenceTransformer(embedding_model_name)
        client = chromadb.PersistentClient(path=vector_db_path)
        collection = client.get_collection(name=collection_name) # Get existing collection
    except Exception as e:
        logging.error(f"Error initializing model or ChromaDB client/collection for query: {e}")
        return []

    if collection is None: # Should not happen if get_collection raises error on not found
        logging.error(f"Collection '{collection_name}' not found.")
        return []

    try:
        query_embedding = model.encode(query_text).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata if filter_metadata else None, # Apply metadata filter if provided
            include=['metadatas', 'documents', 'distances'] # Request these fields in results
        )

        # Process results to return a list of dictionaries with relevant info
        processed_results = []
        if results and results.get('ids') and results.get('ids')[0]: # results is a dict of lists
            num_retrieved = len(results['ids'][0])
            for i in range(num_retrieved):
                res_item = {
                    "retrieved_id": results['ids'][0][i],
                    "document_text": results['documents'][0][i] if results.get('documents') else None,
                    "metadata": results['metadatas'][0][i] if results.get('metadatas') else None,
                    "distance": results['distances'][0][i] if results.get('distances') else None,
                }
                processed_results.append(res_item)
        return processed_results

    except Exception as e:
        logging.error(f"Error querying ChromaDB: {e}")
        return []


# Old retrieve_context function (keyword-based) - can be kept as a fallback or removed.
# For this exercise, we are focusing on the new vector DB approach.
# def retrieve_context_keyword(player_input: str, data: dict) -> str: ... (old implementation)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("--- Running RAG Manager Demonstration ---")

    if not RAG_LIBRARIES_AVAILABLE:
        print("RAG libraries not available. Skipping RAG demonstration.")
    else:
        print("\nLoading raw game data for RAG initialization...")
        # Ensure RAG_DOCUMENT_SOURCES is correctly imported or defined for test
        # from config import RAG_DOCUMENT_SOURCES (already imported)

        all_data = load_raw_data_from_sources(RAG_DOCUMENT_SOURCES)

        if not all_data or all(not v for v in all_data.values()):
            print("No raw data loaded. Make sure RAG_DOCUMENT_SOURCES are correctly set up in config.py and point to valid data.")
        else:
            print(f"Loaded {sum(len(lst) for lst in all_data.values())} total documents across {len(all_data)} categories.")

            # Create a temporary, unique DB path for this test run to avoid conflicts
            test_db_path = "./chroma_db_test_rag_manager" # Use a distinct path for testing
            if os.path.exists(test_db_path):
                import shutil
                print(f"Removing existing test DB at: {test_db_path}")
                shutil.rmtree(test_db_path) # Clean up before run

            print(f"\nInitializing Vector DB at {test_db_path}...")
            success_init = initialize_vector_db(
                all_raw_data=all_data,
                text_fields=RAG_TEXT_FIELDS,
                embedding_model_name=EMBEDDING_MODEL_NAME,
                vector_db_path=test_db_path, # Use test path
                collection_name=COLLECTION_NAME
            )

            if success_init:
                print("Vector DB initialized successfully.")

                print("\n--- Performing Sample Queries ---")
                queries = [
                    "Tell me about healing potions",
                    "Who is Merchant Jane?",
                    "What is the history of the Eldoria Kingdom?",
                    "Information about a gloomy cave",
                    "Is there a sword here?"
                ]

                for q_text in queries:
                    print(f"\nQuery: \"{q_text}\"")
                    retrieved_docs = query_vector_db(
                        query_text=q_text,
                        vector_db_path=test_db_path, # Query the test path
                        collection_name=COLLECTION_NAME,
                        embedding_model_name=EMBEDDING_MODEL_NAME,
                        n_results=2
                    )
                    if retrieved_docs:
                        print("Results:")
                        for doc_info in retrieved_docs:
                            print(f"  ID: {doc_info.get('retrieved_id')}")
                            print(f"  Category: {doc_info.get('metadata',{}).get('category')}")
                            print(f"  Name: {doc_info.get('metadata',{}).get('name')}")
                            print(f"  Distance: {doc_info.get('distance'):.4f}")
                            print(f"  Text: \"{doc_info.get('document_text', '')[:150]}...\"")
                            # print(f"  Metadata: {doc_info.get('metadata')}") # Can be verbose
                    else:
                        print("  No results found or error during query.")

                # Example query with filter
                print(f"\nQuery with filter (category: NPCs): \"friendly merchant\"")
                filtered_results = query_vector_db(
                    query_text="friendly merchant",
                    vector_db_path=test_db_path,
                    collection_name=COLLECTION_NAME,
                    embedding_model_name=EMBEDDING_MODEL_NAME,
                    n_results=2,
                    filter_metadata={"category": "NPCs"}
                )
                if filtered_results:
                    print("Filtered Results (NPCs only):")
                    for doc_info in filtered_results:
                        print(f"  ID: {doc_info.get('retrieved_id')}, Category: {doc_info.get('metadata',{}).get('category')}, Name: {doc_info.get('metadata',{}).get('name')}, Distance: {doc_info.get('distance'):.4f}")
                else:
                    print("  No results found for filtered query.")

                # Clean up test DB
                # print(f"\nCleaning up test DB at: {test_db_path}")
                # shutil.rmtree(test_db_path) # Optional: clean up after test. For manual inspection, can be commented out.

            else:
                print("Failed to initialize Vector DB. Skipping queries.")

    print("\n--- RAG Manager Demonstration Finished ---")
