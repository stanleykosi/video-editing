"""Render canonical golden projects and print decoded expectation observations."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.support.golden_metrics import (  # noqa: E402
    audio_summary,
    decode_audio,
    decoded_pcm_sha256,
    frame_dhash,
    frame_dhash_digest,
    frame_dhash_sequence,
    frequency_levels_db,
    media_tool_fingerprint,
)
from tests.support.golden_projects import BUILDERS  # noqa: E402
from video_engine.api.engine import VideoEngine  # noqa: E402
from video_engine.qc.models import QCRequest  # noqa: E402
from video_engine.render.models import RenderMode, RenderRequest  # noqa: E402
from video_engine.storage.atomic import atomic_write_text  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projects", nargs="*")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Merge observations into the canonical expectation manifest.",
    )
    args = parser.parse_args()
    unknown = sorted(set(args.projects) - set(BUILDERS))
    if unknown:
        parser.error(f"unknown projects: {', '.join(unknown)}")
    selected = args.projects or list(BUILDERS)
    observations: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="video-engine-goldens-") as temporary:
        root = Path(temporary)
        engine = VideoEngine(root)
        for scenario_id in selected:
            scenario = BUILDERS[scenario_id](engine)
            if (
                scenario.browser_required
                and os.environ.get("VIDEO_ENGINE_RUN_REMOTION_INTEGRATION") != "1"
            ):
                continue
            output = root / f"{scenario_id}.mp4"
            section_duration = (
                scenario.project.settings.frame_rate.frames_to_time(
                    scenario.section_duration_frames
                )
                if scenario.section_duration_frames is not None
                else None
            )
            render = engine.renderer(scenario.project).render(
                RenderRequest(
                    output_path=output,
                    mode=RenderMode.PREVIEW,
                    sectioning=scenario.section_duration_frames is not None,
                    section_duration=section_duration,
                )
            )
            qc = engine.qc(scenario.project).run(
                QCRequest(output_path=output, report_dir=root / f"{scenario_id}-qc")
            )
            samples = decode_audio(output)
            compiled = engine.renderer(scenario.project).compile(
                RenderRequest(
                    output_path=output,
                    mode=RenderMode.PREVIEW,
                    sectioning=scenario.section_duration_frames is not None,
                    section_duration=section_duration,
                )
            )
            mux = compiled.graph.node(compiled.graph.outputs["main"])
            encoded_audio = next(
                compiled.graph.node(node_id)
                for node_id in mux.inputs
                if compiled.graph.node(node_id).artifact_type.value == "encoded_audio"
            )
            master_id = encoded_audio.inputs[0]
            master_record = next(
                record for record in render.manifest.records if record.node_id == master_id
            )
            assert master_record.artifact_path is not None
            master_samples = decode_audio(master_record.artifact_path)
            audio_signal = next(check for check in qc.report.checks if check.code == "audio.signal")
            audio_measurements = {
                measurement.name: measurement.value for measurement in audio_signal.measurements
            }
            observations[scenario_id] = {
                "frame_dhash": {
                    str(index): frame_dhash(output, index) for index in scenario.frame_samples
                },
                "all_frame_dhash_sha256": frame_dhash_digest(output),
                "all_frame_dhash": list(frame_dhash_sequence(output)),
                "all_frame_max_hamming": 8,
                "all_frame_mean_hamming": 2.5,
                "audio_samples": int(samples.size),
                "master_pcm_f32le_stereo_sha256": decoded_pcm_sha256(master_record.artifact_path),
                "master_audio": audio_summary(master_samples),
                "loudness": {
                    "integrated_lufs": audio_measurements.get("integrated_loudness"),
                    "true_peak_dbtp": audio_measurements.get("true_peak"),
                },
                "frequency_levels_db": frequency_levels_db(samples, scenario.audio_frequencies_hz),
                "qc_status": qc.report.status.value,
                "qc_findings": sorted(
                    check.code for check in qc.report.checks if check.status.value != "passed"
                ),
                "render_seconds": (
                    render.manifest.completed_at - render.manifest.started_at
                ).total_seconds(),
                "node_count": len(render.manifest.records),
                "cache_hits": render.cache_hits,
                "output_size_bytes": render.manifest.output_size_bytes,
            }
    if args.update:
        expectation_path = ROOT / "testdata" / "engine" / "golden_expectations.json"
        payload = json.loads(expectation_path.read_text(encoding="utf-8"))
        payload["schema_version"] = 3
        payload["media_tool_fingerprint"] = media_tool_fingerprint()
        payload["projects"].update(observations)
        atomic_write_text(
            expectation_path,
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
    print(json.dumps(observations, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
