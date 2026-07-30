"""`video-brain` command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ValidationError

from editorial_brain import EditorialBrain
from editorial_brain.api.exceptions import EditorialBrainError
from editorial_brain.core.models import EditorialBrief, EditorialPlan, ReferenceEditProfile
from editorial_brain.knowledge.base import write_canonical_base
from video_engine.api import Project, VideoEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-brain")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _command(subparsers, "doctor")
    knowledge = _command(subparsers, "knowledge")
    knowledge.add_argument("--brief", type=Path, required=True)
    knowledge.add_argument("--reference-profile", type=Path)
    knowledge_build = _command(subparsers, "knowledge-build")
    knowledge_build.add_argument("--output", type=Path)
    analyze = _command(subparsers, "analyze")
    _project_brief_arguments(analyze)
    reference = _command(subparsers, "analyze-reference")
    reference.add_argument("reference", type=Path)
    for name in ("story", "selects", "plan", "variants"):
        command = _command(subparsers, name)
        _project_brief_arguments(command)
        if name in {"plan", "variants"}:
            command.add_argument("--count", type=int, default=3)
            command.add_argument("--reference-profile", type=Path)
    compile_command = _command(subparsers, "compile")
    compile_command.add_argument("project", type=Path)
    compile_command.add_argument("plan", type=Path)
    apply_command = _command(subparsers, "apply")
    apply_command.add_argument("project", type=Path)
    apply_command.add_argument("plan", type=Path)
    explain = _command(subparsers, "explain")
    explain.add_argument("plan", type=Path)
    _command(subparsers, "benchmark")
    return parser


def _command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser], name: str
) -> argparse.ArgumentParser:
    command = subparsers.add_parser(name)
    command.add_argument("--json", action="store_true", dest="as_json")
    return command


def _project_brief_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project", type=Path)
    parser.add_argument("--brief", type=Path, required=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = _dispatch(args)
        _emit(payload, as_json=args.as_json)
        return 0
    except (EditorialBrainError, ValidationError, ValueError, OSError) as exc:
        error = (
            exc.as_dict()
            if isinstance(exc, EditorialBrainError)
            else {
                "code": "command_failed",
                "message": str(exc),
            }
        )
        _emit({"ok": False, "error": error}, as_json=True, stream=sys.stderr)
        return 2


def _dispatch(args: argparse.Namespace) -> object:
    if args.command == "doctor":
        return _brain(Path.cwd()).doctor()
    if args.command == "knowledge":
        reference = (
            ReferenceEditProfile.model_validate_json(
                args.reference_profile.read_text(encoding="utf-8")
            )
            if args.reference_profile
            else None
        )
        return _brain(Path.cwd()).knowledge(_load_brief(args.brief), reference=reference)
    if args.command == "knowledge-build":
        root = Path.cwd()
        base = _brain(root).consolidate_knowledge()
        if args.output is None:
            write_canonical_base(root / "knowledge", base)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            assert isinstance(base, BaseModel)
            args.output.write_text(base.model_dump_json(), encoding="utf-8")
        return base
    if args.command == "analyze-reference":
        return _brain(Path.cwd()).analyze_reference(args.reference)
    if args.command == "benchmark":
        return _brain(Path.cwd()).benchmark()
    if args.command == "explain":
        plan = EditorialPlan.model_validate_json(args.plan.read_text(encoding="utf-8"))
        return _brain(args.plan.parent).explain(plan)
    if args.command in {"compile", "apply"}:
        project = _load_project(args.project)
        plan = EditorialPlan.model_validate_json(args.plan.read_text(encoding="utf-8"))
        brain = _brain(args.project.parent)
        compiled = brain.compile(project=project, plan=plan, mode="patch")
        if args.command == "compile":
            return compiled
        assert compiled.patch is not None
        editor = VideoEngine(args.project.parent).editor(project)
        editor.apply_patch(compiled.patch)
        VideoEngine(args.project.parent).save_project(editor.project, args.project)
        return {
            "ok": True,
            "project_path": str(args.project.resolve()),
            "project_revision": editor.project.revision,
            "patch_id": compiled.patch.patch_id,
        }
    project = _load_project(args.project)
    brief = _load_brief(args.brief)
    brain = _brain(args.project.parent)
    analysis = brain.analyze(project=project, brief=brief)
    if args.command == "analyze":
        return analysis
    if args.command == "story":
        return brain.build_story(project=project, brief=brief, analysis=analysis)
    if args.command == "selects":
        return brain.generate_selects(project=project, brief=brief, analysis=analysis)
    if args.command in {"plan", "variants"}:
        reference = (
            ReferenceEditProfile.model_validate_json(
                args.reference_profile.read_text(encoding="utf-8")
            )
            if args.reference_profile
            else None
        )
        return brain.plan(
            project=project,
            brief=brief,
            analysis=analysis,
            variants=args.count,
            reference=reference,
        )
    raise ValueError(f"unsupported command {args.command!r}")


def _brain(root: Path) -> EditorialBrain:
    resolved_root = root.resolve()
    working_root = Path.cwd().resolve()
    env_file = resolved_root / ".env"
    if (
        not env_file.is_file()
        and resolved_root.is_relative_to(working_root)
        and (working_root / ".env").is_file()
    ):
        env_file = working_root / ".env"
    return EditorialBrain.from_environment(resolved_root, env_file=env_file)


def _load_project(path: Path) -> Project:
    return Project.model_validate_json(path.read_text(encoding="utf-8"))


def _load_brief(path: Path) -> EditorialBrief:
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError("brief must contain a JSON/YAML object")
    return EditorialBrief.model_validate(payload)


def _emit(value: object, *, as_json: bool, stream: Any = sys.stdout) -> None:
    payload: object
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json", exclude_none=True)
    else:
        payload = value
    if as_json:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")), file=stream)
        return
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
