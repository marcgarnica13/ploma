# media

Sources for the images and the film in the ploma README. The logo, film and stills each build outputs that are committed under `assets/`; the logo also writes the plugin icon to `.claude-plugin/icon.png`. The transcripts stay in `media/transcripts/`.

## Logo

`media/logo/` holds a Python generator that writes the SVG logo and a 512 pixel PNG of the nib to `assets/logo/`, and the plugin icon to `.claude-plugin/icon.png`.

## Film

`media/film/` is a HyperFrames 0.8.166 project that renders the hero film to `assets/film/ploma-hero.gif` and `assets/film/ploma-hero.png`, with an optional `assets/film/ploma-hero.mp4`.

## Stills

`media/stills/` holds four HTML pages that render to `assets/stills/*.png`.

## Transcripts

`media/transcripts/` holds rendered transcripts of real ploma runs on `examples/demo-paper`. They stay in this folder; no build step copies them to `assets/`. Every terminal line in the film and the stills comes from them.

## Tools

The demo paper needs LaTeX, and the film's page image needs poppler. The logo needs fontTools and librsvg. The stills need Chrome (the HyperFrames Chrome Headless Shell, see `media/stills/render.sh`) and ffmpeg:

```bash
sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended latexmk poppler-utils librsvg2-bin ffmpeg
python3 -m pip install fonttools
(cd media && npx -y hyperframes@0.8.166 browser ensure)
```

The film needs Node.js and npm:

```bash
cd media/film
npm install
npm run render && bash make_gif.sh
```

See `media/film/README.md` for the details.
