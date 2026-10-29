# PDF processing

Default: read the PDF directly with the Read tool. Pass a `pages` range (up to 20 pages per request) for documents longer than about ten pages. A normal paper does not need pre-splitting.

## Workflow

1. **Check the size first.** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pdf_pages.py" <file>` reports the page count without poppler; `ls -lh <file>` shows the size.
2. **Read directly.** Up to about 100 pages: page through with `pages`. For a long document you may skim appendices and references and read the method and results sections in detail; this saves tokens, it is not a capacity limit.
3. **Split only as a fallback**, when the file is genuinely oversized (a book, a high-resolution scan), corrupt, or a direct read fails:

```bash
mkdir -p <name>/
gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER -dFirstPage=1 -dLastPage=5 \
   -sOutputFile=<name>/<name>_p001-005.pdf <file>
```

Repeat per five-page range and read the parts in order.

## Errors

- A part fails: split it into one or two page pieces; if it still fails, skip it and record the gap.
- Splitting fails: check `gs --version`; try `pdftk <file> burst output <name>_%03d.pdf`; as a last resort ask the user for specific page ranges.
- Never summarise pages you could not read. Name the gap.
