"""Check whether a from-scratch script is research-ready.

This is a deterministic QC helper for the research-checker sub-agent. It does
not decide truth by itself; it verifies that factual claims have source links,
confidence labels, and optional reachable URLs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests

from asset_manifest import utc_now


URL_RE = re.compile(r"https?://[^\s)>]+")


def markdown_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-", ":", " "} for c in cells):
                continue
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def table_dicts(table: list[list[str]]) -> list[dict[str, str]]:
    if not table:
        return []
    headers = [h.strip().lower() for h in table[0]]
    rows: list[dict[str, str]] = []
    for cells in table[1:]:
        row: dict[str, str] = {}
        for idx, header in enumerate(headers):
            row[header] = cells[idx].strip() if idx < len(cells) else ""
        rows.append(row)
    return rows


def extract_claim_rows(markdown: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in markdown_tables(markdown):
        headers = [h.strip().lower() for h in table[0]]
        has_claim_column = any(h == "claim" for h in headers)
        has_source_url_column = any(h in {"source url", "url", "sources"} for h in headers)
        if has_claim_column or has_source_url_column:
            rows.extend(table_dicts(table))
    return rows


def find_urls(*texts: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for text in texts:
        for url in URL_RE.findall(text):
            cleaned = url.rstrip(".,;]")
            if cleaned not in seen:
                seen.add(cleaned)
                urls.append(cleaned)
    return urls


def check_url(url: str, timeout: int = 10) -> dict[str, Any]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        if response.status_code in {403, 405}:
            response = requests.get(url, stream=True, allow_redirects=True, timeout=timeout)
        return {
            "url": url,
            "status_code": response.status_code,
            "ok": response.status_code < 400,
            "final_url": response.url,
        }
    except Exception as exc:
        return {"url": url, "ok": False, "error": str(exc)}


def check_claims(claim_rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not claim_rows:
        warnings.append("no claim table found; factual script may not be source-tracked")
        return errors, warnings

    for idx, row in enumerate(claim_rows, start=1):
        label = row.get("claim") or row.get("source/claim notes") or f"claim #{idx}"
        source_url = row.get("source url") or row.get("url") or row.get("source") or row.get("sources")
        confidence = row.get("confidence") or row.get("reliability")
        visual = row.get("visual evidence") or row.get("evidence") or row.get("visual")
        source_value = source_url.lower().strip() if source_url else ""
        if not source_value or source_value in {"none", "n/a", "pending"}:
            errors.append(f"{label}: missing source URL")
        if source_url and not URL_RE.search(source_url) and source_value not in {"user-provided", "internal"}:
            warnings.append(f"{label}: source field does not include a URL")
        if not confidence:
            warnings.append(f"{label}: missing confidence/reliability label")
        if not visual:
            warnings.append(f"{label}: missing visual evidence note")
    return errors, warnings


def write_report(path: Path, data: dict[str, Any]) -> None:
    lines = [
        "# Research Check Report",
        "",
        f"- Checked at: {data['checked_at']}",
        f"- Script: `{data['script']}`",
        f"- Research notes: `{data['research_notes']}`",
        f"- Claims found: {data['claims_found']}",
        f"- URLs found: {len(data['urls'])}",
        "",
        "## Errors",
        "",
    ]
    lines.extend(f"- {item}" for item in data["errors"] or ["None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in data["warnings"] or ["None"])
    if data.get("url_checks"):
        lines.extend(["", "## URL Checks", ""])
        for item in data["url_checks"]:
            status = item.get("status_code", "error")
            ok = "ok" if item.get("ok") else "failed"
            lines.append(f"- {ok}: {item['url']} ({status})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate research/source coverage for a script.")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--script", type=Path)
    parser.add_argument("--research-notes", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--check-urls", action="store_true")
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    script = args.script or project_dir / "script.md"
    research_notes = args.research_notes or project_dir / "research_notes.md"
    report = args.output or project_dir / "research_check_report.md"
    json_output = args.json_output or project_dir / "research_check_report.json"

    script_text = script.read_text(encoding="utf-8") if script.exists() else ""
    research_text = research_notes.read_text(encoding="utf-8") if research_notes.exists() else ""
    errors: list[str] = []
    warnings: list[str] = []

    if not script.exists():
        errors.append(f"missing script: {script}")
    if not research_notes.exists():
        warnings.append(f"missing research notes: {research_notes}")

    claims = extract_claim_rows(script_text + "\n" + research_text)
    claim_errors, claim_warnings = check_claims(claims)
    errors.extend(claim_errors)
    warnings.extend(claim_warnings)

    urls = find_urls(script_text, research_text)
    url_checks = [check_url(url) for url in urls] if args.check_urls else []
    for result in url_checks:
        if not result.get("ok"):
            warnings.append(f"URL check failed: {result['url']}")

    data = {
        "checked_at": utc_now(),
        "script": str(script),
        "research_notes": str(research_notes),
        "claims_found": len(claims),
        "urls": urls,
        "url_checks": url_checks,
        "errors": errors,
        "warnings": warnings,
    }
    write_report(report, data)
    json_output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report), "json": str(json_output), "errors": errors, "warnings": warnings}, indent=2))
    if args.fail_on_errors and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
