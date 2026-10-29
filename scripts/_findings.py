"""Shared findings model: one result of one check, rendered the same way everywhere."""
from __future__ import annotations

from dataclasses import asdict, dataclass

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
INFO = "INFO"
SKIP = "SKIP"
STATUSES = (PASS, WARN, FAIL, INFO, SKIP)

# Higher is worse. INFO and SKIP outrank PASS so a report with only notes is not shown as clean PASS.
_RANK = {PASS: 0, SKIP: 1, INFO: 2, WARN: 3, FAIL: 4}


@dataclass
class Finding:
    id: str
    status: str
    summary: str
    observed: str = ""
    remediation: str = ""
    group: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown finding status {self.status!r}; expected one of {STATUSES}")

    def to_dict(self) -> dict:
        return asdict(self)


def render(findings: list[Finding]) -> str:
    """One ``- STATUS id: summary`` line per finding, with indented Observed and Remediation lines."""
    lines: list[str] = []
    for f in findings:
        lines.append(f"- {f.status} {f.id}: {f.summary}")
        if f.observed:
            lines.append(f"  Observed: {f.observed}")
        if f.remediation:
            lines.append(f"  Remediation: {f.remediation}")
    return "\n".join(lines)


def worst(findings: list[Finding]) -> str:
    """Most severe status present (FAIL > WARN > INFO > SKIP > PASS); PASS when empty."""
    return max((f.status for f in findings), key=_RANK.__getitem__, default=PASS)
