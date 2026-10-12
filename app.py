"""Windows development entry point. No network client or AI is used."""
from gui.fonts import prepare_fonts
prepare_fonts()

import tkinter as tk
from tkinter import messagebox


def main():
    root = tk.Tk()
    try:
        from gui.main_window import MainWindow
        MainWindow(root)
    except Exception as exc:
        root.withdraw()
        messagebox.showerror('起動できません', f'必要なファイル・ライブラリを確認してください（{type(exc).__name__}）。\nsetup_windows.batを実行し直してください。')
        root.destroy()
        raise
    root.mainloop()


if __name__ == '__main__':
    main()
