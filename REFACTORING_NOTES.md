# Global Variables Refactoring

## Overview
This document describes the refactoring of global variables in `main.py` into a `GameManager` class.

## Problem
The original code used multiple global variables:
- `hero: Player` - The player character
- `mock_npcs_in_encounter: list[NPC]` - NPCs in current encounter
- `main_player_state: PlayerState` - Player state management
- `dm: GeminiDM` - DM instance
- `app: GamePlayFrame` - UI instance
- `game: GameState` - Game state instance

This approach had several issues:
- **Testability**: Hard to create isolated test instances
- **Maintainability**: Unclear ownership of state
- **Thread safety**: No support for multiple game instances
- **Code organization**: State scattered across global scope

## Solution
Created a `GameManager` class that encapsulates all game state:

```python
class GameManager:
    """Manages all game state including player, NPCs, DM, UI, and game state."""
    def __init__(self):
        self.hero: Player = None
        self.mock_npcs_in_encounter: list[NPC] = []
        self.main_player_state: PlayerState = None
        self.dm: GeminiDM = None
        self.app: GamePlayFrame = None
        self.game: GameState = None
    
    def initialize_dm(self):
        """Initialize the DM instance."""
        self.dm = GeminiDM()
    
    def initialize_player(self, player_data: dict):
        """Initialize the player character."""
        self.hero = Player(player_data=player_data)
        self.main_player_state = PlayerState(player_character=self.hero)
    
    def initialize_game_state(self):
        """Initialize the game state with the player."""
        self.game = GameState(player_character=self.hero)
    
    def load_game_data(self):
        """Load all game data from sources."""
        # ... implementation
    
    def refresh_npcs(self):
        """Refresh NPCs in the encounter."""
        self.mock_npcs_in_encounter = get_fresh_npcs()
```

## Benefits
1. **Improved Testability**: Can create multiple `GameManager` instances for testing
2. **Better Organization**: Clear ownership and lifecycle of game state
3. **Easier Maintenance**: All state management in one place
4. **Future-proof**: Enables potential multi-instance or multiplayer support

## Backward Compatibility
The legacy global variables are maintained for backward compatibility:
```python
# Global GameManager instance
game_manager = GameManager()

# Legacy global variables for backward compatibility (will be deprecated)
hero: Player = None
mock_npcs_in_encounter: list[NPC] = []
main_player_state: PlayerState = None
dm: GeminiDM = None
app: GamePlayFrame = None
game: GameState = None
```

In `main()`, these are updated after initialization:
```python
# Update legacy global variables for backward compatibility
hero = game_manager.hero
mock_npcs_in_encounter = game_manager.mock_npcs_in_encounter
main_player_state = game_manager.main_player_state
dm = game_manager.dm
game = game_manager.game
```

## Migration Path
To fully migrate to the new pattern:

1. **Phase 1** (Current): GameManager class created, legacy globals maintained
2. **Phase 2** (Future): Update all functions to accept GameManager as parameter
3. **Phase 3** (Future): Remove legacy global variables entirely

Example of Phase 2 migration:
```python
# Before
def process_player_input(input_text: str):
    global hero, mock_npcs_in_encounter, main_player_state, dm, app
    # ... use globals

# After
def process_player_input(input_text: str, manager: GameManager):
    # ... use manager.hero, manager.dm, etc.
```

## Testing
The GameManager class makes testing easier:
```python
def test_game_initialization():
    manager = GameManager()
    manager.initialize_dm()
    assert manager.dm is not None
    
    player_data = {...}
    manager.initialize_player(player_data)
    assert manager.hero is not None
    assert manager.main_player_state is not None
```

## Status
✅ **Completed**: GameManager class created with initialization methods
✅ **Completed**: Legacy globals maintained for backward compatibility
⏳ **Future**: Migrate all functions to use GameManager parameter
⏳ **Future**: Remove legacy global variables

## Related Tasks
- Task 3.3: 전역 변수 정리 (Global variable cleanup)
- AC-008: 전역 변수 관리 문제 (Global variable management issue)
