"""Desktop entry point. Normal operation has no network or AI client."""
import sys


def main():
    from gui.fonts import prepare_fonts
    prepare_fonts()
    if '--self-test' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--self-test', action='store_true')
        parser.add_argument('--output', required=True)
        args = parser.parse_args()
        try:
            from tools.portable_smoke import run
            run(args.output)
        except Exception as exc:
            from pathlib import Path
            import traceback
            path = Path(args.output)
            path.mkdir(parents=True, exist_ok=True)
            (path / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise SystemExit(1) from exc
        return
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    try:
        from gui.main_window import MainWindow
        MainWindow(root)
    except Exception as exc:
        root.withdraw()
        guidance = ('ZIPをすべて展開し、_internalフォルダーを含めたまま起動してください。'
                    if getattr(sys, 'frozen', False) else 'setup_windows.batを実行し直してください。')
        messagebox.showerror('起動できません', f'必要なファイル・ライブラリを確認してください（{type(exc).__name__}）。\n{guidance}')
        root.destroy()
        raise
    root.mainloop()


if __name__ == '__main__':
    main()
