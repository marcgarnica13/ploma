"""LaTeX masking helpers shared by the consistency, style and placeholder checks.

Every function returns text of the same length as its input: masked characters become spaces and
newlines are kept, so offsets and line numbers in the masked text match the source file.
"""
from __future__ import annotations

import bisect
import re
from typing import Iterable

from bib_check import strip_comment

_CMD_RE = re.compile(r"\\([A-Za-z]+)\*?")
_OPEN = {"{": "}", "[": "]", "(": ")"}
DISPLAY_MATH_ENVS = ("equation", "align", "gather", "multline", "eqnarray", "displaymath", "math", "flalign",
                     "alignat")
_DISPLAY_RE = re.compile(r"\\begin\s*\{(" + "|".join(DISPLAY_MATH_ENVS) + r")(\*?)\}.*?\\end\s*\{\1\2\}", re.S)


def blank(text: str) -> str:
    """Spaces for every character except newlines."""
    return re.sub(r"[^\n]", " ", text)


def blank_span(text: str, start: int, end: int) -> str:
    return text[:start] + blank(text[start:end]) + text[end:]


def strip_comments(text: str) -> str:
    """Blank every LaTeX comment (from an unescaped ``%`` to the end of its line)."""
    out = []
    for line in text.split("\n"):
        code = strip_comment(line)
        out.append(code + " " * (len(line) - len(code)))
    return "\n".join(out)


def group_end(text: str, i: int) -> int:
    """Index just past the group opening at text[i] (``{``, ``[`` or ``(``), or -1 when unbalanced."""
    opener = text[i]
    closer = _OPEN[opener]
    depth = 0
    j = i
    while j < len(text):
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def arg_spans(text: str, i: int, *, parens: bool = False) -> list[tuple[str, int, int]]:
    """Consecutive ``[..]`` and ``{..}`` groups starting at i, separated by spaces or tabs only.

    Returns (opener, start, end) per group. ``(..)`` groups count too when parens is true.
    """
    spans: list[tuple[str, int, int]] = []
    openers = "[{(" if parens else "[{"
    while True:
        j = i
        while j < len(text) and text[j] in " \t":
            j += 1
        if j >= len(text) or text[j] not in openers:
            return spans
        end = group_end(text, j)
        if end < 0:
            return spans
        spans.append((text[j], j, end))
        i = end


def mask_command_args(text: str, rules: dict[str, int | None], *, cite_like: bool = True) -> str:
    """Blank the arguments of commands named in rules.

    rules maps a command name to None (blank every following group) or n (blank the groups up to and
    including the n-th brace group). With cite_like, every command whose name contains ``cite`` is
    blanked as None.
    """
    out = text
    for m in _CMD_RE.finditer(text):
        name = m.group(1)
        if name in rules:
            limit = rules[name]
        elif cite_like and "cite" in name:
            limit = None
        else:
            continue
        spans = arg_spans(text, m.end(), parens=name in ("cmidrule",))
        braces = 0
        for opener, start, end in spans:
            if limit is not None and braces >= limit:
                break
            out = blank_span(out, start, end)
            if opener == "{":
                braces += 1
    return out


def math_spans(text: str) -> list[tuple[int, int]]:
    """Spans of inline math ($..$, $$..$$, \\(..\\), \\[..\\]) and display math environments."""
    spans = [(m.start(), m.end()) for m in _DISPLAY_RE.finditer(text)]
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            if text[i + 1] in "([":
                close = "\\)" if text[i + 1] == "(" else "\\]"
                end = text.find(close, i + 2)
                if end >= 0:
                    spans.append((i, end + 2))
                    i = end + 2
                    continue
            i += 2
            continue
        if c == "$":
            double = text.startswith("$$", i)
            delim = "$$" if double else "$"
            j = i + len(delim)
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text.startswith(delim, j):
                    break
                j += 1
            if j < n:
                spans.append((i, j + len(delim)))
                i = j + len(delim)
                continue
        i += 1
    return spans


def mask_math(text: str) -> str:
    out = text
    for start, end in math_spans(text):
        out = blank_span(out, start, end)
    return out


def mask_before_document(text: str) -> str:
    """Blank the preamble when the text has ``\\begin{document}``, and anything after ``\\end{document}``."""
    m = re.search(r"\\begin\s*\{document\}", text)
    if m:
        text = blank(text[:m.end()]) + text[m.end():]
    m = re.search(r"\\end\s*\{document\}", text)
    if m:
        text = text[:m.start()] + blank(text[m.start():])
    return text


def env_spans(text: str, names: Iterable[str]) -> list[tuple[int, int, int]]:
    """(begin_start, content_start, end_end) for each environment in names, outermost first match."""
    alt = "|".join(re.escape(n) for n in names)
    out = []
    for m in re.finditer(r"\\begin\s*\{(" + alt + r")\}", text):
        end = re.compile(r"\\end\s*\{" + re.escape(m.group(1)) + r"\}").search(text, m.end())
        if end:
            out.append((m.start(), m.end(), end.end()))
    return out


class LineIndex:
    """Map character offsets to 1-based line numbers."""

    def __init__(self, text: str) -> None:
        self._starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self._starts, offset)
