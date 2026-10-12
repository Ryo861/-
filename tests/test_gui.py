import tempfile
from gui.fonts import prepare_fonts
prepare_fonts()
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from gui.main_window import MainWindow
from tools.create_sample import create_samples
from core.pdf_io import read_pdf


class GuiTests(unittest.TestCase):
    def setUp(self):
        from gui.fonts import prepare_fonts
        prepare_fonts()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest('ディスプレイが必要。Windows実機またはxvfb-runで実行してください。')
        self.temp = tempfile.TemporaryDirectory()
        self.app = MainWindow(self.root)
        self.paths = create_samples(Path(self.temp.name) / 'input')
        self.app.load_files(self.paths)
        self.root.update()

    def tearDown(self):
        if hasattr(self, 'temp'):
            self.root.destroy()
            self.temp.cleanup()

    def test_gui_load_edit_time_save_and_preview(self):
        app = self.app
        self.assertEqual(len(app.documents), 2)
        self.assertIsNotNone(app.photo)
        for entry, value in zip(app.time_entries, ['7:55', '16:45', '11:50', '12:35']):
            entry.insert(0, value)
        app.calculate_time()
        self.assertEqual(app.current.time_validation.effective_minutes, 485)
        app.pick_position(SimpleNamespace(x=200,y=300))
        app.comment.insert('1.0','文末を「だ・である」調に統一しよう。')
        app.approved.set(True)
        app.add_comment()
        self.assertEqual(app.current.findings[0].status,'approved')
        app.findings_list.selection_set(0)
        app.select_finding()
        app.comment.delete('1.0','end')
        app.comment.insert('1.0','編集済みコメント')
        app.update_comment()
        self.assertEqual(app.current.findings[0].comment,'編集済みコメント')
        target = Path(self.temp.name) / 'saved.pdf'
        with patch('gui.main_window.messagebox.askyesno', return_value=True), patch(
            'gui.main_window.filedialog.asksaveasfilename', return_value=str(target)):
            app.save_current()
        self.assertTrue(target.exists())
        self.assertEqual(len(read_pdf(target).pages),2)
        self.assertTrue(app.show_saved.get())
        app.change_page(1)
        self.assertEqual(app.page_index,1)
        self.assertIsNotNone(app.photo)
        self.root.update()
        app.show_saved.set(False)
        app.toggle_saved()
        app.time_entries[1].delete(0,'end')
        app.time_entries[1].insert(0,'16:00')
        app.store_times()
        self.assertIsNone(app.current.time_validation)

    def test_batch_gui(self):
        output = Path(self.temp.name) / 'output'
        output.mkdir()
        with patch('gui.main_window.messagebox.askyesno', return_value=True), patch(
            'gui.main_window.messagebox.showinfo'), patch(
            'gui.main_window.filedialog.askdirectory', return_value=str(output)):
            self.app.save_all()
        self.assertEqual(len(list(output.glob('*.pdf'))),2)
