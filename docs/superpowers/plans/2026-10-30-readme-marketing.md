# ploma public README, logo and hero film: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the ploma README into a public landing page with a nib logo, a HyperFrames hero film of a real ploma session on a shipped demo paper, four stage stills, and the reference material moved to `docs/`.

**Architecture:** Documentation and assets only; `scripts/`, `skills/`, `hooks/` are untouched. Build sources live under `media/` (logo generator, HyperFrames film, stills, transcripts) and write committed outputs to `assets/` and `.claude-plugin/icon.png`. A new `examples/demo-paper` is the paper every run uses; runs happen in a scratch copy so the example stays at its starting state. Each task adds a pytest file that pins what a reviewer would otherwise check by eye (dash-free prose, resolving links, asset sizes, the designed conflict, the film's line-by-line traceability to the transcripts).

**Tech Stack:** Python 3.10+ and pytest (repo standard); TeX Live (pdflatex, bibtex, latexmk), poppler-utils (pdfinfo, pdftotext, pdftoppm), librsvg2-bin (rsvg-convert), fontTools 4.46 (installed); Node 22.22, npm 10.9, FFmpeg 6.1; HyperFrames pinned to `0.8.166` (published 2026-10-16); GSAP 3.14.2 from jsDelivr as in the HyperFrames template.

**Spec:** `docs/superpowers/specs/2026-10-30-readme-marketing-design.md`

## Global Constraints

- No em-dash or en-dash (`—`, `–`) anywhere under `README.md`, `docs/*.md`, `assets/`, `media/`, `examples/demo-paper/` (the repo test regex is `EM_DASH_RE = re.compile("[—–]")` in `tests/_banned.py`; reuse it). LaTeX page ranges are double hyphens (`324--345`) and are fine.
- British spelling as in the current README ("licence", "colour"). Short direct sentences. No superlatives, no exclamation marks, no "not X but Y".
- Sizes: `assets/film/ploma-hero.gif` at or under 6 MB; each still at or under 300 KB; `assets/film/ploma-hero.mp4` committed only when at or under 4 MB; `du -sh assets` under 12 MB.
- Never commit `media/**/node_modules/`, `media/**/out/`, render caches, `examples/demo-paper/build/`, or the font cache `media/logo/.cache/`.
- Palette: ink `#1d1b17` on paper `#f6f4ef` (light), paper-white `#e8e6e0` on `#14151a` (dark), ink blue `#1f5f8b`, copper `#b4552d` (film and stills accent only, never in the mark).
- Composition 1600 by 1000 at 30 fps, about 25 seconds, five beats with the timings in the spec table.
- Every terminal line in the film and in a still is a line (or a condensation that keeps the words) of a transcript under `media/transcripts/`.
- `examples/sample-paper`, `tests/conftest.py` fixtures, the plugin manifests and `.github/workflows/ci.yml` are not modified. CI has no TeX, Node or network beyond pip, so every new test either needs none of them or skips when the tool is absent (`pytest.skip`).
- Commits are small, on `main`. Each commit message ends with the two attribution lines given in the session (`Co-Authored-By` and `Claude-Session`).
- No version bump. The changelog gets an `## Unreleased` section above `## 0.2.0`.

## Review Focus

1. The README viewed in GitHub dark mode shows a dark lockup, not a black mark on a dark page: the `<picture>` must carry both `prefers-color-scheme` sources (Task 8 test `test_logo_picture_has_both_schemes`).
2. The README viewed from the marketplace listing or a fork still shows every image: asset references are relative paths, never `raw.githubusercontent.com` URLs (Task 8 test `test_asset_references_are_relative`).
3. A dash hidden in SVG `<title>` or `alt` text slips past a prose-only check: the dash scan covers `assets/**/*.svg` and `alt=` attributes (Task 3 test `test_svgs_have_no_dashes`, Task 8 test `test_readme_and_docs_have_no_dashes`).
4. A film line edited for rhythm drifts from what ploma printed: every `text` in `media/film/script.json` must be a substring of a transcript (Task 7 test `test_film_script_lines_trace_to_transcripts`).
5. A later edit to the demo paper removes the designed 31% versus 27.4% conflict and grill has nothing to settle: Task 2 test `test_designed_conflict_is_present` pins both values.

---

### Task 1: Build toolchain on this machine

**Files:**
- Create: `media/README.md` (what `media/` holds, the tools each part needs, and this install line)

**Interfaces:**
- Produces: `pdflatex`, `bibtex`, `latexmk`, `pdfinfo`, `pdftotext`, `pdftoppm`, `rsvg-convert` on PATH for Tasks 2, 3, 6, 7.

- [ ] **Step 1: Install the packages (Marc approved this on 2026-10-30)**

Run:
```bash
sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended latexmk poppler-utils librsvg2-bin
```
Expected: exit 0.

- [ ] **Step 2: Verify**

Run: `for t in pdflatex bibtex latexmk pdfinfo pdftotext pdftoppm rsvg-convert; do command -v $t || echo MISSING $t; done`
Expected: seven paths, no `MISSING`.

- [ ] **Step 3: Write `media/README.md`**

Four short sections: Logo (`media/logo/`), Film (`media/film/`), Stills (`media/stills/`), Transcripts (`media/transcripts/`), each one line on what it produces and where the output is committed, then "Tools" with the apt line above and `npm` for the film. Dash-free.

- [ ] **Step 4: Commit**

```bash
git add media/README.md
git commit -m "docs(media): build tree for logo, film, stills and transcripts"
```

---

### Task 2: Demo paper `examples/demo-paper`

**Files:**
- Create: `examples/demo-paper/ploma.yaml`, `main.tex`, `sections/intro.tex`, `sections/method.tex`, `sections/results.tex`, `refs.bib`, `results/bench.json`, `Makefile`, `.gitignore` (`build/`, `*.aux`, `*.bbl`, `*.blg`, `*.log`, `*.out`, `main.pdf`)
- Test: `tests/test_demo_paper.py`

**Interfaces:**
- Produces: `DEMO = REPO_ROOT / "examples" / "demo-paper"` (tests import `REPO_ROOT` from `tests/conftest.py`); `results/bench.json` keys `latency_cut_vs_otel_pct` (27.4), `latency_cut_vs_rawlogs_pct` (41.2), `storage_ratio` (1.1), `n_frameworks` (3), `n_tasks` (1200); the intro's headline sentence contains `31\%` and names no baseline. Tasks 5 to 7 run ploma on a copy of this directory.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_demo_paper.py
import json, re, shutil, subprocess
import pytest
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

DEMO = REPO_ROOT / "examples" / "demo-paper"

def test_config_loads_and_names_the_metrics():
    import ploma_config
    cfg = ploma_config.load(DEMO)
    assert cfg["document"]["main"] == "main.tex"
    assert cfg["pipeline"]["enabled"] is True
    assert set(cfg["pipeline"]["metric_keys"]) >= {"latency_cut_vs_otel_pct", "latency_cut_vs_rawlogs_pct", "storage_ratio", "n_frameworks"}

def test_designed_conflict_is_present():
    intro = (DEMO / "sections" / "intro.tex").read_text()
    bench = json.loads((DEMO / "results" / "bench.json").read_text())
    assert r"31\%" in intro and "27.4" not in intro
    assert bench["latency_cut_vs_otel_pct"] == 27.4
    assert bench["latency_cut_vs_rawlogs_pct"] == 41.2
    assert "OpenTelemetry" not in intro and "raw log" not in intro.lower()

def test_every_bib_entry_has_a_doi():
    bib = (DEMO / "refs.bib").read_text()
    entries = re.split(r"\n(?=@)", bib.strip())
    assert len(entries) >= 6
    for e in entries:
        assert re.search(r"^\s*doi\s*=", e, re.M), e[:60]

def test_marked_fictional_and_dash_free():
    assert "fictional" in (DEMO / "main.tex").read_text()
    for p in DEMO.rglob("*"):
        if p.suffix in {".tex", ".bib", ".json", ".yaml"}:
            assert not EM_DASH_RE.search(p.read_text()), p

@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="TeX Live not installed")
def test_compiles(tmp_path):
    dst = tmp_path / "demo"; shutil.copytree(DEMO, dst)
    subprocess.run(["make"], cwd=dst, check=True, capture_output=True)
    assert (dst / "main.pdf").is_file()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest tests/test_demo_paper.py -q`
Expected: 5 failed (directory missing).

- [ ] **Step 3: Write the paper**

`ploma.yaml` copies `examples/sample-paper/ploma.yaml` with: `document.title: "Tracing Agentic Workloads at Scale"`, `document.anonymized: false`, `venue.page_budget: 10`, `pipeline.outputs_dir: results`, `pipeline.metric_keys: [latency_cut_vs_otel_pct, latency_cut_vs_rawlogs_pct, storage_ratio, n_frameworks, n_tasks]`, same tolerances. `Makefile` copies the sample's without the `figures/fig1.pdf` dependency. `main.tex`: `article` class, 11pt, a comment header on lines 1 to 3 stating the paper is a fictional demo shipped with ploma so the README film can be reproduced; author `ploma demo`; abstract of four sentences that reports 27.4% against OpenTelemetry and 1.1 times storage.

`sections/intro.tex` (the starting state, deliberately unsettled): four to six sentences on LLM agents issuing thousands of tool calls, tracing stacks losing the causal chain between a decision and the tool result, and the contribution. The headline sentence reads `cuts median trace-query latency by 31\%` and names no baseline. Three contributions. `sections/method.tex`: the causal trace model and the query planner, half a page, with a `\label{sec:method}`. `sections/results.tex`: a `booktabs` table with both baselines (OpenTelemetry 27.4%, raw logs 41.2%) and `%% ploma-source: results/bench.json` above it, `n_tasks` 1200 and three frameworks, `\label{sec:results}`.

`refs.bib`: six to eight real records, each with a DOI, chosen from the distributed-tracing and LLM-agent literature (candidates: Pivot Tracing `10.1145/2815400.2815415`, Canopy `10.1145/3132747.3132749`, plus Dapper's successors, OpenTelemetry-adjacent systems papers and agent benchmarks). Verify every DOI before committing: `python3 scripts/cite_lookup.py --help` shows the call; a DOI that does not resolve is replaced, never kept.

`results/bench.json`: flat object with the five keys and values from Interfaces.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_demo_paper.py -q`
Expected: 5 passed (the compile test runs because Task 1 installed TeX Live).

- [ ] **Step 5: Run the ploma checks that need no model**

Run from `examples/demo-paper`: `python3 ../../scripts/doctor.py | head -3` and `python3 ../../scripts/consistency.py --json | python3 -c "import json,sys; d=json.load(sys.stdin); print([f for f in d.get('findings',[]) if '31' in json.dumps(f)][:1])"`
Expected: doctor shows no FAIL in Toolchain or Config (WARNs about project files are expected before onboard); consistency reports a finding on the 31% sentence. Delete any `quality_reports/` or `.ploma/` the scripts created before committing.

- [ ] **Step 6: Commit**

```bash
git add examples/demo-paper tests/test_demo_paper.py
git commit -m "feat(examples): fictional demo paper for the README film"
```

---

### Task 3: Logo

**Files:**
- Create: `media/logo/build_logo.py`, `media/logo/README.md`
- Create (generated, committed): `assets/logo/ploma-mark.svg`, `ploma-mark-dark.svg`, `ploma-lockup.svg`, `ploma-lockup-dark.svg`, `ploma-mark-512.png`
- Modify: `.claude-plugin/icon.png` (replaced by the 512 px nib), `.gitignore` (add `media/logo/.cache/`)
- Test: `tests/test_logo.py`

**Interfaces:**
- Produces: the five files above; Tasks 6, 7 and 8 reference `assets/logo/ploma-lockup.svg` and `ploma-lockup-dark.svg`; the film inlines the mark path.
- Mark geometry (viewBox `0 0 100 100`, stroke `6`, `stroke-linejoin: round`, `fill: none` for the outline): outline `M50 8 C62 26 74 44 74 60 C74 76 63 88 50 92 C37 88 26 76 26 60 C26 44 38 26 50 8 Z`; slit `M50 52 V92`; breather hole `<circle cx="50" cy="48" r="5">` filled. Colour: light `#1d1b17`, dark `#e8e6e0`, as explicit `stroke`/`fill` attributes.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_logo.py
import struct, xml.etree.ElementTree as ET
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

LOGO = REPO_ROOT / "assets" / "logo"
SVGS = ["ploma-mark.svg", "ploma-mark-dark.svg", "ploma-lockup.svg", "ploma-lockup-dark.svg"]

def _png_size(path):
    b = path.read_bytes(); assert b[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", b[16:24])

def test_svgs_parse_have_viewbox_and_explicit_colours():
    for name in SVGS:
        text = (LOGO / name).read_text()
        root = ET.fromstring(text)
        assert root.get("viewBox")
        assert "currentColor" not in text
        assert ("#e8e6e0" in text) == name.endswith("-dark.svg")
        assert ("#1d1b17" in text) != name.endswith("-dark.svg")

def test_lockups_are_outlined_not_text():
    for name in ("ploma-lockup.svg", "ploma-lockup-dark.svg"):
        assert "<text" not in (LOGO / name).read_text()

def test_svgs_have_no_dashes():
    for name in SVGS:
        assert not EM_DASH_RE.search((LOGO / name).read_text()), name

def test_icon_is_the_512_nib():
    assert _png_size(LOGO / "ploma-mark-512.png") == (512, 512)
    assert _png_size(REPO_ROOT / ".claude-plugin" / "icon.png") == (512, 512)
    assert (LOGO / "ploma-mark-512.png").read_bytes() == (REPO_ROOT / ".claude-plugin" / "icon.png").read_bytes()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest tests/test_logo.py -q`
Expected: 4 failed.

- [ ] **Step 3: Write `media/logo/build_logo.py`**

`python3 media/logo/build_logo.py` (no arguments) writes the five files and `.claude-plugin/icon.png`. Functions: `mark_svg(colour: str) -> str`, `lockup_svg(colour: str, word_paths: str) -> str`, `wordmark_paths(font: Path) -> str` (fontTools: open Fraunces, set the variable axes to `opsz=72, wght=500`, draw the glyphs of "ploma" with `SVGPathPen`, advance with the font's hmtx widths and tight tracking of `-0.02em`, return a `<g>` of paths scaled into the lockup's user units), `main()`. The font is fetched once into `media/logo/.cache/Fraunces[SOFT,WONK,opsz,wght].ttf` from `https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf` with `urllib`; the SIL OFL licence line goes in `media/logo/README.md`. Lockup: mark 60 units tall at the left, wordmark baseline aligned with the mark's slit bottom, total viewBox about `0 0 320 80`. PNG: `rsvg-convert -w 512 -h 512 ploma-mark.svg -o ploma-mark-512.png` via `subprocess`, then copy to `.claude-plugin/icon.png`.

- [ ] **Step 4: Run the generator, then the tests**

Run: `python3 media/logo/build_logo.py && python3 -m pytest tests/test_logo.py -q && rsvg-convert -w 16 -h 16 assets/logo/ploma-mark.svg -o /tmp/claude-1001/-home-mgarnica-papers/a8791dfa-b2aa-4195-9e32-25b5d173836a/scratchpad/nib16.png`
Expected: 4 passed; look at the 16 px PNG once (Read tool) and confirm the nib is still a nib. If it is mush, raise the stroke to 7 in `mark_svg` and rerun.

- [ ] **Step 5: Commit**

```bash
git add media/logo assets/logo .claude-plugin/icon.png .gitignore tests/test_logo.py
git commit -m "feat(brand): nib mark, wordmark lockup and plugin icon"
```

---

### Task 4: Reference docs split out of the README

**Files:**
- Create: `docs/install.md`, `docs/hosts.md`, `docs/commit-gate.md`, `docs/testing.md`
- Test: `tests/test_docs.py`

**Interfaces:**
- Produces: the four doc paths Task 8 links to, each with a single H1 and these H2s: install.md `Claude Code`, `Codex`, `Updates`, `API keys`; hosts.md `Switching hosts`, `Co-authors on Codex`; commit-gate.md `Required and recommended checks`, `Overrides`, `Checking the gate`; testing.md `Running the tests`, `Field tests`, `Evals`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docs.py
import re
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

DOCS = {"install.md": ["Claude Code", "Codex", "Updates", "API keys"],
        "hosts.md": ["Switching hosts", "Co-authors on Codex"],
        "commit-gate.md": ["Required and recommended checks", "Overrides", "Checking the gate"],
        "testing.md": ["Running the tests", "Field tests", "Evals"]}

def _links(text):
    return [m.group(1) for m in re.finditer(r"\]\(([^)#]+)(?:#[^)]*)?\)", text) if not m.group(1).startswith(("http", "mailto"))]

def test_docs_exist_with_expected_sections():
    for name, h2s in DOCS.items():
        text = (REPO_ROOT / "docs" / name).read_text()
        assert text.count("\n# ") + text.startswith("# ") == 1
        for h in h2s:
            assert f"\n## {h}\n" in text, (name, h)

def test_docs_have_no_dashes_and_links_resolve():
    for name in DOCS:
        path = REPO_ROOT / "docs" / name
        text = path.read_text()
        assert not EM_DASH_RE.search(text), name
        for link in _links(text):
            assert (path.parent / link).resolve().exists(), (name, link)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest tests/test_docs.py -q`
Expected: 2 failed.

- [ ] **Step 3: Write the four docs by moving README text**

Source is the current `README.md` (commit `d53959c`): `docs/install.md` takes "Install" (both hosts, the HTTPS lines, updates) and the API-keys paragraph with its `config.toml` block; `docs/hosts.md` takes "Switching hosts"; `docs/commit-gate.md` takes "Commit gate"; `docs/testing.md` takes "Running the tests", "Testing" and "Evals (optional, not run by the maintainers)". Move paragraphs verbatim, then only add the H1 and H2s from Interfaces and a one-line lead under each H1. Links between docs are relative (`install.md`, `../CHANGELOG.md`). The README itself is not edited in this task.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_docs.py -q`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add docs/install.md docs/hosts.md docs/commit-gate.md docs/testing.md tests/test_docs.py
git commit -m "docs: install, hosts, commit gate and testing reference pages"
```

---

### Task 5: Real runs and transcripts

**Files:**
- Create: `media/transcripts/run_demo.sh`, `media/transcripts/render_transcript.py`, `media/transcripts/README.md`
- Create (outputs, committed): `media/transcripts/onboard.md`, `compile-1.md`, `validate-bib.md`, `write.md`, `merge.md`, `compile-2.md`, `commit.md`, `grill.md`, `spec.md`, and the raw `media/transcripts/raw/*.jsonl`
- Test: `tests/test_render_transcript.py`

**Interfaces:**
- Consumes: `examples/demo-paper` (Task 2), the toolchain (Task 1).
- Produces: `render_transcript.py` with `render(events: list[dict]) -> str` and CLI `python3 media/transcripts/render_transcript.py <in.jsonl> <out.md>`; the markdown format is `> <user text>` for user turns, assistant text verbatim, and one line `[tool] <name> <first 80 chars of input>` per tool call. Task 6 and Task 7 take their words from these `.md` files. The scratch copy lives at `$HOME/ploma-demo-run` (outside the repo).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_transcript.py
import importlib.util, json
from conftest import REPO_ROOT

def _mod():
    spec = importlib.util.spec_from_file_location("rt", REPO_ROOT / "media" / "transcripts" / "render_transcript.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_render_user_assistant_and_tool_lines():
    events = [
        {"type": "user", "message": {"role": "user", "content": "/ploma:write intro"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Draft: sections/intro_suggestion.tex"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "python3 scripts/style_check.py --root . x"}}]}},
    ]
    out = _mod().render(events)
    assert out.splitlines()[0] == "> /ploma:write intro"
    assert "Draft: sections/intro_suggestion.tex" in out
    assert "[tool] Bash python3 scripts/style_check.py --root . x" in out
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest tests/test_render_transcript.py -q`
Expected: 1 failed (file not found).

- [ ] **Step 3: Write `render_transcript.py`**

`render(events)` handles both shapes the Claude CLI writes: `claude -p --output-format stream-json --verbose` events (`type` in `user`, `assistant`, `result`, `system`) and session files under `~/.claude/projects/` (same `message` envelope, extra fields ignored). `message.content` is a string or a list of blocks; `tool_result` blocks are skipped. `main(argv)` reads JSONL, writes markdown.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_render_transcript.py -q`
Expected: 1 passed.

- [ ] **Step 5: Write `run_demo.sh`**

Bash, `set -euo pipefail`. Variables `PLUGIN=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)`, `RUN=$HOME/ploma-demo-run`, `RAW=$PLUGIN/media/transcripts/raw`. Steps: remove and recreate `$RUN` from `examples/demo-paper`; `git init -q && git add -A && git commit -qm "demo paper"` inside it; warn (not fail) when `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` or `CROSSREF_MAILTO` is unset; then one call per skill, each `cd "$RUN" && claude -p --plugin-dir "$PLUGIN" --dangerously-skip-permissions --output-format stream-json --verbose "<prompt>" > "$RAW/<name>.jsonl"`, in this order and with these prompts: `onboard` `/ploma:onboard --yes`; `compile-1` `/ploma:compile`; `validate-bib` `/ploma:validate-bib --semantic`; `write` `/ploma:write intro`; `merge` `/ploma:write intro --merge` followed by a second call `claude -p -c ... "yes"` appended to the same `merge.jsonl`; `compile-2` `/ploma:compile`; `commit` `/ploma:commit intro: ground the latency claim in bench.json --no-pr`. After each call run `render_transcript.py` to the matching `.md`. Print the `$RUN` path at the end. The scratch copy is left in place for Marc's session.

- [ ] **Step 6: Run it**

Run: `bash media/transcripts/run_demo.sh`
Expected: seven `.md` files; `merge.md` ends with "Run /ploma:compile to rebuild the PDF."; `commit.md` contains `gate:` and a commit hash; `$HOME/ploma-demo-run/sections/intro.tex` now says 27.4. If a skill stops on a question it could not ask (write asks when a draft exists, commit asks about pushing), answer it with `claude -p -c ... "<answer>"` appended to that skill's `.jsonl`, re-render, and note the answer in `media/transcripts/README.md`.

- [ ] **Step 7: Marc's interactive session (orchestrator step, not a subagent step)**

Reset the scratch copy's intro to the starting state so grill sees the conflict: `cd $HOME/ploma-demo-run && git checkout -- sections/intro.tex && rm -rf quality_reports/decisions`. Ask Marc to run, in Claude Code inside `$HOME/ploma-demo-run` with `--plugin-dir /home/mgarnica/papers`: `/ploma:grill sections/intro.tex` (answer each question; pick the recommended answer when there is no reason not to) and then `/ploma:spec --no-verify`. When he is done, find the session file (`ls -t ~/.claude/projects/*ploma-demo-run*/*.jsonl | head -1`), copy it to `media/transcripts/raw/session.jsonl`, and render `grill.md` and `spec.md` from it by splitting at the second skill's user turn.

- [ ] **Step 8: Write `media/transcripts/README.md` and commit**

The README names each file, the command that produced it, the date, and the one rule: film and still text may shorten these transcripts but never add words to them.

```bash
git add media/transcripts tests/test_render_transcript.py
git commit -m "docs(media): real ploma runs on the demo paper, rendered transcripts"
```

---

### Task 6: Stage stills

**Files:**
- Create: `media/shared/chrome.css` (mac window chrome, terminal palette, type), `media/stills/grill.html`, `spec.html`, `write.html`, `ship.html`, `media/stills/render.sh`
- Create (outputs, committed): `assets/stills/grill.png`, `spec.png`, `write.png`, `ship.png`
- Modify: `.gitignore` (add `media/**/node_modules/`, `media/**/out/`, `media/**/.hyperframes/`)
- Test: `tests/test_stills.py`

**Interfaces:**
- Consumes: `media/transcripts/grill.md`, `spec.md`, `write.md`, `commit.md` (Task 5).
- Produces: `media/shared/chrome.css` classes `.win`, `.titlebar`, `.dot.r/.y/.g`, `.term`, `.pdfwin`, `.page` with the palette tokens as CSS variables (`--ink`, `--paper`, `--term-bg: #1b1e24`, `--term-fg: #d8dbe2`, `--accent: #1f5f8b`, `--copper: #b4552d`); Task 7 reuses the file. Four PNGs 1400 px wide for Task 8.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stills.py
import re, struct
from conftest import REPO_ROOT

STILLS = ["grill", "spec", "write", "ship"]

def test_stills_exist_1400_wide_and_small():
    for n in STILLS:
        p = REPO_ROOT / "assets" / "stills" / f"{n}.png"
        b = p.read_bytes()
        assert b[:8] == b"\x89PNG\r\n\x1a\n"
        w, h = struct.unpack(">II", b[16:24])
        assert w == 1400 and 600 <= h <= 1000, (n, w, h)
        assert len(b) <= 300_000, (n, len(b))

def test_still_text_traces_to_transcripts():
    corpus = "\n".join(p.read_text() for p in (REPO_ROOT / "media" / "transcripts").glob("*.md"))
    for n in STILLS:
        html = (REPO_ROOT / "media" / "stills" / f"{n}.html").read_text()
        for m in re.finditer(r'<span class="ln"[^>]*>(.*?)</span>', html, re.S):
            line = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if line:
                assert line in corpus, (n, line)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest tests/test_stills.py -q`
Expected: 2 failed.

- [ ] **Step 3: Write `chrome.css` and the four stills**

Each still is a complete HTML page, 1400 by 820 body, one `.win.term` window (grill, write, ship) or one `.win.term` beside a narrow `.win.pdfwin` (spec shows `paper_spec.md` as a document window). Terminal lines are `<span class="ln">` elements whose text content is copied from the transcript (whole lines; a line may be dropped, never reworded). Fonts via Google Fonts links: `IBM Plex Mono` for terminal text, `Source Serif 4` for the document window. The grill still shows the one question with its options and the recommended one marked; the ship still shows the gate verdict lines.

- [ ] **Step 4: Write `render.sh` and render**

`media/stills/render.sh` renders each HTML with the HyperFrames CLI's Chrome: inside `media/film` (created in Task 7 if not yet present, otherwise `npx -y hyperframes@0.8.166 doctor` here to provision Chrome) run `npx -y hyperframes@0.8.166 capture file://$PWD/media/stills/<n>.html --output media/stills/out/<n>.png` or, when `capture` does not take a local file, headless Chrome directly (`"$CHROME" --headless=new --screenshot=... --window-size=1400,820 file://...`, `CHROME` found with `npx -y hyperframes@0.8.166 doctor`). Then `ffmpeg -y -i out/<n>.png -vf scale=1400:-1 assets/stills/<n>.png` and `optipng -o2` when installed. Check `--help` for the exact flag names before writing them down.

Run: `bash media/stills/render.sh && python3 -m pytest tests/test_stills.py -q`
Expected: 2 passed. Look at `assets/stills/grill.png` once with the Read tool.

- [ ] **Step 5: Commit**

```bash
git add media/shared media/stills assets/stills .gitignore tests/test_stills.py
git commit -m "feat(brand): four stage stills rendered from the real transcripts"
```

---

### Task 7: Hero film

**Files:**
- Create: `media/film/` as a HyperFrames project (`package.json` pinning `hyperframes@0.8.166`, `compositions/main.html`, `script.json`, `pdf_words.py`, `make_gif.sh`, `README.md`)
- Create (outputs, committed): `assets/film/ploma-hero.gif`, `assets/film/ploma-hero.png`, and `assets/film/ploma-hero.mp4` when at or under 4 MB
- Test: `tests/test_film.py`

**Interfaces:**
- Consumes: `media/shared/chrome.css` (Task 6), transcripts (Task 5), the compiled `$HOME/ploma-demo-run/main.pdf` after the merge, the mark path (Task 3).
- Produces: `media/film/script.json`: `{"beats": [{"name": "open", "start": 0.0, "lines": [{"at": 0.8, "text": "/ploma:grill sections/intro.tex", "role": "user"}, ...]}, ...]}`; every `text` is a substring of a transcript. `media/film/pdf_words.json`: `[{"text": "cuts", "x": 0.12, "y": 0.41, "w": 0.03, "h": 0.012}, ...]`, fractions of the page.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_film.py
import json
from conftest import REPO_ROOT

FILM = REPO_ROOT / "media" / "film"
OUT = REPO_ROOT / "assets" / "film"

def test_film_script_lines_trace_to_transcripts():
    corpus = "\n".join(p.read_text() for p in (REPO_ROOT / "media" / "transcripts").glob("*.md"))
    script = json.loads((FILM / "script.json").read_text())
    names = [b["name"] for b in script["beats"]]
    assert names == ["open", "grill", "write", "ship", "tagline"]
    for beat in script["beats"]:
        for line in beat["lines"]:
            assert line["text"] in corpus, (beat["name"], line["text"])

def test_pdf_words_cover_the_grounded_number():
    words = json.loads((FILM / "pdf_words.json").read_text())
    assert any(w["text"].startswith("27.4") for w in words)
    assert all(0 <= w["x"] <= 1 and 0 <= w["y"] <= 1 for w in words)

def test_outputs_exist_and_fit_the_budget():
    gif = (OUT / "ploma-hero.gif").read_bytes()
    assert gif[:6] == b"GIF89a" and len(gif) <= 6_000_000
    assert (OUT / "ploma-hero.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    mp4 = OUT / "ploma-hero.mp4"
    assert not mp4.exists() or mp4.stat().st_size <= 4_000_000
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest tests/test_film.py -q`
Expected: 3 failed.

- [ ] **Step 3: Scaffold the project and provision Chrome**

Run in `media/`: `npx -y hyperframes@0.8.166 init film --help` first to see the template options, then `npx -y hyperframes@0.8.166 init film`, then in `media/film`: `npm pkg set dependencies.hyperframes=0.8.166 && npm install && npx hyperframes doctor`. If doctor reports no browser, follow its remediation (it names the install command). Record the exact commands in `media/film/README.md`.

- [ ] **Step 4: Write `pdf_words.py` and `script.json`**

`pdf_words.py <main.pdf> <out.json>`: runs `pdftotext -bbox-layout -f 1 -l 1`, parses the XHTML `<word xMin yMin xMax yMax>` elements and the `<page width height>`, writes the fractions. Also runs `pdftoppm -r 200 -png -f 1 -l 1 <main.pdf> media/film/assets/page` to produce `media/film/assets/page-1.png` (committed, under 600 KB; lower `-r` if larger). Input is `$HOME/ploma-demo-run/main.pdf` after Task 5's merge and second compile.

`script.json`: condense `grill.md`, `write.md`, `merge.md`, `compile-2.md`, `commit.md` into the five beats with the spec's timings (open 0 to 3 s, grill 3 to 9, write 9 to 17, ship 17 to 22, tagline 22 to 25). Each `text` is copied, not typed from memory. The tagline beat has two lines, `ploma` and `Your paper. Your claims. Checked.`; add both to `media/transcripts/README.md` under "Fixed copy" so the traceability test treats them as sourced text.

- [ ] **Step 5: Write `compositions/main.html`**

Root `<div id="root" data-composition-id="main" data-start="0" data-duration="25" data-width="1600" data-height="1000">`. Loads `../../shared/chrome.css`, GSAP 3.14.2 from jsDelivr, Google Fonts. Builds the terminal lines and the PDF word masks from `script.json` and `pdf_words.json` at load (fetch both, then register the timeline; registration after the tweens, as the HyperFrames schema requires). One paused GSAP timeline on `window.__timelines.main`: lines fade and slide in at their `at` times; a typing effect on user lines (`text` revealed character by character over 0.6 s); the PDF window slides in at the start of the second compile (about 15 s); the page image sits under a layer of white rectangles, one per word, that fade out in reading order over 2.5 s; the rectangle over the `27.4` word becomes a translucent `--accent` highlight instead of fading; the ship beat ticks the three gate lines 0.8 s apart; at 22 s both windows dim to 30% and the lockup plus tagline fade in centred. The nib mark path from Task 3 appears on the prompt line at 0.3 s. No wall-clock, no randomness, no infinite repeats.

- [ ] **Step 6: Preview once, then render and make the GIF**

Run: `cd media/film && npx hyperframes preview` (open the URL, watch the loop once, fix anything that overlaps), then `npx hyperframes render --output out/ploma-hero.mp4`.

`make_gif.sh`: `ffmpeg -y -i out/ploma-hero.mp4 -vf "fps=15,scale=1000:-1:flags=lanczos,palettegen=max_colors=192" out/palette.png && ffmpeg -y -i out/ploma-hero.mp4 -i out/palette.png -lavfi "fps=15,scale=1000:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" ../../assets/film/ploma-hero.gif`, then the still `ffmpeg -y -ss 15.5 -i out/ploma-hero.mp4 -frames:v 1 ../../assets/film/ploma-hero.png`, then `[ $(stat -c%s out/ploma-hero.mp4) -le 4000000 ] && cp out/ploma-hero.mp4 ../../assets/film/`. If the GIF is over 6 MB, drop `fps` to 12, then `scale` to 900, in that order.

Run: `bash media/film/make_gif.sh && python3 -m pytest tests/test_film.py -q && du -sh assets`
Expected: 3 passed; `assets` under 12 MB.

- [ ] **Step 7: Commit**

```bash
git add media/film assets/film media/transcripts/README.md tests/test_film.py
git commit -m "feat(brand): HyperFrames hero film, GIF and still from the real session"
```

---

### Task 8: The README, the changelog and the link tests

**Files:**
- Modify: `README.md` (rewritten), `CHANGELOG.md` (new `## Unreleased` section)
- Test: `tests/test_readme.py`

**Interfaces:**
- Consumes: `assets/logo/ploma-lockup*.svg` (Task 3), `docs/*.md` (Task 4), `assets/stills/*.png` (Task 6), `assets/film/ploma-hero.gif` and `.png` and maybe `.mp4` (Task 7), `.claude-plugin/plugin.json` version.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_readme.py
import json, re
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

README = (REPO_ROOT / "README.md").read_text()

def _refs(text):
    md = re.findall(r"\]\(([^)#\s]+)", text)
    html = re.findall(r'(?:src|srcset|href)="([^"#]+)"', text)
    return [r for r in md + html if not r.startswith(("http", "mailto"))]

def test_readme_and_docs_have_no_dashes():
    for p in [REPO_ROOT / "README.md", *(REPO_ROOT / "docs").glob("*.md")]:
        assert not EM_DASH_RE.search(p.read_text()), p

def test_every_relative_reference_resolves():
    for r in _refs(README):
        assert (REPO_ROOT / r).exists(), r

def test_asset_references_are_relative():
    assert "raw.githubusercontent.com" not in README
    assert "assets/film/ploma-hero.gif" in README

def test_logo_picture_has_both_schemes():
    assert 'media="(prefers-color-scheme: dark)"' in README and "ploma-lockup-dark.svg" in README
    assert "ploma-lockup.svg" in README

def test_sections_in_spec_order():
    heads = [h for h in re.findall(r"^## (.+)$", README, re.M)]
    assert heads == ["Why ploma exists", "How a paper gets written", "What stops slop", "Install in two minutes", "The full lifecycle", "Trust and testing", "Credits and licence"]

def test_demo_paper_is_declared_fictional_and_version_matches():
    assert "examples/demo-paper" in README and "fictional" in README
    version = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    assert version in README
    assert "## Unreleased" in (REPO_ROOT / "CHANGELOG.md").read_text()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest tests/test_readme.py -q`
Expected: at least 4 failed (the dash test may already pass).

- [ ] **Step 3: Write the README**

Header (HTML, centred): `<picture>` with the dark source and the light `<img>` (width 360, alt `ploma`); the thesis in a `<p>` (from the spec, tightened only); the tagline in a second `<p>`; one badge row with shields.io static badges: version (text from `plugin.json`), licence Apache-2.0, Claude Code, Codex, tests `1440 passed` (static, updated at release); two links `[Install](#install-in-two-minutes)` and `[See the workflow](#how-a-paper-gets-written)`. Then `![ploma session on the demo paper](assets/film/ploma-hero.gif)` and a one-line caption: the MP4 link (`assets/film/ploma-hero.mp4` when committed, otherwise the 0.2.0 release asset URL), and "The paper is a fictional demo that ships in `examples/demo-paper`, so you can replay this session."

Sections, as `##` headings in exactly the order the test pins. "How a paper gets written" has four `###` subsections (Grill, Spec, Write, Ship), each a still `<img src="assets/stills/<n>.png" width="700">` then one or two sentences, outcome first. "The full lifecycle" keeps the current stage table verbatim and wraps the per-skill list in `<details><summary>All 23 skills</summary>`. "Install in two minutes" is a two-column table (Claude Code, Codex) with the three commands each, then one line linking `docs/install.md` for HTTPS, keys and updates. "Trust and testing" links `docs/testing.md`, `docs/commit-gate.md`, `docs/hosts.md` and the changelog's known issues. "Credits and licence" names Apache-2.0, `UPSTREAMS.md`, HyperFrames (Apache-2.0) and Fraunces (SIL OFL).

Changelog: `## Unreleased` with four bullets: public README and docs split; nib logo and plugin icon; hero film and stills from a real session on the demo paper; `examples/demo-paper`.

- [ ] **Step 4: Check nothing was lost from the old README**

Run (one-off, not a test):
```bash
git show 66c48df:README.md | python3 -c "
import sys,re,pathlib
old=[p.strip() for p in sys.stdin.read().split('\n\n') if p.strip() and not p.startswith(('#','|','\`\`\`'))]
new=pathlib.Path('README.md').read_text()+''.join(p.read_text() for p in pathlib.Path('docs').glob('*.md'))
for p in old:
    key=re.sub(r'\s+',' ',p)[:50]
    if key not in re.sub(r'\s+',' ',new): print('MISSING:',key)"
```
Expected: no `MISSING` lines except paragraphs you rewrote on purpose; for each of those, confirm the fact it carried is still somewhere in README or docs.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_readme.py -q`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add README.md CHANGELOG.md tests/test_readme.py
git commit -m "docs: public README with logo, hero film and workflow stills"
```

---

### Task 9: Whole-tree verification and push

**Files:** none new.

- [ ] **Step 1: Full suite and validation**

Run: `python3 -m pytest -q && claude plugin validate .`
Expected: at least 1440 plus the new tests pass; validate prints no error.

- [ ] **Step 2: Dash and size sweep**

Run: `grep -rnP "[—–]" README.md docs/*.md assets media examples/demo-paper; du -sh assets; git status --short`
Expected: no grep hits, `assets` under 12 MB, clean tree.

- [ ] **Step 3: Scratch copy and example state**

Run: `git diff --stat 66c48df -- examples/demo-paper | tail -1; ls examples/demo-paper` and `grep -c "27.4" examples/demo-paper/sections/intro.tex`
Expected: the committed intro still says 31% (grep prints `0`); no `quality_reports/`, `.ploma/` or `main.pdf` in the example.

- [ ] **Step 4: Push and look**

Run: `git push origin main`, then open `https://github.com/marcgarnica13/ploma` in light and dark mode: the lockup swaps, the GIF plays, each still loads, each link resolves, the details block opens. Fix anything broken with one more commit.

- [ ] **Step 5: Hand back**

Report to Marc: the README URL, the GIF and MP4 sizes, the test count, and the two manual steps that remain his: flipping the repo to public, and (if the MP4 was not committed) attaching it to the 0.2.0 release.
