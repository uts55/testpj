import unittest
import os
import json
import shutil
import tempfile
from data_loader import load_game_data # Assuming data_loader.py is in the parent directory or accessible via PYTHONPATH

class TestDataLoader(unittest.TestCase):
    """Test cases for the load_game_data function."""

    def setUp(self):
        """Set up a temporary directory structure for test JSON files."""
        # Create a top-level temporary directory for this test case
        self.base_temp_dir = tempfile.mkdtemp(prefix="test_data_loader_")

        # Create the 'data/NPCs' and 'data/GameObjects' structure within base_temp_dir
        self.npcs_dir = os.path.join(self.base_temp_dir, "data", "NPCs")
        self.game_objects_dir = os.path.join(self.base_temp_dir, "data", "GameObjects")

        os.makedirs(self.npcs_dir)
        os.makedirs(self.game_objects_dir)

        # self.addCleanup(shutil.rmtree, self.base_temp_dir) # Ensure cleanup

    def tearDown(self):
        """Clean up the temporary directory structure."""
        shutil.rmtree(self.base_temp_dir)

    def _create_json_file(self, dir_path, filename, content):
        """Helper method to create a JSON file."""
        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'w') as f:
            json.dump(content, f)
        return filepath

    def _create_raw_file(self, dir_path, filename, raw_content_str):
        """Helper method to create a file with raw string content."""
        filepath = os.path.join(dir_path, filename)
        with open(filepath, 'w') as f:
            f.write(raw_content_str)
        return filepath

    def test_load_valid_data(self):
        """Test loading of valid NPC and GameObject JSON files."""
        npc_data1 = {"name": "Guard Eric", "description": "A stoic guard."}
        npc_data2 = {"name": "Merchant Freya", "description": "A friendly merchant."}
        obj_data1 = {"name": "Sunstone", "description": "A glowing stone."}

        self._create_json_file(self.npcs_dir, "eric.json", npc_data1)
        self._create_json_file(self.npcs_dir, "freya.json", npc_data2)
        self._create_json_file(self.game_objects_dir, "sunstone.json", obj_data1)

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)

        self.assertEqual(len(loaded_data["npcs"]), 2)
        self.assertEqual(len(loaded_data["game_objects"]), 1)
        self.assertIn(npc_data1, loaded_data["npcs"])
        self.assertIn(npc_data2, loaded_data["npcs"])
        self.assertIn(obj_data1, loaded_data["game_objects"])

    def test_load_malformed_json(self):
        """Test that malformed JSON files are skipped."""
        npc_data_valid = {"name": "Valid NPC", "description": "This one is fine."}
        self._create_json_file(self.npcs_dir, "valid_npc.json", npc_data_valid)
        self._create_raw_file(self.npcs_dir, "malformed.json", "{'name': 'Broken', 'description': 'unterminated string")

        # We can't easily check print output for warnings without more complex mocking.
        # So, we primarily check that the function doesn't crash and loads valid files.
        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)

        self.assertEqual(len(loaded_data["npcs"]), 1, "Should only load the valid NPC file.")
        self.assertIn(npc_data_valid, loaded_data["npcs"])
        self.assertEqual(len(loaded_data["game_objects"]), 0)


    def test_load_empty_json_file(self):
        """Test loading an empty JSON file (should be skipped or handled as error by json.load)."""
        # json.load on an empty file raises JSONDecodeError. data_loader should skip it.
        self._create_raw_file(self.npcs_dir, "empty.json", "")
        npc_data_valid = {"name": "Another NPC", "description": "Also fine."}
        self._create_json_file(self.npcs_dir, "another_npc.json", npc_data_valid)

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)

        self.assertEqual(len(loaded_data["npcs"]), 1, "Should skip the empty JSON and load the valid one.")
        self.assertIn(npc_data_valid, loaded_data["npcs"])

    def test_load_json_with_list_root(self):
        """Test loading JSON files where the root is a list containing one object."""
        list_npc_data = [{"name": "List NPC", "description": "Contained in a list."}]
        self._create_json_file(self.npcs_dir, "list_npc.json", list_npc_data)

        dict_npc_data = {"name": "Dict NPC", "description": "Regular dict."}
        self._create_json_file(self.npcs_dir, "dict_npc.json", dict_npc_data)

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)

        self.assertEqual(len(loaded_data["npcs"]), 2)
        # The data_loader is expected to extract the dictionary from the list
        self.assertIn(list_npc_data[0], loaded_data["npcs"])
        self.assertIn(dict_npc_data, loaded_data["npcs"])

    def test_load_json_with_list_root_multiple_items_or_empty(self):
        """Test JSONs with list root but multiple items or empty list (should be skipped)."""
        list_multi_npc_data = [
            {"name": "NPC A", "description": "First in list."},
            {"name": "NPC B", "description": "Second in list."}
        ]
        self._create_json_file(self.npcs_dir, "list_multi_npc.json", list_multi_npc_data)
        self._create_json_file(self.npcs_dir, "list_empty.json", [])

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)
        self.assertEqual(len(loaded_data["npcs"]), 0, "Should skip lists with multiple items or empty lists.")


    def test_ignore_files_in_subdirectories(self):
        """Test that files in subdirectories are not loaded."""
        npc_data_main = {"name": "Main NPC", "description": "Lives in main NPCs dir."}
        self._create_json_file(self.npcs_dir, "main_npc.json", npc_data_main)

        archive_npc_dir = os.path.join(self.npcs_dir, "archive")
        os.makedirs(archive_npc_dir)
        self._create_json_file(archive_npc_dir, "archived_npc.json", {"name": "Old NPC", "description": "Archived."})

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)

        self.assertEqual(len(loaded_data["npcs"]), 1)
        self.assertIn(npc_data_main, loaded_data["npcs"])

    def test_non_json_files_ignored(self):
        """Test that non-JSON files are ignored."""
        npc_data_valid = {"name": "JSON NPC", "description": "A valid JSON."}
        self._create_json_file(self.npcs_dir, "json_npc.json", npc_data_valid)
        self._create_raw_file(self.npcs_dir, "text_file.txt", "This is not a JSON file.")

        loaded_data = load_game_data(npc_dir=self.npcs_dir, game_object_dir=self.game_objects_dir)
        self.assertEqual(len(loaded_data["npcs"]), 1)
        self.assertIn(npc_data_valid, loaded_data["npcs"])

    def test_missing_directories(self):
        """Test behavior when specified directories do not exist."""
        # Create a valid NPCs directory for one part of the test
        valid_npc_data = {"name": "Test NPC", "description": "In a valid directory."}
        self._create_json_file(self.npcs_dir, "test_npc.json", valid_npc_data)

        # Test with one valid and one missing directory
        missing_obj_dir = os.path.join(self.base_temp_dir, "data", "NonExistentObjects")
        loaded_data_one_missing = load_game_data(npc_dir=self.npcs_dir, game_object_dir=missing_obj_dir)
        self.assertEqual(len(loaded_data_one_missing["npcs"]), 1)
        self.assertIn(valid_npc_data, loaded_data_one_missing["npcs"])
        self.assertEqual(len(loaded_data_one_missing["game_objects"]), 0)

        # Test with both directories missing
        missing_npc_dir = os.path.join(self.base_temp_dir, "data", "NonExistentNPCs")
        loaded_data_both_missing = load_game_data(npc_dir=missing_npc_dir, game_object_dir=missing_obj_dir)
        self.assertEqual(len(loaded_data_both_missing["npcs"]), 0)
        self.assertEqual(len(loaded_data_both_missing["game_objects"]), 0)
        # Expect warnings to be printed by data_loader.py, cannot easily capture here.

if __name__ == '__main__':
    unittest.main()
