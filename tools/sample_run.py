from pathlib import Path
from core.models import Finding
from core.pdf_io import inspect_pdf, export_pdf, safe_filename
from core.time_checker import validate_time
from tools.create_sample import create_samples


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='outputs/demo')
    args = parser.parse_args()
    root = Path(args.output)
    paths = create_samples(root / 'originals')
    for i, path in enumerate(paths, 1):
        doc = inspect_pdf(path, f'匿名{i:03d}')
        doc.time_validation = validate_time('7:55', '16:45', [('11:50', '12:35')])
        doc.findings = [
            Finding(0, '「実習開始」と記入しよう。', (0.25, 0.46), status='approved'),
            Finding(0, '誰に、どのように声をかけたか書こう。', None, region='振り返り', status='approved')]
        result = export_pdf(doc, root / safe_filename(doc.anonymized_student_id))
        print(f'{doc.anonymized_student_id}: 正味485分／原本1ページ＋コメント1ページ → {result}')


if __name__ == '__main__':
    main()
