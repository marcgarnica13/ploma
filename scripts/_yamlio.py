"""YAML I/O for ploma: PyYAML when installed, else the bundled subset loader."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import _yamlmini

try:
    import yaml as _yaml
    LOADER = "pyyaml"
except ImportError:
    _yaml = None
    LOADER = "yamlmini"


class YamlError(ValueError):
    """Raised when a YAML file cannot be parsed by the active loader."""


def _normalise(data: Any) -> Any:
    """Convert dates and datetimes to ISO strings, recursively, so both loaders agree."""
    if isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    if isinstance(data, dict):
        return {_normalise(k): _normalise(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_normalise(v) for v in data]
    return data


def loads_yaml(text: str) -> Any:
    if _yaml is not None:
        try:
            return _normalise(_yaml.safe_load(text))
        except _yaml.YAMLError as exc:
            raise YamlError(str(exc)) from exc
    try:
        return _normalise(_yamlmini.load(text))
    except _yamlmini.YamlMiniError as exc:
        raise YamlError(str(exc)) from exc


def load_yaml(path: Path) -> Any:
    return loads_yaml(Path(path).read_text(encoding="utf-8"))


def dump_yaml(data: Any) -> str:
    if _yaml is not None:
        # width: never fold long strings; _yamlmini cannot read multi-line plain scalars.
        return _yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True, width=10**9)
    return _yamlmini.dump(data)
