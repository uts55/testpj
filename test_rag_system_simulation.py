import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch
import io

# Assuming rag_system_simulation.py is in the same directory or accessible in PYTHONPATH
from rag_system_simulation import load_documents

class TestLoadDocuments(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Remove the temporary directory after tests
        shutil.rmtree(self.test_dir)

    def _create_temp_json_file(self, data, filename_prefix="test_"):
        """Helper to create a temporary JSON file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=self.test_dir,
            prefix=filename_prefix,
            suffix=".json",
            delete=False  # We will manage deletion ourselves if needed, or let tearDown handle dir
        )
        json.dump(data, temp_file)
        temp_file.close()
        return temp_file.name

    def _create_temp_file(self, content, filename_prefix="test_", suffix=".txt"):
        """Helper to create a temporary non-JSON file."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=self.test_dir,
            prefix=filename_prefix,
            suffix=suffix,
            delete=False
        )
        temp_file.write(content)
        temp_file.close()
        return temp_file.name

    # 1. Test loading a single JSON file
    def test_load_single_json_file(self):
        doc_content = [{"id": "single_file_test", "data": "content1"}]
        file_path = self._create_temp_json_file(doc_content, "single_")
        
        loaded_docs = load_documents([file_path])
        self.assertEqual(len(loaded_docs), 1)
        self.assertEqual(loaded_docs[0], doc_content[0])

    # 2. Test loading multiple specified JSON files
    def test_load_multiple_specified_json_files(self):
        doc1_content = [{"id": "multi_file_test1", "data": "content_mf1"}]
        doc2_content = [{"id": "multi_file_test2", "data": "content_mf2"}]
        file1_path = self._create_temp_json_file(doc1_content, "multi1_")
        file2_path = self._create_temp_json_file(doc2_content, "multi2_")

        loaded_docs = load_documents([file1_path, file2_path])
        self.assertEqual(len(loaded_docs), 2)
        self.assertIn(doc1_content[0], loaded_docs)
        self.assertIn(doc2_content[0], loaded_docs)

    # 3. Test loading JSON files from a directory
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_json_files_from_directory(self, mock_stdout):
        dir_path = os.path.join(self.test_dir, "subdir1")
        os.makedirs(dir_path, exist_ok=True)

        doc_content = [{"id": "dir_json_test", "data": "content_dir1"}]
        json_file_path = os.path.join(dir_path, "data.json")
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(doc_content, f)

        non_json_file_path = os.path.join(dir_path, "notes.txt")
        with open(non_json_file_path, 'w', encoding='utf-8') as f:
            f.write("This is not JSON.")

        loaded_docs = load_documents([dir_path])
        self.assertEqual(len(loaded_docs), 1)
        self.assertEqual(loaded_docs[0], doc_content[0])
        
        output = mock_stdout.getvalue()
        self.assertIn(f"Warning: Skipping non-JSON file: {non_json_file_path}", output)

    # 4. Test loading a mix of specified JSON files and directories
    def test_load_mix_of_files_and_directories(self):
        # Directory part
        dir_path_mix = os.path.join(self.test_dir, "subdir_mix")
        os.makedirs(dir_path_mix, exist_ok=True)
        dir_doc_content = [{"id": "dir_mix_doc", "data": "content_dir_mix"}]
        dir_json_file_path = os.path.join(dir_path_mix, "data_in_dir.json")
        with open(dir_json_file_path, 'w', encoding='utf-8') as f:
            json.dump(dir_doc_content, f)

        # Standalone file part
        standalone_doc_content = [{"id": "standalone_mix_doc", "data": "content_standalone_mix"}]
        standalone_file_path = self._create_temp_json_file(standalone_doc_content, "standalone_")

        loaded_docs = load_documents([dir_path_mix, standalone_file_path])
        self.assertEqual(len(loaded_docs), 2)
        self.assertIn(dir_doc_content[0], loaded_docs)
        self.assertIn(standalone_doc_content[0], loaded_docs)

    # 5. Test with an invalid path
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_invalid_path(self, mock_stdout):
        invalid_path = os.path.join(self.test_dir, "non_existent_path")
        loaded_docs = load_documents([invalid_path])
        self.assertEqual(len(loaded_docs), 0)
        output = mock_stdout.getvalue()
        self.assertIn(f"Warning: Source path not found or invalid, skipping: {invalid_path}", output)

    # 6. Test with a non-JSON file specified directly
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_non_json_file_directly(self, mock_stdout):
        non_json_file_path = self._create_temp_file("This is plain text.", "nonjson_direct_")
        loaded_docs = load_documents([non_json_file_path])
        self.assertEqual(len(loaded_docs), 0)
        output = mock_stdout.getvalue()
        self.assertIn(f"Warning: Skipping non-JSON file: {non_json_file_path}", output)

    # 7. Test with a directory containing no JSON files
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_directory_with_no_json_files(self, mock_stdout):
        empty_dir_path = os.path.join(self.test_dir, "empty_dir")
        os.makedirs(empty_dir_path, exist_ok=True)
        
        txt_file_in_empty_dir = os.path.join(empty_dir_path, "some.txt")
        with open(txt_file_in_empty_dir, 'w') as f:
            f.write("hello")

        loaded_docs = load_documents([empty_dir_path])
        self.assertEqual(len(loaded_docs), 0)
        output = mock_stdout.getvalue()
        # Check that it warns about the .txt file
        self.assertIn(f"Warning: Skipping non-JSON file: {txt_file_in_empty_dir}", output)
        
        # Also test a truly empty directory
        truly_empty_dir_path = os.path.join(self.test_dir, "truly_empty_dir")
        os.makedirs(truly_empty_dir_path, exist_ok=True)
        mock_stdout.truncate(0) # Clear previous stdout
        mock_stdout.seek(0)
        loaded_docs_empty = load_documents([truly_empty_dir_path])
        self.assertEqual(len(loaded_docs_empty), 0)
        self.assertEqual(mock_stdout.getvalue(), "") # No output for truly empty dir

    # 8. Test with a JSON file containing a single JSON object (not a list)
    def test_load_json_file_with_single_object(self):
        doc_content = {"id": "single_object_test", "data": "content2"} # Not a list
        file_path = self._create_temp_json_file(doc_content, "single_obj_")
        
        loaded_docs = load_documents([file_path])
        self.assertEqual(len(loaded_docs), 1)
        self.assertEqual(loaded_docs[0], doc_content)

    # 9. Test with a JSON file that has invalid JSON content
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_invalid_json_content(self, mock_stdout):
        # Create a file with invalid JSON content
        # Note: tempfile creates the file, so we open it in 'w' to overwrite with bad content.
        # Or, more simply, use _create_temp_file which is more direct for text content.
        
        # Path for the invalid JSON file
        invalid_json_path = os.path.join(self.test_dir, "invalid.json")
        with open(invalid_json_path, 'w', encoding='utf-8') as f:
            f.write('{"id": "broken", data: "test"}') # Invalid: 'data' key not in quotes

        loaded_docs = load_documents([invalid_json_path])
        self.assertEqual(len(loaded_docs), 0)
        output = mock_stdout.getvalue()
        self.assertIn(f"Error: Invalid JSON format in - {invalid_json_path}", output)

    # Test with a mix of valid and invalid files to ensure partial success
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_load_mix_valid_and_invalid_files(self, mock_stdout):
        valid_doc_content = [{"id": "valid_doc", "data": "content_valid"}]
        valid_file_path = self._create_temp_json_file(valid_doc_content, "valid_mix_")

        invalid_json_path = os.path.join(self.test_dir, "invalid_mix.json")
        with open(invalid_json_path, 'w', encoding='utf-8') as f:
            f.write('{"id": "broken_mix", data: "test_mix"}')
            
        non_existent_path = os.path.join(self.test_dir, "non_existent_mix.json")

        loaded_docs = load_documents([valid_file_path, invalid_json_path, non_existent_path])
        self.assertEqual(len(loaded_docs), 1) # Only the valid document should be loaded
        self.assertEqual(loaded_docs[0], valid_doc_content[0])

        output = mock_stdout.getvalue()
        self.assertIn(f"Error: Invalid JSON format in - {invalid_json_path}", output)
        self.assertIn(f"Warning: Source path not found or invalid, skipping: {non_existent_path}", output)


if __name__ == '__main__':
    unittest.main()
