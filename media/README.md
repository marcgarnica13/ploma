# media

Sources for the images and the film in the ploma README. Each part builds an output that is committed under `assets/`.

## Logo

`media/logo/` holds a Python generator that writes the SVG logo and the plugin icon to `assets/logo/`.

## Film

`media/film/` is a HyperFrames 0.8.166 project that renders the hero film to `assets/film/ploma-hero.gif` and `assets/film/ploma-hero.png`, with an optional `assets/film/ploma-hero.mp4`.

## Stills

`media/stills/` holds four HTML pages that render to `assets/stills/*.png`.

## Transcripts

`media/transcripts/` holds rendered transcripts of real ploma runs on `examples/demo-paper`. Every line in the film and the stills comes from them.

## Tools

The logo, stills and demo paper need LaTeX, poppler and librsvg:

```bash
sudo apt-get install -y texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended latexmk poppler-utils librsvg2-bin
```

The film needs Node.js and npm:

```bash
cd media/film
npm install
npx hyperframes render
```
