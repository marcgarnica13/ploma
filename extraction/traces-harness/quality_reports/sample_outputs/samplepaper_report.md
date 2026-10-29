# Proofreading Report: manuscript/samplepaper.tex

**Date:** 2026-06-04 (full-audit). Build: clean, 13 pp, **no overfull hbox**; one cosmetic underfull
at the StatsBomb URL in the bibliography. No source files edited — report only.

## HIGH severity (8)

1. **TYPO** L51 "steming" → "stemming".
2. **GRAMMAR/QUALITY** L51 "what is going on the sports field is at a very high level" — missing
   preposition + redundant "level…at a very high level". Rewrite (e.g., "what is happening on the
   pitch is reconstructed in high detail").
3. **CONSISTENCY** L51 bare `\cite{Davis202207} divided…` — a numeric `\cite` cannot be the sentence
   subject → "Davis et al.~\cite{Davis202207} divided…".
4. **GRAMMAR** L68 "to provide a analysis" → "an analysis".
5. **TYPO** L68 "event data source\cite{Decroos2020}" → add space "source~\cite{Decroos2020}".
6. **TYPO** L70 "infering" → "inferring".
7. **GRAMMAR** L70 "We complement the approach presented by Chan et al. \cite{Chan2025} inferring a
   process model…" — missing "by": "…\cite{Chan2025} **by** inferring a process model…".
8. **CONSISTENCY** "Heuristic map" capitalization drift — L43 "Heuristic map", L106 "Heuristic maps",
   L108 "heuristic map", L113 caption uses BOTH "Heuristic Map" and "Heuristic map", L168 "player
   heuristic map", L179 "Heuristic map". Pick one form (recommend "heuristic map", parallel to "Petri
   net"/"Heuristic net") and apply throughout. Worst offender: the L113 caption.

## MEDIUM severity (selected)

9. L53 "the developing of offensive and defensive tactics" — awkward; also **overclaim**: paper studies
   only offensive (box penetration). "models the development of offensive [and defensive — drop or
   scope] tactics".
10. L53 "event data is interpreted as a time-ordered sequence of events, includes key attributes…" —
    "includes" has no subject (comma splice) → "…sequence of events that include key attributes…".
11. L60 "the actual processes (intend)" → "(intent)".
12. L60 "deviations between the theoretical processes … with the processes seen in reality" → "…
    **and** the processes seen in reality".
14. L62 "the discovering algorithm" → "the discovery algorithm" (matches L87).
15. L62 "are scarce, however, in physical flows…" — comma splice → "…are scarce; however, …".
16. L62 fragment "Mainly because the discovering algorithm cannot assume all behavior is reported." —
    merge into prior sentence.
17. L62 "Petri Nets" vs "Petri net" (L102/104) — lowercase "nets".
18. L68 "PM has been preliminary explored" → "preliminarily explored".
19. L72 **leftover author comment** `%IMPORTANT NOT TO MISS THIS AT THE CONCUSIONS…` (also typo
    "CONCUSIONS"). Remove before submission — its content (DFG can't be replayed) is already in the body.
20. **Traceability:** "19 of 20 teams" appears ONLY in the abstract (L43); the body/Table never
    restates it. Add it to §5.2 so the headline number is supported in-text.
24. L87 zone-count notation drift: "$|Z|=24$" then "$K$" for the same quantity → use one (define
    $K=|Z|=24$). (INV-7.)
26. L168 "Figure~\ref{fig:player_map}" → "Fig.~\ref{…}" (rest of paper uses "Fig.").
31. **Tension:** L119 "$\theta=0.90$ … at no cost in fitness or precision" vs L146 "HM gives up a
    portion of fitness". The "no cost" refers to threshold choice (0.9 vs others), not HM vs DFG —
    reword to avoid reading as a contradiction.
34. **Overclaim/traceability:** abstract (L43) says "replicated on 2021/2022", but the body (§5.1,
    L119) reports only 2022/23 (290 matches) — the replication is never presented. Either add one
    sentence with the 2021/22 result (it exists in `results/.../108/`) or soften the abstract.

## LOW severity (selected)

22. L53 "esthetically" → "aesthetically".
23. L102/104 "PM4PY" → "PM4Py" (canonical).
25. L168 double space "model  all" → single space.
27. L97 "Heuristic Miner" vs L119 "Heuristic-Miner" — pick one hyphenation; abbreviation (HM) defined twice.
28. "directly-follows graph" vs "directly-follows-graph" — standardize bare-noun form.
29. L118 subsection title "Data and Methods" → sentence case "Data and methods" (matches siblings).
30. L51 straight single quotes around the analyst questions → LaTeX directional quotes `` `…' ``.
32. L51 "intended to perform" → "intends to perform" (tense).
33. L43 "2022/2023"/"2021/2022" → "2022/23"/"2021/22" (match body).
36. L176 "micro contributions" → "micro-contributions".
38. terminology: "intend/intent/intention/purpose" for the unobserved plan — standardize on "purpose".

## Counts

- HIGH 8 · MEDIUM ~13 · LOW ~17. No overfull boxes. No fabricated content found.
- **Most impactful before submission:** the 8 HIGH typos/grammar (all in §1–§2), the "Heuristic map"
  capitalization sweep, and the two traceability items (#20 "19 of 20" and #34 "2021/22 replication"
  not in the body).
