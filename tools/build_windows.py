"""Build and validate an onedir Windows ZIP. Run on Windows only."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from importlib import metadata


def main():
    if sys.platform != 'win32':
        raise SystemExit('Windows上で実行してください。クロスコンパイルはしません。')
    root = Path(__file__).resolve().parents[1]
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--onedir', '--windowed', '--name', 'PracticeRecordChecker',
        '--collect-all', 'pypdfium2', '--collect-all', 'pypdfium2_raw',
        '--collect-all', 'reportlab', '--collect-all', 'PIL',
        '--hidden-import', 'tools.portable_smoke', '--hidden-import', 'tools.create_sample',
        '--add-data', f'{root / "assets"};assets', str(root / 'app.py')
    ], cwd=root, check=True)
    bundle = root / 'dist/PracticeRecordChecker'
    for directory in ('sample_data', 'third_party', 'docs'):
        shutil.copytree(root / directory, bundle / directory, dirs_exist_ok=True)
    for file in ('LICENSES_AND_MODELS.md',):
        shutil.copy2(root / file, bundle / file)
    shutil.copy2(root / 'docs/インストール不要版の使い方.txt', bundle / 'はじめに読んでください.txt')
    notices = bundle / 'third_party/windows-distribution'
    notices.mkdir(parents=True, exist_ok=True)
    # Preserve actual Windows wheel and bundled-font licenses, not just Linux copies.
    for dist in metadata.distributions():
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license', 'copying', 'notice')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    name = dist.metadata['Name'].replace('/', '_')
                    safe_parts = [part for part in Path(str(file)).parts if part not in ('.', '..')]
                    dest = notices / name / Path(*safe_parts)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.is_file():
        raise RuntimeError('Python LICENSE.txt is required for redistribution')
    shutil.copy2(python_license, notices / 'Python_LICENSE.txt')
    # The actual bundled Tcl/Tk license terms must be included as well.
    for folder in (Path(sys.base_prefix) / 'tcl', Path(sys.base_prefix) / 'Lib/tkinter'):
        if folder.exists():
            for path in folder.rglob('*'):
                if path.is_file() and any(word in path.name.lower() for word in ('license', 'copying', 'notice')):
                    dest = notices / 'TclTk' / path.relative_to(Path(sys.base_prefix))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
    reports = root / 'build/portable-smoke'
    if reports.exists():
        shutil.rmtree(reports)  # generated build output only
    exe = bundle / 'PracticeRecordChecker.exe'
    completed = subprocess.run([str(exe), '--self-test', '--output', str(reports)],
                               cwd=root, timeout=120)
    if completed.returncode:
        error = reports / 'error.txt'
        detail = error.read_text(encoding='utf-8') if error.exists() else 'EXE self-test failed without a report'
        escaped = detail.replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print(f'::error title=Portable EXE check::{escaped}')
        raise SystemExit(completed.returncode)
    result = json.loads((reports / 'result.json').read_text(encoding='utf-8'))
    assert result['passed'] and result['frozen']
    shutil.copy2(reports / 'result.json', bundle / 'Windows動作確認結果.json')
    archive = Path(shutil.make_archive(str(root / 'dist/practice-record-checker-windows-portable'),
                                      'zip', root / 'dist', bundle.name))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.sha256.txt').write_text(digest + '  ' + archive.name + '\n', encoding='utf-8')
    print('Validated portable ZIP:', archive.name)


if __name__ == '__main__':
    main()
