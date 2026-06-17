# remarkable-block-notebooks
A collection of PNG (Template) and PDF (Workbook) pages for 
Remarkable Paper Pure and Pro Move

Block pages and a ToC as well.

The SVG files can be used as templates on any Remarkable device.

## iPad

The `ipad/` directory contains an A4 set (2480×3508 px @ 300dpi) with a
Leuchtturm 1917 ivory background (`#FAF4E6`):

- `ipad/squared-right.svg`, `squared-left.svg`, `tiny-grid.svg`, `toc.svg`
  — editable SVG masters.
- `ipad/png/*.png` — A4 PNG renders, ready to import as page templates in
  GoodNotes, Notability, or Noteshelf.
- `ipad/ipad-templates.pdf` — single multi-page A4 PDF, ready to open as a
  new notebook in any iPad note app.

Run `python3 ipad/generate.py` to regenerate the set. PNG and PDF rendering
require Google Chrome (set `CHROME_BIN` to override the default macOS path).
