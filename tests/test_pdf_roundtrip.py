import io
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import ImageChops
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from reportlab.pdfgen import canvas

from core.models import Finding
from core.pdf_io import inspect_pdf, export_pdf, render_page, fingerprint, position_to_pdf, safe_filename
from core.batch import export_batch
from core.time_checker import validate_time
from tools.create_sample import create_samples


class PdfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = create_samples(self.root / 'inputs')
        self.doc = inspect_pdf(self.paths[0], '匿名001')

    def tearDown(self):
        self.temp.cleanup()

    def test_original_content_and_japanese_output(self):
        before = fingerprint(self.doc.path)
        self.doc.time_validation = validate_time('7:55','16:45',[('11:50','12:35')])
        self.doc.findings = [Finding(0, '誰に、どのように声をかけたか書こう。', None, status='approved'),
                             Finding(0, '未承認は出力しない', (.5,.5))]
        dest = export_pdf(self.doc, self.root / 'out.pdf')
        reader = PdfReader(dest)
        self.assertEqual(len(reader.pages), 2)
        self.assertEqual(fingerprint(self.doc.path), before)
        self.assertIsNone(ImageChops.difference(render_page(self.doc.path), render_page(dest)).getbbox())
        text = reader.pages[1].extract_text()
        self.assertIn('誰に、どのように', text)
        self.assertIn('485分', text)
        self.assertNotIn('未承認は出力しない', text)
        self.assertTrue(reader.pages[1]['/Resources']['/Font'])
        fonts = reader.pages[1]['/Resources']['/Font'].get_object()
        self.assertTrue(any('/FontFile2' in font.get_object().get('/FontDescriptor', {}) for font in fonts.values()))
        # Real render test for appended Japanese text, not only PDF text extraction.
        image = render_page(dest, 1)
        self.assertIsNotNone(ImageChops.difference(image, image.copy().point(lambda _:255)).getbbox())

    def test_coordinates_and_rotated_crop_preserve_original(self):
        for rotation in (0, 90, 180, 270):
            stream = io.BytesIO()
            c = canvas.Canvas(stream, pagesize=(400, 600))
            c.setFillColorRGB(.1, .4, .7)
            c.rect(90, 100, 80, 100, fill=1)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(100, 350, 'Original content')
            c.save()
            page = PdfReader(stream).pages[0]
            page.cropbox = RectangleObject([50, 60, 350, 560])
            page.rotate(rotation)
            writer = PdfWriter()
            writer.add_page(page)
            path = self.root / f'rotation{rotation}.pdf'
            writer.write(path)
            doc = inspect_pdf(path, f'rot{rotation}')
            before = render_page(path)
            # Also test unmarked normalization retains exact raster content.
            clean = export_pdf(doc, self.root / f'clean{rotation}.pdf')
            clean_image = render_page(clean)
            self.assertEqual(before.size, clean_image.size)
            self.assertIsNone(ImageChops.difference(before, clean_image).getbbox())
            doc.findings = [Finding(0, '位置テスト', (.72, .31), status='approved')]
            target = export_pdf(doc, self.root / f'marked{rotation}.pdf')
            after = render_page(target)
            diff = ImageChops.difference(before, after)
            bbox = diff.getbbox()
            self.assertIsNotNone(bbox)
            x, y = .72*before.width, .31*before.height
            self.assertLess(abs((bbox[0]+bbox[2])/2-x), 2)
            self.assertLess(abs((bbox[1]+bbox[3])/2-y), 2)
            # Changes limited to the marker footprint; no shifted original content.
            self.assertLess(bbox[2]-bbox[0], 26)
            self.assertLess(bbox[3]-bbox[1], 26)

    def test_invalid_position_and_page(self):
        self.assertEqual(position_to_pdf((.25,.75), 400,600), (100,150))
        for position in ((-1,0), (0,1.2), (math.nan, 0)):
            with self.assertRaises(ValueError):
                position_to_pdf(position, 400,600)
        self.doc.findings = [Finding(2, '不正ページ', status='approved')]
        with self.assertRaises(ValueError):
            export_pdf(self.doc, self.root / 'invalid.pdf')

    def test_no_original_overwrite_existing_and_changed_source(self):
        before = self.doc.path.read_bytes()
        with self.assertRaises(ValueError):
            export_pdf(self.doc, self.doc.path, overwrite=True)
        target = self.root / 'existing.pdf'
        target.write_bytes(b'existing')
        with self.assertRaises(FileExistsError):
            export_pdf(self.doc, target)
        self.assertEqual(target.read_bytes(), b'existing')
        self.assertEqual(self.doc.path.read_bytes(), before)
        self.doc.path.write_bytes(before + b'\n')
        with self.assertRaises(ValueError):
            export_pdf(self.doc, self.root / 'changed.pdf')

    def test_multipage_confirmation_and_page_count(self):
        writer = PdfWriter()
        for path in self.paths:
            writer.add_page(PdfReader(path).pages[0])
        path = self.root / 'multi.pdf'
        writer.write(path)
        doc = inspect_pdf(path, '匿名複数頁')
        doc.findings = [Finding(1, '2ページの指摘', (.4,.4), status='approved')]
        with self.assertRaises(ValueError):
            export_pdf(doc, self.root / 'multiout.pdf')
        doc.multi_page_confirmed = True
        dest = export_pdf(doc, self.root / 'multiout.pdf')
        self.assertEqual(len(PdfReader(dest).pages), 3)
        self.assertIsNone(ImageChops.difference(render_page(path), render_page(dest)).getbbox())

    def test_long_comments_not_lost(self):
        comment = '長いコメントを省略せず複数ページに表示します。'*180
        self.doc.findings = [Finding(0, comment, status='approved')]
        dest = export_pdf(self.doc, self.root / 'long.pdf')
        reader = PdfReader(dest)
        self.assertGreater(len(reader.pages), 2)
        text = ''.join(p.extract_text().replace('介護実習記録 — 教員確認済みコメント', '') for p in reader.pages[1:]).replace('\n', '')
        self.assertIn(comment, text)

    def test_encrypted_broken_and_zero_pages_rejected(self):
        for mode in ('encrypted', 'zero', 'broken'):
            path = self.root / (mode + '.pdf')
            if mode == 'broken':
                path.write_bytes(b'not a PDF')
            else:
                writer = PdfWriter()
                if mode == 'encrypted':
                    writer.add_page(PdfReader(self.doc.path).pages[0])
                    writer.encrypt('test-password')
                writer.write(path)
            with self.assertRaises(Exception):
                inspect_pdf(path, '匿名')

    def test_batch_isolates_failures_and_does_not_overwrite(self):
        second = inspect_pdf(self.paths[1], '匿名002')
        self.doc.findings = [Finding(0, '一人目', status='approved')]
        second.findings = [Finding(0, '二人目', status='approved')]
        folder = self.root / 'batch'
        results = export_batch([self.doc, second], folder)
        self.assertTrue(all(path and error is None for _, path, error in results))
        original_hash = fingerprint(results[0][1])
        third = inspect_pdf(self.paths[1], '匿名003')
        retry = export_batch([self.doc, third], folder)
        self.assertEqual(retry[0][2], 'FileExistsError')
        self.assertIsNotNone(retry[1][1])
        self.assertEqual(fingerprint(results[0][1]), original_hash)

    def test_offline_processing(self):
        with patch('socket.socket', side_effect=AssertionError('network prohibited')):
            doc = inspect_pdf(self.paths[0], '匿名')
            doc.findings = [Finding(0, 'ローカル', (.2,.3), status='approved')]
            export_pdf(doc, self.root / 'offline.pdf')
            render_page(self.root / 'offline.pdf', 1)

    def test_embedded_image_preserved(self):
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        image = Image.new('RGB', (300, 200), '#b0c0d0')
        image.paste('#334455', (40, 20, 120, 100))
        path = self.root / 'image.pdf'
        c = canvas.Canvas(str(path), pagesize=(400, 600))
        c.drawImage(ImageReader(image), 40, 100, width=300, height=200)
        c.save()
        doc = inspect_pdf(path, '画像')
        doc.findings = [Finding(0, '位置不明コメント', status='approved')]
        target = export_pdf(doc, self.root / 'image_out.pdf')
        self.assertIsNone(ImageChops.difference(render_page(path), render_page(target)).getbbox())
        self.assertTrue(PdfReader(target).pages[0]['/Resources']['/XObject'])

    def test_missing_font_glyph_rejects_without_output(self):
        self.doc.findings = [Finding(0, '確認😀', status='approved')]
        target = self.root / 'unsupported.pdf'
        with self.assertRaisesRegex(ValueError, 'フォントにない文字'):
            export_pdf(self.doc, target)
        self.assertFalse(target.exists())

    def test_windows_filenames(self):
        self.assertEqual(safe_filename('匿名001','2026-10-12'), '匿名001_2026-10-12_添削済.pdf')
        self.assertEqual(safe_filename('CON','2026-10-12'), '_CON_2026-10-12_添削済.pdf')
        self.assertNotIn('/', safe_filename('a/b:c*'))
        self.assertNotIn('?', safe_filename('a?b'))
