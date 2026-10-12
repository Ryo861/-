"""Functional check executed INSIDE the frozen Windows EXE, without dialogs."""
import json
from pathlib import Path
from core.models import Finding
from core.pdf_io import inspect_pdf, export_pdf, read_pdf, render_page, fingerprint
from core.time_checker import validate_time
from tools.create_sample import create_samples


def run(output):
    root_dir = Path(output)
    root_dir.mkdir(parents=True, exist_ok=True)
    paths = create_samples(root_dir / 'originals')
    doc = inspect_pdf(paths[0], '匿名001')
    original_hash = fingerprint(doc.path)
    result = validate_time('7:55', '16:45', [('11:50', '12:35')])
    assert result.effective_minutes == 485 and result.result == 'pass'
    doc.time_validation = result
    doc.findings = [Finding(0, '「実習開始」と記入しよう。', (.25, .46), status='approved')]
    target = export_pdf(doc, root_dir / '添削済.pdf')
    reader = read_pdf(target)
    assert len(reader.pages) == 2
    assert '実習開始' in reader.pages[1].extract_text()
    assert fingerprint(doc.path) == original_hash
    for i in range(2):
        render_page(target, i).save(root_dir / f'page{i+1}.png')
    import tkinter as tk
    from gui.main_window import MainWindow
    from tkinter import font
    root = tk.Tk()
    try:
        app = MainWindow(root)
        app.load_files(paths)
        root.update()
        assert len(app.documents) == 2 and app.photo is not None
        family = font.nametofont('TkDefaultFont', root=root).actual('family')
        assert family in ('BIZ UDGothic', 'BIZ UDゴシック', 'Yu Gothic UI', 'Meiryo')
        app.position = (.25, .46)
        app.comment.insert('1.0', '教員による確認')
        app.approved.set(True)
        app.add_comment()
        assert app.current.findings[0].status == 'approved'
        app.saved_preview = target
        app.show_saved.set(True)
        app.toggle_saved()
        app.change_page(1)
        root.update()
        assert app.page_index == 1 and app.photo is not None
    finally:
        root.destroy()
    (root_dir / 'result.json').write_text(json.dumps({
        'passed': True, 'effective_minutes': 485, 'output_pages': 2,
        'gui_loaded_documents': 2, 'gui_font': family,
        'original_unchanged': True, 'frozen': __import__('sys').frozen,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
