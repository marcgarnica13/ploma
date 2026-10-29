"""Tests for the fallback YAML subset loader."""
from __future__ import annotations

from pathlib import Path

import pytest

import _yamlio
import _yamlmini

FIXTURE = Path(__file__).parent / "fixtures" / "yaml" / "ploma_full.yaml"


def test_loads_spec_example_identically_to_pyyaml():
    text = FIXTURE.read_text()
    yaml = pytest.importorskip("yaml")
    assert _yamlmini.load(text) == _yamlio._normalise(yaml.safe_load(text))


def test_scalars():
    assert _yamlmini.load("a: 1\nb: 1.5\nc: true\nd: null\ne: 'x'\nf: \"y\"\ng: 2026-10-29") == {
        "a": 1, "b": 1.5, "c": True, "d": None, "e": "x", "f": "y", "g": "2026-10-29"}


def test_inline_list_and_map():
    assert _yamlmini.load("k: [a, 2, true]\nm: {x: 1, y: z}") == {"k": ["a", 2, True], "m": {"x": 1, "y": "z"}}


def test_list_of_maps():
    assert _yamlmini.load("e:\n  - a: 1\n    b: 2\n  - a: 3") == {"e": [{"a": 1, "b": 2}, {"a": 3}]}


def test_anchor_raises():
    with pytest.raises(_yamlmini.YamlMiniError) as e:
        _yamlmini.load("a: &x 1\nb: *x")
    assert e.value.line == 1


def test_tab_indent_raises():
    with pytest.raises(_yamlmini.YamlMiniError):
        _yamlmini.load("a:\n\tb: 1")


def test_dump_round_trips_spec_example():
    data = _yamlmini.load(FIXTURE.read_text())
    assert _yamlmini.load(_yamlmini.dump(data)) == data


@pytest.mark.parametrize("value", [">gt", ">= 0.5", "|pipe", "&amp", "*star", "!tag", "%pct", "@at", "`tick",
                                   "- dash", "-", "a: b", "x #y", "", " pad", "yes", "1.5", "null", "2026-10-29"])
def test_dump_round_trips_indicator_strings(value):
    data = {"k": value, "l": [value], "m": {value or "e": value}}
    assert _yamlmini.load(_yamlmini.dump(data)) == data


def test_multi_line_plain_scalar_names_the_problem():
    with pytest.raises(_yamlmini.YamlMiniError, match="multi-line plain scalars are not supported; quote the value"):
        _yamlmini.load("document:\n  title: A long title that PyYAML\n    wrapped onto a second line\n  slug: x\n")
    with pytest.raises(_yamlmini.YamlMiniError, match="multi-line plain scalars are not supported"):
        _yamlmini.load("keys:\n- a long item\n  continued\n")


def test_pyyaml_dump_of_a_long_title_loads_with_yamlmini():
    """dump_yaml must not wrap long strings: _yamlmini cannot read PyYAML's folded plain scalars."""
    yaml = pytest.importorskip("yaml")
    import _yamlio
    if _yamlio._yaml is None:
        pytest.skip("PyYAML not active")
    title = "Capturing Team Strategies in Large Organisations via Sequence Mining and Visual Analysis"
    assert len(title) == 88
    data = {"ploma": "0.1", "document": {"type": "paper", "main": "main.tex", "title": title, "slug": "main"},
            "build": {"bib_files": ["refs.bib"], "command": "make"}, "note": "café " * 30}
    text = _yamlio.dump_yaml(data)
    assert _yamlmini.load(text) == data
    assert "café" in text and list(_yamlmini.load(text)) == ["ploma", "document", "build", "note"]
