# ploma public README, logo and hero film: design

Date: 2026-10-30. Status: approved by Marc on 2026-10-30. The implementation plan is `docs/superpowers/plans/2026-10-30-readme-marketing.md`.

## Context

ploma 0.2.0 is released and the repo (`marcgarnica13/ploma`, private today) is about to go public. The current README is a reference manual: dense, correct, no visuals, no logo. Marc wants a landing page instead. A researcher who writes LaTeX papers and uses Claude Code or Codex should land on it and feel, within thirty seconds, that they found the exact assistant: state-of-the-art agents that understand the work, review it scientifically, check every finding, and raise productivity without degrading the writing. No slop.

Marc also wants a logo and an animated hero film rendered with HyperFrames (HeyGen's open-source HTML-to-video renderer) showing mac-styled windows: a beautiful terminal driving a session while a PDF fills itself in.

Decisions were taken in a brainstorm on 2026-10-30 against a mockup page (hero layout, live sketch of the film, page order, three logo directions). Marc approved every recommended option.

## Intent

The README has one job: earn trust fast, then get the reader to install. The fanciness comes from craft (logo, motion, typography, structure, real output), never from adjectives. The page itself must read as something ploma would let through its own gate.

## Goals

- A public-facing README that opens with a logo lockup, a one-line thesis, and the hero film, then tells the workflow story in the order grill, understand, reason, commit to text.
- A logo: a fountain-pen nib (ploma is Catalan for fountain pen), monochrome, crisp at 16 px and 400 px, light and dark variants, plus a wordmark lockup.
- A hero film of about 25 seconds rendered with HyperFrames, embedded as an autoplaying GIF with the MP4 one click away.
- A fictional but realistic demo paper in `examples/demo-paper` that ploma actually runs on, so the film and the section screenshots show real ploma output.
- The reference material that lives in the README today survives, moved into `docs/` and linked.

## Non-goals

- No docs site, no GitHub Pages. The README is the whole landing page.
- No changes to skills, hooks, scripts or behaviour. This is documentation and assets only.
- No version bump; the work lands on `main` under an `Unreleased` heading in the changelog.
- Flipping the repo to public stays Marc's manual step after the README lands.

## Anti-goals (what makes this a failure even if it ships)

- Marketing copy that ploma's own proofreader would flag: adjective stacks, "not X but Y" framing, em-dashes, exclamation marks, invented statistics.
- A film that shows output ploma does not produce. Every line in the terminal must come from a real run, condensed but not invented.
- A README that no longer tells a co-author how to install on Codex or switch hosts because the detail was cut rather than moved.
- A README that breaks `claude plugin validate .` or the test suite. (Checked: no test or script reads `README.md`, `docs/`, `assets/`, `media/` or `examples/demo-paper`; the tests read only `examples/sample-paper`. The risk is low but the check stays.)

## Constraints

- Prose rules from Marc: no em-dashes anywhere (README, docs, SVG metadata, alt text), short direct sentences, British spelling as in the current README ("licence").
- GitHub README rendering: Markdown plus the HTML subset GitHub allows. `<picture>` with `prefers-color-scheme` sources works for the logo; GIFs autoplay; MP4s committed to the repo do not render inline. Relative asset paths so the marketplace listing and forks render too.
- Plugin installs clone this repo, so committed assets must stay small: GIF at or under 6 MB, stills at or under 300 KB each, MP4 committed only when at or under 4 MB (see Film).
- Toolchain on the build machine: Node 22.22, npm 10.9, FFmpeg 6.1. No system Chromium was found; HyperFrames' renderer supplies its own headless Chrome or the plan installs one. TeX Live is absent here; Marc decided (2026-10-30) that the builder installs it on this machine (`texlive-latex-recommended`, `texlive-latex-extra`, `texlive-fonts-recommended`, `latexmk`, about 600 MB, via apt) so compile, the commit gate and the stills run locally.
- The real runs: every skill except grill runs headless on `examples/demo-paper` (`claude -p --plugin-dir .`). Grill needs a person: Marc runs one interactive grill session on the demo paper and pastes the transcript into `media/transcripts/grill.md`. The builder prepares the demo paper and the exact command first, so Marc's part is one session. Runs bill model calls and `validate-bib --semantic` needs network and the citation API keys from the plugin options.
- HyperFrames is Apache-2.0; its sources and the composition live in the repo so the film can be re-rendered. `node_modules` and render output are gitignored.
- Licence stays Apache-2.0; Fraunces (used for the wordmark) is under the SIL Open Font License and is converted to outlines, so no font file ships.

## Decisions (as Marc took them)

### Hero layout: A, cinematic

Small logo lockup centred, one-line thesis, one tagline, badges, two links ("Install", "See the workflow"), then the film full width. The headline is read first; the film proves it a second later.

### The film: five beats, about 25 seconds, loops

Composition 1600 by 1000, 30 fps, dark studio gradient background. Two mac-styled windows: a Terminal window front left (title "demo-paper, claude") and a PDF viewer behind right (title "main.pdf, page 1 of N"). The terminal shows a Claude Code session, so its lines are the user's typed skill commands and ploma's replies as Claude Code prints them, not a bare shell.

| Beat | Time | Terminal | PDF window |
|---|---|---|---|
| 1 Open | 0 to 3 s | Empty prompt; the nib mark fades in on the prompt line; the user types `/ploma:grill sections/intro.tex` | hidden |
| 2 It grills you | 3 to 9 s | ploma lists what the repo settled (including: the intro says 31%, `results/bench.json` says 27.4%, the results win, with file:line evidence), then asks the one open question (see Demo paper) with a recommended answer and its reason; the user picks it with one keystroke; the decision log line appears | hidden |
| 3 It writes, you say yes | 9 to 17 s | `/ploma:write intro`: ploma reports the suggestion file, citations verified, the claim pinned to `bench.json`; then `/ploma:write intro --merge`, ploma shows the diff summary and asks, the user types `yes`; then `/ploma:compile`, pages against budget | slides in on compile; the introduction appears word by word; the grounded number is highlighted as it lands |
| 4 It refuses to lie | 17 to 22 s | `/ploma:commit`; the gate checks tick one by one (compile, bib, consistency); `gate: PASS`; the commit line | holds |
| 5 Tagline | 22 to 25 s | both windows dim | the lockup and the tagline hold two seconds, then loop |

Marc chose to show the merge and the yes rather than let the PDF fill in straight after write (which ploma does not do). All terminal text is taken from real runs on the demo paper and condensed (fewer lines, same words). The PDF window shows the page compiled by the real `/ploma:compile` run (TeX Live is installed for this), rendered to PNG; the word-by-word reveal is a mask animation over that page so the words are exactly the ones `/ploma:write` produced and the merge put in the manuscript.

Outputs: `assets/film/ploma-hero.gif` (1000 px wide, 15 fps, two-pass palette, at or under 6 MB), `assets/film/ploma-hero.png` (a still from beat 3, the fallback and social preview), and `assets/film/ploma-hero.mp4` committed when it is at or under 4 MB (H.264, 1600 by 1000; a 25 second screen recording of this kind compresses well) and linked from the GIF caption. If it comes out larger, it is attached to the existing 0.2.0 GitHub release instead and the caption links there. My call: committing it avoids coupling the README to a release that predates it.

### Page order

1. Logo lockup, thesis, tagline, badges (version, licence, Claude Code, Codex, tests), links to Install and to the workflow section.
2. The film, with a one-line caption linking to the MP4 and to `examples/demo-paper`, stating that the paper is a fictional demo that ships in the repo so the session can be reproduced.
3. Why ploma exists. Three short paragraphs, one concrete example each: agents write fluent prose that is not grounded; science needs every number traceable to a result and every citation to a record; ploma makes the agent earn each sentence and refuses to commit until the checks pass.
4. How a paper gets written. Four stages, one mac-styled still each: Grill (one question, recommended answer), Spec (the binding paper spec), Write (a suggestion file, merged only on your yes), Ship (the commit gate verdict). One or two sentences per stage, outcome first.
5. What stops slop. verify-claims, audit-reproducibility, validate-bib against Crossref and OpenAlex, review in referee mode, devils-advocate, proofread. One line each.
6. Install in two minutes. Claude Code and Codex side by side (a two-column table); onboard writes nothing without approval. HTTPS setup and API keys link to `docs/install.md`.
7. The full lifecycle. The existing stage table kept as is; the per-skill list collapsed in a `<details>` block.
8. Trust and testing. The test count as measured at build time (1440 today), headless field tests on real papers, no billed evals, known issues linked to the changelog.
9. Credits and licence. Apache-2.0, `UPSTREAMS.md`, HyperFrames credited for the film.

### Reference material moves to docs/

- `docs/install.md`: both hosts in full, HTTPS credentials, updates, API keys and `~/.codex/config.toml`.
- `docs/hosts.md`: switching hosts, co-authors on Codex, `host_mismatch`.
- `docs/commit-gate.md`: required and recommended checks, override syntax, streak, `gate.py check`.
- `docs/testing.md`: pytest, `claude plugin validate`, headless field tests on both hosts, the optional evals and their sandbox notes.

Nothing in the current README is deleted; every paragraph either stays or moves. The README links each doc where its summary ends.

### Logo: A, the nib

A fountain-pen nib outline with breather hole and slit, two strokes, monochrome. Beside the wordmark the slit reads as the "l" of ploma. Wordmark in Fraunces (soft serif, medium weight, tight tracking), converted to paths.

Files under `assets/logo/`: `ploma-mark.svg` and `ploma-mark-dark.svg` (explicit fills, since GitHub's `<img>` does not inherit `currentColor`), `ploma-lockup.svg` and `ploma-lockup-dark.svg`, `ploma-mark-512.png`. The README header uses `<picture>` to pick the variant by colour scheme. The repo already tracks `.claude-plugin/icon.png` (512 by 512, from the plugin skeleton, referenced by no manifest); my call: it is replaced by the nib at the same path and size, so one icon exists. The manifests themselves are untouched.

Palette for the whole identity: ink `#1d1b17` on paper `#f6f4ef` (light), paper-white `#e8e6e0` on `#14151a` (dark); accent ink blue `#1f5f8b`; copper `#b4552d` only as a small accent in the film and stills, never in the mark.

### Demo paper: `examples/demo-paper`

A fictional, plausible systems paper. Working title "Tracing Agentic Workloads at Scale" (builder may improve it). Contents: `ploma.yaml`, `main.tex`, `sections/intro.tex`, `sections/method.tex`, `sections/results.tex`, `refs.bib`, `results/bench.json`, `Makefile`. It must compile with pdflatex or latexmk.

Two things are built into it on purpose. First, the intro carries one claim that disagrees with `results/bench.json` (the manuscript says 31%, the results say 27.4%). Grill looks facts up before asking, so this conflict shows under "Settled by the repo" in beat 2 and gives write a real number to pin. Second, one decision the repo cannot settle, so grill has a genuine question: `bench.json` reports the latency cut against two baselines (for example OpenTelemetry and raw logs) and the intro names neither, so the Empiricist asks which baseline the headline claim compares against, recommending the stronger one. My call, from the grill skill's rule that it never asks what the repo answers.

Citations are real, resolvable records with DOIs so `validate-bib --semantic` passes. Authors are "ploma demo", no real names. The README and the paper's own comment header say it is fictional.

The existing `examples/sample-paper` stays; tests and evals keep pointing at it.

### Copy

Thesis (draft, builder may tighten but not lengthen): "A research co-author for Claude Code and Codex. It grills your idea, grounds every claim in your results and your references, and refuses to commit what it cannot check."

Tagline: "Your paper. Your claims. Checked."

Voice: short sentences, concrete nouns, outcome first. Say what ploma does, never what it is like. No superlatives.

## Pipeline (how it gets made)

1. `media/film/` is a HyperFrames project (`npx hyperframes init`), composition in HTML with GSAP timeline, mac Terminal and window chrome built from HyperFrames blocks where they fit and plain HTML where they do not. `media/film/README.md` documents `npm install`, `npx hyperframes preview`, `npx hyperframes render`, and the FFmpeg command that produces the GIF and the still.
2. `media/stills/` holds the four stage stills as HTML compositions rendered to PNG with the same chrome and palette.
3. The transcript text for the film and the stills is captured by running ploma on `examples/demo-paper` for real (headless `claude -p --plugin-dir .` for write, merge, compile, validate-bib, spec and commit; Marc's interactive session, copied verbatim, for grill) and saved under `media/transcripts/` so the condensation is auditable. The runs happen in a scratch copy of the demo paper so the committed example stays at its starting state (the 31% intro, no suggestion file, no decision log).
4. `scripts/` is not touched. A small `media/Makefile` or npm scripts tie render, gif and still together.
5. `.gitignore` gains `media/**/node_modules/`, `media/**/out/`, `media/**/.hyperframes/` (or whatever cache the pinned version writes) and `examples/demo-paper/build/`. The banned-term test (`tests/_banned.py`) scans only skills, agents, rules, templates and profiles, so the em-dash check for README, docs and assets is the grep in Verification.

## Left to the builder

- Exact HyperFrames version to pin, and whether its Terminal block or plain HTML chrome gives the better result.
- Typeface for the terminal (a mono face with a terminal feel) and for the PDF rendition (Computer Modern-like).
- Exact timing within each beat, easing, and the cursor and typing effects.
- Badge provider and exact badges.
- The demo paper's method and results sections beyond what the intro and `bench.json` need.
- Whether the tests count badge is static text updated at release or a live badge.

## Verification

- `python3 -m pytest -q` passes with the same count or more; `claude plugin validate .` passes.
- `grep -rn "—" README.md docs assets media examples/demo-paper` returns nothing.
- `du -sh assets` under 12 MB in total; the GIF under 6 MB; the MP4 under 4 MB or not committed; no `node_modules`, no render output committed.
- `examples/demo-paper` compiles with the installed TeX Live and is committed in its starting state.
- README rendered on GitHub (push, then view): logo swaps with the theme, GIF autoplays, every link resolves, `<details>` opens.
- `/ploma:doctor` on `examples/demo-paper` reports READY; `/ploma:validate-bib --semantic` passes; `/ploma:compile` passes where TeX Live exists.
- Every terminal line in the film can be matched to a line in `media/transcripts/`.
- The four docs together contain every paragraph removed from the README (diff the old README against README plus docs).
