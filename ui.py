import os # Ensure os is imported for getenv

# Conditionally import tkinter and define BaseFrame
is_test_mode_for_ui = (os.getenv("RUNNING_INTERACTIVE_TEST") == "true")
if not is_test_mode_for_ui:
    import tkinter as tk
    from tkinter import scrolledtext
    BaseFrame = tk.Frame
else:
    BaseFrame = object # Inherit from object in test mode

class GamePlayFrame(BaseFrame):
    def __init__(self, master=None, process_input_callback=None, 
                 save_game_callback=None, load_game_callback=None, exit_callback=None):

        self.is_test_mode = is_test_mode_for_ui # Use the globally checked flag

        if not self.is_test_mode:
            if master is None:
                raise ValueError("Tkinter master window must be provided when not in GUI mode.")
            super().__init__(master) # Call tk.Frame.__init__
            self.master = master
            self.master.title("Text Adventure RPG")
            self.pack(fill=tk.BOTH, expand=True)
        else: # Test mode
            self.master = None # No actual master window in test mode
            # super() for object doesn't need arguments and is implicitly called.
            print("UI_LOG: GamePlayFrame initialized in TEST MODE (inherits from object).")

        # Common initializations for both modes
        self.process_input_callback = process_input_callback
        self.save_game_callback = save_game_callback
        self.load_game_callback = load_game_callback
        self.exit_callback = exit_callback
        self.choice_buttons = [] # Initialize for both modes

        if not self.is_test_mode:
            self.create_widgets()
        else:
            # In test mode, create_widgets is not called, but attributes might be expected.
            # For instance, if other methods assume self.hp_label exists, they would fail.
            # However, our test mode methods print to console, so they don't rely on tk widgets.
            pass


    def create_widgets(self):
        # This entire method relies on Tkinter, skip if in test mode or no master
        if self.is_test_mode or not self.master:
            print("UI_LOG: Skipping widget creation in test mode or no master.")
            return

        # Narration Text Area
        self.narration_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state='disabled')
        self.narration_area.pack(padx=10, pady=(10,5), fill=tk.BOTH, expand=True)

        # Dialogue Choices Frame (initially empty)
        self.dialogue_choices_frame = tk.Frame(self)
        self.dialogue_choices_frame.pack(padx=10, pady=2, fill=tk.X) # Less pady than input_entry
        self.choice_buttons = []

        # Input Entry
        self.input_entry = tk.Entry(self)
        self.input_entry.pack(padx=10, pady=5, fill=tk.X)

        # Send Button
        self.send_button = tk.Button(self, text="Send", command=self.handle_send_button)
        self.send_button.pack(padx=10, pady=5)

        # Game State Frame
        self.state_frame = tk.Frame(self, borderwidth=2, relief="groove")
        self.state_frame.pack(padx=10, pady=5, fill=tk.X) # pady uniform

        # HP Label
        self.hp_label = tk.Label(self.state_frame, text="HP: [HP]")
        self.hp_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Location Label
        self.location_label = tk.Label(self.state_frame, text="Location: [Location]")
        self.location_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Inventory Label
        self.inventory_label = tk.Label(self.state_frame, text="Inventory: [Inventory]")
        self.inventory_label.pack(side=tk.LEFT, padx=5, pady=5)

        # NPCs Label
        self.npcs_label = tk.Label(self.state_frame, text="NPCs: [NPCs]")
        self.npcs_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Action Buttons Frame
        self.actions_frame = tk.Frame(self)
        self.actions_frame.pack(padx=10, pady=5, fill=tk.X) # pady uniform

        # Save Game Button
        self.save_button = tk.Button(self.actions_frame, text="Save Game", command=self.save_game_callback)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5) # Added pady here
        
        # Load Game Button
        self.load_button = tk.Button(self.actions_frame, text="Load Game", command=self.load_game_callback)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5) # Added pady here

        # Exit Button
        self.exit_button = tk.Button(self.actions_frame, text="Exit", command=self.exit_callback)
        self.exit_button.pack(side=tk.LEFT, padx=5, pady=5) # Added pady here

    def handle_send_button(self):
        if self.is_test_mode:
            print("UI_LOG: handle_send_button called in TEST MODE. Input should be simulated via process_input_callback directly.")
            return
        input_text = self.input_entry.get()
        if input_text:
            self.add_narration(f"> {input_text}")
            self.input_entry.delete(0, tk.END)
            if self.process_input_callback:
                self.process_input_callback(input_text)
            else:
                self.add_narration(f"UI Echo (no callback): {input_text}")

    def disable_input(self):
        if self.is_test_mode:
            print("UI_LOG: disable_input called in TEST MODE.")
            return
        if hasattr(self, 'input_entry'):
            self.input_entry.config(state=tk.DISABLED)
        if hasattr(self, 'send_button'):
            self.send_button.config(state=tk.DISABLED)

    def enable_input(self):
        if self.is_test_mode:
            print("UI_LOG: enable_input called in TEST MODE.")
            return
        if hasattr(self, 'input_entry'):
            self.input_entry.config(state=tk.NORMAL)
        if hasattr(self, 'send_button'):
            self.send_button.config(state=tk.NORMAL)
        if hasattr(self, 'input_entry'): # Check again before focus
            self.input_entry.focus_set()

    def display_dialogue(self, npc_name: str, npc_text: str, player_choices: list[dict]):
        if self.is_test_mode:
            print(f"UI_LOG (display_dialogue): {npc_name}: {npc_text}")
            if player_choices:
                for i, choice_data in enumerate(player_choices):
                    print(f"  CHOICE {i+1}: {choice_data.get('text')}")
            else:
                print("  (No player choices)")
            return

        for button in self.choice_buttons:
            button.destroy()
        self.choice_buttons.clear()

        self.add_narration(f"{npc_name}: {npc_text}")

        if player_choices:
            self.disable_input()
            for i, choice_data in enumerate(player_choices):
                choice_text = choice_data.get("text", f"Choice {i+1}")
                button = tk.Button(self.dialogue_choices_frame, text=choice_text,
                                   command=lambda idx=str(i+1): self.process_input_callback(idx))
                button.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
                self.choice_buttons.append(button)
        else:
            self.enable_input()


    def add_narration(self, message: str):
        if self.is_test_mode:
            print(f"UI_NARRATION: {message}")
            return
        self.narration_area.config(state='normal')
        self.narration_area.insert(tk.END, message + '\n')
        self.narration_area.see(tk.END)
        self.narration_area.config(state='disabled')

    def update_hp(self, hp_value):
        if self.is_test_mode:
            print(f"UI_LOG (update_hp): HP: {hp_value}")
            return
        self.hp_label.config(text=f"HP: {hp_value}")

    def update_location(self, location_name):
        if self.is_test_mode:
            print(f"UI_LOG (update_location): Location: {location_name}")
            return
        self.location_label.config(text=f"Location: {location_name}")

    def update_inventory(self, inventory_string):
        if self.is_test_mode:
            print(f"UI_LOG (update_inventory): Inventory: {inventory_string}")
            return
        self.inventory_label.config(text=f"Inventory: {inventory_string}")

    def update_npcs(self, npc_string):
        if self.is_test_mode:
            print(f"UI_LOG (update_npcs): NPCs: {npc_string}")
            return
        self.npcs_label.config(text=f"NPCs: {npc_string}")

    def is_destroyed(self):
        if self.is_test_mode:
            # In test mode, the app is never truly "destroyed" in a Tkinter sense
            # unless we explicitly manage a state for it. Assume not destroyed unless
            # a 'quit' command in the test harness sets a flag or similar.
            # For now, let's assume it's not destroyed until a 'quit' type command is processed.
            return getattr(self, '_test_destroyed_flag', False)
        # For actual Tkinter mode
        if not self.master: return True # No master window
        try:
            return not bool(self.master.winfo_exists())
        except tk.TclError:
            return True
        except AttributeError:
            return True

if __name__ == "__main__":
    # This direct execution block will run with Tkinter as is_test_mode will be False
    # (unless RUNNING_INTERACTIVE_TEST is set in the environment when running ui.py directly)
    import os # Ensure os is imported for getenv
    if os.getenv("RUNNING_INTERACTIVE_TEST") == "true":
        print("Running ui.py in TEST MODE (no Tkinter window will be created from __main__ block).")
        # Optionally, could run some test functions here that don't require Tkinter master
        # For example, create a dummy GamePlayFrame for console logging:
        # test_app_console = GamePlayFrame(master=None) # master=None implies test mode or needs a check
        # test_app_console.add_narration("Console narration test from ui.py direct test mode.")
        # test_app_console.display_dialogue("TestNPC", "Hello from console test.", [{"text": "Option 1"}])

    else:
        print("Running ui.py in normal Tkinter mode for direct testing.")
        root = tk.Tk()
    # Example of running ui.py directly with a dummy callback
    def dummy_process_input(text):
        print(f"Dummy process_input_callback received: {text}")
        app.add_narration(f"DM (dummy): You said '{text}'\n")
    
    def dummy_save():
        print("Dummy save_game_callback called")
        app.add_narration("Game Saved (Dummy).\n")

    def dummy_load():
        print("Dummy load_game_callback called")
        app.add_narration("Game Loaded (Dummy).\n")
        app.update_hp("HP from Dummy Load")
        app.update_location("Dummy Loaded Location")
        app.update_inventory("Dummy Loaded Inventory")
        app.update_npcs("Dummy Loaded NPCs")

    def dummy_exit():
        print("Dummy exit_callback called")
        app.add_narration("Exiting (Dummy).\n")
        if app.master:
            app.master.destroy()

    app = GamePlayFrame(master=root, 
                      process_input_callback=dummy_process_input,
                      save_game_callback=dummy_save,
                      load_game_callback=dummy_load,
                      exit_callback=dummy_exit)
    app.add_narration("This is ui.py running directly with dummy action callbacks.\n")
    app.update_hp("[HP]") # Initial placeholder values
    app.update_location("[Location]")
    app.update_inventory("[Inventory]")
    app.update_npcs("[NPCs]")
    app.mainloop()
