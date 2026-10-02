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

## RCU notebook templates (RMT)

Ready-to-upload RCU template archives live beside their source files:

- Root: four original SVG templates (squared left/right, tiny grid, contents).
- `remarkable-pure/`: four existing templates plus Mechanical Grid - 1 mm.
- `remarkable-pro-move/`: four existing templates.
- `remarkable-paper-pro/`: eleven existing templates, including cover and ivory variants.

In RCU, open **Templates**, click **Upload**, and select an `.rmt` file.
Then choose it in a notebook's template picker. Use the folder for your device.
Names, categories, orientation, and stable unique identifiers are included.
The iPad designs are excluded from RMT generation; use their SVG, PNG, and PDF files in iPad apps.
Use an RCU release compatible with your tablet firmware.

Archives contain `template.json` and `template.svg` in an uncompressed TAR.
Existing SVG masters remain vectors. Where only a device-specific PNG exists,
its original image is embedded losslessly in SVG; packaging does not turn it
into vector artwork. All original variants are retained, including similarly
named Paper Pro files. PDF workbooks and lettering practice PDFs are documents,
so they are not packaged as page templates.

The new Paper Pure Mechanical Grid uses 1 mm squares (at the screen's nominal
226 PPI), with stronger lines every 5 mm and 10 mm. Its SVG, PNG, and PDF are in
`remarkable-pure/`. Keep the original scale when physical spacing matters.
Its RMT preserves the identifier of the version first created for this grid.

Run `python3 build_rmt.py` to regenerate all 24 packages and `rmt-manifest.json`.
The builder uses only the Python standard library and validates each archive.
Packages have been validated locally; installation on a tablet is not tested.

Format and installation reference: [RCU user manual](https://www.davisr.me/projects/rcu/manual.pdf).
