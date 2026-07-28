"""Validate immutable coverage and evidence shape for all canonical goldens."""

from __future__ import annotations

import json
from pathlib import Path

from baseline_bundle import materialize_baseline

ROOT = Path(__file__).resolve().parents[1]
EXPECTATIONS = ROOT / "testdata" / "engine" / "golden_expectations.json"
REQUIRED = {
    "existing_footage_edit",
    "faceless_vertical_edit",
    "podcast_clip",
    "interview_edit",
    "product_ad",
    "recap",
    "documentary",
    "motion_graphics_video",
    "long_form_sequence",
    "hdr_to_sdr_project",
    "mixed_frame_rate_project",
    "multitrack_audio_project",
}
HISTORICAL = {"existing_footage_edit", "faceless_vertical_edit"}


def main() -> int:
    payload = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))
    projects = payload.get("projects", {})
    baseline = materialize_baseline()
    failures: list[str] = []
    if payload.get("schema_version") != 3:
        failures.append("unsupported expectations schema version")
    fingerprint = payload.get("media_tool_fingerprint")
    if (
        not isinstance(fingerprint, str)
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        failures.append("invalid media tool fingerprint")
    if set(projects) != REQUIRED:
        failures.append(
            f"project ids differ: missing={sorted(REQUIRED - set(projects))}, "
            f"extra={sorted(set(projects) - REQUIRED)}"
        )
    for project_id in sorted(REQUIRED & set(projects)):
        expectation = projects[project_id]
        if project_id in HISTORICAL:
            evidence_path = Path(str(expectation.get("evidence", "")))
            evidence = baseline / evidence_path.relative_to("engine_baseline")
            if not evidence.is_file():
                failures.append(f"{project_id}: missing parity evidence {evidence}")
            continue
        hashes = expectation.get("frame_dhash")
        if not isinstance(hashes, dict) or not hashes:
            failures.append(f"{project_id}: no decoded frame hashes")
        elif any(
            not isinstance(value, str)
            or len(value) != 16
            or any(character not in "0123456789abcdef" for character in value)
            for value in hashes.values()
        ):
            failures.append(f"{project_id}: invalid dHash evidence")
        if not isinstance(expectation.get("audio_samples"), int):
            failures.append(f"{project_id}: no decoded audio sample count")
        sequence = expectation.get("all_frame_dhash")
        if not isinstance(sequence, list) or not sequence:
            failures.append(f"{project_id}: no all-frame dHash sequence")
        elif any(
            not isinstance(value, str)
            or len(value) != 16
            or any(character not in "0123456789abcdef" for character in value)
            for value in sequence
        ):
            failures.append(f"{project_id}: invalid all-frame dHash sequence")
        max_hamming = expectation.get("all_frame_max_hamming")
        if not isinstance(max_hamming, int) or not 0 <= max_hamming <= 64:
            failures.append(f"{project_id}: invalid all-frame maximum Hamming distance")
        mean_hamming = expectation.get("all_frame_mean_hamming")
        if not isinstance(mean_hamming, (int, float)) or not 0 <= mean_hamming <= 64:
            failures.append(f"{project_id}: invalid all-frame mean Hamming distance")
        for digest_field in (
            "all_frame_dhash_sha256",
            "master_pcm_f32le_stereo_sha256",
        ):
            digest = expectation.get(digest_field)
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                failures.append(f"{project_id}: invalid {digest_field}")
        if not isinstance(expectation.get("loudness"), dict):
            failures.append(f"{project_id}: no loudness evidence")
        if not isinstance(expectation.get("master_audio"), dict):
            failures.append(f"{project_id}: no tolerant master-audio evidence")
        if not isinstance(expectation.get("qc_findings"), list):
            failures.append(f"{project_id}: no expected QC finding list")
    print(
        json.dumps(
            {
                "ok": not failures,
                "expectations": str(EXPECTATIONS),
                "project_count": len(projects),
                "failures": failures,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
