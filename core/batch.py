from pathlib import Path
from .pdf_io import export_pdf, safe_filename


def export_batch(documents, output_dir):
    """Sequential, isolated failures; never silently overwrite existing files."""
    outcomes = []
    for document in documents:
        target = Path(output_dir) / safe_filename(document.anonymized_student_id)
        try:
            export_pdf(document, target)
            document.status = '保存済'
            outcomes.append((document, target, None))
        except Exception as exc:
            document.status = '保存失敗'
            outcomes.append((document, None, type(exc).__name__))
    return outcomes
