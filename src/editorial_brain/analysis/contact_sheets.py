"""Diagnostic contact-sheet composition for source evidence."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from editorial_brain.core.models import ShotFrame


def build_contact_sheet(
    frames: list[ShotFrame],
    destination: Path,
    *,
    columns: int = 4,
    cell_width: int = 320,
    cell_height: int = 200,
) -> Path:
    if columns <= 0 or cell_width <= 0 or cell_height <= 0:
        raise ValueError("contact-sheet dimensions must be positive")
    readable = [
        frame for frame in frames if frame.artifact_path and Path(frame.artifact_path).is_file()
    ]
    if not readable:
        raise ValueError("contact sheet requires at least one readable frame")
    rows = (len(readable) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "black")
    draw = ImageDraw.Draw(sheet)
    for position, frame in enumerate(readable):
        row, column = divmod(position, columns)
        x = column * cell_width
        y = row * cell_height
        assert frame.artifact_path is not None
        with Image.open(frame.artifact_path) as source:
            image = source.convert("RGB")
            image.thumbnail((cell_width, cell_height - 28), Image.Resampling.LANCZOS)
            offset_x = x + (cell_width - image.width) // 2
            sheet.paste(image, (offset_x, y))
        label = f"{frame.id}  {float(frame.time.fraction):.3f}s"
        draw.rectangle((x, y + cell_height - 28, x + cell_width, y + cell_height), fill="black")
        draw.text((x + 6, y + cell_height - 22), label, fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=True)
    return destination
