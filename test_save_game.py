import os
import shutil
import unittest
from unittest import mock
import traceback # Added for exception printing

# --- Import project modules ---
# Add project root to sys.path to allow imports
import sys

# Preemptive mock for tkinter and its submodules used by main.py
mock_tkinter = mock.MagicMock()
mock_tkinter.simpledialog = mock.MagicMock()
mock_tkinter.messagebox = mock.MagicMock()
mock_tkinter.Toplevel = mock.MagicMock()
mock_tkinter.Listbox = mock.MagicMock()
mock_tkinter.Scrollbar = mock.MagicMock()
mock_tkinter.Button = mock.MagicMock()
mock_tkinter.Frame = mock.MagicMock()
mock_tkinter.constants = mock.MagicMock()
mock_tkinter.constants.VERTICAL = "vertical"
mock_tkinter.constants.END = "end"
mock_tkinter.constants.BOTH = "both"
mock_tkinter.constants.Y = "y"
mock_tkinter.constants.RIGHT = "right"
mock_tkinter.constants.LEFT = "left"
mock_tkinter.constants.X = "x"


sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.simpledialog'] = mock_tkinter.simpledialog
sys.modules['tkinter.messagebox'] = mock_tkinter.messagebox
sys.modules['tkinter.constants'] = mock_tkinter.constants


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import main
import config
from game_state import GameState as RealGameState
from game_state import Player as RealPlayer
from gemini_dm import GeminiDialogueManager as RealGeminiDialogueManager
from rag_manager import RAGManager as RealRAGManager
from ui.main_menu_frame import MainMenuFrame as RealMainMenuFrame


# --- Global test variables ---
narration_messages = []
SAVE_DIR_FOR_TEST_1 = "./Save_Test_Dir_1/"
SAVE_DIR_FOR_TEST_2 = "./Save_Test_Dir_2/"
SAVE_DIR_FOR_TEST_CANCEL = "./Save_Test_Dir_Cancel/"
SAVE_DIR_FOR_TEST_LOAD = "./Save_Test_Load_Success/"
SAVE_DIR_FOR_LOAD_MISSING = "./Save_Missing_Dir_Test/"
SAVE_DIR_FOR_LOAD_EMPTY = "./Save_Empty_Dir_Test/"
SAVE_DIR_FOR_INGAME_LOAD_BTN = "./Save_Ingame_Load_Btn_Test/"


# --- Mock Classes ---
class MockListbox:
    def __init__(self, master, yscrollcommand=None, exportselection=False):
        self.items = []
        self.current_selection_index = None
        self._yscrollcommand = yscrollcommand
        self._exportselection = exportselection
        self.view_mock = mock.MagicMock(name="yview_mock")
        # print("MockListbox Initialized") # Reduced verbosity

    def insert(self, index, item):
        self.items.append(item)
        # print(f"MockListbox.insert: Added '{item}'")

    def get(self, index_or_indices):
        actual_idx = -1
        if isinstance(index_or_indices, tuple) and len(index_or_indices) > 0 :
            try: actual_idx = int(index_or_indices[0])
            except ValueError: raise ValueError(f"MockListbox.get received non-integer index string in tuple: {index_or_indices[0]}")
        elif isinstance(index_or_indices, int): actual_idx = index_or_indices
        elif isinstance(index_or_indices, str) and index_or_indices.isdigit(): actual_idx = int(index_or_indices)
        else:
            if self.items: return self.items[-1]
            return None
        if 0 <= actual_idx < len(self.items): return self.items[actual_idx]
        return None

    def curselection(self): return self.current_selection_index
    def pack(self, side=None, fill=None, expand=None): pass
    def config(self, command=None): pass
    def yview(self, *args): self.view_mock(*args)

captured_on_load_selected_command = None
class MockButtonImpl:
    def __init__(self, master, text=None, command=None):
        global captured_on_load_selected_command
        self.text = text; self.command = command
        if text == "Load Selected": captured_on_load_selected_command = command
    def pack(self, side=None, expand=None, padx=None): pass

class MockToplevelInstance:
    def __init__(self, master): self.master = master
    def title(self, value): pass
    def geometry(self, value): pass
    def transient(self, master): pass
    def grab_set(self): pass
    def destroy(self): print("MockToplevelInstance.destroy called")

class MockTk:
    def __init__(self): pass # print("MockTk Initialized")
    def title(self, value): pass
    def geometry(self, value): pass
    def destroy(self): print("MockTk.destroy called")
    def pack_forget(self): pass
    def pack(self, fill=None, expand=None): pass
    def after(self, ms, callback): pass
    def mainloop(self): pass

class MockGamePlayFrame:
    def __init__(self, master, process_input_callback, save_game_callback, load_game_callback, exit_callback):
        self.master = master; # print("MockGamePlayFrame Initialized")
    def add_narration(self, message): global narration_messages; narration_messages.append(message.strip())
    def update_hp(self, hp): pass
    def update_location(self, loc): pass
    def update_inventory(self, inv): pass
    def update_npcs(self, npcs): pass
    def pack(self, fill=None, expand=None): pass
    def pack_forget(self): pass
    def destroy(self): print("MockGamePlayFrame.destroy called")

class MockPlayer(RealPlayer):
    def __init__(self, id, name, **kwargs):
        super().__init__(id=id, name=name, inventory=[], skills=[], knowledge_fragments=[], current_location="mock_loc")
        # print(f"MockPlayer Initialized: {name} ({id})")

class MockGameStateGeneral(RealGameState):
    def __init__(self):
        super().__init__()
        self.save_game_called_with_path = None
        # print("MockGameStateGeneral Initialized")
    def save_game(self, filepath: str):
        self.save_game_called_with_path = filepath
        # print(f"MockGameStateGeneral.save_game CALLED WITH: {filepath}")
        save_dir_actual = os.path.dirname(filepath)
        if save_dir_actual: os.makedirs(save_dir_actual, exist_ok=True)
        with open(filepath, 'w') as f: f.write("{}")
        # print(f"MockGameStateGeneral: Touched/Created file at {filepath}")
    def initialize_new_game(self, main_player_id: str, default_player_name: str, start_location_id: str):
        super().initialize_new_game(main_player_id, default_player_name, start_location_id)
        # print(f"MockGameStateGeneral.initialize_new_game called for player {main_player_id}")


class MockGameStateLoadTest(RealGameState):
    def __init__(self):
        super().__init__()
        self.load_game_called_with_path = None
        self._player_loaded_successfully = False
        # print("MockGameStateLoadTest Initialized")
    def load_game(self, filepath: str):
        # print(f"MockGameStateLoadTest.load_game CALLED WITH: {filepath}")
        self.load_game_called_with_path = filepath
        loaded_player = MockPlayer(id=main.MAIN_PLAYER_ID, name="Loaded Player")
        self.players = {main.MAIN_PLAYER_ID: loaded_player}
        self._player_loaded_successfully = True
    def get_player(self, player_id: str):
        # print(f"MockGameStateLoadTest.get_player for {player_id}. Player loaded: {self._player_loaded_successfully}")
        if self._player_loaded_successfully and player_id == main.MAIN_PLAYER_ID:
            return self.players.get(player_id)
        return None
    def initialize_new_game(self, main_player_id: str, default_player_name: str, start_location_id: str):
        super().initialize_new_game(main_player_id, default_player_name, start_location_id)


class MockGeminiDialogueManager(RealGeminiDialogueManager):
    def __init__(self, api_key, gemini_model_name, tools, system_instruction_text, max_history_items):
        self.model = mock.Mock(); self.history = ["initial_history_item"]
        # print(f"MockGeminiDialogueManager Initialized with history: {self.history}")
    def send_message(self, user_prompt_text: str, rag_context: str = None):
        return "Mocked Gemini: Welcome!" if user_prompt_text == config.INITIAL_PROMPT_TEXT else "Mocked Gemini response."

class MockRAGManager(RealRAGManager):
     def __init__(self, embedding_model_name, vector_db_path, collection_name):
        self.collection = mock.Mock(); self.collection.count.return_value = 0
        # print("MockRAGManager Initialized")

class MockMainMenuFrame(RealMainMenuFrame):
    def __init__(self, master, start_cb, load_cb, settings_cb, exit_cb):
        self.master = master; # print("MockMainMenuFrame Initialized")
    def pack(self, fill=None, expand=None): pass

def setup_test_environment(test_save_dir, askstring_return_value=None, mock_gamestate_class=MockGameStateGeneral, setup_main_managers=True):
    global narration_messages, captured_on_load_selected_command
    narration_messages = []; captured_on_load_selected_command = None

    original_save_dir = config.SAVE_GAME_DIR
    config.SAVE_GAME_DIR = test_save_dir
    # print(f"Set config.SAVE_GAME_DIR to: {config.SAVE_GAME_DIR}")

    if not os.path.exists(config.SAVE_GAME_DIR): os.makedirs(config.SAVE_GAME_DIR, exist_ok=True)
    # else: print(f"Directory {config.SAVE_GAME_DIR} already exists.")


    if askstring_return_value is not None:
        mock_tkinter.simpledialog.askstring.return_value = askstring_return_value

    current_mock_listbox = MockListbox(None)
    mock_tkinter.Listbox.return_value = current_mock_listbox
    mock_tkinter.Button.side_effect = lambda master, text=None, command=None: MockButtonImpl(master, text, command)
    mock_tkinter.Toplevel.return_value = MockToplevelInstance(None)

    patches = [
        mock.patch('main.GameState', mock_gamestate_class),
        mock.patch('main.GamePlayFrame', MockGamePlayFrame),
        mock.patch('main.GeminiDialogueManager', MockGeminiDialogueManager),
        mock.patch('main.RAGManager', MockRAGManager),
        mock.patch('main.MainMenuFrame', MockMainMenuFrame),
        mock.patch('main.show_frame', mock.MagicMock(name="show_frame_mock")),
        mock.patch('main.update_ui_game_state', mock.MagicMock(name="update_ui_game_state_mock")),
        mock.patch('main.os.path.isdir', mock.MagicMock(name="os_path_isdir_mock")),
        mock.patch('main.os.listdir', mock.MagicMock(name="os_listdir_mock"))
    ]
    for p in patches: p.start()

    if setup_main_managers:
        main.root_tk_window = MockTk()
        main.game_state_manager = main.GameState()
        main.dialogue_manager = main.GeminiDialogueManager("mock_api_key", "m", None, "m", 10)
        main.rag_system_manager = main.RAGManager("m", "./mock_db", "m")
        # print("Initialized managers with mocks.")
    return original_save_dir, patches, current_mock_listbox

def cleanup_test_environment(original_save_dir, test_save_dir, patches):
    if os.path.exists(test_save_dir) and test_save_dir.startswith("./Save_Test_"):
        shutil.rmtree(test_save_dir)
    for p in patches: p.stop()
    mock.patch.stopall()
    config.SAVE_GAME_DIR = original_save_dir

def run_first_save_test():
    print("\n--- Test: First Save ---")
    test_dir = SAVE_DIR_FOR_TEST_1
    if os.path.exists(test_dir): shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    original_save_dir, patches, _ = setup_test_environment(test_dir, "test_save_1", MockGameStateGeneral)
    try:
        main.start_new_game()
        main.handle_save_game()
        expected_path = os.path.join(config.SAVE_GAME_DIR, "test_save_1.json")
        assert os.path.exists(expected_path)
        assert any("Game saved as test_save_1.json." in msg for msg in narration_messages)
        print("--- Test: First Save PASSED ---")
    finally: cleanup_test_environment(original_save_dir, test_dir, patches)

def run_second_save_test():
    print("\n--- Test: Second Save ---")
    test_dir = SAVE_DIR_FOR_TEST_2
    if os.path.exists(test_dir): shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    original_save_dir, patches, _ = setup_test_environment(test_dir, "test_save_2", MockGameStateGeneral)
    try:
        dummy_path = os.path.join(config.SAVE_GAME_DIR, "test_save_1.json")
        with open(dummy_path, 'w') as f: f.write('{}')
        main.game_play_frame = MockGamePlayFrame(None,None,None,None,None); main.current_frame = main.game_play_frame
        main.handle_save_game()
        assert os.path.exists(os.path.join(config.SAVE_GAME_DIR, "test_save_2.json"))
        assert os.path.exists(dummy_path)
        assert any("Game saved as test_save_2.json." in msg for msg in narration_messages)
        print("--- Test: Second Save PASSED ---")
    finally: cleanup_test_environment(original_save_dir, test_dir, patches)

def run_cancel_save_test():
    print("\n--- Test: Cancel Save ---")
    test_dir = SAVE_DIR_FOR_TEST_CANCEL
    if os.path.exists(test_dir): shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    original_save_dir, patches, _ = setup_test_environment(test_dir, None, MockGameStateGeneral)
    try:
        initial_files = os.listdir(config.SAVE_GAME_DIR)
        main.game_play_frame = MockGamePlayFrame(None,None,None,None,None); main.current_frame = main.game_play_frame
        main.game_state_manager.save_game = mock.MagicMock()
        main.handle_save_game()
        main.game_state_manager.save_game.assert_not_called()
        assert len(os.listdir(config.SAVE_GAME_DIR)) == len(initial_files)
        assert any("Save cancelled." in msg for msg in narration_messages)
        print("--- Test: Cancel Save PASSED ---")
    finally: cleanup_test_environment(original_save_dir, test_dir, patches)

def run_load_game_success_test():
    print("\n--- Test: Load Game Success ---")
    test_dir = SAVE_DIR_FOR_TEST_LOAD
    if os.path.exists(test_dir): shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    original_save_dir, patches, current_mock_listbox = setup_test_environment(test_dir, mock_gamestate_class=MockGameStateLoadTest)
    global captured_on_load_selected_command, narration_messages; narration_messages = []
    try:
        for sf_name in ["load_test_1.json", "load_test_2.json"]:
            with open(os.path.join(config.SAVE_GAME_DIR, sf_name), 'w') as f: f.write('{}')

        main.current_frame = main.MainMenuFrame(None,None,None,None,None)
        main.load_existing_game()

        target_save_file = "load_test_1.json"
        selected_idx = current_mock_listbox.items.index(target_save_file)
        current_mock_listbox.current_selection_index = (selected_idx,)

        captured_on_load_selected_command()

        assert main.game_state_manager.load_game_called_with_path == os.path.join(config.SAVE_GAME_DIR, target_save_file)
        assert main.dialogue_manager.history == []
        main.show_frame.assert_called(); assert isinstance(main.show_frame.call_args.args[0], MockGamePlayFrame)
        main.update_ui_game_state.assert_called_once()
        assert any(f"Game '{target_save_file}' loaded." in msg for msg in narration_messages)
        print("--- Test: Load Game Success PASSED ---")
    finally: cleanup_test_environment(original_save_dir, test_dir, patches)

def run_load_game_missing_dir_test():
    print("\n--- Test: Load Game Missing Directory ---")
    test_dir = SAVE_DIR_FOR_LOAD_MISSING
    if os.path.exists(test_dir): shutil.rmtree(test_dir)

    original_save_dir, patches, _ = setup_test_environment(test_dir, mock_gamestate_class=MockGameStateLoadTest)
    mock_os_path_isdir = main.os.path.isdir

    try:
        mock_os_path_isdir.side_effect = lambda path_arg: False if path_arg == config.SAVE_GAME_DIR else True

        main.current_frame = main.MainMenuFrame(None,None,None,None,None)
        main.load_existing_game()

        mock_os_path_isdir.assert_any_call(config.SAVE_GAME_DIR)
        mock_tkinter.messagebox.showerror.assert_called_once()
        args, _ = mock_tkinter.messagebox.showerror.call_args
        assert args[0] == "Load Game Error" and f"Save directory '{config.SAVE_GAME_DIR}' not found." in args[1]
        print("--- Test: Load Game Missing Directory PASSED ---")
    finally:
        cleanup_test_environment(original_save_dir, test_dir, patches)

def run_load_game_empty_dir_test():
    print("\n--- Test: Load Game Empty Directory ---")
    test_dir = SAVE_DIR_FOR_LOAD_EMPTY
    if os.path.exists(test_dir): shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    original_save_dir, patches, _ = setup_test_environment(test_dir, mock_gamestate_class=MockGameStateLoadTest)

    mock_os_path_isdir = main.os.path.isdir
    mock_os_listdir = main.os.listdir

    try:
        mock_os_path_isdir.side_effect = lambda path_arg: True if path_arg == config.SAVE_GAME_DIR else False
        mock_os_listdir.return_value = []

        main.current_frame = main.MainMenuFrame(None,None,None,None,None)
        main.load_existing_game()

        mock_os_path_isdir.assert_any_call(config.SAVE_GAME_DIR)
        mock_os_listdir.assert_called_with(config.SAVE_GAME_DIR)

        mock_tkinter.messagebox.showinfo.assert_called_once()
        args, _ = mock_tkinter.messagebox.showinfo.call_args
        assert args[0] == "Load Game" and "No save files found" in args[1]
        print("--- Test: Load Game Empty Directory PASSED ---")
    finally:
        cleanup_test_environment(original_save_dir, test_dir, patches)

def run_ingame_load_button_test():
    print("\n--- Test: In-Game Load Button ---")
    test_dir = SAVE_DIR_FOR_INGAME_LOAD_BTN
    if not os.path.exists(test_dir): os.makedirs(test_dir, exist_ok=True)

    original_save_dir, patches, _ = setup_test_environment(test_dir, mock_gamestate_class=MockGameStateGeneral, setup_main_managers=True)

    global narration_messages; narration_messages = []
    try:
        main.game_state_manager = main.GameState()
        main.game_play_frame = main.GamePlayFrame(None, None, None, None, None)
        main.current_frame = main.game_play_frame
        print("Manually set main.game_state_manager and main.game_play_frame for in-game load test.")

        main.handle_load_game()

        expected_msg_part1 = "To load a specific save file, please use the 'Load Saved Game' option from the Main Menu."
        expected_msg_part2 = "Progress since your last explicit save might be lost if you load from Main Menu without saving now."

        assert len(narration_messages) == 1, f"Expected 1 narration message, got {len(narration_messages)}: {narration_messages}"
        full_message = narration_messages[0]
        assert expected_msg_part1 in full_message and expected_msg_part2 in full_message, \
            f"Expected narration messages not found. Got: '{full_message}'"
        print("--- Test: In-Game Load Button PASSED ---")

    finally:
        cleanup_test_environment(original_save_dir, test_dir, patches)


if __name__ == "__main__":
    test_to_run = sys.argv[1] if len(sys.argv) > 1 else "all"
    narration_messages = []

    import traceback

    try:
        if test_to_run == "all" or test_to_run == "first_save":
            run_first_save_test()
        if test_to_run == "all" or test_to_run == "second_save":
            if test_to_run == "all" : narration_messages = []
            run_second_save_test()
        if test_to_run == "all" or test_to_run == "cancel_save":
            if test_to_run == "all": narration_messages = []
            run_cancel_save_test()
        if test_to_run == "all" or test_to_run == "load_game_success":
            if test_to_run == "all": narration_messages = []
            run_load_game_success_test()
        if test_to_run == "all" or test_to_run == "load_missing_dir":
            if test_to_run == "all": narration_messages = []
            run_load_game_missing_dir_test()
        if test_to_run == "all" or test_to_run == "load_empty_dir":
            if test_to_run == "all": narration_messages = []
            run_load_game_empty_dir_test()
        if test_to_run == "all" or test_to_run == "ingame_load_button":
            if test_to_run == "all": narration_messages = []
            run_ingame_load_button_test()

    except AssertionError as e:
        print(f"\n--- Test FAILED ---"); print(f"Assertion Error: {e}"); traceback.print_exc()
    except Exception as e:
        print(f"\n--- Test ERROR ---"); print(f"An unexpected error: {e}"); traceback.print_exc()
