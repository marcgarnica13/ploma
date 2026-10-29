"""Domain terms banned from shipped generic files (global constraints). Reused by later tests.

``llncs`` is banned too outside ``venues/`` and ``inventory.py``; it is kept separate as
LLNCS_RE so venue files, which legitimately name the class, can use BANNED_RE alone.
"""
from __future__ import annotations

import re

BANNED_TERMS = ("soccer", "football", "pm4py", "possession", "pitch", "StatsBomb", "Wyscout",
                "action##zone", "TAGS_FILE", "MONGO", "samplepaper", "mybib", "sports_pm",
                "heuristic net")
BANNED_RE = re.compile("|".join(re.escape(t) for t in BANNED_TERMS), re.IGNORECASE)
LLNCS_RE = re.compile(r"llncs", re.IGNORECASE)
EM_DASH_RE = re.compile("[—–]")
