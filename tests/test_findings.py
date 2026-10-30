"""Tests for the shared findings model."""
from __future__ import annotations

import pytest

from _findings import FAIL, INFO, PASS, SKIP, WARN, Finding, render, worst


def test_to_dict_has_all_fields():
    f = Finding("a.b", WARN, "something", observed="x", remediation="y", group="g")
    assert f.to_dict() == {"id": "a.b", "status": "WARN", "summary": "something",
                           "observed": "x", "remediation": "y", "group": "g"}


def test_invalid_status_rejected():
    with pytest.raises(ValueError):
        Finding("a", "BAD", "s")


def test_render_line_and_details():
    out = render([Finding("x.one", PASS, "fine"),
                  Finding("x.two", FAIL, "broken", observed="got 3", remediation="set it to 2")])
    assert out.splitlines() == [
        "- PASS x.one: fine",
        "- FAIL x.two: broken",
        "  Observed: got 3",
        "  Remediation: set it to 2",
    ]


def test_worst_orders_statuses():
    mk = lambda s: Finding("i", s, "s")  # noqa: E731
    assert worst([]) == PASS
    assert worst([mk(PASS), mk(INFO), mk(SKIP)]) in (INFO, SKIP)
    assert worst([mk(PASS), mk(WARN), mk(INFO)]) == WARN
    assert worst([mk(WARN), mk(FAIL), mk(PASS)]) == FAIL


def test_render_localizes_skill_references(monkeypatch):
    f = Finding("x.y", WARN, "run /ploma:compile", observed="saw /ploma:doctor", remediation="Run /ploma:onboard")
    monkeypatch.setenv("PLOMA_HOST", "codex")
    assert render([f]).splitlines() == ["- WARN x.y: run $ploma:compile", "  Observed: saw $ploma:doctor",
                                        "  Remediation: Run $ploma:onboard"]
    assert f.remediation == "Run /ploma:onboard"  # the finding itself (and JSON) keeps /ploma:
    monkeypatch.setenv("PLOMA_HOST", "claude")
    assert "/ploma:compile" in render([f])
