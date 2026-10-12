from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass
class Finding:
    page_index: int
    comment: str
    position: tuple[float, float] | None = None  # visible crop, top-left, normalized
    region: str = '手動指定'
    category: str = '教員コメント'
    original_text: str = ''
    suggested_text: str = ''
    certainty: str = '教員による手動指定'
    status: str = 'draft'
    finding_id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class TimeValidation:
    result: str
    evidence: str
    effective_minutes: int | None = None
    threshold_minutes: int = 450


@dataclass
class Document:
    path: Path
    page_count: int
    fingerprint: str
    anonymized_student_id: str
    findings: list[Finding] = field(default_factory=list)
    time_inputs: list[str] = field(default_factory=lambda: ['', '', '', ''])
    time_validation: TimeValidation | None = None
    extra_breaks: str = ''
    no_break: bool = False
    saved_path: Path | None = None
    status: str = '未確認'
    multi_page_confirmed: bool = False
