import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from datetime import date
from PIL import ImageTk

from core.models import Finding
from core.pdf_io import inspect_pdf, render_page, export_pdf, safe_filename
from core.time_checker import validate_time


class MainWindow:
    def __init__(self, root):
        from gui.fonts import configure_tk_fonts
        configure_tk_fonts(root)
        self.root = root
        root.title('介護実習記録チェッカー — フェーズA（AIなし・ローカル処理）')
        root.geometry('1280x850')
        root.minsize(1000, 650)
        self.documents = []
        self.current = None
        self.page_index = 0
        self.zoom = 1.0
        self.position = None
        self.selected_finding = None
        self.photo = None
        self.next_id = 1
        self.saved_preview = None
        self.status = tk.StringVar(value='PDFを追加してください。自動認識・外部送信は行いません。')
        self.page_label = tk.StringVar(value='原本')
        self.time_result = tk.StringVar(value='未判定（時刻を手入力してください）')
        self.position_label = tk.StringVar(value='位置不明：コメント一覧にだけ出力します')
        self.no_break = tk.BooleanVar()
        self.approved = tk.BooleanVar()
        self.preview_marks = tk.BooleanVar(value=True)
        self.show_saved = tk.BooleanVar()
        self.time_entries = []
        self._build()
        root.protocol('WM_DELETE_WINDOW', self.close)

    def _build(self):
        bar = ttk.Frame(self.root, padding=8)
        bar.pack(fill='x')
        ttk.Button(bar, text='① PDFを追加（複数可）', command=self.add_files).pack(side='left')
        ttk.Button(bar, text='練習用PDFを作成', command=self.make_sample).pack(side='left', padx=6)
        ttk.Label(bar, text='フェーズA：OCR・AIなし／通信なし／原本を保持').pack(side='left', padx=12)
        ttk.Button(bar, text='操作方法', command=self.help).pack(side='right')
        panes = ttk.Panedwindow(self.root, orient='horizontal')
        panes.pack(fill='both', expand=True, padx=8)
        left = ttk.Frame(panes, width=200, padding=5)
        center = ttk.Frame(panes, padding=5)
        right_holder = ttk.Frame(panes, width=370)
        form_canvas = tk.Canvas(right_holder, width=370, highlightthickness=0)
        form_scroll = ttk.Scrollbar(right_holder, orient='vertical', command=form_canvas.yview)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        form_canvas.pack(side='left', fill='both', expand=True)
        form_scroll.pack(side='right', fill='y')
        right = ttk.Frame(form_canvas, padding=5)
        form_window = form_canvas.create_window(0, 0, anchor='nw', window=right)
        right.bind('<Configure>', lambda e: form_canvas.configure(scrollregion=form_canvas.bbox('all')))
        form_canvas.bind('<Configure>', lambda e: form_canvas.itemconfigure(form_window, width=e.width))
        panes.add(left, weight=1)
        panes.add(center, weight=4)
        panes.add(right_holder, weight=2)
        ttk.Label(left, text='入力ファイル（1PDF＝1生徒）').pack(anchor='w')
        self.files = tk.Listbox(left, width=26, exportselection=False)
        self.files.pack(fill='both', expand=True, pady=5)
        self.files.bind('<<ListboxSelect>>', self.select_file)
        file_scroll = ttk.Scrollbar(left, orient='horizontal', command=self.files.xview)
        self.files.configure(xscrollcommand=file_scroll.set)
        file_scroll.pack(fill='x')
        ttk.Button(left, text='一覧から外す', command=self.remove_file).pack(fill='x')
        ttk.Label(left, text='複数ページは同一生徒か確認。\n自動分割・氏名推定はしません。', wraplength=190).pack(pady=8)
        toolbar = ttk.Frame(center)
        toolbar.pack(fill='x')
        ttk.Button(toolbar, text='◀', width=3, command=lambda: self.change_page(-1)).pack(side='left')
        ttk.Button(toolbar, text='▶', width=3, command=lambda: self.change_page(1)).pack(side='left')
        ttk.Label(toolbar, textvariable=self.page_label).pack(side='left', padx=6)
        ttk.Button(toolbar, text='−', width=3, command=lambda: self.change_zoom(-0.25)).pack(side='right')
        ttk.Button(toolbar, text='＋', width=3, command=lambda: self.change_zoom(0.25)).pack(side='right')
        ttk.Checkbutton(center, text='赤い番号を表示', variable=self.preview_marks, command=self.render).pack(anchor='w')
        ttk.Checkbutton(center, text='保存済PDFを確認（この表示中は位置指定不可）', variable=self.show_saved,
                        command=self.toggle_saved).pack(anchor='w')
        holder = ttk.Frame(center)
        holder.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(holder, background='#e5e7eb', highlightthickness=0)
        vs = ttk.Scrollbar(holder, orient='vertical', command=self.canvas.yview)
        hs = ttk.Scrollbar(holder, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        vs.grid(row=0, column=1, sticky='ns')
        hs.grid(row=1, column=0, sticky='ew')
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self.canvas.bind('<Button-1>', self.pick_position)
        ttk.Label(center, text='原本の指摘位置をクリック → 右でコメント入力・承認', wraplength=550).pack(anchor='w')
        ttk.Label(right, text='② 実習時間（24時間制 H:MM）').pack(anchor='w')
        times = ttk.Frame(right)
        times.pack(fill='x')
        for i, name in enumerate(['開始', '終了', '休憩開始', '休憩終了']):
            ttk.Label(times, text=name).grid(row=i//2*2, column=i%2, sticky='w', padx=4)
            e = ttk.Entry(times, width=15)
            e.grid(row=i//2*2+1, column=i%2, padx=4, pady=2)
            self.time_entries.append(e)
        ttk.Checkbutton(right, text='休憩なしを教員が確認した', variable=self.no_break).pack(anchor='w')
        ttk.Label(right, text='追加休憩（例 14:00-14:10;15:00-15:05）').pack(anchor='w')
        self.extra_breaks = ttk.Entry(right)
        self.extra_breaks.pack(fill='x')
        ttk.Button(right, text='実習時間を計算', command=self.calculate_time).pack(fill='x', pady=4)
        ttk.Label(right, textvariable=self.time_result, wraplength=345).pack(anchor='w')
        ttk.Separator(right).pack(fill='x', pady=8)
        ttk.Label(right, text='③ コメント（追加後に承認）').pack(anchor='w')
        self.findings_list = tk.Listbox(right, height=5, exportselection=False)
        self.findings_list.pack(fill='x')
        self.findings_list.bind('<<ListboxSelect>>', self.select_finding)
        ttk.Label(right, textvariable=self.position_label, wraplength=345).pack(anchor='w')
        ttk.Button(right, text='位置を外す／位置不明にする', command=self.clear_position).pack(fill='x')
        self.comment = tk.Text(right, height=4, wrap='word')
        self.comment.pack(fill='x', pady=3)
        ttk.Checkbutton(right, text='このコメントを教員が承認', variable=self.approved).pack(anchor='w')
        actions = ttk.Frame(right)
        actions.pack(fill='x')
        ttk.Button(actions, text='新規追加', command=self.add_comment).pack(side='left')
        ttk.Button(actions, text='選択を更新', command=self.update_comment).pack(side='left', padx=4)
        ttk.Button(actions, text='削除', command=self.delete_comment).pack(side='left')
        ttk.Label(right, text='未承認コメントはPDFに出力しません。\n位置不明のコメントは末尾一覧のみ。', wraplength=345).pack(anchor='w', pady=5)
        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(fill='x')
        ttk.Button(bottom, text='④ 選択した生徒を承認してPDF保存', command=self.save_current).pack(side='left')
        ttk.Button(bottom, text='全員を確認して個別PDFを一括保存', command=self.save_all).pack(side='left', padx=8)
        ttk.Button(bottom, text='匿名ID／表示名を変更', command=self.rename).pack(side='right')
        ttk.Label(self.root, textvariable=self.status, padding=8, wraplength=1200).pack(fill='x')

    def error(self, exc):
        # Do not expose library error messages that may include document content.
        text = str(exc) if isinstance(exc, (ValueError, FileExistsError)) else f'処理できませんでした（{type(exc).__name__}）。読めるPDFか、保存先の権限を確認してください。'
        if isinstance(exc, FileExistsError):
            text = '同名の出力が既にあります。別の保存先・名前を選んでください。'
        messagebox.showerror('処理を確認してください', text, parent=self.root)
        self.status.set('処理失敗：原本は変更していません。対象を選んで再実行できます。')

    def add_files(self):
        paths = filedialog.askopenfilenames(title='実習記録PDFを選択', filetypes=[('PDF', '*.pdf')])
        self.load_files(paths)

    def load_files(self, paths):
        failures = []
        for path in paths:
            if any(d.path == Path(path).resolve() for d in self.documents):
                continue
            try:
                document = inspect_pdf(path, f'匿名{self.next_id:03d}')
                self.next_id += 1
                self.documents.append(document)
            except Exception as exc:
                failures.append(f'{Path(path).name}：読込不可（{type(exc).__name__}）')
        self.refresh_files()
        if self.documents and self.current is None:
            self.files.selection_set(0)
            self.select_file()
        self.status.set(f'{len(self.documents)}件を読み込みました。原本を確認し、時刻とコメントを入力してください。')
        if failures:
            messagebox.showwarning('一部のPDFを読み込めません', '\n'.join(failures), parent=self.root)

    def refresh_files(self):
        self.files.delete(0, 'end')
        for d in self.documents:
            self.files.insert('end', f'{d.anonymized_student_id}・{d.page_count}頁・{d.status}\n{d.path.name}')
        if self.current in self.documents:
            self.files.selection_set(self.documents.index(self.current))

    def store_times(self):
        if self.current:
            new = [e.get() for e in self.time_entries]
            extra = self.extra_breaks.get()
            changed = (new != self.current.time_inputs or extra != getattr(self.current, 'extra_breaks', '')
                       or self.no_break.get() != getattr(self.current, 'no_break', False))
            self.current.time_inputs = new
            self.current.extra_breaks = extra
            self.current.no_break = self.no_break.get()
            if changed:
                self.current.time_validation = None

    def select_file(self, event=None):
        selection = self.files.curselection()
        if not selection:
            return
        self.store_times()
        self.current = self.documents[selection[0]]
        self.page_index = 0
        self.show_saved.set(False)
        self.saved_preview = getattr(self.current, 'saved_path', None)
        for e, value in zip(self.time_entries, self.current.time_inputs):
            e.delete(0, 'end')
            e.insert(0, value)
        self.no_break.set(getattr(self.current, 'no_break', False))
        self.extra_breaks.delete(0, 'end')
        self.extra_breaks.insert(0, getattr(self.current, 'extra_breaks', ''))
        self.show_time()
        self.reset_editor()
        self.refresh_findings()
        self.render()
        if self.current.page_count > 1:
            self.status.set('複数ページPDFです。全ページを確認してください。保存時に同一生徒か確認します。')

    def remove_file(self):
        if not self.current:
            return
        if not messagebox.askyesno('一覧から外す', 'このPDFの未保存コメントを破棄して一覧から外しますか？原本は削除しません。'):
            return
        self.documents.remove(self.current)
        self.current = None
        self.refresh_files()
        self.canvas.delete('all')
        self.reset_editor()
        self.refresh_findings()
        if self.documents:
            self.files.selection_set(0)
            self.select_file()

    def render(self):
        if not self.current:
            return
        path = self.saved_preview if self.show_saved.get() else self.current.path
        if not path:
            return
        try:
            image = render_page(path, self.page_index, self.zoom)
            self.image_size = image.size
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor='nw', image=self.photo)
            self.canvas.configure(scrollregion=(0, 0, *image.size))
            if self.preview_marks.get() and not self.show_saved.get():
                approved_number = 0
                for f in self.current.findings:
                    if f.status == 'approved':
                        approved_number += 1
                    if f.page_index == self.page_index and f.position:
                        x, y = f.position[0]*image.width, f.position[1]*image.height
                        r = max(5, 10*self.zoom)
                        x = max(r+2, min(image.width-r-2, x))
                        y = max(r+2, min(image.height-r-2, y))
                        color = '#c00000' if f.status == 'approved' else '#b06a00'
                        self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, width=2)
                        self.canvas.create_text(x, y, text=str(approved_number) if f.status == 'approved' else '?', fill=color)
            if self.position and not self.show_saved.get():
                x, y = self.position[0]*image.width, self.position[1]*image.height
                self.canvas.create_line(x-8, y, x+8, y, fill='#0066cc', width=2)
                self.canvas.create_line(x, y-8, x, y+8, fill='#0066cc', width=2)
            if self.show_saved.get():
                from core.pdf_io import read_pdf
                count = len(read_pdf(path).pages)
            else:
                count = self.current.page_count
            self.page_label.set(f'{"保存済" if self.show_saved.get() else "原本"} {self.page_index+1}/{count}頁 {self.zoom:.0%}')
        except Exception as exc:
            self.canvas.delete('all')
            self.error(exc)

    def change_page(self, delta):
        if not self.current:
            return
        count = self.current.page_count
        if self.show_saved.get() and self.saved_preview:
            from core.pdf_io import read_pdf
            try:
                count = len(read_pdf(self.saved_preview).pages)
            except Exception as exc:
                return self.error(exc)
        self.page_index = min(count-1, max(0, self.page_index+delta))
        self.reset_editor()
        self.render()

    def change_zoom(self, delta):
        self.zoom = min(3, max(0.5, self.zoom+delta))
        self.render()

    def toggle_saved(self):
        if self.show_saved.get() and not self.saved_preview:
            self.show_saved.set(False)
            messagebox.showinfo('保存後に確認できます', '先にPDFを保存してください。')
        self.page_index = 0
        self.reset_editor()
        self.render()

    def pick_position(self, event):
        if not self.current or self.show_saved.get():
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        w, h = self.image_size
        if 0 <= x <= w and 0 <= y <= h:
            self.position = (x/w, y/h)
            self.position_label.set(f'原本 {self.page_index+1}ページに番号を配置（青い十字）')
            self.render()

    def clear_position(self):
        self.position = None
        self.position_label.set('位置不明：コメント一覧にだけ出力します')
        self.render()

    def reset_editor(self):
        self.selected_finding = None
        self.position = None
        self.approved.set(False)
        self.comment.delete('1.0', 'end')
        self.position_label.set('位置不明：コメント一覧にだけ出力します')

    def refresh_findings(self):
        self.findings_list.delete(0, 'end')
        if self.current:
            for f in self.current.findings:
                label = '承認' if f.status == 'approved' else '未承認'
                self.findings_list.insert('end', f'[{label}] {f.page_index+1}頁 {f.comment[:24]}')

    def select_finding(self, event=None):
        selection = self.findings_list.curselection()
        if not self.current or not selection:
            return
        f = self.current.findings[selection[0]]
        self.selected_finding = f
        self.show_saved.set(False)
        self.page_index = f.page_index
        self.position = f.position
        self.comment.delete('1.0', 'end')
        self.comment.insert('1.0', f.comment)
        self.approved.set(f.status == 'approved')
        self.position_label.set(f'原本 {f.page_index+1}ページの位置' if f.position else '位置不明：コメント一覧にだけ出力します')
        self.render()

    def add_comment(self):
        if not self.current or self.show_saved.get():
            return
        text = self.comment.get('1.0', 'end').strip()
        if not text:
            return messagebox.showinfo('コメントを入力', '短いコメントを入力してください。')
        f = Finding(self.page_index, text, self.position, status='approved' if self.approved.get() else 'draft')
        self.current.findings.append(f)
        self.current.status = '編集中'
        self.reset_editor()
        self.refresh_findings()
        self.refresh_files()
        self.render()

    def update_comment(self):
        if not self.selected_finding:
            return messagebox.showinfo('コメントを選択', 'コメント一覧から更新する項目を選択してください。')
        text = self.comment.get('1.0', 'end').strip()
        if not text:
            return
        self.selected_finding.comment = text
        self.selected_finding.position = self.position
        self.selected_finding.page_index = self.page_index
        self.selected_finding.status = 'approved' if self.approved.get() else 'draft'
        self.current.status = '編集中'
        self.reset_editor()
        self.refresh_findings()
        self.refresh_files()
        self.render()

    def delete_comment(self):
        if self.selected_finding:
            self.current.findings.remove(self.selected_finding)
            self.current.status = '編集中'
            self.reset_editor()
            self.refresh_findings()
            self.refresh_files()
            self.render()

    def calculate_time(self):
        if not self.current:
            return
        self.store_times()
        a, b, s, e = self.current.time_inputs
        breaks = [(s, e)] if s or e else []
        try:
            for interval in self.extra_breaks.get().strip().split(';'):
                if interval.strip():
                    parts = interval.strip().split('-')
                    if len(parts) != 2:
                        raise ValueError('追加休憩は 14:00-14:10 の形で入力してください。')
                    breaks.append(tuple(parts))
            if self.no_break.get() and breaks:
                raise ValueError('「休憩なし」と休憩時刻が両方入力されています。確認してください。')
            self.current.time_validation = validate_time(a, b, breaks, no_break_confirmed=self.no_break.get())
        except ValueError as exc:
            from core.models import TimeValidation
            self.current.time_validation = TimeValidation('needs_review', str(exc))
        self.show_time()

    def show_time(self):
        result = self.current.time_validation if self.current else None
        if result:
            label = {'pass':'時間要件クリア', 'fail':'時間不足', 'needs_review':'要確認'}[result.result]
            self.time_result.set(label + '\n' + result.evidence)
        else:
            self.time_result.set('未判定（時刻を入力し「計算」を押してください）')

    def rename(self):
        if not self.current:
            return
        name = simpledialog.askstring('出力名を指定', '匿名IDまたは教員が指定した表示名\n氏名の自動推定は行いません。', initialvalue=self.current.anonymized_student_id)
        if name and name.strip():
            self.current.anonymized_student_id = name.strip()
            self.refresh_files()

    def confirm_document(self, document):
        if document.page_count > 1 and not document.multi_page_confirmed:
            document.multi_page_confirmed = messagebox.askyesno('複数ページの確認',
                f'{document.anonymized_student_id}：{document.page_count}ページすべてが同じ生徒の記録ですか？\n異なる生徒ならキャンセルして、PDFを分けて追加してください。')
            if not document.multi_page_confirmed:
                return False
        return True

    def save_current(self):
        if not self.current:
            return
        self.store_times()
        self.show_time()
        if not self.confirm_document(self.current):
            return
        if not messagebox.askyesno('教員による確定', '承認済みコメントと計算済みの時間結果だけを保存します。\n原本・全ページ・コメントを確認しましたか？\n入力欄だけの未追加コメントは保存されません。'):
            return
        target = filedialog.asksaveasfilename(title='添削済PDFの保存先', defaultextension='.pdf',
                     initialfile=safe_filename(self.current.anonymized_student_id),
                     filetypes=[('PDF', '*.pdf')], confirmoverwrite=False)
        if not target:
            return
        overwrite = False
        if Path(target).exists():
            overwrite = messagebox.askyesno('上書き確認', 'この保存先にファイルがあります。上書きしますか？原本への上書きはできません。')
            if not overwrite:
                return
        try:
            export_pdf(self.current, target, overwrite=overwrite)
            self.current.status = '保存済'
            self.current.saved_path = Path(target)
            self.saved_preview = Path(target)
            self.refresh_files()
            self.show_saved.set(True)
            self.toggle_saved()
            self.status.set('保存しました。保存済PDFの全ページと末尾コメントを確認し、ロイロノートから手動返却してください。')
        except Exception as exc:
            self.error(exc)

    def save_all(self):
        if not self.documents:
            return
        self.store_times()
        self.show_time()
        for d in self.documents:
            if not self.confirm_document(d):
                return
        if not messagebox.askyesno('全員の教員確認', 'すべての生徒の原本・承認済みコメント・時間結果を確認しましたか？\n個別PDFを保存します。同名ファイルは上書きせず失敗として表示します。\n未計算の時間結果と未承認コメントは出力しません。'):
            return
        directory = filedialog.askdirectory(title='個別PDFを保存するフォルダー')
        if not directory:
            return
        from core.batch import export_batch
        self.status.set('順番に個別PDFを保存しています…')
        self.root.update_idletasks()
        outcomes = export_batch(self.documents, directory)
        ok, failed = 0, []
        for d, path, error in outcomes:
            if path:
                ok += 1
                d.saved_path = path
            else:
                failed.append(f'{d.anonymized_student_id}：{error}')
        self.saved_preview = getattr(self.current, 'saved_path', None)
        self.refresh_files()
        self.status.set(f'保存成功 {ok}件／失敗 {len(failed)}件。失敗した生徒を選択して個別保存で再実行できます。')
        if failed:
            messagebox.showwarning('一部保存失敗', '\n'.join(failed) + '\n同名ファイル、入力変更、保存先の権限を確認してください。')
        else:
            messagebox.showinfo('一括保存完了', f'{ok}件の個別PDFを保存しました。全ページを確認してから返却してください。')

    def make_sample(self):
        target = filedialog.askdirectory(title='練習用PDFの保存フォルダー（実データなし）')
        if not target:
            return
        from tools.create_sample import create_samples
        try:
            paths = create_samples(Path(target))
            self.load_files(paths)
        except Exception as exc:
            self.error(exc)

    def help(self):
        messagebox.showinfo('操作方法',
            '1.「PDFを追加」で原本を選びます（複数選択可）。\n'
            '2. 開始・終了・休憩時刻を手入力し「計算」を押します。\n'
            '3. 原本の指摘位置をクリックし、コメントを入力します。\n'
            '4.「このコメントを教員が承認」にチェックして「新規追加」。\n'
            '   修正は一覧から選び「選択を更新」。位置不明でも追加できます。\n'
            '5.「承認してPDF保存」で別ファイルとして保存します。\n'
            '6. 保存済PDFを表示し、矢印でコメントページまで確認します。\n\n'
            '原本は書き換えません。読み取り・自動添削機能はありません。\n'
            '未保存の作業はアプリ終了で失われます。こまめにPDF保存してください。', parent=self.root)

    def close(self):
        if self.documents and not messagebox.askyesno('終了確認', '終了すると入力した時刻・コメントの作業状態は失われます。\n保存したPDFと原本は残ります。終了しますか？'):
            return
        self.root.destroy()
