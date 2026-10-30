# Logo

The ploma logo is a fountain pen nib and the word "ploma" set in Fraunces. Ploma is the Catalan word for a fountain pen.

## Build

```bash
python3 media/logo/build_logo.py
```

The script needs Python 3, fontTools and `rsvg-convert` from librsvg. It writes these files:

- `assets/logo/ploma-mark.svg` and `assets/logo/ploma-mark-dark.svg`: the nib alone.
- `assets/logo/ploma-lockup.svg` and `assets/logo/ploma-lockup-dark.svg`: the nib with the wordmark.
- `assets/logo/ploma-mark-512.png`: the light nib at 512 by 512 pixels on an opaque `#f6f4ef` tile, so it stays visible on dark surfaces.
- `.claude-plugin/icon.png`: a byte-identical copy of the 512 pixel tile.

The light files use `#1d1b17`. The dark files use `#e8e6e0`.

## Wordmark

The wordmark is Fraunces at an optical size of 72 and a weight of 500, with tracking of -0.02 em. The glyphs are converted to paths, so the SVG files need no font to display.

## Font licence

Fraunces is released under the SIL Open Font License 1.1. The script downloads it from the Google Fonts repository at build time into `media/logo/.cache/`. That folder is ignored by git, and the font is never committed.
