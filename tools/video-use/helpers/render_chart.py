"""Render data charts for video projects and log their provenance.

The helper renders a PNG with matplotlib and writes a Vega-Lite-style spec JSON
beside it for reproducibility. Use `--data-url` for public CSV endpoints or
`--csv` for local data.

Examples:
    python tools/video-use/helpers/render_chart.py --csv data.csv --x year --y value --title "Revenue" --project-dir edit/demo
    python tools/video-use/helpers/render_chart.py --data-url "https://example.com/data.csv" --x date --y cases --kind line
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from asset_manifest import add_asset_entry, utc_now


def parse_value(value: str) -> Any:
    raw = value.strip()
    if raw == "":
        return None
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        pass
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return raw


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def download_data(url: str, project_dir: Path) -> Path:
    out_dir = project_dir / "assets" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(url.split("?", 1)[0]).name or "data.csv"
    if not filename.endswith(".csv"):
        filename += ".csv"
    out_path = out_dir / filename
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    out_path.write_bytes(response.content)
    return out_path


def make_vega_spec(args: argparse.Namespace, data_path: Path) -> dict[str, Any]:
    mark = {"line": "line", "bar": "bar", "scatter": "point"}[args.kind]
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": args.title,
        "data": {"url": str(data_path)},
        "mark": mark,
        "encoding": {
            "x": {"field": args.x, "type": args.x_type},
            "y": {"field": args.y, "type": args.y_type, "title": args.y_label or args.y},
        },
    }


def render_chart(args: argparse.Namespace, data_path: Path, output: Path) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for chart rendering. Install project "
            "dependencies before rendering charts."
        ) from exc

    rows = read_csv(data_path)
    if not rows:
        raise SystemExit(f"no rows found in {data_path}")
    if args.x not in rows[0] or args.y not in rows[0]:
        raise SystemExit(f"CSV must contain columns {args.x!r} and {args.y!r}")

    x_values = [parse_value(row[args.x]) for row in rows if row.get(args.x) and row.get(args.y)]
    y_values = [parse_value(row[args.y]) for row in rows if row.get(args.x) and row.get(args.y)]
    y_values = [float(value) for value in y_values if isinstance(value, (int, float))]
    x_values = x_values[: len(y_values)]

    width, height = [int(part) for part in args.size.lower().split("x", 1)]
    fig, ax = plt.subplots(figsize=(width / 160, height / 160), dpi=160)
    fig.patch.set_facecolor(args.background)
    ax.set_facecolor(args.background)

    if args.kind == "line":
        ax.plot(x_values, y_values, color=args.color, linewidth=3)
    elif args.kind == "bar":
        ax.bar(x_values, y_values, color=args.color)
    elif args.kind == "scatter":
        ax.scatter(x_values, y_values, color=args.color, s=40)

    ax.set_title(args.title, fontsize=18, weight="bold", loc="left", pad=16)
    ax.set_xlabel(args.x_label or args.x)
    ax.set_ylabel(args.y_label or args.y)
    if args.note:
        fig.text(0.01, 0.015, args.note, fontsize=8, color="#475569")
    if args.source_label:
        fig.text(0.99, 0.015, args.source_label, fontsize=8, color="#475569", ha="right")

    ax.grid(True, color="#d8dee9", linewidth=0.8, alpha=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.04, 1, 1))

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Render chart plates from CSV/API data.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path)
    source.add_argument("--data-url")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--x", required=True)
    parser.add_argument("--y", required=True)
    parser.add_argument("--kind", choices=["line", "bar", "scatter"], default="line")
    parser.add_argument("--title", default="Chart")
    parser.add_argument("--x-label", default=None)
    parser.add_argument("--y-label", default=None)
    parser.add_argument("--x-type", default="temporal")
    parser.add_argument("--y-type", default="quantitative")
    parser.add_argument("--units", default=None)
    parser.add_argument("--date-range", default=None)
    parser.add_argument("--transformations", default=None)
    parser.add_argument("--data-source", default=None)
    parser.add_argument("--source-label", default=None)
    parser.add_argument("--license-url", default=None)
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--color", default="#2563eb")
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    if args.data_url:
        data_path = download_data(args.data_url, args.project_dir)
        query_url = args.data_url
    else:
        data_path = args.csv.resolve()
        query_url = None

    output = args.output or (args.project_dir / "assets" / "charts" / "chart.png")
    output = output.resolve()
    render_chart(args, data_path, output)

    spec_path = output.with_suffix(".vl.json")
    spec_path.write_text(json.dumps(make_vega_spec(args, data_path), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    entry = {
        "source_platform": "local_chart_renderer",
        "asset_type": "chart",
        "asset_id": output.stem,
        "asset_title": args.title,
        "source_url": query_url,
        "local_path": str(output),
        "downloaded_at": utc_now(),
        "license_url": args.license_url,
        "data_source": args.data_source or query_url or str(data_path),
        "query_url": query_url,
        "retrieved_at": utc_now(),
        "units": args.units,
        "date_range": args.date_range,
        "transformations": args.transformations,
        "chart_spec_path": str(spec_path),
        "policy_or_license_notes": "Generated chart; verify data license/citation before final use.",
    }
    manifest_path, asset = add_asset_entry(args.project_dir, entry)
    print(json.dumps({"manifest": str(manifest_path), "asset": asset}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
