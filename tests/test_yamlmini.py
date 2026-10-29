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
