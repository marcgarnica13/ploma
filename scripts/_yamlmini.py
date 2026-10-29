"""Fallback loader for the YAML subset ploma uses when PyYAML is absent.

Block maps and lists, inline ``[a, b]``/``{k: v}``, quoted and bare scalars
with PyYAML's YAML 1.1 typing (dates stay strings), comments. Anchors,
aliases, tags, ``|``/``>`` scalars, tab indents and ``---`` raise.
"""
from __future__ import annotations

import re
from typing import Any

_INT = re.compile(r"^[-+]?(0|[1-9][0-9_]*)$")
_FLOAT = re.compile(r"^[-+]?([0-9][0-9_]*)?\.[0-9_]*([eE][-+][0-9]+)?$")
_WORDS = {"true": True, "yes": True, "on": True, "false": False, "no": False, "off": False,
          "~": None, "null": None, ".inf": float("inf"), "+.inf": float("inf"),
          "-.inf": float("-inf"), ".nan": float("nan")}
_PLAIN_OK = re.compile(r"^[A-Za-z0-9_./()+$^=~<>-][^:#\n]*$")
_ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "/": "/", "0": "\0"}
_ANCHOR = "anchors, aliases and tags are not supported"
_BAD_START = {"&": _ANCHOR, "*": _ANCHOR, "!": _ANCHOR, "|": "block scalars (| and >) are not supported",
              ">": "block scalars (| and >) are not supported", "@": "reserved indicator '@'",
              "`": "reserved indicator '`'", "%": "directives are not supported"}


class YamlMiniError(ValueError):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def _scan(s: str):
    """Yield (index, char, bracket depth) for characters outside quoted strings."""
    quote, depth = "", 0
    for i, ch in enumerate(s):
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"" and (i == 0 or s[i - 1] in " \t:[{,-"):
            quote = ch
        else:
            depth += (ch in "[{") - (ch in "]}")
            yield i, ch, depth


def _strip_comment(s: str) -> str:
    for i, ch, _ in _scan(s):
        if ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


def _find_colon(s: str) -> int:
    """Index of the key separator (``:`` then space or end), outside quotes and brackets."""
    for i, ch, depth in _scan(s):
        if ch == ":" and depth == 0 and (i + 1 == len(s) or s[i + 1] == " "):
            return i
    return -1


def _split_flow(s: str) -> list[str]:
    parts, start = [], 0
    for i, ch, depth in _scan(s):
        if ch == "," and depth == 0:
            parts.append(s[start:i].strip())
            start = i + 1
    if s[start:].strip():
        parts.append(s[start:].strip())
    return parts


def _scalar(s: str, line: int) -> Any:
    s = s.strip()
    if not s:
        return None
    if s[0] in _BAD_START:
        raise YamlMiniError(line, _BAD_START[s[0]])
    if s[0] in "[{":
        if s[-1] != {"[": "]", "{": "}"}[s[0]]:
            raise YamlMiniError(line, "unterminated inline collection")
        if s[0] == "[":
            return [_scalar(p, line) for p in _split_flow(s[1:-1])]
        out = {}
        for p in _split_flow(s[1:-1]):
            c = _find_colon(p)
            if c < 0:
                raise YamlMiniError(line, f"inline map entry without ': ' in {p!r}")
            out[_key(p[:c], line)] = _scalar(p[c + 1:], line)
        return out
    if s[0] == '"':
        if len(s) < 2 or not s.endswith('"') or s.endswith('\\"') and not s.endswith('\\\\"'):
            raise YamlMiniError(line, "unterminated double-quoted string")
        return re.sub(r'\\(.)', lambda m: _ESC.get(m.group(1), "\\" + m.group(1)), s[1:-1])
    if s[0] == "'":
        if len(s) < 2 or not s.endswith("'") or "'" in s[1:-1].replace("''", ""):
            raise YamlMiniError(line, "unterminated single-quoted string")
        return s[1:-1].replace("''", "'")
    if _find_colon(s) >= 0:
        raise YamlMiniError(line, f"unexpected mapping in scalar {s!r}")
    low = s.lower()
    if low in _WORDS:
        return _WORDS[low]
    if _INT.match(s):
        return int(s.replace("_", ""))
    if _FLOAT.match(s) and any(c.isdigit() for c in s):
        return float(s.replace("_", ""))
    return s


def _key(k: str, line: int) -> Any:
    v = _scalar(k, line)
    if k.strip().startswith("?") or isinstance(v, (list, dict)):
        raise YamlMiniError(line, "complex and collection keys are not supported")
    return v


class _Parser:
    def __init__(self, text: str) -> None:
        self.lines: list[list[Any]] = []  # [lineno, indent, content]
        for no, raw in enumerate(text.splitlines(), 1):
            lead = raw[: len(raw) - len(raw.lstrip(" \t"))]
            if "\t" in lead and raw.strip():
                raise YamlMiniError(no, "tabs are not allowed for indentation")
            content = _strip_comment(raw.strip())
            if not content:
                continue
            if content.startswith(("---", "...")) and (len(content) == 3 or content[3] == " "):
                raise YamlMiniError(no, "document separators are not supported")
            self.lines.append([no, len(lead), content])
        self.i = 0

    @staticmethod
    def _is_item(content: str) -> bool:
        return content == "-" or content.startswith("- ")

    def parse(self) -> Any:
        value = self.block(self.lines[0][1]) if self.lines else None
        if self.i < len(self.lines):
            raise YamlMiniError(self.lines[self.i][0], "unexpected indentation")
        return value

    def block(self, indent: int) -> Any:
        no, ind, content = self.lines[self.i]
        if ind != indent:
            raise YamlMiniError(no, "unexpected indentation")
        if self._is_item(content):
            return self.seq(indent)
        if _find_colon(content) < 0:
            self.i += 1
            return _scalar(content, no)
        return self.map(indent)

    def child(self, indent: int, allow_same_indent_seq: bool) -> Any:
        """Value on the following lines for a key or item with an empty inline value."""
        if self.i < len(self.lines):
            _, ind, content = self.lines[self.i]
            if ind > indent or (allow_same_indent_seq and ind == indent and self._is_item(content)):
                return self.block(ind)
        return None

    def map(self, indent: int) -> dict:
        out: dict = {}
        while self.i < len(self.lines):
            no, ind, content = self.lines[self.i]
            if ind < indent:
                break
            if ind > indent:
                raise YamlMiniError(no, "unexpected indentation")
            if self._is_item(content):
                raise YamlMiniError(no, "list item where a mapping key was expected")
            c = _find_colon(content)
            if c < 0:
                raise YamlMiniError(no, f"expected 'key: value', got {content!r}")
            key = _key(content[:c], no)
            rest = content[c + 1:].strip()
            self.i += 1
            out[key] = _scalar(rest, no) if rest else self.child(indent, True)
        return out

    def seq(self, indent: int) -> list:
        out: list = []
        while self.i < len(self.lines):
            no, ind, content = self.lines[self.i]
            if ind < indent or (ind == indent and not self._is_item(content)):
                break
            if ind > indent:
                raise YamlMiniError(no, "unexpected indentation")
            rest = content[1:].lstrip(" ")
            if not rest:
                self.i += 1
                out.append(self.child(indent, False))
            elif self._is_item(rest) or (rest[0] not in "[{" and _find_colon(rest) >= 0):
                # "- k: v" or "- - x": re-read the rest as a line at a deeper indent
                self.lines[self.i] = [no, indent + len(content) - len(rest), rest]
                out.append(self.block(indent + len(content) - len(rest)))
            else:
                self.i += 1
                out.append(_scalar(rest, no))
        return out


def load(text: str) -> Any:
    return _Parser(text).parse()


def _dump_scalar(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return "{}" if isinstance(v, dict) else "[]"
    if v is None or isinstance(v, bool):
        return {None: "null", True: "true", False: "false"}[v]
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return ".nan" if v != v else ".inf" if v > 0 else "-.inf"
        r = repr(v)
        return r if "." in r else r.replace("e", ".0e") if "e" in r else r + ".0"
    s = str(v)
    plain = _PLAIN_OK.match(s) and s == s.strip() and s != "-" and not s.startswith("- ")
    if plain and isinstance(_scalar(s, 0), str):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def _dump(data: Any, indent: int, level: int) -> list[str]:
    pad = " " * (indent * level)
    lines: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = _dump_scalar(k)
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{key}:")
                lines.extend(_dump(v, indent, level + 1))
            else:
                lines.append(f"{pad}{key}: {_dump_scalar(v)}")
    elif isinstance(data, list):
        for v in data:
            if isinstance(v, (dict, list)) and v:
                sub = _dump(v, indent, level + 1)
                lines.append(f"{pad}{'-'.ljust(indent)}{sub[0][len(pad) + indent:]}")
                lines.extend(sub[1:])
            else:
                lines.append(f"{pad}- {_dump_scalar(v)}")
    else:
        lines.append(pad + _dump_scalar(data))
    return lines


def dump(data: Any, indent: int = 2) -> str:
    return "\n".join(_dump(data, max(indent, 2), 0)) + "\n"
