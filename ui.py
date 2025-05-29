import tkinter as tk
from tkinter import scrolledtext

class Application(tk.Frame):
    def __init__(self, master=None, process_input_callback=None, 
                 save_game_callback=None, load_game_callback=None, exit_callback=None):
        super().__init__(master)
        self.master = master
        self.master.title("Text Adventure RPG")
        self.pack(fill=tk.BOTH, expand=True)
        self.process_input_callback = process_input_callback
        self.save_game_callback = save_game_callback
        self.load_game_callback = load_game_callback
        self.exit_callback = exit_callback
        self.create_widgets()

    def create_widgets(self):
        # Narration Text Area
        self.narration_area = scrolledtext.ScrolledText(self, wrap=tk.WORD, state='disabled')
        # Added more padding (pady top) for narration_area
        self.narration_area.pack(padx=10, pady=(10,5), fill=tk.BOTH, expand=True) 
        # Initial welcome message moved to add_narration for consistent handling
        # self.add_narration("Welcome to the Text Adventure RPG!") # Done in main.py or by first DM message

        # Input Entry
        self.input_entry = tk.Entry(self)
        self.input_entry.pack(padx=10, pady=5, fill=tk.X)

        # Send Button
        self.send_button = tk.Button(self, text="Send", command=self.handle_send_button)
        self.send_button.pack(padx=10, pady=5) # pady uniform

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
        input_text = self.input_entry.get()
        if input_text:
            # Display player's input in narration area using the refined add_narration method
            self.add_narration(f"> {input_text}") # add_narration handles newline
            
            # Clear the input entry
            self.input_entry.delete(0, tk.END)

            # Call the callback function from main.py to process the input
            if self.process_input_callback:
                self.process_input_callback(input_text)
            else:
                # Fallback if no callback is provided (e.g., when running ui.py directly)
                self.add_narration(f"UI Echo (no callback): {input_text}")

    # Method to add text to the narration area from outside (e.g., from main.py)
    def add_narration(self, message: str): # Added type hint for clarity
        self.narration_area.config(state='normal')
        self.narration_area.insert(tk.END, message + '\n') # Ensure newline is added
        self.narration_area.see(tk.END)
        self.narration_area.config(state='disabled')

    def update_hp(self, hp_value):
        self.hp_label.config(text=f"HP: {hp_value}")

    def update_location(self, location_name):
        self.location_label.config(text=f"Location: {location_name}")

    def update_inventory(self, inventory_string): # Expects a pre-formatted string
        self.inventory_label.config(text=f"Inventory: {inventory_string}")

    def update_npcs(self, npc_string): # Expects a pre-formatted string
        self.npcs_label.config(text=f"NPCs: {npc_string}")

if __name__ == "__main__":
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

    app = Application(master=root, 
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
