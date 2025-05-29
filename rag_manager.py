import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class RAGManager:
    def __init__(self, embedding_model_name: str, vector_db_path: str, collection_name: str):
        self.embedding_function = None
        self.client = None
        self.collection = None

        try:
            logger.info(f"Initializing RAGManager with embedding_model_name='{embedding_model_name}', vector_db_path='{vector_db_path}', collection_name='{collection_name}'")
            
            # Initialize SentenceTransformerEmbeddingFunction
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=embedding_model_name
                )
                logger.info(f"Embedding function with model '{embedding_model_name}' loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load embedding model '{embedding_model_name}': {e}", exc_info=True)
                raise  # Re-raise to indicate initialization failure

            # Initialize ChromaDB Persistent Client
            try:
                self.client = chromadb.PersistentClient(path=vector_db_path)
                logger.info(f"ChromaDB client created successfully (path: {vector_db_path}).")
            except Exception as e:
                logger.error(f"Failed to create ChromaDB client at path '{vector_db_path}': {e}", exc_info=True)
                raise

            # Get or create ChromaDB collection
            try:
                self.collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function # Pass the function object itself
                )
                logger.info(f"ChromaDB collection '{collection_name}' retrieved or created successfully.")
            except Exception as e:
                logger.error(f"Failed to get or create ChromaDB collection '{collection_name}': {e}", exc_info=True)
                raise
            
            logger.info("RAGManager initialized successfully.")

        except Exception as e:
            logger.critical(f"RAGManager initialization failed: {e}", exc_info=True)
            # Depending on desired behavior, you might re-raise the exception
            # or ensure the RAGManager is in a state that indicates failure.
            # For now, the individual components might be None if an error occurred.

    def add_documents_to_collection(self, text_chunks: list[str], document_ids: list[str], document_metadatas: list[dict], force_reindex: bool = False):
        if not self.client:
            logger.error("Cannot add documents or reindex: ChromaDB client is not initialized.")
            return

        # Determine the collection name. This is crucial for re-indexing.
        # A more robust class design would store the original collection_name from __init__ as an instance variable.
        collection_name_to_use = ""
        if self.collection:
            collection_name_to_use = self.collection.name
        elif force_reindex:
            # If self.collection is None AND force_reindex is True, we have a problem:
            # we need a name to recreate the collection, but it's not stored if self.collection is None.
            # This implies __init__ might have failed or the collection was already lost.
            logger.error("Cannot force reindex: self.collection is None, so the collection name for re-creation cannot be determined.")
            return
        
        # If not forcing reindex, and self.collection is None, we cannot proceed.
        if not force_reindex and not self.collection:
            logger.error("Cannot add documents: Collection is not initialized and not forcing reindex.")
            return

        try:
            if force_reindex:
                if not collection_name_to_use: # Should be caught by the check above if self.collection was None.
                    logger.error("Critical error during reindex: Collection name is unknown.")
                    return

                logger.info(f"Force reindex is True. Clearing collection '{collection_name_to_use}' before adding documents.")
                try:
                    self.client.delete_collection(name=collection_name_to_use)
                    logger.info(f"Successfully deleted collection '{collection_name_to_use}'.")
                except Exception as e:
                    # Log error but proceed to recreate, as get_or_create_collection handles "not found" implicitly if deletion failed,
                    # or creates anew if it was truly gone.
                    logger.warning(f"Error or issue during deletion of collection '{collection_name_to_use}': {e}. Will attempt to get/create it.", exc_info=True)
                
                try:
                    # Recreate the collection
                    self.collection = self.client.get_or_create_collection(
                        name=collection_name_to_use, 
                        embedding_function=self.embedding_function
                        # metadata={"hnsw:space": "cosine"} can be added if it was part of the original spec,
                        # but current __init__ doesn't specify it for get_or_create_collection.
                    )
                    logger.info(f"Successfully got or recreated collection '{collection_name_to_use}'.")
                except Exception as e:
                    logger.error(f"Fatal error: Failed to get or create collection '{collection_name_to_use}' during reindex: {e}", exc_info=True)
                    self.collection = None # Ensure collection is None if recreation fails
                    return # Cannot proceed if recreation fails

            # After potential re-indexing, self.collection should be valid if reindex was successful.
            # If not force_reindex, self.collection must have been valid from the start.
            if not self.collection:
                logger.error("Cannot add documents: Collection is not available (possibly due to failed initialization or re-initialization).")
                return

            # Document addition logic:
            if text_chunks:
                # If force_reindex is True, collection is now fresh/cleared, so add.
                # If force_reindex is False, only add if collection is empty.
                if force_reindex or self.collection.count() == 0:
                    logger.info(f"Adding {len(text_chunks)} text chunks to collection '{self.collection.name}'...")
                    self.collection.add(
                        documents=text_chunks,
                        ids=document_ids,
                        metadatas=document_metadatas
                    )
                    logger.info(f"Successfully added {len(text_chunks)} documents to collection '{self.collection.name}'. Current count: {self.collection.count()}")
                else: # Not force_reindex and collection is not empty
                    logger.info(f"Collection '{self.collection.name}' already contains {self.collection.count()} documents and force_reindex is False. Skipping addition.")
            else:
                logger.info("No text chunks provided to add to the collection.")

        except Exception as e:
            # Use the determined name for logging if self.collection might have become None
            log_coll_name = self.collection.name if self.collection else collection_name_to_use if collection_name_to_use else "N/A"
            logger.error(f"Error during document addition process for collection '{log_coll_name}': {e}", exc_info=True)

    def search(self, query_text: str, n_results: int = 3, search_filters: dict = None) -> list[str]: # Signature updated
        if not self.collection:
            logger.error("Cannot search: Collection is not initialized.")
            return []
        
        log_message = f"Searching collection '{self.collection.name}' for query: '{query_text}' with n_results={n_results}"
        if search_filters:
            log_message += f" and filters: {search_filters}"
        logger.debug(log_message)

        query_params = {
            'query_texts': [query_text],
            'n_results': n_results,
            'include': ['documents', 'metadatas'] # Include metadatas
        }

        if search_filters: # Add 'where' clause if search_filters are provided
            query_params['where'] = search_filters
            
        try:
            results = self.collection.query(**query_params) # Use ** to pass parameters
            
            formatted_results = []
            if results and results.get('documents') and results.get('metadatas') and \
               results['documents'][0] and results['metadatas'][0]:
                
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                if len(docs) != len(metas):
                    logger.warning("Mismatch between number of documents and metadatas returned. Processing based on shorter list.")
                
                for i in range(min(len(docs), len(metas))):
                    doc_text = docs[i]
                    meta = metas[i] if metas[i] else {} # Ensure meta is a dict
                    source = meta.get('_metadata', {}).get('source', 'Unknown') # Accessing nested _metadata
                    formatted_string = f"Source: {source} | Content: {doc_text}"
                    formatted_results.append(formatted_string)
                
                logger.info(f"Found and formatted {len(formatted_results)} relevant documents for query '{query_text}' (filters applied: {bool(search_filters)}).")
                return formatted_results
            else:
                logger.info(f"No documents or metadatas found for query '{query_text}' (filters applied: {bool(search_filters)}).")
                return []
        except Exception as e:
            logger.error(f"Error searching collection '{self.collection.name}' for query '{query_text}' with filters {search_filters}: {e}", exc_info=True)
            return []
