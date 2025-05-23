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

    def add_documents_to_collection(self, text_chunks: list[str], document_ids: list[str], document_metadatas: list[dict]):
        if not self.collection:
            logger.error("Cannot add documents: Collection is not initialized.")
            return

        try:
            if self.collection.count() == 0 and text_chunks:
                logger.info(f"Collection '{self.collection.name}' is empty. Adding {len(text_chunks)} text chunks...")
                self.collection.add(
                    documents=text_chunks,
                    ids=document_ids,
                    metadatas=document_metadatas
                )
                logger.info(f"Successfully added {len(text_chunks)} documents to collection '{self.collection.name}'. Current count: {self.collection.count()}")
            elif text_chunks: # text_chunks is not empty, but collection is not empty
                logger.info(f"Collection '{self.collection.name}' already contains {self.collection.count()} documents. Skipping addition.")
            else: # text_chunks is empty
                logger.info("No text chunks provided to add to the collection.")
        except Exception as e:
            logger.error(f"Error adding documents to collection '{self.collection.name}': {e}", exc_info=True)

    def search(self, query_text: str, n_results: int = 3) -> list[str]:
        if not self.collection:
            logger.error("Cannot search: Collection is not initialized.")
            return []
        
        logger.debug(f"Searching collection '{self.collection.name}' for query: '{query_text}' with n_results={n_results}")
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=['documents'] # We only need the document content
            )
            
            if results and results.get('documents') and results['documents'][0]:
                retrieved_docs = results['documents'][0]
                logger.info(f"Found {len(retrieved_docs)} relevant documents for query '{query_text}'.")
                return retrieved_docs
            else:
                logger.info(f"No documents found for query '{query_text}'.")
                return []
        except Exception as e:
            logger.error(f"Error searching collection '{self.collection.name}' for query '{query_text}': {e}", exc_info=True)
            return []
