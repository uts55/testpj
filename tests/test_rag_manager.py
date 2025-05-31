import unittest
from unittest.mock import patch, MagicMock, call
import os
import shutil
import tempfile
import json # For handling JSON strings in metadata if needed

# Functions and classes to test from rag_manager
from rag_manager import get_text_from_doc, initialize_vector_db, query_vector_db, RAG_LIBRARIES_AVAILABLE

# Sample data for testing (similar to what data_loader would produce)
sample_npc_doc = {
    "id": "npc1", "name": "Old Man Willow", "description": "A wise hermit.",
    "dialogue_responses": {
        "greeting": {"npc_text": "Hello there, traveler."},
        "farewell": {"npc_text": "Safe travels."}
    }
}
sample_item_doc = {"id": "item1", "name": "Sunstone", "description": "A glowing gem."}
sample_lore_doc = {"id": "lore1", "text_content": "Long ago, two suns...", "source_category": "Lore"}
sample_location_doc = {"id": "loc1", "name": "Whispering Woods", "description": "An ancient forest."}

sample_all_raw_data = {
    "NPCs": [sample_npc_doc],
    "Items": [sample_item_doc],
    "Lore": [sample_lore_doc],
    "Regions": [sample_location_doc] # Using 'Regions' as per GameState expectation
}

# Configuration (can be overridden in tests)
TEST_TEXT_FIELDS = ['name', 'description', 'text_content', 'dialogue_responses']
TEST_EMBEDDING_MODEL = 'all-MiniLM-L6-v2' # Dummy, won't be loaded if mocked
TEST_COLLECTION_NAME = "test_dnd_content"


@unittest.skipIf(not RAG_LIBRARIES_AVAILABLE, "RAG libraries (sentence-transformers, chromadb) not available, skipping RAG tests.")
class TestRagManager(unittest.TestCase):
    """Test cases for RAG manager functions."""

    def setUp(self):
        """Set up a temporary directory for ChromaDB if needed for some integration-like tests."""
        self.test_db_path = tempfile.mkdtemp(prefix="test_chroma_")
        # self.addCleanup(shutil.rmtree, self.test_db_path) # For Python 3.8+

    def tearDown(self):
        """Clean up the temporary directory."""
        shutil.rmtree(self.test_db_path)

    def test_get_text_from_doc(self):
        """Test extraction of text from various document structures."""
        # Test with NPC doc (includes special dialogue handling)
        npc_text = get_text_from_doc(sample_npc_doc, TEST_TEXT_FIELDS)
        self.assertIn("Old Man Willow", npc_text)
        self.assertIn("wise hermit", npc_text)
        self.assertIn("Hello there, traveler.", npc_text)
        self.assertIn("Safe travels.", npc_text)

        # Test with Item doc
        item_text = get_text_from_doc(sample_item_doc, TEST_TEXT_FIELDS)
        self.assertIn("Sunstone", item_text)
        self.assertIn("glowing gem", item_text)

        # Test with Lore doc (uses 'text_content')
        lore_text = get_text_from_doc(sample_lore_doc, TEST_TEXT_FIELDS)
        self.assertIn("Long ago, two suns...", lore_text)

        # Test with Location doc
        location_text = get_text_from_doc(sample_location_doc, TEST_TEXT_FIELDS)
        self.assertIn("Whispering Woods", location_text)
        self.assertIn("ancient forest", location_text)

        # Test with missing fields
        minimal_doc = {"name": "Minimal"}
        minimal_text = get_text_from_doc(minimal_doc, TEST_TEXT_FIELDS)
        self.assertEqual(minimal_text, "Minimal")

        # Test with empty doc
        empty_text = get_text_from_doc({}, TEST_TEXT_FIELDS)
        self.assertEqual(empty_text, "")

        # Test with non-dict doc
        non_dict_text = get_text_from_doc("just a string", TEST_TEXT_FIELDS)
        self.assertEqual(non_dict_text, "")


    @patch('rag_manager.chromadb')
    @patch('rag_manager.SentenceTransformer')
    def test_initialize_vector_db(self, MockSentenceTransformer, MockChromaDB):
        """Test the initialization of the vector DB, mocking external libraries."""
        # Setup mocks
        mock_model_instance = MockSentenceTransformer.return_value
        mock_model_instance.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3] # Dummy embedding

        mock_client_instance = MockChromaDB.PersistentClient.return_value
        mock_collection_instance = mock_client_instance.get_or_create_collection.return_value

        success = initialize_vector_db(
            sample_all_raw_data, TEST_TEXT_FIELDS, TEST_EMBEDDING_MODEL,
            self.test_db_path, TEST_COLLECTION_NAME
        )
        self.assertTrue(success)
        MockSentenceTransformer.assert_called_once_with(TEST_EMBEDDING_MODEL)
        MockChromaDB.PersistentClient.assert_called_once_with(path=self.test_db_path)
        mock_client_instance.get_or_create_collection.assert_called_once_with(name=TEST_COLLECTION_NAME)

        # Verify collection.add was called with expected data structure
        # There are 4 docs in sample_all_raw_data
        self.assertEqual(mock_model_instance.encode.call_count, 4)

        # Check the actual calls to collection.add
        # Since we batch, there should be one call for this small dataset
        add_calls = mock_collection_instance.add.call_args_list
        self.assertEqual(len(add_calls), 1) # One batch call

        args, _kwargs = add_calls[0]

        # Check ids
        expected_ids = [
            "NPCs_npc1", "Items_item1", "Lore_lore1", "Regions_loc1"
        ]
        self.assertListEqual(sorted(args[0]['ids']), sorted(expected_ids)) # ids are in kwargs for .add

        # Check embeddings (all are the same mocked embedding)
        self.assertEqual(len(args[0]['embeddings']), 4)
        self.assertEqual(args[0]['embeddings'][0], [0.1, 0.2, 0.3])

        # Check metadatas (structure and content for one item)
        self.assertEqual(len(args[0]['metadatas']), 4)
        npc_metadata = next(m for m in args[0]['metadatas'] if m['id'] == 'npc1')
        self.assertEqual(npc_metadata['category'], 'NPCs')
        self.assertEqual(npc_metadata['name'], 'Old Man Willow')

        # Check documents (the text that was embedded)
        self.assertEqual(len(args[0]['documents']), 4)
        npc_doc_text = next(d for i, d in enumerate(args[0]['documents']) if args[0]['ids'][i] == "NPCs_npc1")
        self.assertIn("Old Man Willow", npc_doc_text)


    @patch('rag_manager.chromadb')
    @patch('rag_manager.SentenceTransformer')
    def test_query_vector_db(self, MockSentenceTransformer, MockChromaDB):
        """Test querying the vector DB, mocking external libraries."""
        # Setup mocks
        mock_model_instance = MockSentenceTransformer.return_value
        mock_model_instance.encode.return_value.tolist.return_value = [0.4, 0.5, 0.6] # Dummy query embedding

        mock_client_instance = MockChromaDB.PersistentClient.return_value
        mock_collection_instance = mock_client_instance.get_collection.return_value

        # Mock query results from ChromaDB
        mock_query_results = {
            "ids": [["NPCs_npc1", "Items_item1"]],
            "documents": [["Text for NPC1", "Text for Item1"]],
            "metadatas": [[
                {"category": "NPCs", "id": "npc1", "name": "Old Man Willow"},
                {"category": "Items", "id": "item1", "name": "Sunstone"}
            ]],
            "distances": [[0.123, 0.456]]
        }
        mock_collection_instance.query.return_value = mock_query_results

        query_text = "tell me about willows"
        results = query_vector_db(
            query_text, self.test_db_path, TEST_COLLECTION_NAME,
            TEST_EMBEDDING_MODEL, n_results=2
        )

        self.assertEqual(len(results), 2)
        MockSentenceTransformer.assert_called_once_with(TEST_EMBEDDING_MODEL)
        mock_model_instance.encode.assert_called_once_with(query_text)
        MockChromaDB.PersistentClient.assert_called_once_with(path=self.test_db_path)
        mock_client_instance.get_collection.assert_called_once_with(name=TEST_COLLECTION_NAME)

        mock_collection_instance.query.assert_called_once()
        query_args = mock_collection_instance.query.call_args[1] # kwargs
        self.assertEqual(query_args['query_embeddings'], [[0.4,0.5,0.6]])
        self.assertEqual(query_args['n_results'], 2)

        self.assertEqual(results[0]['retrieved_id'], "NPCs_npc1")
        self.assertEqual(results[0]['metadata']['name'], "Old Man Willow")
        self.assertEqual(results[0]['document_text'], "Text for NPC1")
        self.assertAlmostEqual(results[0]['distance'], 0.123)


    @patch('rag_manager.chromadb')
    @patch('rag_manager.SentenceTransformer')
    def test_initialize_vector_db_no_data(self, MockSentenceTransformer, MockChromaDB):
        """Test initialization with no raw data."""
        mock_client_instance = MockChromaDB.PersistentClient.return_value
        mock_collection_instance = mock_client_instance.get_or_create_collection.return_value

        success = initialize_vector_db(
            {}, TEST_TEXT_FIELDS, TEST_EMBEDDING_MODEL,
            self.test_db_path, TEST_COLLECTION_NAME
        )
        self.assertTrue(success) # Should succeed, but add no documents
        mock_collection_instance.add.assert_not_called()

    @patch('rag_manager.chromadb')
    @patch('rag_manager.SentenceTransformer')
    def test_query_vector_db_empty_results(self, MockSentenceTransformer, MockChromaDB):
        """Test query that returns empty results from ChromaDB."""
        mock_model_instance = MockSentenceTransformer.return_value
        mock_model_instance.encode.return_value.tolist.return_value = [0.7, 0.8, 0.9]

        mock_client_instance = MockChromaDB.PersistentClient.return_value
        mock_collection_instance = mock_client_instance.get_collection.return_value
        mock_collection_instance.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]} # Empty results

        results = query_vector_db("unknown query", self.test_db_path, TEST_COLLECTION_NAME, TEST_EMBEDDING_MODEL)
        self.assertEqual(len(results), 0)

    # Integration-like test (optional, can be slow, requires actual libraries)
    # This test would only run if RAG_LIBRARIES_AVAILABLE is True and mocks are removed.
    # For CI/automated testing, it's often better to keep this separate or disabled by default.
    @unittest.skipUnless(RAG_LIBRARIES_AVAILABLE, "Skipping RAG integration test as libraries are not available.")
    def test_rag_pipeline_integration_light(self):
        """A light integration test for the RAG pipeline if libraries are available."""
        # 1. Initialize a real ChromaDB instance in the temp path
        init_success = initialize_vector_db(
            sample_all_raw_data, TEST_TEXT_FIELDS, TEST_EMBEDDING_MODEL,
            self.test_db_path, TEST_COLLECTION_NAME
        )
        self.assertTrue(init_success, "Light integration: DB initialization failed.")

        # 2. Query it
        results = query_vector_db(
            "wise hermit", self.test_db_path, TEST_COLLECTION_NAME,
            TEST_EMBEDDING_MODEL, n_results=1
        )
        self.assertTrue(len(results) >= 1, "Light integration: Query returned no results.")
        if results:
            # Check if the most relevant result is the Old Man Willow NPC
            self.assertEqual(results[0]['metadata']['id'], "npc1")
            self.assertEqual(results[0]['metadata']['category'], "NPCs")
            self.assertIn("Old Man Willow", results[0]['document_text'])


if __name__ == '__main__':
    # Configure logging for test output (optional)
    # import logging
    # logging.basicConfig(level=logging.INFO)
    unittest.main()
