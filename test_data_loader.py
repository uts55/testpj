import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import shutil
import logging

# Assuming data_loader.py and config.py are in the same directory or accessible in PYTHONPATH
from data_loader import split_text_into_chunks, load_documents, extract_text_for_rag
from config import CHUNK_SIZE, CHUNK_OVERLAP # For default chunking params

# Suppress logging during tests for cleaner output, can be enabled for debugging
logging.disable(logging.CRITICAL)

class TestSplitTextIntoChunks(unittest.TestCase):
    def test_uses_recursive_character_splitter(self):
        mock_text = "This is a test sentence for splitting."
        with patch('data_loader.RecursiveCharacterTextSplitter') as mock_splitter_class:
            mock_splitter_instance = MagicMock()
            mock_splitter_instance.split_text.return_value = ["chunk1", "chunk2"]
            mock_splitter_class.return_value = mock_splitter_instance

            split_text_into_chunks(mock_text, chunk_size=10, chunk_overlap=2)

            mock_splitter_class.assert_called_once_with(
                chunk_size=10,
                chunk_overlap=2,
                length_function=len,
                is_separator_regex=False
            )
            mock_splitter_instance.split_text.assert_called_once_with(mock_text)

    def test_basic_splitting_with_defaults(self):
        # Uses default CHUNK_SIZE and CHUNK_OVERLAP from config
        text = "a" * (CHUNK_SIZE + CHUNK_SIZE // 2) # Make text long enough for multiple chunks
        chunks = split_text_into_chunks(text)
        self.assertTrue(len(chunks) > 1)
        self.assertTrue(all(len(chunk) <= CHUNK_SIZE for chunk in chunks))

    def test_custom_chunk_size_overlap(self):
        text = "This is a longer test sentence. It should be split into multiple chunks based on custom settings."
        custom_size = 20
        custom_overlap = 5
        chunks = split_text_into_chunks(text, chunk_size=custom_size, chunk_overlap=custom_overlap)
        self.assertTrue(all(len(chunk) <= custom_size for chunk in chunks))
        if len(chunks) > 1:
            # Check overlap: end of first chunk should overlap with start of second
            self.assertEqual(chunks[0][custom_size-custom_overlap:], chunks[1][:custom_overlap])

    def test_text_shorter_than_chunk_size(self):
        text = "Short text."
        chunks = split_text_into_chunks(text, chunk_size=100, chunk_overlap=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_empty_text(self):
        text = ""
        chunks = split_text_into_chunks(text, chunk_size=100, chunk_overlap=10)
        # RecursiveCharacterTextSplitter might return an empty list or a list with an empty string
        # depending on its internal logic for empty inputs. Let's assume it returns an empty list.
        self.assertEqual(len(chunks), 0)


    def test_overlap_greater_than_or_equal_to_size(self):
        text = "Some text"
        with self.assertRaises(ValueError):
            split_text_into_chunks(text, chunk_size=10, chunk_overlap=10)
        with self.assertRaises(ValueError):
            split_text_into_chunks(text, chunk_size=10, chunk_overlap=11)


class TestLoadDocuments(unittest.TestCase):
    TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "tests", "test_data")
    SAMPLE_JSON_PATH = os.path.join(TEST_DATA_DIR, "sample.json")
    SAMPLE_TXT_PATH = os.path.join(TEST_DATA_DIR, "sample.txt")
    MIXED_DIR_PATH = os.path.join(TEST_DATA_DIR, "mixed_dir")
    JSON_LIST_PATH = os.path.join(TEST_DATA_DIR, "sample_list.json")
    INVALID_JSON_PATH = os.path.join(TEST_DATA_DIR, "invalid.json")


    @classmethod
    def setUpClass(cls):
        # Create test files and directories (these were created by previous tool calls)
        # For robustness in a standalone test, we'd ensure creation here.
        # Since they are pre-created, we just ensure the paths are correct.
        if not os.path.exists(cls.TEST_DATA_DIR):
            os.makedirs(cls.TEST_DATA_DIR)
        if not os.path.exists(cls.MIXED_DIR_PATH):
             os.makedirs(cls.MIXED_DIR_PATH)
        
        # Sample JSON List file
        with open(cls.JSON_LIST_PATH, 'w') as f:
            json.dump([{"id": 1, "content": "item1"}, {"id": 2, "content": "item2"}], f)
        # Sample Invalid JSON
        with open(cls.INVALID_JSON_PATH, 'w') as f:
            f.write("{'name': 'test', 'value': 1") # Intentionally invalid

    @classmethod
    def tearDownClass(cls):
        # Clean up created test files and directories
        if os.path.exists(cls.JSON_LIST_PATH):
            os.remove(cls.JSON_LIST_PATH)
        if os.path.exists(cls.INVALID_JSON_PATH):
            os.remove(cls.INVALID_JSON_PATH)
        # The other files (sample.json, sample.txt, mixed_dir contents)
        # were created by the tool, ideally they should be cleaned up too.
        # For now, let's assume the test runner environment handles overall cleanup or they are gitignored.
        # If tests/test_data was solely for this TestLoadDocuments, we could do:
        # if os.path.exists(cls.TEST_DATA_DIR):
        #     shutil.rmtree(cls.TEST_DATA_DIR)

    def test_load_single_json_file(self):
        documents = load_documents([self.SAMPLE_JSON_PATH])
        self.assertEqual(len(documents), 1)
        doc = documents[0]
        self.assertEqual(doc['name'], "Test Object")
        self.assertIn("_metadata", doc)
        self.assertEqual(doc["_metadata"]["source"], self.SAMPLE_JSON_PATH)
        self.assertEqual(doc["_metadata"]["document_type"], "json")

    def test_load_single_txt_file(self):
        documents = load_documents([self.SAMPLE_TXT_PATH])
        self.assertEqual(len(documents), 1)
        doc = documents[0]
        with open(self.SAMPLE_TXT_PATH, 'r') as f:
            expected_content = f.read()
        self.assertEqual(doc['text_content'], expected_content)
        self.assertIn("_metadata", doc)
        self.assertEqual(doc["_metadata"]["source"], self.SAMPLE_TXT_PATH)
        self.assertEqual(doc["_metadata"]["document_type"], "txt")

    @patch('logging.Logger.error')
    def test_load_non_existent_file(self, mock_log_error):
        documents = load_documents(["non_existent_file.json"])
        self.assertEqual(len(documents), 0)
        mock_log_error.assert_called_with("File not found - non_existent_file.json")

    def test_load_from_directory(self):
        documents = load_documents([self.MIXED_DIR_PATH])
        # Expecting 2 files: sample_in_dir.json, sample_in_dir.txt
        self.assertEqual(len(documents), 2)
        
        json_doc_found = False
        txt_doc_found = False
        
        for doc in documents:
            self.assertIn("_metadata", doc)
            source = doc["_metadata"]["source"]
            doc_type = doc["_metadata"]["document_type"]

            if source.endswith("sample_in_dir.json"):
                self.assertEqual(doc_type, "json")
                self.assertEqual(doc["item_name"], "Directory Item")
                json_doc_found = True
            elif source.endswith("sample_in_dir.txt"):
                self.assertEqual(doc_type, "txt")
                self.assertTrue("Sample text from a file in a directory." in doc["text_content"])
                txt_doc_found = True
            else:
                self.fail(f"Unexpected document loaded: {source}")
        
        self.assertTrue(json_doc_found, "JSON file from directory not loaded.")
        self.assertTrue(txt_doc_found, "TXT file from directory not loaded.")

    def test_load_json_list(self):
        documents = load_documents([self.JSON_LIST_PATH])
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0]['content'], "item1")
        self.assertEqual(documents[1]['content'], "item2")
        for doc in documents:
            self.assertIn("_metadata", doc)
            self.assertEqual(doc["_metadata"]["source"], self.JSON_LIST_PATH)
            self.assertEqual(doc["_metadata"]["document_type"], "json")
    
    @patch('logging.Logger.error')
    def test_load_invalid_json(self, mock_log_error):
        documents = load_documents([self.INVALID_JSON_PATH])
        self.assertEqual(len(documents),0)
        mock_log_error.assert_any_call(f"Invalid JSON format in - {self.INVALID_JSON_PATH}")


class TestExtractTextForRAG(unittest.TestCase):
    def test_extract_from_json_fields(self):
        doc = {
            "name": "My Awesome Game Object",
            "description": "A detailed description of the object.",
            "lore_fragments": ["Ancient tale 1.", "Forgotten legend 2."],
            "dialogue_responses": {
                "artifact_info": "This artifact is very old."
            },
            "_metadata": {"source": "test.json", "document_type": "json"}
        }
        # Typical RAG_TEXT_FIELDS from config.py for JSONs
        text_fields = ['name', 'description', 'lore_fragments', 'dialogue_responses.artifact_info']
        extracted_text = extract_text_for_rag(doc, text_fields)
        
        self.assertIn("My Awesome Game Object", extracted_text)
        self.assertIn("A detailed description of the object.", extracted_text)
        self.assertIn("Ancient tale 1.", extracted_text)
        self.assertIn("Forgotten legend 2.", extracted_text)
        self.assertIn("This artifact is very old.", extracted_text)

    def test_extract_from_txt_content(self):
        doc = {
            "text_content": "This is the full content of a text file.",
            "_metadata": {"source": "test.txt", "document_type": "txt"}
        }
        # For .txt files, we'd typically pass 'text_content' as a field
        text_fields = ['text_content']
        extracted_text = extract_text_for_rag(doc, text_fields)
        self.assertEqual(extracted_text, "This is the full content of a text file.")

    def test_extract_from_nested_fields(self):
        doc = {
            "game_item": {
                "name": "Sword of Testing",
                "stats": {
                    "damage": "1d8",
                    "properties": ["sharp", "pointy"]
                },
                "history": "Forged by ancient testers."
            },
             "_metadata": {"source": "test_nested.json", "document_type": "json"}
        }
        text_fields = ["game_item.name", "game_item.stats.properties", "game_item.history"]
        extracted_text = extract_text_for_rag(doc, text_fields)
        self.assertIn("Sword of Testing", extracted_text)
        self.assertIn("sharp", extracted_text)
        self.assertIn("pointy", extracted_text)
        self.assertIn("Forged by ancient testers.", extracted_text)

    def test_extract_with_missing_fields(self):
        doc = {
            "name": "Partial Object",
            # description is missing
            "_metadata": {"source": "partial.json", "document_type": "json"}
        }
        text_fields = ['name', 'description'] # 'description' is missing in doc
        extracted_text = extract_text_for_rag(doc, text_fields)
        self.assertEqual(extracted_text, "Partial Object") # Only name should be extracted

    def test_extract_from_empty_document(self):
        doc = {
             "_metadata": {"source": "empty.json", "document_type": "json"}
        }
        text_fields = ['name', 'description']
        extracted_text = extract_text_for_rag(doc, text_fields)
        self.assertEqual(extracted_text, "")

    def test_extract_all_rag_text_fields(self):
        # This test uses the actual RAG_TEXT_FIELDS from config.py (which should include 'text_content')
        from config import RAG_TEXT_FIELDS
        doc = {
            "name": "Comprehensive Item",
            "description": "Full desc.",
            "lore_fragments": ["Lore A", "Lore B"],
            "dialogue_responses": {"artifact_info": "Artifact details."},
            "knowledge_fragments": ["Knowledge 1"],
            "text_content": "Text file content here.", # Simulating a loaded .txt file's structure
            "_metadata": {"source": "all_fields.json", "document_type": "json"} # Type might be txt if text_content is primary
        }
        extracted_text = extract_text_for_rag(doc, RAG_TEXT_FIELDS)
        self.assertIn("Comprehensive Item", extracted_text)
        self.assertIn("Full desc.", extracted_text)
        self.assertIn("Lore A", extracted_text)
        self.assertIn("Artifact details.", extracted_text)
        self.assertIn("Knowledge 1", extracted_text)
        self.assertIn("Text file content here.", extracted_text)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Re-enable logging if it was disabled for tests
logging.disable(logging.NOTSET)
