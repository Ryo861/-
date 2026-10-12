"""Make the bundled OFL Japanese font available to Tk without OS-wide install."""
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def prepare_fonts():
    root = Path(__file__).resolve().parents[1]
    font = root / 'assets/fonts/BIZUDGothic-Regular.ttf'
    if sys.platform == 'win32':
        import ctypes
        if not ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, 0):
            raise RuntimeError('日本語フォントを登録できません。assetsフォルダーを確認してください。')
    elif sys.platform.startswith('linux'):
        local = root / '.local'
        local.mkdir(exist_ok=True)
        cache = local / 'font-cache'
        cache.mkdir(exist_ok=True)
        conf = local / 'fonts.conf'
        conf.write_text(f'''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>
  <dir>{escape(str(font.parent))}</dir>
  <cachedir>{escape(str(cache))}</cachedir>
</fontconfig>
''', encoding='utf-8')
        os.environ['FONTCONFIG_FILE'] = str(conf)


def configure_tk_fonts(root):
    from tkinter import font
    available = set(font.families(root))
    family = next((name for name in ('BIZ UDGothic', 'BIZ UDゴシック', 'Yu Gothic UI', 'Meiryo')
                   if name in available), None)
    if family is None:
        raise RuntimeError('日本語GUIフォントが見つかりません。')
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont',
                 'TkCaptionFont', 'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont'):
        font.nametofont(name, root=root).configure(family=family, size=10)
