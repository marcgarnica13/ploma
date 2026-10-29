# ploma Foundation Implementation Plan (milestone 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the installable `ploma` plugin skeleton with `/ploma:onboard`, `/ploma:doctor`, `/ploma:compile`, `/ploma:validate-bib`, `/ploma:status`, `/ploma:help`, the hooks, the eager rules, the venue and discipline files, and every deterministic script those skills need, so `traces-16` can install it into the real paper repo and report defects.

**Architecture:** A single Claude Code plugin at the repo root (manifest in `.claude-plugin/`). Deterministic work lives in `scripts/*.py` (python3 stdlib, optional PyYAML), each with `--json` output and pytest coverage against `examples/sample-paper/` and stored fixtures. Skills are thin prose that call the scripts and quote their output. Hooks inject the eager rules, the resolved config and the lifecycle state at session and subagent start.

**Tech Stack:** Python 3.10+ (stdlib only; PyYAML optional), pytest, Claude Code plugin format (skills, agents, hooks.json), YAML config and profiles, JSON schemas (documented, checked by a small in-house validator).

**Spec:** `docs/superpowers/specs/2026-10-29-ploma-design.md`

## Global Constraints

- Plugin name `ploma`; marketplace name `ploma`; install string `/plugin install ploma@ploma`; marketplace `source: "./"`.
- Component paths in `plugin.json` start with `./`. Scripts live in `scripts/`, never `bin/`.
- `claude plugin validate .` passes with no warnings (this build has no `--strict`).
- Every script: python3 stdlib only, `import yaml` optional with `scripts/_yamlmini.py` fallback, `--json` flag, documented exit codes, no network except `cite_lookup.py`.
- Every hook: python3, fail-open (`except Exception: sys.exit(0)`), state under `${CLAUDE_PROJECT_DIR}/.ploma/`; without `ploma.yaml` it exits before importing anything beyond `sys`, `os`, `json` and prints nothing (SessionStart alone prints the onboard line, and only when a `.tex` file exists within two directory levels).
- SessionStart injection under 10,000 characters; eager rules together under 6,500.
- No domain text in shipped skills, agents, rules or generic profiles. Banned terms (case-insensitive): `soccer`, `football`, `pm4py`, `possession`, `pitch`, `StatsBomb`, `Wyscout`, `action##zone`, `TAGS_FILE`, `MONGO`, `llncs` outside `venues/` and `inventory.py`, `samplepaper`, `mybib`, `sports_pm`, `heuristic net`. `tests/test_skills.py` enforces this.
- No em-dashes in any shipped prose (`—` and `–` as sentence punctuation). Enforced by `tests/test_skills.py` on skills, agents, rules, templates.
- Report-only critics never edit the manuscript. Every finding carries location, current text, fix and severity.
- Config paths are relative to the repo root. Project overrides in `ploma.d/`.
- Doctor statuses: PASS, WARN, FAIL, INFO, SKIP. Verdicts: READY, READY_WITH_WARNINGS, NOT_READY. Doctor makes no network calls.
- Gate: required `compile`, `bib`; recommended `consistency`, `claims`, `proofread` (consistency becomes required in 0.1.1); override with `commit anyway: <reason>`; refuse after three consecutive overrides.
- Nothing under `extraction/` is imported or referenced by shipped code.
- Commits are small, on `main`, with the attribution trailer the session requires.

## Review Focus

1. A paper whose main file has `\input` or `\include` chains and a bibliography declared only in an included file: `bib_check.resolve_bib_files` must follow the chain (Task 7 test `test_bib_files_declared_in_included_file`).
2. A `ploma.yaml` written by hand with a path that no longer exists after a rename: `ploma_config.validate` must FAIL with the key and path, not crash (Task 3 test `test_missing_path_is_a_finding`).
3. A LaTeX log with Windows line endings or a wrapped overfull line split at 79 characters: `latex_log.parse_log` must still count the overfull box (Task 5 test `test_wrapped_overfull_line`).
4. A repo with two `\documentclass` files (a paper and a response letter): `inventory` must return both candidates and `onboard` must ask, never pick silently (Task 11 test `test_two_main_candidates_become_a_gap`).
5. SessionStart on a repo whose `ploma.yaml` is invalid YAML: the hook must emit a one-line notice and exit 0, never crash the session (Task 15 test `test_invalid_yaml_yields_notice_and_exit_zero`).

---

## File structure

```
.claude-plugin/plugin.json, marketplace.json
scripts/_findings.py          Finding dataclass, status constants, JSON rendering
scripts/_yamlmini.py          fallback YAML subset loader
scripts/_yamlio.py            load_yaml(path), dump_yaml(data) choosing PyYAML or mini
scripts/ploma_config.py       load, validate, resolve ploma.yaml
scripts/profiles.py           venue and discipline loading with ploma.d/ shadowing
scripts/latex_log.py          log triage
scripts/pdf_pages.py          page count and section page map
scripts/bib_check.py          bib parsing, cite keys, structural checks
scripts/cite_lookup.py        Crossref, OpenAlex, Semantic Scholar existence check with cache
scripts/state.py              lifecycle state
scripts/gate.py               commit gate verdict
scripts/inventory.py          read-only repo detection, venue guess, gaps, legacy harness
scripts/receipt.py            apply receipt
scripts/project_files.py      render and apply the files onboard writes
scripts/doctor.py             readiness audit
scripts/compile.py            run build, triage, report, gate entry, state event
scripts/validate_bib.py       structural plus semantic bib audit report
schemas/{ploma,venue,discipline,state,verdict,receipt}.schema.json
venues/*.yaml  disciplines/*.yaml
rules/eager/{00-core,limits,style}.md  rules/reference/*.md
hooks/hooks.json  hooks/{session_context,pre_compact,context_monitor,verify_reminder,log_reminder}.py
templates/{claude-md-section.md, rules/ploma-manuscript.md, rules/ploma-pipeline.md, quality_reports/README.md, learnings.md, statusline.sh}
skills/{onboard,doctor,help,status,compile,validate-bib}/SKILL.md
examples/sample-paper/        main.tex, sections/*.tex, refs.bib, Makefile, figures/fig1.pdf, review/review1.md, results/metrics.json
tests/conftest.py, tests/fixtures/{logs,bib,tex,harness}/, tests/test_*.py
evals/{onboard,doctor,help,status,compile,validate-bib}/
README.md UPSTREAMS.md CHANGELOG.md LICENSE .gitignore .github/workflows/ci.yml
```

Shared conventions for all scripts: `main(argv) -> int` entry; `--json` prints one JSON object; exit 0 on success, 1 on findings that fail, 2 on usage or unreadable input. Findings use `scripts/_findings.py`.

---

### Task 1: Plugin skeleton, manifests, manifest test, CI

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `UPSTREAMS.md`, `CHANGELOG.md`, `LICENSE` (Apache-2.0, Marc Garnica Caparrós), `.gitignore`, `.github/workflows/ci.yml`, `tests/conftest.py`, `tests/test_manifest.py`, `skills/help/SKILL.md` (placeholder, completed in Task 18)
- Modify: `README.md` (replace the seed README)

**Interfaces:**
- Produces: `tests/conftest.py` adds `<repo>/scripts` and `<repo>/hooks` to `sys.path` and exposes fixtures `repo_root: Path`, `sample_paper: Path` (a `tmp_path` copy of `examples/sample-paper/`, filled in Task 4).

- [ ] **Step 1: Write the failing manifest test**

```python
# tests/test_manifest.py
def test_plugin_manifest_shape(repo_root):
    m = json.loads((repo_root / ".claude-plugin/plugin.json").read_text())
    assert m["name"] == "ploma"
    assert m["version"] == "0.1.0"
    assert m["license"] == "Apache-2.0"
    for key in ("skills", "agents", "hooks"):
        if key in m:
            vals = m[key] if isinstance(m[key], list) else [m[key]]
            assert all(v.startswith("./") for v in vals)

def test_marketplace_entry_matches_manifest(repo_root):
    mk = json.loads((repo_root / ".claude-plugin/marketplace.json").read_text())
    assert mk["name"] == "ploma"
    assert mk["plugins"][0]["name"] == "ploma"
    assert mk["plugins"][0]["source"] == "./"

def test_no_bin_dir_and_no_root_claude_md(repo_root):
    assert not (repo_root / "bin").exists()
    assert not (repo_root / "CLAUDE.md").exists()

def test_every_skill_dir_has_skill_md(repo_root):
    for d in (repo_root / "skills").iterdir():
        assert (d / "SKILL.md").exists(), d
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest tests/test_manifest.py -v`
Expected: FAIL (manifest missing)

- [ ] **Step 3: Write `.claude-plugin/plugin.json`**

Fields: `name`, `version` "0.1.0", `description` (one sentence: harness for LaTeX academic papers), `author` {name, url}, `homepage`, `repository`, `license`, `keywords`, `hooks` "./hooks/hooks.json", `userConfig` with `crossref_mailto` (string, not sensitive, description "email for the Crossref polite pool"), `openalex_api_key` and `semantic_scholar_api_key` (string, sensitive). No `commands`, no `agents` key yet (agents directory is added in milestone 2 and auto-discovered).

- [ ] **Step 4: Write `.claude-plugin/marketplace.json`**

`name` ploma, `owner` {name, url}, `metadata.description`, `plugins: [{name: ploma, source: "./", description, category: "productivity"}]`.

- [ ] **Step 5: Write `tests/conftest.py`, `.gitignore`, `LICENSE`, `UPSTREAMS.md`, `CHANGELOG.md`, `README.md`, CI**

`.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ploma/`, `examples/sample-paper/build/`.
`UPSTREAMS.md`: tramat table format (Upstream | What ploma took | Observed | Last reviewed) with rows for pedrohcgs/claude-code-my-workflow v1.9, hugosantanna/clo-author v4.2.0, chrisblattman/claudeblattman v2.1, Imbad0202/academic-research-skills (ideas only, CC-BY-NC-4.0), CodySwannGT/lisa 4.81.5, marcgarnica13/tramat 0.0.3, obra/superpowers 7.0.0, mattpocock/skills grill-me, SNL-UCSB/paper-writing-skill, Dhuliawala et al. 2023 CoVe. Note the two licences not yet checked.
`CHANGELOG.md`: `## 0.1.0 (unreleased)` header.
`README.md`: status, what ploma is, the install block from spec §15, the lifecycle table, "running the tests".
`.github/workflows/ci.yml`: `python3 -m pytest -q` on push and pull request, python 3.10 and 3.12 matrix.

- [ ] **Step 6: Run tests and validate the manifest**

Run: `python3 -m pytest tests/test_manifest.py -v && claude plugin validate .`
Expected: PASS, and validate reports no errors and no warnings

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin README.md UPSTREAMS.md CHANGELOG.md LICENSE .gitignore .github tests skills/help
git commit -m "feat: plugin skeleton, manifests, manifest tests, CI"
```

---

### Task 2: Fallback YAML loader

**Files:**
- Create: `scripts/_yamlmini.py`, `scripts/_yamlio.py`, `tests/test_yamlmini.py`, `tests/fixtures/yaml/ploma_full.yaml` (the spec §5 example verbatim)

**Interfaces:**
- Produces: `_yamlmini.load(text: str) -> Any` raising `YamlMiniError(line: int, message: str)`; `_yamlmini.dump(data: Any, indent: int = 2) -> str`; `_yamlio.load_yaml(path: Path) -> Any`; `_yamlio.dump_yaml(data: Any) -> str`; `_yamlio.LOADER: str` equal to `"pyyaml"` or `"yamlmini"`.

Supported subset: nested maps, block lists of scalars and maps, inline `[a, b]` and `{k: v}` with scalar members, strings (bare, single, double quoted), ints, floats, `true/false`, `null`, `#` comments, blank lines. Not supported, must raise: anchors and aliases (`&`, `*`), multi-line `|` and `>` scalars, tabs for indentation, documents separators.

- [ ] **Step 1: Write the failing tests**

```python
def test_loads_spec_example_identically_to_pyyaml():
    text = FIXTURE.read_text()
    yaml = pytest.importorskip("yaml")
    assert _yamlmini.load(text) == yaml.safe_load(text)

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
```

Note on `g: 2026-10-29`: PyYAML parses a bare date into `datetime.date`; the mini loader keeps it a string. `_yamlio.load_yaml` normalises `date` and `datetime` values to ISO strings so both loaders agree. The first test compares after that normalisation (call `_yamlio._normalise`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_yamlmini.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `scripts/_yamlmini.py` and `scripts/_yamlio.py`**

Line-based recursive descent on an indentation stack. Keep under 250 lines. `_yamlio.load_yaml` tries `import yaml` and falls back; sets `LOADER`.

- [ ] **Step 4: Run tests to verify they pass, also with PyYAML hidden**

Run: `python3 -m pytest tests/test_yamlmini.py -v` then `python3 -c "import sys; sys.modules['yaml']=None; import _yamlio; print(_yamlio.LOADER)"` from `scripts/`
Expected: PASS; second command prints `yamlmini`

- [ ] **Step 5: Commit**

```bash
git add scripts/_yamlmini.py scripts/_yamlio.py tests/test_yamlmini.py tests/fixtures/yaml
git commit -m "feat: fallback YAML subset loader"
```

---

### Task 3: Findings module, config schema, config loader

**Files:**
- Create: `scripts/_findings.py`, `scripts/ploma_config.py`, `schemas/ploma.schema.json`, `tests/test_findings.py`, `tests/test_ploma_config.py`, `tests/fixtures/yaml/ploma_minimal.yaml`, `tests/fixtures/yaml/ploma_bad_type.yaml`

**Interfaces:**
- Produces:
  - `_findings.Finding(id: str, status: str, summary: str, observed: str = "", remediation: str = "", group: str = "")` with `to_dict()`; constants `PASS, WARN, FAIL, INFO, SKIP`; `render(findings: list[Finding]) -> str` (one line `- STATUS id: summary` plus indented `Observed:` and `Remediation:` lines when present); `worst(findings) -> str`.
  - `ploma_config.DEFAULTS: dict` (every optional key's default, including `limits` {review_rounds 5, cove_regenerations 2, doi_lookups_per_run 50}, `build.overfull_threshold_pt` 10, `outputs.dir` "quality_reports", `style` block, `pipeline.enabled` False, `pipeline.figure_provenance` "optional").
  - `ploma_config.load(root: Path) -> dict` (merged with DEFAULTS; raises `ConfigError(message)` when missing or unparseable).
  - `ploma_config.validate(cfg: dict, root: Path) -> list[Finding]` (schema shape, enums, paths exist, `document.type == "paper"` else FAIL `config.document_type_unsupported` with summary "document.type 'proposal' is not supported in ploma v0.1").
  - `ploma_config.resolve(cfg, root) -> dict` adding `_paths` with absolute `main`, `root`, `bib_files`, `pdf`, `log`, `outputs_dir`, `build_cwd`.
  - `ploma_config.summary(cfg) -> str` (under 1,500 characters; used by the SessionStart hook).
  - CLI: `python3 scripts/ploma_config.py [--root R] [--json] [validate|summary]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_load_minimal_applies_defaults(tmp_path):
    (tmp_path / "ploma.yaml").write_text(MINIMAL)       # document.main, build.engine, venue.profile only
    cfg = ploma_config.load(tmp_path)
    assert cfg["outputs"]["dir"] == "quality_reports"
    assert cfg["limits"]["review_rounds"] == 5
    assert cfg["pipeline"]["enabled"] is False

def test_missing_config_raises(tmp_path):
    with pytest.raises(ploma_config.ConfigError):
        ploma_config.load(tmp_path)

def test_missing_path_is_a_finding(sample_paper):
    cfg = ploma_config.load(sample_paper)
    cfg["build"]["bib_files"] = ["gone.bib"]
    f = {x.id: x for x in ploma_config.validate(cfg, sample_paper)}
    assert f["config.path.build.bib_files"].status == FAIL
    assert "gone.bib" in f["config.path.build.bib_files"].observed

def test_unsupported_document_type(sample_paper):
    cfg = ploma_config.load(sample_paper); cfg["document"]["type"] = "proposal"
    f = {x.id: x for x in ploma_config.validate(cfg, sample_paper)}
    assert f["config.document_type_unsupported"].status == FAIL
    assert "not supported in ploma v0.1" in f["config.document_type_unsupported"].summary

def test_bad_type_is_a_finding(tmp_path):
    (tmp_path / "ploma.yaml").write_text(BAD_TYPE)      # build.overfull_threshold_pt: "ten"
    cfg = ploma_config.load(tmp_path)
    ids = [x.id for x in ploma_config.validate(cfg, tmp_path)]
    assert "config.type.build.overfull_threshold_pt" in ids

def test_summary_is_short(sample_paper):
    assert len(ploma_config.summary(ploma_config.load(sample_paper))) < 1500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ploma_config.py tests/test_findings.py -v`
Expected: FAIL

- [ ] **Step 3: Write `schemas/ploma.schema.json`**

JSON Schema draft 2020-12 describing spec §5 exactly: required `ploma`, `document.main`, `build.engine`, `venue.profile`; enums `document.type` [paper, proposal, thesis], `build.engine` [pdflatex, xelatex, lualatex], `build.bib_tool` [bibtex, biber], `venue.cite_style` [numeric, author-year], `pipeline.figure_provenance` [optional, required]; types for every key.

- [ ] **Step 4: Implement `scripts/_findings.py` and `scripts/ploma_config.py`**

Validation walks the schema with a small in-house checker supporting `type`, `enum`, `required`, `properties`, `items` (enough for our schemas; no external library). Path checks run after shape checks and only for keys present.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ploma_config.py tests/test_findings.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/_findings.py scripts/ploma_config.py schemas/ploma.schema.json tests/test_findings.py tests/test_ploma_config.py tests/fixtures/yaml
git commit -m "feat: findings model, ploma.yaml schema and loader"
```

Note: `test_missing_path_is_a_finding` and `test_summary_is_short` need the sample paper from Task 4; write them now, mark them `xfail(strict=False)` until Task 4 lands, then remove the marker in Task 4.

---

### Task 4: Sample paper and fixtures

**Files:**
- Create: `examples/sample-paper/` (`main.tex`, `sections/intro.tex`, `sections/method.tex`, `sections/results.tex`, `refs.bib`, `Makefile`, `figures/fig1.pdf`, `review/review1.md`, `results/metrics.json`, `ploma.yaml`, `.gitignore`), `tests/fixtures/logs/{clean,overfull,undefined,error,rerun,crlf_wrapped}.log`, `tests/fixtures/bib/{simple,nested_braces,duplicates,case_mismatch}.bib`, `tests/fixtures/tex/{llncs_main,two_mains_a,two_mains_b,biblatex_main,included_bib}.tex`, `tests/test_sample_paper.py`
- Modify: `tests/conftest.py` (the `sample_paper` fixture copies the example into `tmp_path`)

**Interfaces:**
- Produces: a compilable `article`-class paper (plain `pdflatex`, `\input{sections/...}`, `\bibliography{refs}`, three cited keys plus one unused entry, one figure, numbers in the abstract that recur in a results table: "12 teams", "0.81"), a `Makefile` with `build`, `clean`, `cleanall` targets and `MAIN = main`, `results/metrics.json` with `{"avg_fitness": 0.81, "n_teams": 12}`, `review/review1.md` in the conference web-form format with the header `Reviewer #3` (so the ID differs from the file name), a `ploma.yaml` consistent with the example (venue `generic-conference`, `page_budget: 8`, `pipeline.enabled: true`, `outputs_dir: results`, `metric_keys: [avg_fitness, n_teams]`).
- `figures/fig1.pdf` is a hand-written minimal valid PDF (one page, no fonts) so `pdf_pages` can count it; it carries `% ploma:source scripts/make_fig1.py --season 2023` in the `\includegraphics` line's preceding comment.

- [ ] **Step 1: Write the failing sanity test**

```python
def test_sample_paper_layout(sample_paper):
    for p in ("main.tex", "sections/intro.tex", "refs.bib", "Makefile", "figures/fig1.pdf",
              "review/review1.md", "results/metrics.json", "ploma.yaml"):
        assert (sample_paper / p).exists(), p

def test_sample_paper_config_validates(sample_paper):
    cfg = ploma_config.load(sample_paper)
    assert [f for f in ploma_config.validate(cfg, sample_paper) if f.status == FAIL] == []

def test_log_fixtures_present(repo_root):
    names = {p.stem for p in (repo_root / "tests/fixtures/logs").glob("*.log")}
    assert {"clean", "overfull", "undefined", "error", "rerun", "crlf_wrapped"} <= names
```

- [ ] **Step 2: Run to verify it fails, create the files, run to verify it passes**

Run: `python3 -m pytest tests/test_sample_paper.py tests/test_ploma_config.py -v`
Expected: PASS after creation (also remove the `xfail` markers from Task 3)

Fixture content rules: the `.log` fixtures are real pdflatex log excerpts shaped by hand: `overfull.log` has two `Overfull \hbox (23.4pt too wide)` and one `(4.1pt too wide)`; `undefined.log` has `LaTeX Warning: Citation 'smith2020' on page 2 undefined` and `Reference 'fig:one' ... undefined` and `There were undefined references.`; `error.log` has `! Undefined control sequence.` followed by `l.42 \badmacro` and a `./sections/method.tex:42:` file-line-error form; `rerun.log` has `Label(s) may have changed. Rerun to get cross-references right.`; `crlf_wrapped.log` is `overfull.log` with CRLF endings and one overfull line wrapped at 79 characters.

- [ ] **Step 3: Commit**

```bash
git add examples/sample-paper tests/fixtures tests/test_sample_paper.py tests/conftest.py tests/test_ploma_config.py
git commit -m "test: sample paper and log, bib, tex fixtures"
```

---

### Task 5: LaTeX log triage

**Files:**
- Create: `scripts/latex_log.py`, `tests/test_latex_log.py`

**Interfaces:**
- Produces: `latex_log.parse_log(text: str, overfull_threshold_pt: float = 10.0) -> LogReport` where `LogReport` is a dataclass with `errors: list[dict(file, line, message)]`, `undefined_citations: list[str]`, `undefined_references: list[str]`, `overfull: list[dict(pt, context)]` (only boxes above threshold), `overfull_total: int` (all boxes), `rerun_needed: bool`, `package_warnings: list[str]`, `ok: bool` (no errors), `to_dict()`. CLI: `python3 scripts/latex_log.py <logfile> [--threshold 10] [--json]`, exit 0 when `ok`, 1 otherwise.

- [ ] **Step 1: Write the failing tests**

```python
def test_clean_log():
    r = parse_log(LOGS["clean"]); assert r.ok and r.overfull == [] and not r.rerun_needed

def test_overfull_threshold():
    r = parse_log(LOGS["overfull"], 10.0)
    assert [round(o["pt"], 1) for o in r.overfull] == [23.4, 23.4] and r.overfull_total == 3

def test_undefined():
    r = parse_log(LOGS["undefined"])
    assert r.undefined_citations == ["smith2020"] and r.undefined_references == ["fig:one"]

def test_error_with_file_line():
    r = parse_log(LOGS["error"])
    assert not r.ok and r.errors[0]["file"].endswith("sections/method.tex") and r.errors[0]["line"] == 42

def test_rerun():
    assert parse_log(LOGS["rerun"]).rerun_needed

def test_wrapped_overfull_line():
    assert len(parse_log(LOGS["crlf_wrapped"], 10.0).overfull) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_latex_log.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `scripts/latex_log.py`**

Normalise line endings, join lines that pdflatex wrapped at 79 characters before matching, regexes from spec §13 research (`^!`, `Overfull \\hbox \((\d+(\.\d+)?)pt too wide`, `LaTeX Warning: Citation '([^']+)'`, `Reference '([^']+)'`, `Label\(s\) may have changed`, `^(.+?):(\d+): (.+)$` for file-line-error).

- [ ] **Step 4: Run tests to verify they pass, then commit**

Run: `python3 -m pytest tests/test_latex_log.py -v`
Expected: PASS

```bash
git add scripts/latex_log.py tests/test_latex_log.py
git commit -m "feat: LaTeX log triage script"
```

---

### Task 6: PDF page count and section page map

**Files:**
- Create: `scripts/pdf_pages.py`, `tests/test_pdf_pages.py`, `tests/fixtures/pdf/three_pages.pdf` (hand-written minimal PDF, three page objects)

**Interfaces:**
- Produces: `pdf_pages.page_count(pdf: Path) -> tuple[int | None, str]` (count and method: `"pdfinfo"`, `"scan"`, or an error message); `pdf_pages.section_page_map(pdf: Path, headings: list[str]) -> tuple[dict[str, int] | None, str]` (first page where each heading appears via `pdftotext -layout`; `None` with reason when `pdftotext` is absent); `pdf_pages.budget_report(pages: int, budget: int | None) -> dict(pages, budget, over_by, status)` with status `PASS`, `WARN` (over by 0 is PASS; over by 1 or more is FAIL), `SKIP` when budget is None. CLI: `python3 scripts/pdf_pages.py <pdf> [--budget N] [--headings h1,h2] [--json]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_scan_counts_pages_without_pdfinfo(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    assert pdf_pages.page_count(FIX / "three_pages.pdf") == (3, "scan")

def test_pdfinfo_preferred_when_present(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: "/usr/bin/pdfinfo")
    monkeypatch.setattr(pdf_pages, "_run", lambda cmd: "Pages:          14\n")
    assert pdf_pages.page_count(FIX / "three_pages.pdf") == (14, "pdfinfo")

def test_budget_report():
    assert pdf_pages.budget_report(14, 13)["status"] == "FAIL"
    assert pdf_pages.budget_report(13, 13)["status"] == "PASS"
    assert pdf_pages.budget_report(13, None)["status"] == "SKIP"

def test_section_map_without_pdftotext(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    pages, reason = pdf_pages.section_page_map(FIX / "three_pages.pdf", ["Introduction"])
    assert pages is None and "pdftotext" in reason
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

Implementation notes: `_which` wraps `shutil.which`; `_run` wraps `subprocess.run(..., capture_output=True, text=True).stdout`; the scan fallback counts `/Type /Page` occurrences excluding `/Pages`.

```bash
git add scripts/pdf_pages.py tests/test_pdf_pages.py tests/fixtures/pdf
git commit -m "feat: PDF page count and budget report"
```

---

### Task 7: Bibliography structural checks

**Files:**
- Create: `scripts/bib_check.py`, `tests/test_bib_check.py`

**Interfaces:**
- Produces:
  - `bib_check.parse_bib(text: str) -> list[Entry]`, `Entry` dataclass `key, type, fields: dict[str, str]` (lowercased field names, braces and quotes stripped, nested braces preserved inside values); `@comment`, `@preamble`, `@string` skipped.
  - `bib_check.tex_sources(main: Path) -> list[Path]` following `\input{}` and `\include{}` recursively (adds `.tex` when missing; ignores commented lines).
  - `bib_check.cite_keys(tex_files: list[Path]) -> dict[str, list[tuple[Path, int]]]` matching `\cite`, `\citep`, `\citet`, `\citealp`, `\parencite`, `\textcite`, `\autocite`, `\nocite`, with optional `[...]` arguments and comma lists; commented text ignored.
  - `bib_check.resolve_bib_files(main: Path, declared: list[Path]) -> list[Path]` union of config `bib_files` and `\bibliography{a,b}` and `\addbibresource{x.bib}` found in any source.
  - `bib_check.check(main: Path, bib_files: list[Path]) -> list[Finding]` with ids `bib.missing.<key>` (FAIL), `bib.near_miss.<key>` (WARN, edit distance ≤ 2 to an existing key), `bib.unused.<key>` (INFO), `bib.duplicate_doi.<a>+<b>` (WARN), `bib.duplicate_title.<a>+<b>` (WARN, normalised titles equal after lowercasing and stripping non-alphanumerics), `bib.cite_style_mix` (WARN when both `\cite` and natbib or biblatex commands appear).
  - CLI: `python3 scripts/bib_check.py <main.tex> [--bib a.bib ...] [--json]`, exit 1 on any FAIL.

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_nested_braces():
    e = parse_bib(BIB["nested_braces"])[0]
    assert e.fields["title"] == "A {Nested} Title with {{Double}} Braces"

def test_cite_keys_variants(tmp_path):
    t = tmp_path / "a.tex"; t.write_text(r"\cite{a} \citep[p.~3]{b,c} \textcite{d} % \cite{ignored}")
    assert set(cite_keys([t])) == {"a", "b", "c", "d"}

def test_bib_files_declared_in_included_file(tmp_path):
    (tmp_path / "main.tex").write_text(r"\documentclass{article}\begin{document}\input{back}\end{document}")
    (tmp_path / "back.tex").write_text(r"\bibliography{refs,extra}")
    assert [p.name for p in resolve_bib_files(tmp_path / "main.tex", [])] == ["refs.bib", "extra.bib"]

def test_missing_and_near_miss(sample_paper):
    (sample_paper / "sections/intro.tex").write_text(r"\cite{Fernandeznavarro2016}")
    ids = {f.id: f for f in check(sample_paper / "main.tex", [sample_paper / "refs.bib"])}
    assert ids["bib.missing.Fernandeznavarro2016"].status == FAIL
    assert "bib.near_miss.Fernandeznavarro2016" in ids       # refs.bib holds FernandezNavarro2016

def test_duplicates():
    fs = {f.id for f in check_entries(parse_bib(BIB["duplicates"]))}
    assert any(i.startswith("bib.duplicate_doi.") for i in fs)
    assert any(i.startswith("bib.duplicate_title.") for i in fs)

def test_shared_booktitle_is_not_a_duplicate():
    assert not any(i.startswith("bib.duplicate_title.") for i in {f.id for f in check_entries(parse_bib(BIB["simple"]))})
```

`BIB["simple"]` holds two entries with the same `booktitle` and different titles (the traces false positive). `check_entries(entries) -> list[Finding]` is the bib-only part of `check`.

- [ ] **Step 2: Run to verify failure, implement `scripts/bib_check.py`, run to verify pass**

Parser: a brace-depth scanner, not regex, for entry bodies. Edit distance: `difflib` is not an edit distance; implement a 20-line Levenshtein.

- [ ] **Step 3: Commit**

```bash
git add scripts/bib_check.py tests/test_bib_check.py
git commit -m "feat: bibliography structural checks"
```

---

### Task 8: Citation existence lookup with cache

**Files:**
- Create: `scripts/cite_lookup.py`, `tests/test_cite_lookup.py`, `tests/fixtures/api/{crossref_hit,crossref_miss,openalex_hit,s2_hit}.json`

**Interfaces:**
- Produces:
  - `cite_lookup.LookupResult` dataclass `key, status, source, evidence, doi` with `status` in `verified | partial | mismatch | missing | unreachable | skipped`.
  - `cite_lookup.lookup(entry: Entry, *, fetch: Callable[[str, dict], tuple[int, str]], mailto: str = "", keys: dict = {}, cache: dict) -> LookupResult`. Order: DOI lookup on Crossref when the entry has a DOI; else title search Crossref, then OpenAlex, then Semantic Scholar. Match rule: normalised title similarity (`difflib.SequenceMatcher.ratio()`) ≥ 0.90 and first author family name contained in the hit's authors and year within ±1 gives `verified`; title ≥ 0.90 with an author or year mismatch gives `partial`; a confident hit with title ratio < 0.6 on a DOI lookup gives `mismatch`; no hit anywhere gives `missing`; HTTP failure or timeout on every source gives `unreachable`.
  - `cite_lookup.run(entries: list[Entry], *, max_lookups: int, delay_s: float = 0.5, cache_path: Path, mailto, keys, fetch=None) -> list[LookupResult]`; entries beyond `max_lookups` get `skipped`; cache keyed by DOI or normalised title; results older than 90 days are refreshed.
  - `cite_lookup.default_cache_path() -> Path`: `${CLAUDE_PLUGIN_DATA}/cache/cite_lookup.json` when the env var is set, else `<cwd>/.ploma/cite_lookup.json`.
  - CLI: `python3 scripts/cite_lookup.py <refs.bib> [--keys k1,k2] [--max 50] [--mailto x] [--json]`.

- [ ] **Step 1: Write the failing tests** (all use an injected `fetch` that returns fixture bodies; no network)

```python
def test_doi_hit_is_verified():
    r = lookup(ENTRY_WITH_DOI, fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}), cache={})
    assert r.status == "verified" and r.source == "crossref"

def test_title_fallback_order():
    calls = []; r = lookup(ENTRY_NO_DOI, fetch=recording_fetch(calls, miss_all=True), cache={})
    assert r.status == "missing" and [host(c) for c in calls] == ["api.crossref.org", "api.openalex.org", "api.semanticscholar.org"]

def test_author_mismatch_is_partial(): ...
def test_all_unreachable(): ...
def test_cache_hit_skips_fetch(): ...
def test_max_lookups_marks_skipped(): ...
def test_mailto_is_sent_to_crossref(): ...   # query string contains mailto=
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

`fetch` default uses `urllib.request` with a 10 second timeout and a `User-Agent: ploma/0.1 (mailto:...)` header.

```bash
git add scripts/cite_lookup.py tests/test_cite_lookup.py tests/fixtures/api
git commit -m "feat: citation existence lookup with cache"
```

---

### Task 9: Lifecycle state

**Files:**
- Create: `scripts/state.py`, `schemas/state.schema.json`, `tests/test_state.py`

**Interfaces:**
- Produces:
  - `state.STAGES: list[str]` = `["onboard", "brainstorm", "lit-review", "grill", "spec", "write", "compile", "format", "validate", "review", "respond", "commit"]`; `state.SKILL_TO_STAGE: dict` mapping every ploma skill name to a stage (`validate-bib`, `verify-claims`, `audit-reproducibility`, `proofread` map to `validate`; `devils-advocate` to `review`; session skills map to `None`).
  - `state.path(root, cfg) -> Path` (`<outputs.dir>/ploma-state.yaml`).
  - `state.load(root, cfg) -> dict` (empty state when absent: `{"ploma_state": "0.1", "stage": None, "rounds": {}, "events": []}`).
  - `state.record(root, cfg, skill: str, status: str, artifact: str | None = None, **extra) -> dict` appends an event with UTC ISO timestamp, updates `stage`, increments `rounds[skill]` for `review` and `respond`.
  - `state.latest(st, skill) -> dict | None`.
  - `state.next_stage(st, cfg) -> dict(stage, reason)`: first stage in `STAGES` after the last recorded stage whose latest event is not PASS, falling back to the first stage with no event; before any event, `onboard` if no config else `compile`.
  - `state.render(st, cfg) -> str` (under 600 characters: current stage, last five events as `skill status date`, recommendation).
  - CLI: `python3 scripts/state.py [--root R] record <skill> <status> [--artifact P] | next | render [--json]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_record_and_next(sample_paper):
    cfg = ploma_config.load(sample_paper)
    st = state.record(sample_paper, cfg, "compile", "PASS", artifact="quality_reports/compile_main.md", pages=7)
    assert st["stage"] == "compile" and st["events"][-1]["pages"] == 7
    assert state.next_stage(st, cfg)["stage"] == "format"

def test_review_round_increments(sample_paper):
    cfg = ploma_config.load(sample_paper)
    state.record(sample_paper, cfg, "review", "PASS"); st = state.record(sample_paper, cfg, "review", "PASS")
    assert st["rounds"]["review"] == 2

def test_next_before_any_event(sample_paper):
    assert state.next_stage(state.load(sample_paper, ploma_config.load(sample_paper)), None)["stage"] == "compile"

def test_render_is_short(sample_paper): ...
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

```bash
git add scripts/state.py schemas/state.schema.json tests/test_state.py
git commit -m "feat: lifecycle state file"
```

---

### Task 10: Commit gate verdict

**Files:**
- Create: `scripts/gate.py`, `schemas/verdict.schema.json`, `tests/test_gate.py`

**Interfaces:**
- Produces:
  - `gate.REQUIRED = ("compile", "bib")`, `gate.RECOMMENDED = ("consistency", "claims", "proofread")`, `gate.MAX_CONSECUTIVE_OVERRIDES = 3`.
  - `gate.manuscript_sha(root, cfg) -> str`: sha256 over the sorted relative paths and contents of every `.tex` and `.bib` under `document.root`, excluding `*_suggestion.tex` and files matched by the repo's `.gitignore` (checked with `git check-ignore` when git is available, else skipped).
  - `gate.path(root, cfg) -> Path` (`<outputs.dir>/verdicts/commit-gate.json`).
  - `gate.record(root, cfg, check: str, status: str, artifact: str, **extra) -> dict` writes the entry with `at` and the current `manuscript_sha` at the top level.
  - `gate.check(root, cfg) -> GateReport` dataclass: `checks: dict[name, dict(status, fresh: bool, required: bool, present: bool)]`, `verdict: "PASS" | "FAIL" | "INCOMPLETE"` (FAIL when any required present check is FAIL; INCOMPLETE when a required check is missing or stale; PASS otherwise; recommended checks only add `warnings: list[str]`), `override_streak: int`, `can_override: bool` (streak < 3), `to_dict()`.
  - `gate.override(root, cfg, reason: str, checks: list[str]) -> dict` appends to `overrides[]` and increments the streak; `gate.reset_streak(root, cfg)` is called by `record` whenever a required check records PASS.
  - CLI: `python3 scripts/gate.py [--root R] record <check> <status> --artifact P [--extra k=v] | check [--json] | override --reason R --checks a,b`.

- [ ] **Step 1: Write the failing tests**

```python
def test_incomplete_until_required_present(sample_paper, cfg):
    assert gate.check(sample_paper, cfg).verdict == "INCOMPLETE"

def test_pass_when_required_pass(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    r = gate.check(sample_paper, cfg); assert r.verdict == "PASS" and "claims" in " ".join(r.warnings)

def test_stale_after_manuscript_edit(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    (sample_paper / "sections/intro.tex").write_text("changed")
    r = gate.check(sample_paper, cfg); assert r.verdict == "INCOMPLETE" and not r.checks["compile"]["fresh"]

def test_suggestion_files_do_not_stale_the_gate(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    (sample_paper / "sections/intro_suggestion.tex").write_text("draft")
    assert gate.check(sample_paper, cfg).verdict == "PASS"

def test_override_streak_hard_stop(sample_paper, cfg):
    gate.record(sample_paper, cfg, "compile", "FAIL", "x.md")
    for _ in range(3): gate.override(sample_paper, cfg, "deadline", ["compile"])
    assert gate.check(sample_paper, cfg).can_override is False

def test_required_pass_resets_streak(sample_paper, cfg):
    gate.override(sample_paper, cfg, "r", ["compile"]); gate.record(sample_paper, cfg, "compile", "PASS", "x.md")
    assert gate.check(sample_paper, cfg).override_streak == 0
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

```bash
git add scripts/gate.py schemas/verdict.schema.json tests/test_gate.py
git commit -m "feat: commit gate verdict file"
```

---

### Task 11: Repository inventory for onboard

**Files:**
- Create: `scripts/inventory.py`, `tests/test_inventory.py`, `tests/fixtures/harness/legacy/.claude/{settings.json,skills/compile-latex/SKILL.md,rules/content-invariants.md,hooks/context-monitor.py}`

**Interfaces:**
- Produces:
  - `inventory.CLASS_TO_VENUE: dict[str, str]` = `{"llncs": "llncs-conference", "sn-jnl": "springer-ml", "svjour3": "springer-ml", "IEEEtran": "ieee-conference", "acmart": "acm-sigconf", "elsarticle": "elsevier", "article": "generic-journal", "amsart": "generic-journal", "revtex4-2": "generic-journal"}` (llncs maps to the conference profile; the springer-ml journal is offered as the second option because the traces repo targets it with llncs).
  - `inventory.inventory(root: Path, home: Path | None = None) -> dict` with keys: `main_candidates: list[str]`, `main: str | None` (single candidate or the one with `\begin{document}` and the most `\input`s; `None` when ambiguous), `doc_class`, `doc_class_options: list`, `engine_hint` (`xelatex` or `lualatex` when `fontspec` or `polyglossia` is used, else `pdflatex`), `bib_tool` (`biber` when `biblatex`, else `bibtex`), `bib_files: list[str]`, `build: dict(kind: "make" | "latexmk" | None, command, cwd, main_from_makefile)`, `pdf`, `pdf_pages: int | None`, `title`, `anonymized: bool`, `figures: list[dict(path, line, has_provenance)]`, `reviews_dir: str | None` (a directory named `review`, `reviews` or `referee*` holding `.md`, `.txt`, `.pdf`, `.docx`), `results_dir: str | None` (directory named `results` or `outputs` holding `.json` or `.csv`), `code: dict(dir, language) | None` (sibling directory with `pyproject.toml`, `requirements.txt`, `DESCRIPTION`, `Project.toml` or `package.json`), `git_remote: str | None`, `superpowers: dict(enabled: bool, id: str | None)` from `enabledPlugins` keys starting `superpowers@` in `<home>/.claude/settings.json`, `<root>/.claude/settings.json` and `<root>/.claude/settings.local.json`, `legacy_harness: list[dict(kind, path, consequence)]`.
  - `inventory.detect_legacy_harness(root) -> list[dict]`: kinds `skill_name_conflict` (a `.claude/skills/<name>` whose name is in `LEGACY_SKILL_NAMES`, the twenty traces names), `hook_entry` (any `hooks` entry in `.claude/settings.json` whose command contains `.claude/hooks/`), `statusline` (`.claude/scripts/statusline.sh` or `statusLine` in settings), `rule_restates_facts` (a `.claude/rules/*.md`, excluding `ploma-*`, with a command-shaped line: `\documentclass`, `cd <dir> && make`, `make <target>`, `pdflatex `, `bibtex `, `biber `, or a path ending in `.bib`; prose such as "make sure" never matches).
  - `inventory.propose_config(inv: dict) -> dict` (the `ploma.yaml` proposal; `venue.page_budget` null; `pipeline` present only when `code` and `results_dir` are both found, with `enabled: true` and empty `metric_keys`, `gotchas`).
  - `inventory.gaps(inv: dict, proposal: dict) -> list[dict(key, question, recommended, options)]`: `document.main` when ambiguous; `venue.profile` always (recommended from `CLASS_TO_VENUE`, options are the shipped profile keys whose `doc_classes` include the class, plus `generic-journal` and `generic-conference`); `venue.page_budget` always (recommended: the profile's `page_budget` or `null`); `pipeline.enabled` when `code` is found; `pipeline.metric_keys` when pipeline is enabled (recommended: top-level numeric keys found in the first results JSON).
  - CLI: `python3 scripts/inventory.py [--root R] [--json] [inventory|propose|gaps]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_sample_paper_inventory(sample_paper):
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    assert inv["main"] == "main.tex" and inv["doc_class"] == "article" and inv["bib_tool"] == "bibtex"
    assert inv["bib_files"] == ["refs.bib"] and inv["build"]["kind"] == "make" and inv["build"]["main_from_makefile"] == "main"
    assert inv["figures"][0]["has_provenance"] is True and inv["reviews_dir"] == "review" and inv["results_dir"] == "results"

def test_llncs_fixture_maps_to_llncs_conference(tmp_path):
    shutil.copy(FIX_TEX / "llncs_main.tex", tmp_path / "paper.tex")
    inv = inventory.inventory(tmp_path); g = {x["key"]: x for x in inventory.gaps(inv, inventory.propose_config(inv))}
    assert inv["doc_class"] == "llncs" and inv["anonymized"] is True
    assert g["venue.profile"]["recommended"] == "llncs-conference" and "springer-ml" in g["venue.profile"]["options"]

def test_two_main_candidates_become_a_gap(tmp_path):
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] is None and len(inv["main_candidates"]) == 2
    assert "document.main" in {x["key"] for x in inventory.gaps(inv, inventory.propose_config(inv))}

def test_biblatex_means_biber(tmp_path): ...
def test_superpowers_detected_on_either_marketplace(tmp_path): ...   # settings with superpowers@superpowers-marketplace
def test_legacy_harness_detected(repo_root):
    kinds = {c["kind"] for c in inventory.detect_legacy_harness(FIX_HARNESS / "legacy")}
    assert kinds == {"skill_name_conflict", "hook_entry", "rule_restates_facts"}

def test_make_sure_prose_is_not_a_fact(tmp_path):
    (tmp_path / ".claude/rules").mkdir(parents=True)
    (tmp_path / ".claude/rules/style.md").write_text("Make sure every figure has a caption. We make the case briefly.")
    assert inventory.detect_legacy_harness(tmp_path) == []

def test_superpowers_in_settings_local(tmp_path): ...   # enabled only in .claude/settings.local.json

def test_no_legacy_on_sample(sample_paper):
    assert inventory.detect_legacy_harness(sample_paper) == []
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

```bash
git add scripts/inventory.py tests/test_inventory.py tests/fixtures/harness
git commit -m "feat: read-only repository inventory for onboard"
```

---

### Task 12: Apply receipt

**Files:**
- Create: `scripts/receipt.py`, `schemas/receipt.schema.json`, `tests/test_receipt.py`

**Interfaces:**
- Produces: `receipt.MODES = ("enforced", "created-once", "merged")`; `receipt.write(root, cfg, files: list[dict(path, mode, sha256)]) -> Path` (`<outputs.dir>/ploma-receipt.json` with `ploma_version`, `at`); `receipt.load(root, cfg) -> dict | None`; `receipt.compare(root, cfg) -> list[dict(path, mode, state)]` with state `unchanged | hand_edited | missing`; `receipt.sha256_file(path) -> str`.

- [ ] **Step 1: Tests**: write then compare reports `unchanged`; edit a file then `hand_edited`; delete then `missing`; `load` on a fresh repo is `None`.
- [ ] **Step 2: Implement, run, commit** (`git commit -m "feat: onboard apply receipt"`).

---

### Task 13: Venue profiles, discipline cards, profile loader

**Files:**
- Create: `schemas/venue.schema.json`, `schemas/discipline.schema.json`, `scripts/profiles.py`, `venues/{springer-ml,llncs-conference,ieee-conference,acm-sigconf,elsevier,arxiv,generic-journal,generic-conference}.yaml`, `disciplines/{ml,generic,social-science}.yaml`, `tests/test_profiles.py`

**Interfaces:**
- Produces: `profiles.load_venue(key: str, root: Path | None) -> dict` (shipped file shadowed by `<root>/ploma.d/venues/<key>.yaml`; raises `ProfileError` listing available keys when missing), `profiles.load_discipline(key, root) -> dict`, `profiles.list_venues(root) -> list[str]`, `profiles.validate_venue(d) -> list[Finding]` (schema shape; `referee_pool` values sum to 1.0 within 0.001; every `doc_classes` entry is a string), `profiles.venues_for_class(doc_class, root) -> list[str]`.
- Venue schema keys exactly as spec §12. Discipline schema: `key`, `name`, `paper_types: list[dict(key, name, weights: dict, sanity_checks: list[str])]`, `default_paper_type`, `reproducibility_norms: list[str]`, `method_conventions: list[str]`, `challenge_examples: list[str]`, `peeves: {critical: [], constructive: []}`.
- Content sources: `springer-ml` and `llncs-conference` from `extraction/traces-harness/.claude/references/journal-profiles.md` with every domain sentence rewritten generically (the six soccer concerns become six generic ML concerns; the `MLCONF` typical concerns are already generic); the ML paper type with its weights and five sanity checks from `extraction/traces-harness/.claude/agents/methods-referee.md`; the six social-science paper types from the same file into `social-science.yaml`; the generic peeves from `editor.md` stay for Task 2 of milestone 2, the discipline-specific ones go to `ml.yaml`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("key", ["springer-ml","llncs-conference","ieee-conference","acm-sigconf","elsevier","arxiv","generic-journal","generic-conference"])
def test_shipped_venue_validates(key):
    assert [f for f in profiles.validate_venue(profiles.load_venue(key, None)) if f.status == FAIL] == []

def test_pool_sums_to_one(): ...
def test_shadowing(tmp_path):
    (tmp_path / "ploma.d/venues").mkdir(parents=True)
    (tmp_path / "ploma.d/venues/springer-ml.yaml").write_text(SHIPPED_WITH_PAGE_BUDGET_20)
    assert profiles.load_venue("springer-ml", tmp_path)["page_budget"] == 20

def test_unknown_key_lists_available():
    with pytest.raises(profiles.ProfileError, match="generic-journal"): profiles.load_venue("nope", None)

def test_venues_for_class():
    assert "llncs-conference" in profiles.venues_for_class("llncs", None) and "springer-ml" in profiles.venues_for_class("llncs", None)

def test_no_domain_words_in_generic_files(repo_root):
    for p in list((repo_root / "venues").glob("*.yaml")) + [repo_root / "disciplines/generic.yaml"]:
        assert not BANNED_RE.search(p.read_text()), p
```

- [ ] **Step 2: Run to verify failure, write the profiles and loader, run to verify pass, commit**

```bash
git add schemas/venue.schema.json schemas/discipline.schema.json scripts/profiles.py venues disciplines tests/test_profiles.py
git commit -m "feat: venue profiles, discipline cards, profile loader"
```

---

### Task 14: Doctor

**Files:**
- Create: `scripts/doctor.py`, `tests/test_doctor.py`

**Interfaces:**
- Consumes: `ploma_config`, `profiles`, `bib_check`, `inventory.detect_legacy_harness`, `receipt.compare`, `gate.check`, `state`, `project_files.render_all` (Task 17; until then the project-files group is SKIP with reason "renderer not available", and Task 17 removes that branch).
- Produces: `doctor.run(root: Path, *, which=shutil.which, home: Path | None = None) -> DoctorReport` dataclass `groups: list[dict(id, title, findings: list[Finding])]`, `verdict`, `counts: dict`, `to_dict()`, `render() -> str` in the lisa format: `Overall verdict: X`, `Counts: PASS n WARN n FAIL n INFO n SKIP n`, then `<n>. <title>` and `- STATUS id: summary` with `Observed:` and `Remediation:` lines. Group ids: `runtime`, `config`, `toolchain`, `manuscript`, `project-files`, `state`, `dependencies`, `legacy-harness`. Verdict ladder: NOT_READY if any FAIL; READY_WITH_WARNINGS if any WARN; else READY. CLI: `python3 scripts/doctor.py [path] [--json]`, exit 1 when NOT_READY.
- Severities per spec §9: missing `ploma.yaml` is FAIL `config.missing` with remediation "Run /ploma:onboard"; engine binary missing FAIL; `pdfinfo`/`pdftotext` missing WARN; `chktex`/`lacheck`/`texcount` missing SKIP; PDF missing or older than sources WARN `manuscript.pdf_stale` with remediation "Run /ploma:compile"; figures without provenance INFO (WARN when `pipeline.figure_provenance == "required"`); legacy harness conflicts WARN; superpowers missing WARN; override streak ≥ 2 WARN; citation APIs SKIP "doctor makes no network calls".

- [ ] **Step 1: Write the failing tests**

```python
def test_empty_dir_is_not_ready(tmp_path):
    r = doctor.run(tmp_path, which=lambda n: None)
    assert r.verdict == "NOT_READY"
    first_fail = next(f for g in r.groups for f in g["findings"] if f.status == FAIL)
    assert first_fail.id == "config.missing" and "/ploma:onboard" in first_fail.remediation

def test_onboarded_sample_is_ready(onboarded_sample):          # fixture: sample_paper after project_files.apply, with a PDF newer than sources
    r = doctor.run(onboarded_sample, which=lambda n: "/usr/bin/" + n if n in ("pdflatex","bibtex","pdfinfo","pdftotext","make","git") else None)
    assert r.verdict == "READY", r.render()

def test_missing_linters_are_skip_not_warn(onboarded_sample):
    r = doctor.run(onboarded_sample, which=lambda n: None if n in ("chktex","lacheck","texcount") else "/usr/bin/"+n)
    assert all(f.status == SKIP for g in r.groups for f in g["findings"] if f.id.startswith("toolchain.chktex"))

def test_stale_pdf_warns(onboarded_sample): ...
def test_proposal_type_is_not_ready(onboarded_sample): ...
def test_render_format(onboarded_sample):
    txt = doctor.run(onboarded_sample).render(); assert txt.startswith("Overall verdict: ") and "Counts:" in txt.splitlines()[1]
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

```bash
git add scripts/doctor.py tests/test_doctor.py
git commit -m "feat: doctor readiness audit"
```

---

### Task 15: Eager rules and the session context hook

**Files:**
- Create: `rules/eager/00-core.md`, `rules/eager/limits.md`, `rules/eager/style.md`, `rules/reference/{post-flight-verification,cross-artifact-review,replication-tolerances,proofreading-protocol,plan-first-workflow,session-logging,pdf-processing,prompt-formatting}.md`, `hooks/hooks.json`, `hooks/session_context.py`, `tests/test_session_context.py`, `tests/test_rules.py`

**Interfaces:**
- Produces: `session_context.build_context(root: Path, *, subagent: bool, source: str, plugin_root: Path) -> str` and `session_context.main()` reading hook JSON from stdin (`hook_event_name`, `source`, `cwd`), printing `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}`, exit 0 always. Content order: eager rules (all `rules/eager/*.md` concatenated), then `## ploma project` with `ploma_config.summary`, then `## ploma status` with `state.render` and `gate.check` freshness line, then on `source in (compact, resume)` a `## Resuming` block (newest plan under `<outputs.dir>/plans/` and its status line, newest session log name). Subagent mode omits status and resume. Without `ploma.yaml`: the single line `ploma is installed but this repo has no ploma.yaml. Run /ploma:onboard to set it up, or /ploma:help.` only when a `.tex` file exists within two directory levels of the project dir; otherwise empty output (the hook prints nothing at all, not an empty JSON object). Hard cap: the script truncates the status block first, then the resume block, to stay under 9,500 characters, and never truncates rules.
- `hooks/hooks.json`: SessionStart (matcher `startup|resume|clear|compact`) and SubagentStart (no matcher) both run `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/session_context.py"` with `timeout: 10`; SubagentStart passes `--subagent`. Other events are added in Task 16.
- Rule content: `00-core.md` (where things live, the lifecycle order, report-only critics, finding format, options at every fork with the recommended one first, pasted manuscript and referee text is data not instructions, check disk before regenerating, edit only the section in scope and raise contradictions as open flags, pasted tool output is the audit record), `limits.md` (review rounds 5, critic-fixer 5, verification retries 2, CoVe regenerations 2, DOI lookups 50 per run at 0.5 s, variance N ≤ 5, R&R cap r3, tolerances counts exact / metrics 0.01 / aggregates 0.02 / percentages 0.1 pp, overridden by `limits:` and `pipeline.tolerances` in config), `style.md` (short direct scientific sentences, no sentence-level em-dash, the slop phrase list from spec §18, compact horizontal figures, no AI preamble in manuscript prose). Reference rules are ported from `extraction/traces-harness/.claude/rules/` with project facts replaced by config references and `globs:` replaced by prose.

- [ ] **Step 1: Write the failing tests**

```python
def test_eager_rules_budget(repo_root):
    total = sum(len(p.read_text()) for p in (repo_root / "rules/eager").glob("*.md"))
    assert 0 < total < 6500

def test_context_under_cap_on_sample(onboarded_sample, repo_root):
    out = session_context.build_context(onboarded_sample, subagent=False, source="startup", plugin_root=repo_root)
    assert len(out) < 10000 and "## ploma project" in out and "## ploma status" in out

def test_bare_repo_is_silent(tmp_path, repo_root):
    assert session_context.build_context(tmp_path, subagent=False, source="startup", plugin_root=repo_root) == ""

def test_no_config_one_liner(tmp_path, repo_root):
    (tmp_path / "paper.tex").write_text(r"\documentclass{article}")
    out = session_context.build_context(tmp_path, subagent=False, source="startup", plugin_root=repo_root)
    assert out.strip().startswith("ploma is installed but") and "/ploma:onboard" in out

def test_invalid_yaml_yields_notice_and_exit_zero(tmp_path, repo_root, capsys):
    (tmp_path / "ploma.yaml").write_text("document: [unclosed")
    rc = session_context.main(stdin=io.StringIO(json.dumps({"hook_event_name":"SessionStart","source":"startup","cwd":str(tmp_path)})), plugin_root=repo_root)
    assert rc == 0 and "could not be parsed" in json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]

def test_subagent_mode_omits_status(onboarded_sample, repo_root): ...
def test_resume_block_on_compact(onboarded_sample, repo_root): ...
def test_hooks_json_wires_session_events(repo_root):
    h = json.loads((repo_root / "hooks/hooks.json").read_text())["hooks"]
    assert "SessionStart" in h and "SubagentStart" in h

def test_no_em_dash_and_no_domain_words_in_rules(repo_root): ...
```

- [ ] **Step 2: Run to verify failure, write the rules and the hook, run to verify pass, commit**

```bash
git add rules hooks/hooks.json hooks/session_context.py tests/test_session_context.py tests/test_rules.py
git commit -m "feat: eager rules and session context hook"
```

---

### Task 16: Ported hooks

**Files:**
- Create: `hooks/_hookutil.py` (read stdin JSON, resolve project dir, `.ploma/` state dir, `fail_open` decorator, `emit(obj)`), `hooks/pre_compact.py`, `hooks/context_monitor.py`, `hooks/verify_reminder.py`, `hooks/log_reminder.py`, `tests/test_hooks.py`
- Modify: `hooks/hooks.json` (PreCompact, PostToolUse `Bash|Task|Agent` and `Write|Edit`, Stop)

**Interfaces:**
- `pre_compact.main(stdin, root) -> int`: reads the three newest `<outputs.dir>/plans/*.md` whose text lacks `COMPLETED`, status from the first line matching `^\*\*Status:\*\*\s*(DRAFT|APPROVED)` (no substring search), current task as the first `- [ ]` line; last 50 lines of the newest session log for lines starting `Decision:` or `Decided:`; writes `.ploma/pre-compact-state.json`; prints a short summary to stderr; blocks once per DRAFT plan when `PLOMA_PRECOMPACT_BLOCK_ON_DRAFT=1` using `.ploma/precompact-block-sentinel.json`; never appends to project files (the traces version did; dropped).
- `context_monitor.main(stdin, root) -> int`: same thresholds and throttle as traces (40, 55, 65 nudge to `/ploma:checkpoint`; 80 info; 90 caution; 60 s throttle), estimate from transcript size via `transcript_path` when present else a tool-call counter, state in `.ploma/context-monitor-cache.json`; output `{"systemMessage": ..., "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}` only when a threshold is crossed.
- `verify_reminder.main(stdin, root, cfg) -> int`: suffix lookup lower-cased on both sides; map `.tex` to "Run /ploma:compile", `.bib` to "Run /ploma:validate-bib", the pipeline language extension (`.py`, `.r`, `.jl`, `.m` by `pipeline.language`) to "Run the code reviewer"; skip paths under `<outputs.dir>/`, `.claude/`, `.ploma/`, `docs/`; dedupe per file for 300 s in `.ploma/verify-reminder-cache.json`.
- `log_reminder.main(stdin, root, cfg) -> int`: ported unchanged in behaviour (stderr once when no session log; once after 50 responses without the newest log changing; respects `stop_hook_active`), state in `.ploma/log-reminder-state.json`, never blocks.

- [ ] **Step 1: Write the failing tests** (one per behaviour named above, plus `test_all_hooks_exit_zero_on_garbage_stdin` feeding `"not json"` to every `main` and asserting 0, and `test_hooks_noop_without_config` asserting empty stdout and exit 0 on a bare `tmp_path` for every hook including `session_context`)
- [ ] **Step 2: Run to verify failure, port the hooks from `extraction/traces-harness/.claude/hooks/`, run to verify pass, commit**

```bash
git add hooks tests/test_hooks.py
git commit -m "feat: port pre-compact, context monitor, verify and log reminder hooks"
```

---

### Task 17: Project files renderer and applier

**Files:**
- Create: `scripts/project_files.py`, `templates/claude-md-section.md`, `templates/rules/ploma-manuscript.md`, `templates/rules/ploma-pipeline.md`, `templates/quality_reports/README.md`, `templates/learnings.md`, `templates/statusline.sh`, `tests/test_project_files.py`
- Modify: `scripts/doctor.py` (project-files group now compares `render_all` output with disk for enforced files and reports drift as WARN `project-files.drift.<path>`; marker section presence; `.gitignore` coverage; receipt presence)

**Interfaces:**
- Produces: `project_files.FileSpec` dataclass `path: str, mode: str, content: str`; `project_files.render_all(cfg: dict, root: Path) -> list[FileSpec]` returning in order: `.claude/rules/ploma-manuscript.md` (enforced; frontmatter `paths:` covering `<document.root>/**/*.tex` and each bib file; body: engine, class, bib tool, cite style, anonymity, style block, "facts live in ploma.yaml, do not restate them here"), `.claude/rules/ploma-pipeline.md` (enforced, only when `pipeline.enabled`; `paths:` on `<run_from>/**`; env contract, gotchas, run command, tolerances), `<outputs.dir>/README.md` (created-once), `<outputs.dir>/learnings.md` (created-once), `<outputs.dir>/ploma-state.yaml` (created-once, via `state`), `CLAUDE.md` (merged: the section between `<!-- ploma:begin -->` and `<!-- ploma:end -->` replaced or appended), `.gitignore` (merged: lines `.ploma/`, `<outputs.dir>/session_logs/`, `<outputs.dir>/.cache/` appended when absent); `project_files.settings_suggestion(cfg) -> dict` (the proposed `.claude/settings.json` additions: `plansDirectory`, Bash allow entries for the build command, `pdfinfo`, `pdftotext`, `chktex`, `lacheck`, `texcount`); `project_files.plan(root, cfg) -> list[dict(path, mode, action: create | overwrite | merge | skip_hand_edited | unchanged, diff: str)]` using `receipt.compare`; `project_files.apply(root, cfg, plan) -> list[dict]` writing per mode and then `receipt.write`. Template variables use `{{ key.path }}` substituted by a 15-line renderer (no Jinja).

- [ ] **Step 1: Write the failing tests**

```python
def test_render_all_paths_and_modes(sample_paper, cfg):
    specs = {s.path: s.mode for s in project_files.render_all(cfg, sample_paper)}
    assert specs[".claude/rules/ploma-manuscript.md"] == "enforced" and specs["CLAUDE.md"] == "merged" and specs["results/README.md"] == "created-once"

def test_apply_is_idempotent(sample_paper, cfg):
    project_files.apply(sample_paper, cfg, project_files.plan(sample_paper, cfg))
    second = project_files.plan(sample_paper, cfg); assert {p["action"] for p in second} == {"unchanged"}

def test_created_once_survives_hand_edit(sample_paper, cfg): ...
def test_marker_section_replaced_in_place(sample_paper, cfg):
    (sample_paper / "CLAUDE.md").write_text("# Mine\n\nkeep\n\n<!-- ploma:begin -->\nold\n<!-- ploma:end -->\n\nafter\n")
    project_files.apply(sample_paper, cfg, project_files.plan(sample_paper, cfg))
    t = (sample_paper / "CLAUDE.md").read_text(); assert "keep" in t and "after" in t and "old" not in t and t.count("ploma:begin") == 1

def test_enforced_drift_is_doctor_warn(onboarded_sample): ...
def test_rules_have_paths_frontmatter_and_no_domain_words(sample_paper, cfg): ...
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit**

```bash
git add scripts/project_files.py templates tests/test_project_files.py scripts/doctor.py tests/test_doctor.py
git commit -m "feat: project files renderer and applier; doctor drift checks"
```

---

### Task 18: Skills onboard, doctor, help, status; skill lint test; evals

**Files:**
- Create: `skills/onboard/SKILL.md`, `skills/onboard/references/questions.md`, `skills/doctor/SKILL.md`, `skills/status/SKILL.md`, `tests/test_skills.py`, `evals/{onboard,doctor,help,status}/prompt.md`, `evals/{onboard,doctor,help,status}/graders/*.md`
- Modify: `skills/help/SKILL.md`

**Interfaces:**
- `tests/test_skills.py` (used by every later skill task): every `skills/*/SKILL.md` has frontmatter with `name` equal to the directory, `description` under 1,536 characters, `allowed-tools` present; body under 500 lines; no banned domain words; no em-dash; every relative path it mentions under `${CLAUDE_PLUGIN_ROOT}/` exists; skills in `HIDDEN = {onboard, commit, deep-audit, learn, checkpoint, compress-session}` have `disable-model-invocation: true`.
- `skills/onboard/SKILL.md` (`disable-model-invocation: true`, `argument-hint: "[--dry-run] [--yes]"`, allowed-tools Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion): the eight-step flow of spec §8 with the legacy-harness step. Each step names the script command and quotes its JSON as the audit record. Gaps are asked with `AskUserQuestion`, one call with up to four questions, recommended option first, except `document.main` which is asked alone first when ambiguous. "Propose" shows the full `ploma.yaml` and the plan table; writing happens only after the user says yes (or `--yes`). Ends with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"` and the verdict.
- `skills/doctor/SKILL.md`: run `doctor.py`, print its render verbatim, then one sentence per FAIL and WARN with the remediation, never ask to proceed, never fix.
- `skills/status/SKILL.md`: `state.py render`, `gate.py check`, context monitor cache if present, newest plan and session log; one screen.
- `skills/help/SKILL.md`: what ploma is, the lifecycle table with the skill for each stage, which skills exist now and which arrive in milestone 2 (named, marked "not yet installed"), the install and update commands.
- Evals: `prompt.md` with `max_turns` and the prompt (`/ploma:doctor` on the sample paper via `case.yaml` `add_dirs: [examples/sample-paper]`), graders `tool_used.md` (Skill with the name), `llm.md` (rubric: verdict line present, no "proceed?" question, remediation per FAIL).

- [ ] **Step 1: Write `tests/test_skills.py` and run it** (fails on the placeholder help skill)
- [ ] **Step 2: Write the four skills and the evals, run `python3 -m pytest tests/test_skills.py -v` and `claude plugin validate .`**
- [ ] **Step 3: Dry-run onboard by hand on `examples/sample-paper/`** in a throwaway copy: `claude --plugin-dir . -p "/ploma:onboard --dry-run"` from the copy; expected: a proposal with `document.main: main.tex`, venue gap with `generic-conference` recommended, no file written. Record the transcript path in the commit message.
- [ ] **Step 4: Commit**

```bash
git add skills tests/test_skills.py evals
git commit -m "feat: onboard, doctor, help, status skills with evals"
```

---

### Task 19: Compile script and skill

**Files:**
- Create: `scripts/compile.py`, `skills/compile/SKILL.md`, `tests/test_compile.py`, `evals/compile/`

**Interfaces:**
- Produces: `compile.run(root, cfg, *, runner=subprocess.run, clean: bool = False) -> CompileReport` dataclass `ok, command, cwd, returncode, log: LogReport, pages: int | None, budget: dict, report_path, duration_s, to_dict()`. Build command: `build.command` run in `build.cwd` when set; otherwise `latexmk -<engineflag> -interaction=nonstopmode -halt-on-error -file-line-error <main>` where the engine flag is `-pdf`, `-pdfxe` or `-pdflua`; `clean` runs `make clean` or `latexmk -c`. After the run: `latex_log.parse_log` on `build.log` (even on failure), `pdf_pages.page_count` and `budget_report`, write `<outputs.dir>/compile_<slug>.md` (sections Build, Errors, Undefined, Overfull, Pages vs budget, Next step), `gate.record("compile", PASS | FAIL, ...)` with `pages`, `overfull`, `undefined` extras (FAIL when errors or undefined citations or references, or budget FAIL), `state.record("compile", ...)`. CLI: `python3 scripts/compile.py [--root R] [--clean] [--json]`, exit 0 on PASS.
- `skills/compile/SKILL.md`: run the script, quote the report, on errors show the first error with file and line and stop ("fix the first error, not the last"), max two rebuilds within one invocation, then recommend `/ploma:format` when over budget or `/ploma:validate-bib` on undefined citations.

- [ ] **Step 1: Write the failing tests** (runner stubbed to copy a fixture log into place and write a fixture PDF; cases: clean run gives PASS and gate entry with pages; error log gives FAIL and report lists the file and line; over budget gives FAIL with `over_by`; missing `build.command` uses latexmk with `-pdfxe` for xelatex; `clean=True` runs the clean target)
- [ ] **Step 2: Run to verify failure, implement, run to verify pass, write the skill and eval, run `tests/test_skills.py`, commit**

```bash
git add scripts/compile.py skills/compile tests/test_compile.py evals/compile
git commit -m "feat: compile script and skill"
```

---

### Task 20: Validate-bib script and skill

**Files:**
- Create: `scripts/validate_bib.py`, `skills/validate-bib/SKILL.md`, `tests/test_validate_bib.py`, `evals/validate-bib/`

**Interfaces:**
- Produces: `validate_bib.run(root, cfg, *, semantic: bool, skip_doi: bool = False, mailto: str = "", keys: dict = {}, fetch=None) -> BibReport` with `findings`, `lookups: list[LookupResult]`, `verdict: PASS | FAIL`, `report_path`, `to_dict()`. Structural part from `bib_check.check`; semantic part runs `cite_lookup.run` on the cited entries (max `limits.doi_lookups_per_run`) and adds findings `bib.lookup.missing.<key>` (FAIL), `bib.lookup.mismatch.<key>` (FAIL), `bib.lookup.partial.<key>` (WARN), `bib.lookup.unreachable.<key>` (WARN, never FAIL). Report `<outputs.dir>/bib_audit_<structural|semantic>.md` in the format of `extraction/traces-harness/quality_reports/sample_outputs/bib_audit_semantic.md` (summary table Check × Critical/Medium/Low, `Verdict:` line, sections Structural, Citation drift, DOI verification, Style, Next steps). `gate.record("bib", verdict, ...)`, `state.record("validate-bib", ...)`. CLI: `python3 scripts/validate_bib.py [--root R] [--semantic] [--skip-doi] [--mailto X] [--json]`.
- `skills/validate-bib/SKILL.md` (`argument-hint: "[--semantic] [--skip-doi]"`): run the script passing `${user_config.crossref_mailto}`; quote the summary table and verdict; list FAILs with the fix; `--cite-claim` from traces is dropped (verify-claims owns claim checks, milestone 2).

- [ ] **Step 1: Write the failing tests** (structural PASS on the sample; a missing key gives FAIL and the report's Structural section names it; semantic with a fake fetch that verifies all gives PASS and a DOI table; an unreachable API gives WARN not FAIL; the report file matches the section headings of the sample format)
- [ ] **Step 2: Run to verify failure, implement, run to verify pass, write the skill and eval, commit**

```bash
git add scripts/validate_bib.py skills/validate-bib tests/test_validate_bib.py evals/validate-bib
git commit -m "feat: validate-bib script and skill"
```

---

### Task 21: Milestone wrap: docs, validation, hand-off

**Files:**
- Modify: `README.md` (install on both hosts, the HTTPS note, running tests, what is in milestone 1), `CHANGELOG.md` (`0.1.0-m1` entry), `skills/help/SKILL.md` (milestone table current)

- [ ] **Step 1: Run the full suite and the validator**

Run: `python3 -m pytest -q && claude plugin validate .`
Expected: all tests pass; validate clean

- [ ] **Step 2: Run the shipped eval cases once locally**

Run: `claude plugin eval . --trust-plugin --max-cost-usd 5 --json /tmp/claude-1001/-home-mgarnica-papers/b4e0a978-aa5b-4d23-9754-bdfd063a6d19/scratchpad/evals-m1.json`
Expected: every milestone-1 case passes its `tool_used` grader; record the scores in the commit message. If the eval runner is unavailable in this environment, say so in the commit message and leave the cases for `traces-16`.

- [ ] **Step 3: Commit and send the hand-off message to `traces-16`**

```bash
git add README.md CHANGELOG.md skills/help
git commit -m "docs: milestone 1 ready for real-TeX testing"
git push origin main
```

Message to `traces-16`: commit SHA, install commands, the four skills to run on the traces repo in order (`/ploma:onboard` then `/ploma:doctor` then `/ploma:compile` then `/ploma:validate-bib --semantic`), the legacy-harness checklist expectation, and a request to report defects as a list with the script output pasted.

---

## Self-review notes

- Spec coverage: §4 layout (Tasks 1, 4), §5 config (3), §6 state and gate (9, 10, 12), §7 lifecycle order (9) and the compile and validate-bib rows (19, 20), §8 onboard (11, 17, 18), §9 doctor (14, 17), §11 hooks (15, 16), §12 profiles (13), §13 scripts (5, 6, 7, 8 and the rest), §14 evals and CI (1, 18), §15 install docs (21). The remaining skills, agents, consistency, style check, placeholders and commit gate wiring are in the milestone 2 plan.
- Names used across tasks: `ploma_config.load/validate/resolve/summary`, `_findings.Finding/PASS/WARN/FAIL/INFO/SKIP`, `state.record/load/next_stage/render`, `gate.record/check/override`, `inventory.inventory/propose_config/gaps/detect_legacy_harness`, `receipt.write/compare`, `profiles.load_venue/load_discipline`, `project_files.render_all/plan/apply`, `latex_log.parse_log`, `pdf_pages.page_count/budget_report`, `bib_check.check/cite_keys/resolve_bib_files`, `cite_lookup.lookup/run`. Each later task consumes exactly these.
- Review Focus tests are placed: 1 in Task 7, 2 in Task 3, 3 in Task 5, 4 in Task 11, 5 in Task 15.
