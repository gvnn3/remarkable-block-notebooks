#!/usr/bin/env python3
"""Generate iPad A4 notebook templates (SVG + PNG + multi-page PDF).

Mirrors the reMarkable templates in this repo (squared-right/left, tiny-grid,
toc) but resized to A4 at 300dpi with a Leuchtturm 1917 ivory background.

PNG and PDF rasterization is performed by Google Chrome in headless mode.
Set CHROME_BIN to override the default macOS path.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PAGE_W = 2480
PAGE_H = 3508

BG = "#FAF4E6"
ACCENT = "#737e99"
GRID_COARSE = "#808080"
GRID_FINE = "#999999"

MARGIN_L = 80
MARGIN_R = 80
MARGIN_T = 100
MARGIN_B = 80
HEADER_BAND = 80

INNER_X0 = MARGIN_L
INNER_X1 = PAGE_W - MARGIN_R
GRID_Y0 = MARGIN_T + HEADER_BAND
GRID_Y1 = PAGE_H - MARGIN_B

OUT = Path(__file__).resolve().parent


def svg_open():
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{PAGE_W}" height="{PAGE_H}" '
        f'viewBox="0 0 {PAGE_W} {PAGE_H}">\n'
        f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="{BG}"/>\n'
    )


def svg_close():
    return "</svg>\n"


def hline(x0, x1, y, color, width=1.0, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
        f'stroke="{color}" stroke-width="{width}"{extra}/>\n'
    )


def vline(x, y0, y1, color, width=1.0, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x:.2f}" y1="{y0:.2f}" x2="{x:.2f}" y2="{y1:.2f}" '
        f'stroke="{color}" stroke-width="{width}"{extra}/>\n'
    )


def text(x, y, content, size=36, color=ACCENT, anchor="start", weight="normal"):
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" '
        f'font-family="Helvetica,Arial,sans-serif" font-size="{size}" '
        f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}">'
        f"{content}</text>\n"
    )


def write_squared(side: str):
    """Coarse 58px squared grid; date label top-left or top-right."""
    assert side in ("left", "right")
    cell = 58
    cols = (INNER_X1 - INNER_X0) // cell
    rows = (GRID_Y1 - GRID_Y0) // cell
    grid_w = cols * cell
    grid_h = rows * cell
    x0 = INNER_X0
    x1 = x0 + grid_w
    y0 = GRID_Y0
    y1 = y0 + grid_h

    parts = [svg_open()]

    label_y = MARGIN_T + 60
    if side == "right":
        parts.append(text(x1, label_y, "DATUM/DATE", size=42, anchor="end"))
    else:
        parts.append(text(x0, label_y, "DATUM/DATE", size=42, anchor="start"))

    for i in range(cols + 1):
        x = x0 + i * cell
        parts.append(vline(x, y0, y1, GRID_COARSE, width=1.0))
    for j in range(rows + 1):
        y = y0 + j * cell
        parts.append(hline(x0, x1, y, GRID_COARSE, width=1.0))

    parts.append(svg_close())
    (OUT / f"squared-{side}.svg").write_text("".join(parts))


def write_tiny_grid():
    """Fine 29px grid with TITLE/NO. header and centered spine tick."""
    cell = 29
    cols = (INNER_X1 - INNER_X0) // cell
    rows = (GRID_Y1 - GRID_Y0) // cell
    grid_w = cols * cell
    grid_h = rows * cell
    x0 = INNER_X0
    x1 = x0 + grid_w
    y0 = GRID_Y0
    y1 = y0 + grid_h

    parts = [svg_open()]

    top_rule_y = MARGIN_T + 20
    parts.append(hline(x0, x1, top_rule_y, GRID_FINE, width=1.2))
    cx = (x0 + x1) / 2
    parts.append(vline(cx, top_rule_y, top_rule_y + 28, GRID_FINE, width=1.2))

    parts.append(
        text(x0 + 20, MARGIN_T + 110, "TITLE / NO.", size=40, color=GRID_FINE)
    )

    sep_y = GRID_Y0 - 4
    parts.append(hline(x0, x1, sep_y, GRID_FINE, width=1.0, dash="6 6"))

    for i in range(cols + 1):
        x = x0 + i * cell
        parts.append(vline(x, y0, y1, GRID_FINE, width=0.7))
    for j in range(rows + 1):
        y = y0 + j * cell
        parts.append(hline(x0, x1, y, GRID_FINE, width=0.7))

    parts.append(svg_close())
    (OUT / "tiny-grid.svg").write_text("".join(parts))


def write_toc():
    """Two-column table of contents page."""
    parts = [svg_open()]

    title_y = 200
    parts.append(
        text(
            PAGE_W / 2,
            title_y,
            "INHALT / CONTENT / CONTENU",
            size=72,
            anchor="middle",
        )
    )

    col_split_x = 560
    gap = 110
    page_col_x0 = MARGIN_L
    page_col_x1 = col_split_x
    topic_col_x0 = col_split_x + gap
    topic_col_x1 = PAGE_W - MARGIN_R

    header_rule_top = 250
    header_rule_bottom = 380
    parts.append(
        hline(page_col_x0, page_col_x1, header_rule_top, GRID_COARSE, width=2.0)
    )
    parts.append(
        hline(topic_col_x0, topic_col_x1, header_rule_top, GRID_COARSE, width=2.0)
    )

    parts.append(text(page_col_x0 + 15, 330, "SEITE / PAGE", size=48))
    parts.append(text(topic_col_x0 + 5, 330, "THEMA / TOPIC / SUJET", size=48))

    parts.append(
        hline(page_col_x0, page_col_x1, header_rule_bottom, GRID_COARSE, width=2.0)
    )
    parts.append(
        hline(topic_col_x0, topic_col_x1, header_rule_bottom, GRID_COARSE, width=2.0)
    )

    row_gap = 110
    first_row_y = header_rule_bottom + row_gap
    y = first_row_y
    while y <= PAGE_H - MARGIN_B:
        parts.append(hline(page_col_x0, page_col_x1, y, GRID_COARSE, width=1.5))
        parts.append(hline(topic_col_x0, topic_col_x1, y, GRID_COARSE, width=1.5))
        y += row_gap

    parts.append(svg_close())
    (OUT / "toc.svg").write_text("".join(parts))


TEMPLATES = ("squared-right", "squared-left", "tiny-grid", "toc")


def chrome_bin() -> str:
    return os.environ.get(
        "CHROME_BIN",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )


def write_html_wrapper(build_dir: Path, name: str) -> Path:
    svg = (OUT / f"{name}.svg").read_text()
    html = (
        "<!DOCTYPE html><html><head><style>"
        "html,body{margin:0;padding:0;background:" + BG + ";}"
        f"svg{{display:block;width:{PAGE_W}px;height:{PAGE_H}px;}}"
        "</style></head><body>" + svg + "</body></html>"
    )
    path = build_dir / f"{name}.html"
    path.write_text(html)
    return path


def write_multi_page_html(build_dir: Path) -> Path:
    style = (
        "@page { size: 210mm 297mm; margin: 0; }"
        "html,body{margin:0;padding:0;background:" + BG + ";"
        "-webkit-print-color-adjust:exact;print-color-adjust:exact;}"
        ".page{width:210mm;height:297mm;page-break-after:always;overflow:hidden;}"
        ".page:last-child{page-break-after:auto;}"
        "svg{display:block;width:100%;height:100%;}"
    )
    body_parts = []
    for name in TEMPLATES:
        svg = (OUT / f"{name}.svg").read_text()
        body_parts.append(f'<div class="page">{svg}</div>')
    html = (
        "<!DOCTYPE html><html><head><style>" + style + "</style></head><body>"
        + "".join(body_parts) + "</body></html>"
    )
    path = build_dir / "all-pages.html"
    path.write_text(html)
    return path


def rasterize_pngs(build_dir: Path) -> None:
    chrome = chrome_bin()
    if not Path(chrome).exists():
        print(f"warning: {chrome} not found; skipping PNG render", file=sys.stderr)
        return
    png_dir = OUT / "png"
    png_dir.mkdir(exist_ok=True)
    for name in TEMPLATES:
        html = write_html_wrapper(build_dir, name)
        out_png = png_dir / f"{name}.png"
        subprocess.run(
            [
                chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={PAGE_W},{PAGE_H}",
                f"--screenshot={out_png}",
                html.as_uri(),
            ],
            check=True, capture_output=True,
        )
    print(f"Wrote PNGs to {png_dir}")


def render_pdf(build_dir: Path) -> None:
    chrome = chrome_bin()
    if not Path(chrome).exists():
        print(f"warning: {chrome} not found; skipping PDF render", file=sys.stderr)
        return
    html = write_multi_page_html(build_dir)
    out_pdf = OUT / "ipad-templates.pdf"
    subprocess.run(
        [
            chrome, "--headless", "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_pdf}",
            html.as_uri(),
        ],
        check=True, capture_output=True,
    )
    print(f"Wrote PDF to {out_pdf}")


def main():
    write_squared("right")
    write_squared("left")
    write_tiny_grid()
    write_toc()
    print(f"Wrote SVGs to {OUT}")
    build_dir = OUT / ".build"
    build_dir.mkdir(exist_ok=True)
    try:
        rasterize_pngs(build_dir)
        render_pdf(build_dir)
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
