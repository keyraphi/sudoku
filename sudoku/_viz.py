"""Rendering a Sudoku board to PNG / PDF / interactive viewer."""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageColor

__all__ = ["render", "render_to_png", "render_to_pdf", "show"]

_FONT_CANDIDATES = (
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:\\Windows\\Fonts\\arial.ttf",
)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, cx: float, cy: float,
                   font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
              text, font=font, fill=fill)


def _difficulty_to_color(score: float) -> str:
    """Map difficulty [0, 1] to hex colour: green (easy) → yellow → red (hard).

    Interpolates through three anchors:
      0.0 → #2ca02c (green)
      0.5 → #ffd700 (yellow)
      1.0 → #c81e1e (red)
    """
    score = max(0.0, min(1.0, float(score)))
    if score < 0.5:
        t = score / 0.5
        r = int(44 + (255 - 44) * t)
        g = int(160 + (215 - 160) * t)
        b = int(44 + (0 - 44) * t)
    else:
        t = (score - 0.5) / 0.5
        r = int(255 + (200 - 255) * t)
        g = int(215 + (30 - 215) * t)
        b = int(0 + (30 - 0) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, cx: float, cy: float,
                   font, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
              text, font=font, fill=fill)


def _draw_difficulty_legend(draw: ImageDraw.ImageDraw, img_width: int,
                            y_center: float, cell_px: int) -> None:
    """Draw a horizontal 'easy → hard' colour bar."""
    bar_w = int(min(img_width * 0.55, 9 * cell_px * 0.7))
    bar_h = max(10, cell_px // 6)
    x0 = (img_width - bar_w) // 2
    y0 = int(y_center - bar_h // 2)

    for i in range(bar_w):
        t = i / max(1, bar_w - 1)
        draw.line([(x0 + i, y0), (x0 + i, y0 + bar_h)],
                  fill=_difficulty_to_color(t))

    draw.rectangle([x0, y0, x0 + bar_w, y0 + bar_h],
                   outline="#333333", width=1)

    label_font = _load_font(max(10, int(cell_px * 0.28)))
    label_y = y0 + bar_h + label_font.size // 2 + 4
    _draw_centered(draw, "easy", x0 + 30, label_y, label_font, "#333333")
    _draw_centered(draw, "hard", x0 + bar_w - 30, label_y, label_font, "#333333")
    _draw_centered(draw, "Difficulty", x0 + bar_w / 2,
                   label_y + label_font.size + 2, label_font, "#666666")


def render(
    board,
    *,
    solution=None,
    difficulty=None,
    difficulty_legend: bool = False,
    size: float = 6.0,
    dpi: int = 150,
    title: Optional[str] = None,
    given_color: str = "#111111",
    solution_color: str = "#1f5fbf",
    line_color: str = "#3a3a3a",
    thick_line_color: str = "#000000",
    background: str = "#ffffff",
    glow_color: Optional[str] = None,
    glow_radius: Optional[int] = None,
) -> Image.Image:
    """Render a Sudoku board to a PIL image.

    Parameters
    ----------
    board : array-like (9, 9)
        Puzzle. ``<= 0`` is empty.
    solution : array-like (9, 9), optional
        Digits to draw in the empty cells.
    difficulty : array-like (9, 9), optional
        Float scores in [0, 1] used to color solution digits. Requires
        ``solution``. ``nan`` (typically a given cell) falls back to
        ``solution_color``.
    difficulty_legend : bool
        If true, add an "easy → hard" colour legend below the grid.
    size : float
        Physical width of the grid in inches.
    dpi : int
        Output resolution.
    title : str, optional
        Caption drawn under the grid.
    glow_color : str, optional
        If given, draw a soft glow around the grid in this colour.
    """
    board = np.asarray(board, dtype=np.int32)
    if board.shape != (9, 9):
        raise ValueError(f"board must be (9, 9), got {board.shape}")
    if solution is not None:
        solution = np.asarray(solution, dtype=np.int32)
        if solution.shape != (9, 9):
            raise ValueError(f"solution must be (9, 9), got {solution.shape}")
    if difficulty is not None:
        difficulty = np.asarray(difficulty, dtype=np.float64)
        if difficulty.shape != (9, 9):
            raise ValueError(f"difficulty must be (9, 9), got {difficulty.shape}")
        if solution is None:
            warnings.warn("`difficulty` has no effect without `solution`",
                          stacklevel=2)

    cell = max(24, round(size * dpi / 9))
    margin = cell // 3
    title_px = cell if title else 0
    legend_px = cell if difficulty_legend else 0
    glow_px = glow_radius if glow_color and glow_radius else (cell if glow_color else 0)

    W = 9 * cell + 2 * margin + 2 * glow_px
    H = 9 * cell + 2 * margin + title_px + legend_px + 2 * glow_px

    img = Image.new("RGB", (W, H), background)
    draw = ImageDraw.Draw(img)
    ox, oy = margin + glow_px, margin + glow_px

    font = _load_font(int(cell * 0.72))

    for r in range(9):
        for c in range(9):
            cx = ox + c * cell + cell / 2
            cy = oy + r * cell + cell / 2
            v = int(board[r, c])
            if v > 0:
                _draw_centered(draw, str(v), cx, cy, font, given_color)
            elif solution is not None and int(solution[r, c]) > 0:
                text = str(int(solution[r, c]))
                if difficulty is not None:
                    d = float(difficulty[r, c])
                    col = (_difficulty_to_color(d) if np.isfinite(d)
                           else solution_color)
                else:
                    col = solution_color
                _draw_centered(draw, text, cx, cy, font, col)

    # Grid lines
    thin = max(1, cell // 40)
    thick = max(2, cell // 20)
    for i in range(10):
        is_thick = (i % 3 == 0)
        lw = thick if is_thick else thin
        col = thick_line_color if is_thick else line_color
        draw.line([(ox + i * cell, oy), (ox + i * cell, oy + 9 * cell)],
                  fill=col, width=lw)
        draw.line([(ox, oy + i * cell), (ox + 9 * cell, oy + i * cell)],
                  fill=col, width=lw)

    # Title and legend below the grid
    content_y = oy + 9 * cell
    if title:
        _draw_centered(draw, title, W / 2, content_y + title_px / 2,
                       _load_font(int(cell * 0.6)), given_color)
    if difficulty_legend:
        _draw_difficulty_legend(draw, W,
                                content_y + title_px + legend_px / 2,
                                cell)

    if glow_color:
        img = _apply_glow(img, glow_color, glow_px or cell // 2,
                          (ox, oy, ox + 9 * cell, oy + 9 * cell))

    return img


def _apply_glow(img: Image.Image, color: str, radius: int, bbox) -> Image.Image:
    rgb = ImageColor.getrgb(color)
    layer = Image.new("RGB", img.size, (0, 0, 0))
    ImageDraw.Draw(layer).rectangle(bbox, outline=rgb, width=max(4, radius // 2))
    layer = layer.filter(ImageFilter.GaussianBlur(radius / 1.5))
    return ImageChops.screen(img, layer)


def render_to_png(board, path: Union[str, Path], *, dpi: int = 150, **kwargs):
    img = render(board, dpi=dpi, **kwargs)
    img.save(path, "PNG", dpi=(dpi, dpi))
    return img


def render_to_pdf(board, path: Union[str, Path], *,
                  dpi: int = 300, paper: str = "a4", **kwargs):
    """Render and centre on an A4 / Letter page for printing."""
    img = render(board, dpi=dpi, **kwargs)
    sizes = {"a4": (8.27, 11.69), "letter": (8.5, 11.0)}
    if paper not in sizes:
        raise ValueError(f"paper must be one of {sorted(sizes)}")
    pw, ph = (int(round(x * dpi)) for x in sizes[paper])
    page = Image.new("RGB", (pw, ph), "white")
    page.paste(img, ((pw - img.width) // 2, (ph - img.height) // 2))
    page.save(path, "PDF", resolution=dpi)
    return page


def show(board_or_image, *, use_matplotlib: bool = False, **kwargs):
    """Display a board (or an already-rendered PIL image)."""
    img = board_or_image if isinstance(board_or_image, Image.Image) else render(
        board_or_image, **kwargs)
    if use_matplotlib:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(img)
        ax.axis("off")
        plt.show()
    else:
        img.show()
