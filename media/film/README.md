# film

The README hero film. A terminal runs a real ploma session while a PDF window fills in with the paragraph ploma wrote. It is a HyperFrames project (HeyGen's HTML-to-video renderer), pinned to `hyperframes@0.8.166`.

## Files

| file | what it is |
|---|---|
| `compositions/main.html` | the composition: 1600 by 1000, 25 s, one paused GSAP timeline on `window.__timelines.main` |
| `inline_data.py` | copies `script.json` and `pdf_words.json` into the composition's DATA block |
| `script.json` | the terminal lines, in five beats: `open`, `grill`, `write`, `ship`, `tagline` |
| `pdf_words.py` | writes `pdf_words.json` and `assets/page-1.png` from the compiled PDF |
| `pdf_words.json` | one box per word of the rewritten intro paragraph, as fractions of the page |
| `assets/demo-main.pdf` | the demo paper right after the merge and the second `/ploma:compile` |
| `assets/page-1.png` | page 1 of that PDF at 200 dpi |
| `make_gif.sh` | turns the MP4 into the GIF, the still and the committed MP4 |
| `shared`, `logo` | symlinks to `media/shared` and `assets/logo` |

## The rule

Every `text` in `script.json` is copied from `media/transcripts/*.md`. A line may be cut at a clause boundary. It is never reworded. `tests/test_film.py` checks this. The closing card copy is listed under "Fixed copy" in `media/transcripts/README.md`.

Markdown markers that Claude Code would not show stay in the DOM inside `<i class="mk">`, which `chrome.css` hides. So each line is still a verbatim substring.

The ship beat shows the one verdict sentence ploma printed. The names `compile`, `bib` and `consistency` light up green in turn inside it. There is no checklist.

## Why the symlinks

The render server only serves the project directory. A link to `../../shared/chrome.css` resolves to the server root and fails. So `shared` and `logo` are relative symlinks, and the composition loads `../shared/chrome.css` and `../logo/*.svg`. The styles and logos stay in one place.

## Network

Render needs the network. The composition loads GSAP 3.14.2 from jsDelivr and IBM Plex Mono and Source Serif 4 from Google Fonts. The data is inlined, so the composition makes no fetch. The timeline is registered after every tween is added.

## Commands

Scaffold, once, from `media/`:

```bash
HYPERFRAMES_SKIP_SKILLS=1 npx -y hyperframes@0.8.166 init film --example blank --non-interactive
cd film
npm pkg set dependencies.hyperframes=0.8.166 && npm install
ln -s ../shared shared && ln -s ../../assets/logo logo
```

The template's `index.html`, `AGENTS.md` and `CLAUDE.md` were removed. The browser is the Chrome Headless Shell from `npx -y hyperframes@0.8.166 browser ensure` (see `media/stills/render.sh`).

Word boxes and the page image, from the repo root:

```bash
python3 media/film/pdf_words.py media/film/assets/demo-main.pdf media/film/pdf_words.json
```

Inline the data, render, then make the GIF, the still and the MP4, from `media/film`:

```bash
python3 inline_data.py
npx hyperframes render -c compositions/main.html --fps 30 --output out/ploma-hero.mp4
bash make_gif.sh
```

`npm run render` runs the inline step and the same render. `tests/test_film.py` fails if the inlined data is out of date. The render prints "No index.html file found" from its lint step. That is expected: the composition lives at `compositions/main.html`, and the render goes on.

For quick checks, render with `-q draft` and pull frames with ffmpeg:

```bash
npx hyperframes render -c compositions/main.html --fps 30 -q draft --output out/draft.mp4
ffmpeg -ss 15.6 -i out/draft.mp4 -frames:v 1 out/at-15.6.png
```

`hyperframes snapshot` and `preview` only read `index.html`, so they were not used.

`make_gif.sh` takes `FPS`, `WIDTH` and `STILL_AT` from the environment. If the GIF is over 6 MB, lower `FPS` to 12, then `WIDTH` to 900. The still is at 17.7 s, where the reveal has landed on 27.4% and the compile result is still on screen.

Outputs go to `assets/film/`. `out/`, `node_modules/` and `.hyperframes/` are ignored.
