# remarkable-block-notebooks

Grid, contents and engineering-paper page templates for reMarkable tablets,
plus an A4 set for iPad note apps.

Every reMarkable template is generated from a single layout description in
millimetres, so a 5 mm square measures 5 mm on all three panels. Nothing in
`remarkable-*/` is hand-drawn: edit `generate.py` and rebuild.

## Layout

All measurements are physical, not pixels:

| Element | Size |
| --- | --- |
| Squared grid | 5 mm cells |
| Tiny grid | 2 mm cells |
| Contents rows | 7 mm pitch, 26 mm page column, 8 mm gutter |
| Mechanical grid | 1 mm cells, emphasis at 5 mm and 10 mm |
| Page margin | 9 mm (4.5 mm on the smaller Paper Pro Move panel) |

Stroke weights are declared in millimetres and then clamped to at least one
device pixel. A line thinner than a pixel aliases away or moirés on e-ink —
that is what made the first 1 mm grid unreadable, and the clamp is why the
current one is not.

Labels are drawn as glyph outlines taken from the original masters and stored
in `lettering.json`. The templates reference no font and contain no `<text>`,
so they render the same under any rasteriser.

| Panel | Pixels | PPI |
| --- | --- | --- |
| reMarkable / Paper Pure | 1404 × 1872 | 226 |
| Paper Pro | 1620 × 2160 | 229 |
| Paper Pro Move | 954 × 1696 | 266 |

## Templates

Eighteen packages, one `.rmt` per entry in `templates.json`:

- `remarkable-pure/` — squared left, squared right, tiny grid, contents,
  mechanical grid (landscape, 1872 × 1404).
- `remarkable-pro-move/` — squared left, squared right, tiny grid, contents.
- `remarkable-paper-pro/` — those four on white and on ivory (`#F6F2E8`),
  plus a Fahrenheit 451 cover.

Each directory also holds a PNG preview per template at the panel's native
resolution and a multi-page PDF of the whole set, for printing or for use as
a plain notebook.

## Building

```sh
python3 generate.py     # SVG masters, PNG previews, per-device PDFs
python3 build_rmt.py    # .rmt archives and rmt-manifest.json
```

Both use only the Python standard library. PNG and PDF rasterisation needs
Google Chrome; set `CHROME_BIN` to override the default macOS path, or pass
`--no-raster` to skip it. Rebuilding is byte-for-byte reproducible.

`templates.json` is the catalog: display name, category, orientation and the
`fileName` UUID for each template. **Those UUIDs are the template's identity
on the tablet and must not change.** They are not derived from file paths, so
renaming or moving a template updates the existing entry in the picker rather
than silently adding a second copy. The UUIDs of the packages published before
this layout was reworked are carried over.

## Installing with RCU

In RCU, open **Templates**, click **Upload**, and select an `.rmt` from the
directory for your device. The template then appears in a notebook's template
picker under its category. Use an RCU release compatible with your tablet
firmware.

An `.rmt` is an uncompressed USTAR tar holding `template.json` and
`template.svg`, per Appendix D of the
[RCU user manual](https://www.davisr.me/projects/rcu/manual.pdf). RCU
rasterises the SVG on upload, but the line-art packages also ship a
`template.png` already rendered at the panel's native resolution, which is
what the one template confirmed working on a tablet did. Pass `--no-png` to
build SVG-only archives instead.

The cover is a photograph, so its package embeds the image in an SVG wrapper
rather than pretending to be vector artwork; it carries no separate
`template.png` because the wrapper holds the same pixels.

Status: the archives are validated on build — structure, round-trip and
declared size — but installation on a tablet has only been confirmed for the
mechanical grid.

## iPad

`ipad/` holds a separate A4 set (2480 × 3508 px @ 300 dpi) on a Leuchtturm
1917 ivory background (`#FAF4E6`):

- `ipad/*.svg` — editable masters.
- `ipad/png/*.png` — ready to import as page templates in GoodNotes,
  Notability or Noteshelf.
- `ipad/ipad-templates.pdf` — one multi-page A4 PDF.

Run `python3 ipad/generate.py` to regenerate it. This set is deliberately not
packaged as RMT.

`alphabet/` holds block-lettering practice sheets as PDFs. They are documents,
not page templates.
