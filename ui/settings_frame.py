import tkinter as tk
from tkinter import ttk # Or just tk

class SettingsFrame(tk.Frame):
    def __init__(self, master, back_to_main_menu_callback):
        super().__init__(master)
        self.master = master
        self.back_to_main_menu_callback = back_to_main_menu_callback

        self.create_widgets()

    def create_widgets(self):
        # Title Label
        title_label = tk.Label(self, text="설정", font=("Arial", 24))
        title_label.pack(pady=20)

        # Under Construction Label
        construction_label = tk.Label(self, text="준비 중", font=("Arial", 16))
        construction_label.pack(pady=40)

        # Back to Main Menu Button
        back_button = tk.Button(self, text="메인 메뉴로 돌아가기", command=self.back_to_main_menu_callback)
        back_button.pack(pady=10)

if __name__ == '__main__':
    # Example usage for testing the frame directly
    root = tk.Tk()
    root.title("Settings Menu Test")
    root.geometry("400x300")

    def test_back_to_main():
        print("Back to Main Menu clicked")
        # In a real app, this would hide SettingsFrame and show MainMenuFrame
        # For this test, we can just close the window or print a message
        root.destroy() # Or print a message

    settings_menu = SettingsFrame(root, test_back_to_main)
    settings_menu.pack(expand=True, fill=tk.BOTH)
    root.mainloop()
