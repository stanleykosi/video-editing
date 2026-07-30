"""Human-readable benchmark report generation."""

from editorial_brain.api.results import BenchmarkResult


def markdown_report(result: BenchmarkResult) -> str:
    lines = [
        "# Editorial Brain Benchmark",
        "",
        f"Overall: {'PASS' if result.passed else 'FAIL'}",
        "",
    ]
    for scenario in result.scenarios:
        lines.extend(
            [
                f"## {scenario.scenario_id}",
                "",
                f"Result: {'PASS' if scenario.passed else 'FAIL'}",
                "",
                "| Metric | Category | Value | Gate |",
                "|---|---:|---:|---:|",
            ]
        )
        lines.extend(
            f"| {metric.name} | {metric.category} | {metric.value:.6f} | "
            f"{'' if metric.passed is None else ('PASS' if metric.passed else 'FAIL')} |"
            for metric in scenario.metrics
        )
        lines.append("")
    lines.extend(
        [
            "Technical correctness and expected synthetic editorial behavior are gated separately.",
            "Subjective human-review areas are reported but never labeled human-level editing.",
        ]
    )
    return "\n".join(lines) + "\n"
