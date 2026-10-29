"""Domain terms banned from shipped generic files (global constraints). Reused by later tests.

``llncs`` (the document class) is banned too outside ``venues/`` and ``inventory.py``; it is
kept separate as LLNCS_RE so venue files, which name the class, can use BANNED_RE alone.
LLNCS_RE does not match the venue key ``llncs-conference`` (Ruling R52).
"""
from __future__ import annotations

import re

BANNED_TERMS = ("soccer", "football", "pm4py", "possession", "pitch", "StatsBomb", "Wyscout",
                "action##zone", "TAGS_FILE", "MONGO", "samplepaper", "mybib", "sports_pm",
                "heuristic net")
BANNED_RE = re.compile("|".join(re.escape(t) for t in BANNED_TERMS), re.IGNORECASE)
LLNCS_RE = re.compile(r"llncs(?!-conference)", re.IGNORECASE)
EM_DASH_RE = re.compile("[—–]")
