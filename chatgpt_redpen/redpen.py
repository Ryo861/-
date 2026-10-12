"""Offline PDF red pen renderer. AI recognition is intentionally separate."""
from pathlib import Path
import json
import math
import fitz
from PIL import Image


def _box(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('bbox は [左,上,右,下] が必要です')
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in value):
        raise ValueError('bbox は有限の数値が必要です')
    x, y, r, b = value
    if not (0 <= x < r <= 1 and 0 <= y < b <= 1):
        raise ValueError('bbox は0〜1の正規化座標です')
    return value


def render_redpen(source, corrections, output, preview_dir=None, min_confidence=.85):
    """Render normalized coordinates measured on the displayed (rotated) page.

    Returns a report; unresolved entries are never silently discarded.
    """
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('原本への上書きは禁止です')
    if output.exists():
        raise FileExistsError(output)
    data = json.loads(Path(corrections).read_text(encoding='utf-8')) if isinstance(corrections, (str, Path)) else corrections
    if data.get('version') != 1 or not isinstance(data.get('corrections'), list):
        raise ValueError('version:1 と corrections 配列が必要です')
    fontpath = Path(__file__).with_name('BIZUDGothic-Regular.ttf')
    if not fontpath.exists():
        raise RuntimeError('日本語フォントがありません。描画を中止しました')
    font = fitz.Font(fontfile=str(fontpath))
    report = {'placed': [], 'pending': []}
    with fitz.open(source) as doc:
        if doc.needs_pass or not len(doc):
            raise ValueError('暗号化または空のPDFです')
        entries = data['corrections']
        for item in entries:
            if not isinstance(item.get('page'), int) or isinstance(item['page'], bool) or not 1 <= item['page'] <= len(doc):
                raise ValueError('page は1始まりの有効なページ番号が必要です')
            if item.get('bbox') is not None:
                _box(item['bbox'])
            confidence = item.get('confidence', 0)
            if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError('confidence は0〜1が必要です')
            for key in ('original', 'replacement', 'comment', 'kind'):
                if not isinstance(item.get(key, ''), str):
                    raise ValueError(key + ' は文字列が必要です')
        for number, page in enumerate(doc, 1):
            # Occupancy comes from the original page, before adding any red ink.
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), colorspace=fitz.csGRAY, alpha=False)
            mask = Image.frombytes('L', (pix.width, pix.height), pix.samples).point(lambda v: 255 if v < 225 else 0)
            width, height = page.rect.width, page.rect.height
            occupied = []
            selected = [i for i in entries if i['page'] == number]
            size = 15 if len(selected) <= 4 else 12
            page.insert_font(fontname='redpenJP', fontfile=str(fontpath))
            for index, item in enumerate(selected):
                def pending(reason):
                    report['pending'].append({'item': item, 'reason': reason})
                if item.get('bbox') is None or item.get('confidence', 0) < min_confidence:
                    pending('位置未確定'); continue
                x, y, r, b = item['bbox']
                target = fitz.Rect(x*width, y*height, r*width, b*height)
                text = item.get('replacement') or item.get('comment')
                if not text:
                    pending('修正文字・コメントなし'); continue
                if '\n' in text or len(text) > 24:
                    pending('短いコメントにまとめてください'); continue
                tw = font.text_length(text, fontsize=size) + 8
                th = size*1.6
                candidates = []
                for distance in (5, 18, 32, 48, 70):
                    for cx, cy in ((target.x0, target.y0-th-distance), (target.x1+distance, target.y0), (target.x0, target.y1+distance), (target.x0-tw-distance, target.y0)):
                        candidates.append(fitz.Rect(cx, cy, cx+tw, cy+th))
                label = None
                for candidate in candidates:
                    if not page.rect.contains(candidate) or candidate.intersects(target) or any(candidate.intersects(o) for o in occupied):
                        continue
                    crop = mask.crop((int(candidate.x0*pix.width/width), int(candidate.y0*pix.height/height), math.ceil(candidate.x1*pix.width/width), math.ceil(candidate.y1*pix.height/height)))
                    if crop.getbbox() is None:
                        label = candidate; break
                if label is None:
                    pending('近くに安全な空白がありません。関連指摘をまとめて再指定してください'); continue
                # Derotation maps displayed image coordinates into PDF drawing space.
                transform = page.derotation_matrix
                mark = target * transform
                if item.get('kind') == 'underline':
                    page.draw_line(fitz.Point(target.x0, target.y1)*transform, fitz.Point(target.x1, target.y1)*transform, color=(1,0,0), width=1)
                else:
                    page.draw_oval(mark, color=(1,0,0), width=1)
                anchor = fitz.Point(label.x0+4, label.y0+size*1.15) * transform
                page.insert_text(anchor, text, fontname='redpenJP', fontsize=size, color=(1,0,0), rotate=page.rotation)
                # A leader is useful for displaced labels; never cross original ink.
                end = fitz.Point((target.x0+target.x1)/2, target.y0 if label.y1 <= target.y0 else target.y1)
                start = fitz.Point(min(max(end.x,label.x0),label.x1), label.y1 if label.y1 <= target.y0 else label.y0)
                safe = True
                for step in range(1, 100):
                    point = start + (end-start)*(step/100)
                    if target.contains(point):
                        continue
                    px = min(pix.width-1,max(0,int(point.x*pix.width/width)))
                    py = min(pix.height-1,max(0,int(point.y*pix.height/height)))
                    if mask.getpixel((px,py)) or any(o.contains(point) for o in occupied):
                        safe = False; break
                if safe:
                    page.draw_line(start*transform, end*transform, color=(1,0,0), width=.7)
                occupied.append(label + (-2,-2,2,2))
                report['placed'].append({'item':item, 'label_bbox':[label.x0/width,label.y0/height,label.x1/width,label.y1/height]})
        output.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output, garbage=3, deflate=True)
    if preview_dir:
        export_pages(output, preview_dir)
    return report


def export_pages(pdf, directory, dpi=144):
    """Images used by ChatGPT for recognition and by the teacher for review."""
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    paths = []
    with fitz.open(pdf) as doc:
        for n, page in enumerate(doc, 1):
            path = directory / f'page-{n:03}.png'
            if path.exists():
                raise FileExistsError(path)
            page.get_pixmap(dpi=dpi, alpha=False).save(path)
            paths.append(str(path))
    return paths


def check_minutes(start, end, breaks=None):
    """No inferred breaks, midnight rollover, or automatic time correction."""
    def minutes(s):
        h, m = map(int, s.split(':'))
        if not 0 <= h <= 23 or not 0 <= m <= 59:
            raise ValueError('時刻の範囲外')
        return h*60+m
    try:
        a, b = minutes(start), minutes(end)
        if b <= a or breaks is None:
            return {'status':'要確認', 'minutes':None}
        intervals = sorted((minutes(x), minutes(y)) for x,y in breaks)
        previous = a
        for x,y in intervals:
            if x < previous or y <= x or y > b:
                return {'status':'要確認', 'minutes':None}
            previous = y
        total = b-a-sum(y-x for x,y in intervals)
        return {'status':'不足' if total < 450 else '確認済', 'minutes':total}
    except (ValueError, TypeError, AttributeError):
        return {'status':'要確認', 'minutes':None}
