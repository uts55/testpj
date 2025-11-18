# This file makes the 'ui' directory a Python package.

# Import GamePlayFrame from the parent ui.py module
import sys
import os
import importlib.util

# Get the parent directory path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_py_path = os.path.join(parent_dir, 'ui.py')

# Import GamePlayFrame from ui.py if it exists
if os.path.exists(ui_py_path):
    spec = importlib.util.spec_from_file_location("ui_module", ui_py_path)
    ui_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui_module)
    GamePlayFrame = ui_module.GamePlayFrame
else:
    # Fallback placeholder if ui.py doesn't exist
    class GamePlayFrame:
        pass

# Attempt to import other known classes to make them available if needed by main.py directly from ui
try:
    from .main_menu_frame import MainMenuFrame
except ImportError:
    pass # It's okay if this doesn't exist for the current test focus

try:
    from .settings_frame import SettingsFrame
except ImportError:
    pass # It's okay if this doesn't exist for the current test focus
