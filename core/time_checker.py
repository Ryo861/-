import re
from .models import TimeValidation


def parse_time(value: str) -> int:
    value = value.strip()
    if not re.fullmatch(r'[0-9]{1,2}:[0-9]{2}', value):
        raise ValueError('時刻は24時間制の H:MM（例 7:55）で入力してください。')
    h, m = map(int, value.split(':'))
    if h > 23 or m > 59:
        raise ValueError('時刻の範囲を確認してください。')
    return h * 60 + m


def validate_time(start: str, end: str, breaks: list[tuple[str, str]], *,
                  no_break_confirmed: bool = False) -> TimeValidation:
    """Same-day intervals only. Missing breaks are never assumed to be 45 min."""
    try:
        a, b = parse_time(start), parse_time(end)
        if b <= a:
            raise ValueError('終了は開始より後にしてください。日跨ぎはフェーズAでは要確認です。')
        if not breaks and not no_break_confirmed:
            raise ValueError('休憩時刻が不明です。休憩なしの場合も明示確認が必要です。')
        intervals = sorted((parse_time(s), parse_time(e)) for s, e in breaks)
        previous = a
        for s, e in intervals:
            if s < a or e > b or e <= s or s < previous:
                raise ValueError('休憩の範囲・順序・重複を確認してください。')
            previous = e
        pause = sum(e - s for s, e in intervals)
        total = b - a - pause
        evidence = (f'開始 {start.strip()}／終了 {end.strip()}：{b-a}分\n'
                    f'休憩合計 {pause}分／正味 {total}分（{total//60}時間{total%60}分）\n'
                    '基準：450分以上')
        return TimeValidation('pass' if total >= 450 else 'fail', evidence, total)
    except ValueError as exc:
        return TimeValidation('needs_review', str(exc))
