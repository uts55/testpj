# This file makes the 'ui' directory a Python package.

# Placeholder for GamePlayFrame to allow main.py to import
# The test script (test_save_game.py) will mock main.GamePlayFrame more thoroughly.
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
