import unittest
from rag_manager import retrieve_context # Assuming rag_manager.py is accessible

class TestRagManager(unittest.TestCase):
    """Test cases for the retrieve_context function from rag_manager."""

    def setUp(self):
        """Prepare a fixed dataset for testing context retrieval."""
        self.sample_game_data = {
            "npcs": [
                {"name": "Old Man Hemlock", "description": "A wise old hermit who lives in the Whispering Woods. Knows about herbs."},
                {"name": "Guard Captain Theron", "description": "The stern but fair captain of the city guard. Always vigilant."},
                {"name": "Mysterious Stranger", "description": "A cloaked figure. Says little."},
                {"description": "Nameless wanderer, tells tales of the ancient ruins."}, # NPC missing 'name'
                {"name": "Shopkeeper Mira", "description": None}, # NPC with None description
                {}, # Empty NPC dict
            ],
            "game_objects": [
                {"name": "The Sunstone", "description": "A legendary artifact said to hold the power of the sun."},
                {"name": "Whispering Woods", "description": "A dark and ancient forest, rumored to be enchanted."},
                {"name": "Forgotten Sword", "description": "An old rusty sword. Seems unimportant."},
                {"description": "An odd-looking amulet, humming faintly."}, # GameObject missing 'name'
                {"name": "Empty Chest", "description": ""}, # GameObject with empty string description
            ]
        }
        self.no_context_message = "No specific context found for your input."

    def test_input_matches_npc_name(self):
        """Test when input matches an NPC's name."""
        context = retrieve_context("Tell me about Hemlock", data=self.sample_game_data)
        self.assertIn("Old Man Hemlock", context)
        self.assertIn("wise old hermit", context)

    def test_input_matches_npc_description(self):
        """Test when input matches part of an NPC's description."""
        context = retrieve_context("Who is vigilant?", data=self.sample_game_data)
        self.assertIn("Guard Captain Theron", context)
        self.assertIn("stern but fair", context)

    def test_input_matches_game_object_name(self):
        """Test when input matches a GameObject's name."""
        context = retrieve_context("What is the Sunstone?", data=self.sample_game_data)
        self.assertIn("The Sunstone", context)
        self.assertIn("legendary artifact", context)

    def test_input_matches_game_object_description(self):
        """Test when input matches part of a GameObject's description."""
        context = retrieve_context("Anything enchanted around here?", data=self.sample_game_data)
        self.assertIn("Whispering Woods", context)
        self.assertIn("dark and ancient forest", context)

    def test_input_matches_multiple_items(self):
        """Test when input matches multiple items (NPC and GameObject)."""
        context = retrieve_context("woods sword", data=self.sample_game_data)
        self.assertIn("Old Man Hemlock", context) # "Whispering Woods" in Hemlock's desc
        self.assertIn("Whispering Woods", context) # GameObject "Whispering Woods"
        self.assertIn("Forgotten Sword", context) # GameObject "Forgotten Sword"
        # Check number of lines to infer number of matched items, expecting 3 unique items
        self.assertEqual(len(context.splitlines()), 3)


    def test_input_matches_no_items(self):
        """Test when input matches no items."""
        context = retrieve_context("Tell me about the hidden bakery", data=self.sample_game_data)
        self.assertEqual(context, self.no_context_message)

    def test_empty_string_input(self):
        """Test when the input string is empty."""
        # Keywords will be an empty list. This shouldn't match anything specifically by keyword.
        # Depending on implementation, it might return all items or none.
        # Current rag_manager splits input into keywords; empty input means empty keywords list.
        # The `any(keyword in ...)` logic will result in no matches.
        context = retrieve_context("", data=self.sample_game_data)
        self.assertEqual(context, self.no_context_message)

    def test_input_with_only_stopwords_or_common_words(self):
        """Test input that might only contain common words not in descriptions."""
        # Assuming "the", "is", "a" are not specific keywords in the data.
        context = retrieve_context("the is a of", data=self.sample_game_data)
        self.assertEqual(context, self.no_context_message)

    def test_npc_missing_name(self):
        """Test context retrieval for an NPC missing a 'name' field."""
        context = retrieve_context("ancient ruins", data=self.sample_game_data)
        self.assertIn("Nameless wanderer", context) # Default name used in rag_manager
        self.assertIn("tells tales of the ancient ruins", context)

    def test_npc_missing_description(self):
        """Test context retrieval for an NPC with a None 'description' field."""
        context = retrieve_context("Mira", data=self.sample_game_data)
        self.assertIn("Shopkeeper Mira", context)
        # Ensure it doesn't crash and provides the name.
        # The current rag_manager uses `npc.get('description', 'No description')`
        self.assertIn("No description", context)

    def test_game_object_missing_name(self):
        """Test context retrieval for a GameObject missing a 'name' field."""
        context = retrieve_context("humming amulet", data=self.sample_game_data)
        self.assertIn("Unnamed Object", context) # Default name used in rag_manager
        self.assertIn("odd-looking amulet, humming faintly", context)

    def test_game_object_empty_description(self):
        """Test context retrieval for a GameObject with an empty string 'description'."""
        context = retrieve_context("Empty Chest", data=self.sample_game_data)
        self.assertIn("Empty Chest", context)
        # The current rag_manager uses `game_object.get('description', 'No description')`
        # An empty string is a valid description, so it should be used.
        # The formatting `f"Object: {name} - {desc}"` means it will show "Object: Empty Chest - "
        self.assertTrue(context.endswith(" - ") or context.endswith(" - \n") or "Empty Chest - \n" in context or "Empty Chest - " in context)


    def test_empty_data_source(self):
        """Test with an empty data source."""
        empty_data = {"npcs": [], "game_objects": []}
        context = retrieve_context("anything", data=empty_data)
        self.assertEqual(context, self.no_context_message)

    def test_data_source_with_empty_npc_or_object_dicts(self):
        """Test with data source that contains empty dictionaries for NPCs/objects."""
        data_with_empty_dicts = {
            "npcs": [{}], # Handled by rag_manager's .get("name", "")
            "game_objects": [{}] # Handled by rag_manager's .get("name", "")
        }
        context = retrieve_context("something", data=data_with_empty_dicts)
        # retrieve_context uses .get("name", "Unnamed NPC/Object") and .get("description", "No description")
        # An empty dict will yield these defaults. If "something" isn't in "Unnamed..." or "No description",
        # it should return no_context_message.
        # Let's test for a keyword that IS in the default.
        context_unnamed = retrieve_context("Unnamed", data=data_with_empty_dicts)
        self.assertIn("Unnamed NPC", context_unnamed)
        self.assertIn("Unnamed Object", context_unnamed)
        self.assertEqual(len(context_unnamed.splitlines()), 2)

        context_nodesc = retrieve_context("No description", data=data_with_empty_dicts)
        self.assertIn("Unnamed NPC", context_nodesc)
        self.assertIn("Unnamed Object", context_nodesc)
        self.assertEqual(len(context_nodesc.splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
