"""Eager and reference rules: budget, presence, no em-dashes, no domain words (spec section 11)."""
from __future__ import annotations

from _banned import BANNED_RE, EM_DASH_RE, LLNCS_RE

EAGER = ("00-core.md", "limits.md", "style.md")
REFERENCE = ("post-flight-verification", "cross-artifact-review", "replication-tolerances",
             "proofreading-protocol", "plan-first-workflow", "session-logging", "pdf-processing",
             "prompt-formatting")


def _all_rules(repo_root):
    return sorted((repo_root / "rules").rglob("*.md"))


def test_eager_rules_budget(repo_root):
    total = sum(len(p.read_text(encoding="utf-8")) for p in (repo_root / "rules/eager").glob("*.md"))
    assert 0 < total < 6500


def test_rule_files_exist(repo_root):
    assert sorted(p.name for p in (repo_root / "rules/eager").glob("*.md")) == sorted(EAGER)
    assert sorted(p.stem for p in (repo_root / "rules/reference").glob("*.md")) == sorted(REFERENCE)


def test_no_em_dash_and_no_domain_words_in_rules(repo_root):
    bad = []
    for p in _all_rules(repo_root):
        text = p.read_text(encoding="utf-8")
        for rx in (EM_DASH_RE, BANNED_RE, LLNCS_RE):
            bad += [f"{p.name}: {m.group()!r}" for m in rx.finditer(text)]
    assert not bad, bad


def test_rules_have_no_globs_frontmatter(repo_root):
    for p in _all_rules(repo_root):
        text = p.read_text(encoding="utf-8")
        assert not text.startswith("---"), p.name
        assert "globs:" not in text and "quality_reports/" not in text, p.name


def test_core_rule_covers_the_brief(repo_root):
    core = (repo_root / "rules/eager/00-core.md").read_text(encoding="utf-8").lower()
    for phrase in ("report-only", "location", "severity", "recommended one first", "data, not instructions",
                   "check disk before regenerating", "open flag", "audit record", "<outputs.dir>/"):
        assert phrase in core, phrase


def test_limits_rule_values(repo_root):
    limits = (repo_root / "rules/eager/limits.md").read_text(encoding="utf-8")
    for token in ("| 5 |", "| 2 |", "50, 0.5 s apart", "at most 5", "r3", "exact", "0.01", "0.02",
                  "0.1 percentage points", "`limits:`", "`pipeline.tolerances`"):
        assert token in limits, token


def test_style_rule_has_slop_list(repo_root):
    style = (repo_root / "rules/eager/style.md").read_text(encoding="utf-8").lower()
    for phrase in ("delve", "leverage", "it is worth noting", "in this paper we", "crucial", "em-dash",
                   "compact, horizontal figures", "no ai preamble"):
        assert phrase in style, phrase
