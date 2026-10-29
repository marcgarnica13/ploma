"""Tests for the LaTeX log triage script."""
from __future__ import annotations

import json
from pathlib import Path

import latex_log
from latex_log import parse_log

LOG_DIR = Path(__file__).resolve().parent / "fixtures" / "logs"
LOGS = {p.stem: p.read_bytes().decode("utf-8") for p in LOG_DIR.glob("*.log")}


def test_clean_log():
    r = parse_log(LOGS["clean"]); assert r.ok and r.overfull == [] and not r.rerun_needed


def test_overfull_threshold():
    r = parse_log(LOGS["overfull"], 10.0)
    assert [round(o["pt"], 1) for o in r.overfull] == [23.4, 23.4] and r.overfull_total == 3


def test_overfull_threshold_lowered_keeps_all():
    assert len(parse_log(LOGS["overfull"], 1.0).overfull) == 3


def test_undefined():
    r = parse_log(LOGS["undefined"])
    assert r.undefined_citations == ["smith2020"] and r.undefined_references == ["fig:one"]


def test_error_with_file_line():
    r = parse_log(LOGS["error"])
    assert not r.ok and r.errors[0]["file"].endswith("sections/method.tex") and r.errors[0]["line"] == 42
    assert len(r.errors) == 2


def test_classic_error_takes_line_from_l_marker():
    e = parse_log(LOGS["error"]).errors[1]
    assert e == {"file": None, "line": 42, "message": "Undefined control sequence."}


def test_rerun():
    assert parse_log(LOGS["rerun"]).rerun_needed


def test_wrapped_overfull_line():
    assert len(parse_log(LOGS["crlf_wrapped"], 10.0).overfull) == 2


def test_wrapped_citation_warning():
    full = "LaTeX Warning: Citation 'averyveryverylongcitationkey2020' on page 3 undefined on input line 57."
    first, rest = full[:79], full[79:]
    assert len(first) == 79
    text = "(./main.tex\n" + first + "\n" + rest + "\n\n) [1]\n"
    r = parse_log(text)
    assert r.undefined_citations == ["averyveryverylongcitationkey2020"]
    assert parse_log(text.replace("\n", "\r\n")).undefined_citations == ["averyveryverylongcitationkey2020"]


def test_wrapped_citation_key_split_across_lines():
    # The ruled case above splits after the key; here column 79 falls inside the key,
    # so the citation is only found if the two physical lines are rejoined.
    key = "averyveryverylongcitationkeythatcrossesthewrapcolumn2020"
    full = f"LaTeX Warning: Citation '{key}' on page 3 undefined on input line 57."
    assert 24 < 79 < 25 + len(key)
    text = full[:79] + "\r\n" + full[79:] + "\r\n"
    assert parse_log(text).undefined_citations == [key]


def test_79_char_line_not_joined_into_next_message():
    line79 = "x" * 79
    text = line79 + "\n! Undefined control sequence.\nl.7 \\foo\n"
    r = parse_log(text)
    assert r.errors == [{"file": None, "line": 7, "message": "Undefined control sequence."}]


def test_package_warning():
    text = "Package hyperref Warning: Token not allowed in a PDF string\n(hyperref)                removing `math shift' on input line 3.\n"
    assert parse_log(text).package_warnings == ["hyperref: Token not allowed in a PDF string"]


def test_to_dict_roundtrips_json():
    d = parse_log(LOGS["undefined"]).to_dict()
    assert json.loads(json.dumps(d))["undefined_citations"] == ["smith2020"]
    assert set(d) >= {"errors", "undefined_citations", "undefined_references", "overfull",
                      "overfull_total", "rerun_needed", "package_warnings", "ok"}


def test_cli_exit_codes(capsys, tmp_path):
    assert latex_log.main([str(LOG_DIR / "clean.log")]) == 0
    assert latex_log.main([str(LOG_DIR / "error.log"), "--json"]) == 1
    out = capsys.readouterr().out
    assert json.loads(out[out.index("{"):])["ok"] is False
    assert latex_log.main([str(tmp_path / "missing.log")]) == 2
