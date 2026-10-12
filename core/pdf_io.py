import hashlib
import io
import math
import logging
import os
import re
import tempfile
from datetime import date
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import Document, Finding

# Parser warnings can contain fragments of corrupt documents; do not log them.
logging.getLogger('pypdf').addHandler(logging.NullHandler())
logging.getLogger('pypdf').propagate = False

FONT_PATH = Path(__file__).resolve().parents[1] / 'assets/fonts/BIZUDGothic-Regular.ttf'


def japanese_font():
    if 'BIZUD' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('BIZUD', str(FONT_PATH)))
    return 'BIZUD'


def fingerprint(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read_pdf(path):
    reader = PdfReader(str(path), strict=False)
    if reader.is_encrypted:
        raise ValueError('暗号化PDFは読み込めません。暗号化されていないPDFを書き出してください。')
    if not reader.pages:
        raise ValueError('ページがありません。')
    # Resolve all page boxes early; rendering is additionally checked by inspect_pdf.
    for page in reader.pages:
        w, h = float(page.cropbox.width), float(page.cropbox.height)
        if not all(math.isfinite(x) and 0 < x <= 14400 for x in (w, h)):
            raise ValueError('ページ寸法が不正、または対応上限（200インチ）を超えています。')
        if page.rotation % 90:
            raise ValueError('90度単位以外のページ回転は要確認です。')
    return reader


def render_page(path, page_index=0, scale=1.0):
    """Return an independent RGB image. No files or original text are logged."""
    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[page_index]
        try:
            w, h = page.get_size()
            if w <= 0 or h <= 0:
                raise ValueError('ページ寸法を確認してください。')
            actual = min(scale, 2200 / max(w, h))  # bounded preview memory
            bitmap = page.render(scale=actual)
            try:
                return bitmap.to_pil().convert('RGB').copy()
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        pdf.close()


def inspect_pdf(path, anonymous_id):
    path = Path(path).resolve()
    reader = read_pdf(path)
    render_page(path, 0, 0.5)
    return Document(path, len(reader.pages), fingerprint(path), anonymous_id)


def safe_filename(display_name, on_date=None):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', display_name).strip(' .')[:70]
    if not name:
        name = '匿名'
    # Windows reserved device names apply even before an extension.
    if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        name = '_' + name
    return f'{name}_{on_date or date.today().isoformat()}_添削済.pdf'


def position_to_pdf(position, width, height):
    x, y = position
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (x, y)):
        raise ValueError('番号の位置がページ範囲外です。')
    return x * width, (1 - y) * height


def wrapped(text, font, size, width):
    """Unicode character wrapping without dropping long comments or explicit lines."""
    for line in text.split('\n'):
        current = ''
        for char in line:
            if current and pdfmetrics.stringWidth(current + char, font, size) > width:
                yield current
                current = ''
            current += char
        yield current


def comments_pdf(findings, time_validation):
    stream = io.BytesIO()
    c = canvas.Canvas(stream, pagesize=(595, 842))
    font = japanese_font()
    y = 780

    def header():
        c.setFillColorRGB(0.75, 0, 0)
        c.setFont(font, 16)
        c.drawString(40, 805, '介護実習記録 — 教員確認済みコメント')
        c.setFont(font, 10)
    header()
    entries = []
    if time_validation:
        label = {'pass':'時間要件クリア', 'fail':'時間不足', 'needs_review':'要確認'}[time_validation.result]
        entries.append(f'【実習時間：{label}】\n{time_validation.evidence}')
    for n, f in enumerate(findings, 1):
        location = '赤番号の位置' if f.position is not None else f'{f.region}／位置不明・要確認'
        text = f'【{n}】原本 {f.page_index+1}ページ／{location}\n{f.category}：{f.comment}'
        if f.original_text:
            text += f'\n該当箇所（教員入力）：{f.original_text}'
        if f.suggested_text:
            text += f'\n推奨表現：{f.suggested_text}'
        text += f'\n根拠：{f.certainty}'
        entries.append(text)
    glyphs = pdfmetrics.getFont(font).face.charToGlyph
    for entry in entries:
        for char in entry:
            if char != '\n' and ord(char) not in glyphs:
                raise ValueError(f'日本語フォントにない文字（U+{ord(char):04X}）があります。コメントを見直してください。')
        for line in wrapped(entry, font, 10, 515):
            if y < 45:
                c.showPage()
                header()
                y = 780
            c.drawString(40, y, line)
            y -= 16
        y -= 14
    c.save()
    return PdfReader(stream)


def export_pdf(document: Document, target, *, overwrite=False):
    target = Path(target).resolve()
    if target == document.path or (target.exists() and os.path.samefile(target, document.path)):
        raise ValueError('原本と同じファイルには保存できません。別の保存先を選んでください。')
    if fingerprint(document.path) != document.fingerprint:
        raise ValueError('読込後に原本が変更されています。PDFを追加し直してください。')
    if document.page_count > 1 and not document.multi_page_confirmed:
        raise ValueError('複数ページが同じ生徒の記録であることを確認してください。自動分割はしません。')
    reader = read_pdf(document.path)
    writer = PdfWriter()
    selected = [f for f in document.findings if f.status == 'approved']
    for f in selected:
        if not 0 <= f.page_index < len(reader.pages):
            raise ValueError('コメントのページ番号が不正です。')
        if not f.comment.strip():
            raise ValueError('空のコメントは承認できません。')
    for index, page in enumerate(reader.pages):
        # Normalize rotation first. Map normalized preview coordinates to visible crop.
        page.transfer_rotation_to_content()
        writer.add_page(page)
        out = writer.pages[-1]
        w, h = float(out.cropbox.width), float(out.cropbox.height)
        data = io.BytesIO()
        c = canvas.Canvas(data, pagesize=(w, h))
        marked = False
        for number, f in enumerate(selected, 1):
            if f.page_index != index or f.position is None:
                continue
            x, y = position_to_pdf(f.position, w, h)
            # Keep the complete marker inside the visible crop at all edges.
            x, y = max(12, min(w-12, x)), max(12, min(h-12, y))
            c.setStrokeColorRGB(0.85, 0, 0)
            c.setFillColorRGB(0.85, 0, 0)
            c.setLineWidth(1.3)
            c.circle(x, y, 10)
            c.setFont('Helvetica', 9 if number < 100 else 7)
            c.drawCentredString(x, y-3, str(number))
            marked = True
        c.save()
        if marked:
            overlay = PdfReader(data).pages[0]
            out.merge_transformed_page(overlay, Transformation().translate(
                float(out.cropbox.left), float(out.cropbox.bottom)))
    if selected or document.time_validation:
        for page in comments_pdf(selected, document.time_validation).pages:
            writer.add_page(page)
    writer.add_metadata({'/Title':'介護実習記録 添削済', '/Creator':'介護実習記録チェッカー フェーズA'})
    target.parent.mkdir(parents=True, exist_ok=True)
    # Stage on the same volume. Exclusive create prevents accidental overwrites.
    fd, temporary = tempfile.mkstemp(prefix='.checker-', suffix='.pdf', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            writer.write(f)
        check = read_pdf(temporary)
        if len(check.pages) != len(writer.pages):
            raise ValueError('保存後のページ数が一致しません。')
        render_page(temporary, 0, 0.5)
        if overwrite:
            os.replace(temporary, target)
        else:
            # Copy into an exclusively-created target, cleaning partial output on failure.
            import shutil
            created = False
            try:
                with open(target, 'xb') as dest:
                    created = True
                    with open(temporary, 'rb') as src:
                        shutil.copyfileobj(src, dest)
            except Exception:
                if created:
                    target.unlink(missing_ok=True)
                raise
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target
