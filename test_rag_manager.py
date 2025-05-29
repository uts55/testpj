import unittest
from unittest.mock import patch, MagicMock, ANY
import logging

# Assuming rag_manager.py is in the same directory or accessible in PYTHONPATH
from rag_manager import RAGManager 

# Suppress logging during tests for cleaner output, can be enabled for debugging
# logging.disable(logging.CRITICAL) # Keep this commented out for now to see logs during test dev

class TestRAGManagerInitialization(unittest.TestCase):

    @patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction')
    @patch('rag_manager.chromadb.PersistentClient')
    @patch('logging.Logger.info') # Patch the logger
    @patch('logging.Logger.error')
    @patch('logging.Logger.critical')
    def test_successful_initialization(self, mock_log_critical, mock_log_error, mock_log_info, MockPersistentClient, MockEmbeddingFunction):
        mock_embed_instance = MockEmbeddingFunction.return_value
        mock_client_instance = MockPersistentClient.return_value
        mock_collection_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection_instance

        rag_manager = RAGManager(embedding_model_name="test-model", vector_db_path="/test/db", collection_name="test_collection")

        MockEmbeddingFunction.assert_called_once_with(model_name="test-model")
        MockPersistentClient.assert_called_once_with(path="/test/db")
        mock_client_instance.get_or_create_collection.assert_called_once_with(
            name="test_collection",
            embedding_function=mock_embed_instance
        )
        self.assertEqual(rag_manager.embedding_function, mock_embed_instance)
        self.assertEqual(rag_manager.client, mock_client_instance)
        self.assertEqual(rag_manager.collection, mock_collection_instance)
        
        mock_log_info.assert_any_call("RAGManager initialized successfully.")
        mock_log_error.assert_not_called()
        mock_log_critical.assert_not_called()

    @patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction', side_effect=Exception("Embedding Error"))
    @patch('logging.Logger.error')
    @patch('logging.Logger.critical')
    def test_initialization_embedding_error(self, mock_log_critical, mock_log_error, MockEmbeddingFunction):
        with self.assertRaises(Exception): # Expecting the original error to be re-raised
             RAGManager(embedding_model_name="test-model", vector_db_path="/test/db", collection_name="test_collection")
        
        mock_log_error.assert_any_call("Failed to load embedding model 'test-model': Embedding Error", exc_info=True)
        mock_log_critical.assert_any_call("RAGManager initialization failed: Embedding Error", exc_info=True)

    @patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction')
    @patch('rag_manager.chromadb.PersistentClient', side_effect=Exception("Client Error"))
    @patch('logging.Logger.error')
    @patch('logging.Logger.critical')
    def test_initialization_client_error(self, mock_log_critical, mock_log_error, MockPersistentClient, MockEmbeddingFunction):
        with self.assertRaises(Exception):
            RAGManager(embedding_model_name="test-model", vector_db_path="/test/db", collection_name="test_collection")

        mock_log_error.assert_any_call("Failed to create ChromaDB client at path '/test/db': Client Error", exc_info=True)
        mock_log_critical.assert_any_call("RAGManager initialization failed: Client Error", exc_info=True)

    @patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction')
    @patch('rag_manager.chromadb.PersistentClient')
    @patch('logging.Logger.error')
    @patch('logging.Logger.critical')
    def test_initialization_collection_error(self, mock_log_critical, mock_log_error, MockPersistentClient, MockEmbeddingFunction):
        mock_client_instance = MockPersistentClient.return_value
        mock_client_instance.get_or_create_collection.side_effect = Exception("Collection Error")

        with self.assertRaises(Exception):
            RAGManager(embedding_model_name="test-model", vector_db_path="/test/db", collection_name="test_collection")
        
        mock_log_error.assert_any_call("Failed to get or create ChromaDB collection 'test_collection': Collection Error", exc_info=True)
        mock_log_critical.assert_any_call("RAGManager initialization failed: Collection Error", exc_info=True)


class TestRAGManagerAddDocuments(unittest.TestCase):
    def setUp(self):
        self.mock_embedding_function = MagicMock()
        self.mock_client = MagicMock(spec= ['get_or_create_collection', 'delete_collection'])
        self.mock_collection = MagicMock(spec=['add', 'count', 'name', 'query'])
        self.mock_collection.name = "test_collection"

        # Patch the real constructors within the RAGManager's scope for its initialization
        with patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction', return_value=self.mock_embedding_function):
            with patch('rag_manager.chromadb.PersistentClient', return_value=self.mock_client):
                self.mock_client.get_or_create_collection.return_value = self.mock_collection
                self.rag_manager = RAGManager("test-model", "/fake/path", "test_collection")
        
        # Reset mocks that might be called during init for cleaner test assertions
        self.mock_client.reset_mock()
        self.mock_collection.reset_mock()
        self.mock_client.get_or_create_collection.return_value = self.mock_collection # Re-assign after reset

    @patch('logging.Logger.info')
    def test_add_to_empty_collection(self, mock_log_info):
        self.mock_collection.count.return_value = 0
        chunks = ["chunk1", "chunk2"]
        ids = ["id1", "id2"]
        metadatas = [{"meta": "data1"}, {"meta": "data2"}]

        self.rag_manager.add_documents_to_collection(chunks, ids, metadatas)

        self.mock_collection.add.assert_called_once_with(documents=chunks, ids=ids, metadatas=metadatas)
        mock_log_info.assert_any_call(f"Adding {len(chunks)} text chunks to collection '{self.mock_collection.name}'...")
        mock_log_info.assert_any_call(f"Successfully added {len(chunks)} documents to collection '{self.mock_collection.name}'. Current count: {self.mock_collection.count()}")

    @patch('logging.Logger.info')
    @patch('logging.Logger.warning')
    def test_add_with_force_reindex(self, mock_log_warning, mock_log_info):
        self.mock_collection.count.return_value = 5 # Existing documents
        
        new_mock_collection = MagicMock(spec=['add', 'count', 'name'])
        new_mock_collection.name = "test_collection"
        self.mock_client.get_or_create_collection.return_value = new_mock_collection # This will be the "recreated" collection

        chunks = ["new_chunk1"]
        ids = ["new_id1"]
        metadatas = [{"new_meta": "data_new"}]

        self.rag_manager.add_documents_to_collection(chunks, ids, metadatas, force_reindex=True)

        self.mock_client.delete_collection.assert_called_once_with(name="test_collection")
        self.mock_client.get_or_create_collection.assert_called_with(name="test_collection", embedding_function=self.mock_embedding_function)
        
        self.assertEqual(self.rag_manager.collection, new_mock_collection) # Ensure collection is updated
        new_mock_collection.add.assert_called_once_with(documents=chunks, ids=ids, metadatas=metadatas)
        
        mock_log_info.assert_any_call(f"Force reindex is True. Clearing collection 'test_collection' before adding documents.")
        mock_log_info.assert_any_call(f"Successfully deleted collection 'test_collection'.") # Assuming successful deletion
        mock_log_info.assert_any_call(f"Successfully got or recreated collection 'test_collection'.")
        mock_log_info.assert_any_call(f"Adding {len(chunks)} text chunks to collection '{new_mock_collection.name}'...")

    @patch('logging.Logger.info')
    def test_add_to_non_empty_collection_no_reindex(self, mock_log_info):
        self.mock_collection.count.return_value = 5
        chunks = ["chunk1"]
        ids = ["id1"]
        metadatas = [{"meta": "data1"}]

        self.rag_manager.add_documents_to_collection(chunks, ids, metadatas, force_reindex=False)

        self.mock_collection.add.assert_not_called()
        mock_log_info.assert_any_call(f"Collection '{self.mock_collection.name}' already contains 5 documents and force_reindex is False. Skipping addition.")

    @patch('logging.Logger.info')
    def test_add_empty_chunks(self, mock_log_info):
        self.rag_manager.add_documents_to_collection([], [], [])
        self.mock_collection.add.assert_not_called()
        mock_log_info.assert_any_call("No text chunks provided to add to the collection.")

    @patch('logging.Logger.error')
    def test_add_documents_client_not_initialized(self, mock_log_error):
        self.rag_manager.client = None
        self.rag_manager.add_documents_to_collection(["chunk"], ["id"], [{}])
        mock_log_error.assert_called_once_with("Cannot add documents or reindex: ChromaDB client is not initialized.")

    @patch('logging.Logger.error')
    def test_add_documents_collection_none_no_reindex(self, mock_log_error):
        self.rag_manager.collection = None
        self.rag_manager.add_documents_to_collection(["chunk"], ["id"], [{}], force_reindex=False)
        mock_log_error.assert_called_once_with("Cannot add documents: Collection is not initialized and not forcing reindex.")

    @patch('logging.Logger.error')
    def test_add_documents_collection_none_force_reindex_name_cannot_be_determined(self, mock_log_error):
        self.rag_manager.collection = None # Simulate collection couldn't be initialized
        self.rag_manager.add_documents_to_collection(["c"], ["i"], [{}], force_reindex=True)
        mock_log_error.assert_called_once_with("Cannot force reindex: self.collection is None, so the collection name for re-creation cannot be determined.")


class TestRAGManagerSearch(unittest.TestCase):
    def setUp(self):
        self.mock_embedding_function = MagicMock()
        self.mock_client = MagicMock()
        self.mock_collection = MagicMock(spec=['query', 'name']) # Ensure 'name' is part of spec
        self.mock_collection.name = "test_search_collection"

        with patch('rag_manager.embedding_functions.SentenceTransformerEmbeddingFunction', return_value=self.mock_embedding_function):
            with patch('rag_manager.chromadb.PersistentClient', return_value=self.mock_client):
                self.mock_client.get_or_create_collection.return_value = self.mock_collection
                self.rag_manager = RAGManager("search-model", "/search/db", "test_search_collection")
        self.mock_collection.reset_mock() # Reset after init

    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    def test_search_basic_and_include_param(self, mock_log_debug, mock_log_info):
        query_text = "find this"
        self.mock_collection.query.return_value = {
            'documents': [["doc1 text", "doc2 text"]],
            'metadatas': [[{"_metadata": {"source": "source1"}}, {"_metadata": {"source": "source2"}}]]
        }
        
        results = self.rag_manager.search(query_text, n_results=2)

        self.mock_collection.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=2,
            include=['documents', 'metadatas'] 
            # No 'where' clause if search_filters is None
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "Source: source1 | Content: doc1 text")
        self.assertEqual(results[1], "Source: source2 | Content: doc2 text")
        mock_log_debug.assert_any_call(f"Searching collection '{self.mock_collection.name}' for query: '{query_text}' with n_results=2")
        mock_log_info.assert_any_call(f"Found and formatted {len(results)} relevant documents for query '{query_text}' (filters applied: False).")


    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    def test_search_with_filters(self, mock_log_debug, mock_log_info):
        query_text = "filter this"
        search_filters = {"type": "test"}
        self.mock_collection.query.return_value = {
            'documents': [["filtered doc"]],
            'metadatas': [[{"_metadata": {"source": "filtered_source"}}]]
        }

        results = self.rag_manager.search(query_text, n_results=1, search_filters=search_filters)

        self.mock_collection.query.assert_called_once_with(
            query_texts=[query_text],
            n_results=1,
            include=['documents', 'metadatas'],
            where=search_filters
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Source: filtered_source | Content: filtered doc")
        mock_log_debug.assert_any_call(f"Searching collection '{self.mock_collection.name}' for query: '{query_text}' with n_results=1 and filters: {search_filters}")
        mock_log_info.assert_any_call(f"Found and formatted {len(results)} relevant documents for query '{query_text}' (filters applied: True).")

    @patch('logging.Logger.info')
    def test_search_no_results(self, mock_log_info):
        query_text = "nothing here"
        # Simulate ChromaDB returning empty lists within the main list for no matches
        self.mock_collection.query.return_value = {'documents': [[]], 'metadatas': [[]]} 
        
        results = self.rag_manager.search(query_text)
        
        self.assertEqual(results, [])
        mock_log_info.assert_any_call(f"No documents or metadatas found for query '{query_text}' (filters applied: False).")

    @patch('logging.Logger.error')
    def test_search_collection_not_initialized(self, mock_log_error):
        self.rag_manager.collection = None
        results = self.rag_manager.search("any query")
        self.assertEqual(results, [])
        mock_log_error.assert_called_once_with("Cannot search: Collection is not initialized.")

    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    def test_search_metadata_source_missing(self, mock_log_debug, mock_log_info):
        query_text = "missing source"
        self.mock_collection.query.return_value = {
            'documents': [["doc_no_source"]],
            'metadatas': [[{"_metadata": {}}]] # Source is missing under _metadata
        }
        results = self.rag_manager.search(query_text, n_results=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Source: Unknown | Content: doc_no_source")

    @patch('logging.Logger.info')
    @patch('logging.Logger.debug')
    def test_search_metadata_itself_missing(self, mock_log_debug, mock_log_info):
        query_text = "missing metadata obj"
        # This case is tricky, ChromaDB usually returns parallel lists. If a metadata object is entirely missing for a doc,
        # the structure might be different or it might be an error.
        # Assuming a valid Chroma response where a metadata list might be shorter or an element is None.
        self.mock_collection.query.return_value = {
            'documents': [["doc_no_meta_obj"]],
            'metadatas': [[None]] # Metadata object itself is None
        }
        results = self.rag_manager.search(query_text, n_results=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Source: Unknown | Content: doc_no_meta_obj")


if __name__ == '__main__':
    # It's better to run tests using `python -m unittest test_rag_manager.py`
    # but this allows running the file directly.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Re-enable logging if it was disabled for tests
# logging.disable(logging.NOTSET)
