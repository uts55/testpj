import os # Ensure os is imported for getenv

# Conditionally import tkinter and define BaseFrame
import tkinter as tk
from tkinter import scrolledtext
BaseFrame = tk.Frame

# Export module-level variables (defined after conditional blocks)
__all__ = ['GamePlayFrame', 'tk', 'scrolledtext', 'BaseFrame']

class GamePlayFrame(BaseFrame):
    def __init__(self, master=None, process_input_callback=None, 
                 save_game_callback=None, load_game_callback=None, exit_callback=None):

        if master is None:
            raise ValueError("Tkinter master window must be provided.")
        super().__init__(master) # Call tk.Frame.__init__
        self.master = master
        self.master.title("Text Adventure RPG")
        self.pack(fill=tk.BOTH, expand=True)

        # Common initializations
        self.process_input_callback = process_input_callback
        self.save_game_callback = save_game_callback
        self.load_game_callback = load_game_callback
        self.exit_callback = exit_callback
        self.choice_buttons = []

        self.create_widgets()

    def create_widgets(self):
        # Theme Colors
        bg_color = "#2b2b2b"
        fg_color = "#dcdcdc"
        accent_color = "#4a4a4a"
        text_bg = "#1e1e1e"
        entry_bg = "#3c3f41"
        button_bg = "#444444"
        button_fg = "#ffffff"

        self.configure(bg=bg_color)

        # Narration Text Area
        self.narration_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state='disabled',
                                                        bg=text_bg, fg=fg_color, insertbackground='white',
                                                        font=("Consolas", 10))
        self.narration_area.pack(padx=10, pady=(10,5), fill=tk.BOTH, expand=True)

        # Dialogue Choices Frame (initially empty)
        self.dialogue_choices_frame = tk.Frame(self, bg=bg_color)
        self.dialogue_choices_frame.pack(padx=10, pady=2, fill=tk.X) 
        self.choice_buttons = []

        # Input Entry
        self.placeholder_text = "Enter command..."
        self.placeholder_color = "#888888"
        self.entry_fg_color = "#ffffff"

        self.input_entry = tk.Entry(self, bg=entry_bg, fg=self.placeholder_color, insertbackground='white', font=("Segoe UI", 10))
        self.input_entry.insert(0, self.placeholder_text)
        self.input_entry.pack(padx=10, pady=5, fill=tk.X)
        self.input_entry.bind("<Return>", lambda event: self.handle_send_button())
        self.input_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.input_entry.bind("<FocusOut>", self.on_entry_focus_out)

        # Send Button
        self.send_button = tk.Button(self, text="Send", command=self.handle_send_button, 
                                     bg=button_bg, fg=button_fg, activebackground=accent_color, activeforeground=button_fg, relief=tk.FLAT)
        self.send_button.pack(padx=10, pady=5)

        # Game State Frame
        self.state_frame = tk.Frame(self, borderwidth=1, relief="solid", bg=accent_color)
        self.state_frame.pack(padx=10, pady=5, fill=tk.X)

        # Status Labels Style
        label_style = {"bg": accent_color, "fg": "#ffffff", "font": ("Segoe UI", 9, "bold")}

        # HP Label
        self.hp_label = tk.Label(self.state_frame, text="HP: [HP]", **label_style)
        self.hp_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Location Label
        self.location_label = tk.Label(self.state_frame, text="Location: [Location]", **label_style)
        self.location_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Inventory Label
        self.inventory_label = tk.Label(self.state_frame, text="Inventory: [Inventory]", **label_style)
        self.inventory_label.pack(side=tk.LEFT, padx=10, pady=5)

        # NPCs Label
        self.npcs_label = tk.Label(self.state_frame, text="NPCs: [NPCs]", **label_style)
        self.npcs_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Action Buttons Frame
        self.actions_frame = tk.Frame(self, bg=bg_color)
        self.actions_frame.pack(padx=10, pady=5, fill=tk.X)

        # Save Game Button
        self.save_button = tk.Button(self.actions_frame, text="Save Game", command=self.save_game_callback,
                                     bg=button_bg, fg=button_fg, activebackground=accent_color, activeforeground=button_fg, relief=tk.FLAT)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Load Game Button
        self.load_button = tk.Button(self.actions_frame, text="Load Game", command=self.load_game_callback,
                                     bg=button_bg, fg=button_fg, activebackground=accent_color, activeforeground=button_fg, relief=tk.FLAT)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Exit Button
        self.exit_button = tk.Button(self.actions_frame, text="Exit", command=self.exit_callback,
                                     bg="#800000", fg="#ffffff", activebackground="#a00000", activeforeground="#ffffff", relief=tk.FLAT)
        self.exit_button.pack(side=tk.LEFT, padx=5, pady=5)

    def on_entry_focus_in(self, event):
        if self.input_entry.get() == self.placeholder_text:
            self.input_entry.delete(0, tk.END)
            self.input_entry.config(fg=self.entry_fg_color)

    def on_entry_focus_out(self, event):
        if not self.input_entry.get():
            self.input_entry.insert(0, self.placeholder_text)
            self.input_entry.config(fg=self.placeholder_color)

    def handle_send_button(self):
        input_text = self.input_entry.get()
        if input_text and input_text != self.placeholder_text:
            self.add_narration(f"> {input_text}")
            self.input_entry.delete(0, tk.END)
            self.input_entry.focus_set() # Restore focus to entry
            if self.process_input_callback:
                self.process_input_callback(input_text)
            else:
                self.add_narration(f"UI Echo (no callback): {input_text}")

    def disable_input(self):
        if hasattr(self, 'input_entry'):
            self.input_entry.config(state=tk.DISABLED)
        if hasattr(self, 'send_button'):
            self.send_button.config(state=tk.DISABLED)

    def enable_input(self):
        if hasattr(self, 'input_entry'):
            self.input_entry.config(state=tk.NORMAL)
        if hasattr(self, 'send_button'):
            self.send_button.config(state=tk.NORMAL)
        if hasattr(self, 'input_entry'): 
            self.input_entry.focus_set()

    def display_dialogue(self, npc_name: str, npc_text: str, player_choices: list[dict]):
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
        self.narration_area.config(state='normal')
        self.narration_area.insert(tk.END, message + '\n')
        self.narration_area.see(tk.END)
        self.narration_area.config(state='disabled')

    def update_hp(self, hp_value):
        self.hp_label.config(text=f"HP: {hp_value}")

    def update_location(self, location_name):
        self.location_label.config(text=f"Location: {location_name}")

    def update_inventory(self, inventory_string):
        self.inventory_label.config(text=f"Inventory: {inventory_string}")

    def update_npcs(self, npc_string):
        self.npcs_label.config(text=f"NPCs: {npc_string}")

    def is_destroyed(self):
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
