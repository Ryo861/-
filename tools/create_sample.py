"""Generate synthetic, public-safe PDFs locally. Never include real names."""
from pathlib import Path
import argparse
from reportlab.pdfgen import canvas
from core.pdf_io import japanese_font


def create_samples(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / '練習用_記録01.pdf', directory / '練習用_記録02.pdf']
    for n, path in enumerate(paths, 1):
        if path.exists():
            raise FileExistsError('練習用PDFが既にあります。空のフォルダーを選んでください。')
    for n, path in enumerate(paths, 1):
        c = canvas.Canvas(str(path), pagesize=(578, 838))
        c.setFont(japanese_font(), 18)
        c.drawString(40, 790, f'介護実習記録（合成サンプル {n:02d}）')
        c.setFont(japanese_font(), 12)
        lines = [
            '実データ・個人情報を含まない練習用の記録です。',
            '開始 7:55　終了 16:45　休憩 11:50〜12:35',
            '正味実習時間：485分（8時間5分）',
            '目標：声のかけ方を振り返る。',
            '活動欄：開始',
            '実施内容：声をかけました。',
            '振り返り：コミュニケーションを取った。',
            '次回の課題：具体的な行動を記録する。',
        ]
        for i, line in enumerate(lines):
            y = 735-i*70
            c.drawString(40, y, line)
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.rect(30, y-20, 518, 55)
        c.save()
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='sample_data')
    args = parser.parse_args()
    for path in create_samples(args.output):
        print(path)
