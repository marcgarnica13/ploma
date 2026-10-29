#!/usr/bin/env python3
"""Prose style check: sentence-level em-dashes, slop phrases and long sentences.

Usage:
  python3 scripts/style_check.py [file ...] [--root R] [--allow-em-dash] [--phrases a,b]
                                 [--max-words N] [--json]

With files, checks each file; with --root and no files, checks document.main and every file it
reaches through \\input or \\include, using style.forbid_em_dash and style.forbid_phrases from
ploma.yaml; with neither, reads stdin. LaTeX comments, the arguments of \\cite, \\ref, \\label,
\\url, \\href (first argument), \\doi, \\path, \\nolinkurl, \\includegraphics, \\eqref, \\input and
\\include, inline math and display math environments are blanked before matching, and so are tables,
verbatim environments (verbatim, Verbatim, lstlisting, minted, comment), environment names in
\\begin and \\end, and the preamble. The periods of "e.g.", "i.e." and "et al." do not end a sentence.

Rules:
  style.em_dash.<file>:<line>:<col>        WARN  U+2014, the LaTeX --- ligature, or a spaced U+2013, in prose
  style.slop.<file>:<line>:<col>           WARN  a phrase from SLOP_PHRASES or style.forbid_phrases (named
                                                 in the summary)
  style.long_sentence.<file>:<line>:<col>  INFO  a sentence longer than --max-words words (default 30)
<file> is the path relative to --root, the path as given, or "stdin"; <col> is 1-based.

Exit codes: 0 no FAIL (style findings are WARN or INFO), 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _texmask  # noqa: E402
import bib_check  # noqa: E402
from _findings import INFO, WARN, Finding, render, worst  # noqa: E402

SLOP_PHRASES: list[str] = [
    "delve", "leverage", "it is worth noting", "in this paper we", "crucial", "robust framework",
    "paradigm", "in today's", "a testament to", "landscape",
]
MAX_SENTENCE_WORDS = 30

MASKED_ARGS: dict[str, int | None] = {
    **{name: None for name in ("ref", "eqref", "autoref", "cref", "Cref", "pageref", "nameref", "label",
                               "url", "includegraphics", "input", "include", "doi", "path", "nolinkurl")},
    "href": 1,
}
_EM_RE = re.compile("\u2014|(?<!-)---(?!-)|(?<=\\s)\u2013|\u2013(?=\\s)")
_BREAK_RE = re.compile(r"[.!?](?=[\s}]|$)|\n[ \t]*\n|\\(?:part|chapter|section|subsection|subsubsection|paragraph|"
                       r"item|begin|end|caption|footnote|maketitle)\b|\\\\")
VERBATIM_ENVS = ("verbatim", "verbatim*", "Verbatim", "BVerbatim", "lstlisting", "minted", "comment")
_ENV_NAME_RE = re.compile(r"(\\(?:begin|end)\s*\{)([^{}]*)(\})")
# Periods of these abbreviations do not end a sentence.
_ABBREV_RE = re.compile(r"(?<![A-Za-z])(?:e\.g|i\.e|et\s+al)\.")
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019-]*")
_CMD_NAME_RE = re.compile(r"\\[A-Za-z]+\*?")


def _phrase_re(phrase: str) -> re.Pattern:
    words = [re.escape(w) for w in phrase.split()]
    # A one-word phrase also catches inflections such as "leveraged"; longer phrases match whole words.
    tail = r"\w*" if len(words) == 1 else r"(?!\w)"
    return re.compile(r"(?<![\w])" + r"\s+".join(words) + tail, re.I)


def prose(text: str) -> str:
    """text with everything but prose blanked (same length, newlines kept)."""
    out = _texmask.strip_comments(text)
    out = _texmask.mask_before_document(out)
    out = _texmask.mask_command_args(out, MASKED_ARGS)
    out = _texmask.mask_math(out)
    for start, _, end in _texmask.env_spans(out, ("tabular", "tabular*", "tabularx", "tabulary", "longtable")
                                            + VERBATIM_ENVS):
        out = _texmask.blank_span(out, start, end)
    # Environment names (\begin{landscape}) are markup, not prose; \begin and \end stay for sentence breaks.
    return _ENV_NAME_RE.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), out)


def run(text: str, *, forbid_em_dash: bool, extra_phrases: list[str], max_sentence_words: int = MAX_SENTENCE_WORDS,
        file: str = "") -> list[Finding]:
    masked = prose(text)
    lines = _texmask.LineIndex(masked)
    src_lines = text.split("\n")
    hits: list[tuple[int, Finding]] = []

    label = file or "stdin"

    def where(offset: int) -> tuple[str, str]:
        line = lines.line(offset)
        col = offset - (masked.rfind("\n", 0, offset) + 1) + 1
        loc = f"{label}:{line}:{col}"
        return loc, f"{loc}: {src_lines[line - 1].strip()[:120]}"

    if forbid_em_dash:
        for m in _EM_RE.finditer(masked):
            loc, obs = where(m.start())
            hits.append((m.start(), Finding(f"style.em_dash.{loc}", WARN, "em-dash used as sentence punctuation",
                                            observed=obs, remediation="Split the sentence or use a comma, colon "
                                            "or parentheses.", group="style")))
    phrases = list(dict.fromkeys([p.lower() for p in SLOP_PHRASES] + [p.lower() for p in extra_phrases if p.strip()]))
    for phrase in phrases:
        for m in _phrase_re(phrase).finditer(masked):
            loc, obs = where(m.start())
            hits.append((m.start(), Finding(f"style.slop.{loc}", WARN,
                                            f"slop phrase \"{phrase}\"", observed=obs,
                                            remediation="Say it plainly, or cut it.", group="style")))
    words_only = _CMD_NAME_RE.sub(lambda m: " " * len(m.group()), masked)
    breakable = _ABBREV_RE.sub(lambda m: m.group()[:-1] + " ", masked)
    start = 0
    for b in list(_BREAK_RE.finditer(breakable)) + [None]:
        end = b.start() if b else len(masked)
        words = list(_WORD_RE.finditer(words_only, start, end))
        if len(words) > max_sentence_words:
            loc, obs = where(words[0].start())
            hits.append((words[0].start(), Finding(f"style.long_sentence.{loc}", INFO,
                                                   f"sentence of {len(words)} words (over {max_sentence_words})",
                                                   observed=obs, remediation="Split it into shorter sentences.",
                                                   group="style")))
        start = b.end() if b else end
    hits.sort(key=lambda h: h[0])
    return [f for _, f in hits]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prose style check: em-dashes, slop phrases, long sentences.")
    parser.add_argument("files", nargs="*", help="files to check (default: stdin, or the manuscript with --root)")
    parser.add_argument("--root", help="repo root holding ploma.yaml")
    parser.add_argument("--allow-em-dash", action="store_true", help="do not flag em-dashes")
    parser.add_argument("--phrases", default="", help="comma-separated extra phrases to flag")
    parser.add_argument("--max-words", type=int, default=None, help=f"long sentence threshold "
                        f"(default {MAX_SENTENCE_WORDS})")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    def fail(msg: str) -> int:
        print(json.dumps({"error": msg}) if args.json else f"style_check: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2

    forbid = not args.allow_em_dash
    extra = [p.strip() for p in args.phrases.split(",") if p.strip()]
    inputs: list[tuple[str, str]] = []
    if args.root:
        import ploma_config
        root = Path(args.root).resolve()
        try:
            cfg = ploma_config.load(root)
        except ploma_config.ConfigError as exc:
            return fail(exc.message)
        style = cfg.get("style") or {}
        if not args.allow_em_dash:
            forbid = style.get("forbid_em_dash", True) is not False
        extra += [p for p in (style.get("forbid_phrases") or []) if isinstance(p, str)]
        if not args.files:
            main_path = ploma_config.resolve(cfg, root)["_paths"]["main"]
            if not main_path or not Path(main_path).is_file():
                return fail(f"cannot read main file {main_path or '(document.main not set)'}")
            args.files = [str(p) for p in bib_check.tex_sources(Path(main_path))]
    else:
        root = None
    for name in args.files:
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return fail(f"cannot read {name}: {exc.strerror or exc}")
        label = name
        if root is not None:
            try:
                label = path.resolve().relative_to(root).as_posix()
            except ValueError:
                pass
        inputs.append((label, text))
    if not args.files:
        inputs.append(("", sys.stdin.read()))

    findings: list[Finding] = []
    for label, text in inputs:
        findings += run(text, forbid_em_dash=forbid, extra_phrases=extra,
                        max_sentence_words=args.max_words or MAX_SENTENCE_WORDS, file=label)
    if args.json:
        print(json.dumps({"verdict": worst(findings), "findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        print(f"style_check: {len(findings)} finding(s)")
        if findings:
            print(render(findings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
