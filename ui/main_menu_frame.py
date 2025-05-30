import tkinter as tk
from tkinter import ttk # Or just tk

class MainMenuFrame(tk.Frame):
    def __init__(self, master, new_game_callback, load_game_callback, open_settings_callback, exit_game_callback):
        super().__init__(master)
        self.master = master
        self.new_game_callback = new_game_callback
        self.load_game_callback = load_game_callback
        self.open_settings_callback = open_settings_callback
        self.exit_game_callback = exit_game_callback

        self.create_widgets()

    def create_widgets(self):
        # Game Title Label
        title_label = tk.Label(self, text="텍스트 어드벤처 RPG", font=("Arial", 24))
        title_label.pack(pady=20)

        # New Game Button
        new_game_button = tk.Button(self, text="새 게임", command=self.new_game_callback)
        new_game_button.pack(pady=5, fill=tk.X, padx=50)

        # Load Game Button
        load_game_button = tk.Button(self, text="저장된 게임 불러오기", command=self.load_game_callback)
        load_game_button.pack(pady=5, fill=tk.X, padx=50)

        # Settings Button
        settings_button = tk.Button(self, text="설정", command=self.open_settings_callback)
        settings_button.pack(pady=5, fill=tk.X, padx=50)

        # Exit Button
        exit_button = tk.Button(self, text="나가기", command=self.exit_game_callback)
        exit_button.pack(pady=5, fill=tk.X, padx=50)

if __name__ == '__main__':
    # Example usage for testing the frame directly
    root = tk.Tk()
    root.title("Main Menu Test")
    root.geometry("400x300")

    def test_new_game():
        print("New Game clicked")

    def test_load_game():
        print("Load Game clicked")

    def test_open_settings():
        print("Settings clicked")

    def test_exit_game():
        print("Exit clicked")
        root.destroy()

    main_menu = MainMenuFrame(root, test_new_game, test_load_game, test_open_settings, test_exit_game)
    main_menu.pack(expand=True, fill=tk.BOTH)
    root.mainloop()
