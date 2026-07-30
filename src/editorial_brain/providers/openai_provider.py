"""OpenAI Responses API semantic and multimodal provider.

The provider follows the current Responses API ``text.format`` JSON-schema
contract. Requests expose only verified candidate IDs; timestamps are neither
requested nor accepted.
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from editorial_brain.core.hashing import file_sha256, fingerprint
from editorial_brain.core.models import Confidence, EvidenceKind, ProviderEvidence, ProviderUsage
from editorial_brain.providers.base import (
    ProviderResult,
    ProviderStatus,
    SemanticJudgment,
    SemanticOutput,
    SemanticProvider,
    SemanticRequest,
    VisionJudgment,
    VisionOutput,
    VisionProvider,
    VisionRequest,
)

RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIProvider(SemanticProvider, VisionProvider):
    provider_name = "openai"

    def __init__(
        self,
        *,
        model: str = "gpt-5.6-terra",
        api_key_env: str = "OPENAI_API_KEY",
        reasoning_effort: str = "low",
        env_file: Path | None = None,
    ) -> None:
        self.model_name = model
        self.api_key_env = api_key_env
        self.reasoning_effort = reasoning_effort
        self.env_file = env_file.resolve() if env_file is not None else None

    @property
    def credential_configured(self) -> bool:
        return self._api_key() is not None

    @property
    def credential_source(self) -> str | None:
        if os.environ.get(self.api_key_env):
            return "process_environment"
        if self.env_file is not None and self._api_key() is not None:
            return "project_env_file"
        return None

    @property
    def fingerprint(self) -> str:
        return fingerprint(
            {
                "provider": self.provider_name,
                "model": self.model_name,
                "adapter": "responses-structured-v1",
                "reasoning_effort": self.reasoning_effort,
            }
        )

    def judge(self, request: SemanticRequest) -> ProviderResult[SemanticOutput]:
        allowed_ids = [candidate.candidate_id for candidate in request.candidates]
        content = [
            {
                "type": "input_text",
                "text": (
                    "Judge only the supplied editorial candidates. Return concise observable "
                    "reasons. "
                    "Never create timestamps or candidate IDs.\n"
                    f"Task: {request.task}\nInstruction: {request.instruction}\nCandidates:\n"
                    + json.dumps(
                        [candidate.model_dump(mode="json") for candidate in request.candidates],
                        sort_keys=True,
                    )
                ),
            }
        ]
        result = self._request(request, content, allowed_ids, schema_name="editorial_semantic")
        if result.status is not ProviderStatus.SUCCESS:
            return ProviderResult[SemanticOutput](
                status=result.status,
                error_code=result.error_code,
                error_message=result.error_message,
                retryable=result.retryable,
            )
        assert result.output is not None and result.evidence is not None
        judgments = [
            SemanticJudgment(
                candidate_id=item["candidate_id"],
                score=item["score"],
                labels=item["labels"],
                reasons=item["reasons"],
                confidence=Confidence(
                    score=item["confidence"],
                    basis=EvidenceKind.MODEL_INFERRED,
                    calibration="provider_self_reported",
                ),
            )
            for item in result.output
        ]
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=SemanticOutput(judgments=judgments),
            evidence=result.evidence,
        )

    def inspect(self, request: VisionRequest) -> ProviderResult[VisionOutput]:
        allowed_ids = [frame.candidate_id for frame in request.frames]
        content: list[dict[str, str]] = [
            {
                "type": "input_text",
                "text": (
                    "Describe only observable editorial cues in the supplied frames. Do not infer "
                    "identity, sensitive attributes, psychology, or timestamps. Return one "
                    "judgment "
                    "for each candidate ID.\n"
                    f"Task: {request.task}\nInstruction: {request.instruction}"
                ),
            }
        ]
        for frame in request.frames:
            _validate_frame(frame.path, frame.sha256)
            content.append(
                {
                    "type": "input_text",
                    "text": f"candidate_id={frame.candidate_id}; caption={frame.caption}",
                }
            )
            encoded = base64.b64encode(frame.path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:{frame.media_type};base64,{encoded}",
                    "detail": "auto",
                }
            )
        result = self._request(request, content, allowed_ids, schema_name="editorial_vision")
        if result.status is not ProviderStatus.SUCCESS:
            return ProviderResult[VisionOutput](
                status=result.status,
                error_code=result.error_code,
                error_message=result.error_message,
                retryable=result.retryable,
            )
        assert result.output is not None and result.evidence is not None
        judgments = [
            VisionJudgment(
                candidate_id=item["candidate_id"],
                summary="; ".join(item["reasons"]) or "provider supplied no concise reason",
                labels=item["labels"],
                observable_cues=item["reasons"],
                score=item["score"],
                confidence=Confidence(
                    score=item["confidence"],
                    basis=EvidenceKind.MODEL_INFERRED,
                    calibration="provider_self_reported",
                ),
            )
            for item in result.output
        ]
        return ProviderResult(
            status=ProviderStatus.SUCCESS,
            output=VisionOutput(judgments=judgments),
            evidence=result.evidence,
        )

    def _request(
        self,
        request: SemanticRequest | VisionRequest,
        content: list[dict[str, str]],
        allowed_ids: list[str],
        *,
        schema_name: str,
    ) -> ProviderResult[list[dict[str, Any]]]:
        api_key = self._api_key()
        if not api_key:
            return ProviderResult(
                status=ProviderStatus.UNAVAILABLE,
                error_code="missing_api_key",
                error_message=f"{self.api_key_env} is not configured",
            )
        try:
            import httpx
        except ImportError:
            return ProviderResult(
                status=ProviderStatus.UNAVAILABLE,
                error_code="optional_dependency_missing",
                error_message="install the brain-cloud optional dependency",
            )
        schema = _judgment_schema(allowed_ids)
        body = {
            "model": self.model_name,
            "store": False,
            "reasoning": {"effort": self.reasoning_effort},
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        last_status: int | None = None
        last_error = "provider request failed"
        response_payload: dict[str, Any] | None = None
        response_headers: dict[str, str] = {}
        for attempt in range(request.retry.attempts):
            try:
                response = httpx.post(
                    RESPONSES_URL,
                    headers=headers,
                    json=body,
                    timeout=request.timeout_seconds,
                )
                last_status = response.status_code
                response_headers = dict(response.headers)
                if response.status_code == 200:
                    parsed = response.json()
                    if not isinstance(parsed, dict):
                        raise ValueError("OpenAI response root must be an object")
                    response_payload = parsed
                    break
                last_error = f"OpenAI returned HTTP {response.status_code}"
                if response.status_code not in request.retry.retry_status_codes:
                    break
            except (httpx.HTTPError, ValueError) as exc:
                last_error = f"OpenAI request failed: {type(exc).__name__}"
            if attempt + 1 < request.retry.attempts:
                delay = min(
                    request.retry.maximum_backoff_seconds,
                    request.retry.initial_backoff_seconds * (2**attempt),
                )
                if delay:
                    time.sleep(delay)
        if response_payload is None:
            status = ProviderStatus.RATE_LIMITED if last_status == 429 else ProviderStatus.FAILED
            return ProviderResult(
                status=status,
                error_code=f"http_{last_status}" if last_status else "network_error",
                error_message=last_error,
                retryable=last_status in request.retry.retry_status_codes if last_status else True,
            )
        try:
            output_text = _response_output_text(response_payload)
            parsed_output = json.loads(output_text)
            judgments = parsed_output["judgments"]
            if not isinstance(judgments, list):
                raise TypeError("judgments must be an array")
            _validate_judgments(judgments, allowed_ids)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return ProviderResult(
                status=ProviderStatus.FAILED,
                error_code="invalid_provider_response",
                error_message=f"OpenAI response validation failed: {exc}",
            )
        usage = response_payload.get("usage", {})
        usage = usage if isinstance(usage, dict) else {}
        evidence = ProviderEvidence(
            provider=self.provider_name,
            model=self.model_name,
            provider_fingerprint=self.fingerprint,
            prompt_fingerprint=fingerprint(
                {"schema": schema, "schema_version": request.schema_version, "prompt": content}
            ),
            request_id=str(response_payload.get("id") or response_headers.get("x-request-id") or "")
            or None,
            usage=ProviderUsage(
                input_tokens=_optional_int(usage.get("input_tokens")),
                output_tokens=_optional_int(usage.get("output_tokens")),
            ),
            confidence=Confidence(
                score=min(float(item["confidence"]) for item in judgments) if judgments else 0,
                basis=EvidenceKind.MODEL_INFERRED,
                calibration="minimum_provider_self_reported",
                sample_size=len(judgments) or None,
            ),
        )
        return ProviderResult(status=ProviderStatus.SUCCESS, output=judgments, evidence=evidence)

    def _api_key(self) -> str | None:
        configured = os.environ.get(self.api_key_env)
        if configured:
            return configured
        if self.env_file is None or not self.env_file.is_file():
            return None
        from dotenv import dotenv_values

        value = dotenv_values(self.env_file).get(self.api_key_env)
        return value if isinstance(value, str) and value else None


def _judgment_schema(candidate_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "judgments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "candidate_id": {"type": "string", "enum": candidate_ids},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "reasons": {
                            "type": "array",
                            "maxItems": 8,
                            "items": {"type": "string"},
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["candidate_id", "score", "labels", "reasons", "confidence"],
                },
            }
        },
        "required": ["judgments"],
    }


def _response_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, list):
        raise TypeError("response.output must be an array")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    return text
            if isinstance(part, dict) and part.get("type") == "refusal":
                raise ValueError("provider refused the request")
    raise ValueError("response contains no output_text")


def _validate_judgments(values: list[Any], allowed_ids: list[str]) -> None:
    seen: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            raise TypeError("judgment must be an object")
        candidate_id = value.get("candidate_id")
        if candidate_id not in allowed_ids:
            raise ValueError(f"provider returned unknown candidate ID {candidate_id!r}")
        seen.append(candidate_id)
    if sorted(seen) != sorted(allowed_ids):
        raise ValueError("provider must return exactly one judgment per candidate")


def _validate_frame(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise ValueError(f"frame does not exist: {path}")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("frame exceeds 20 MiB provider safety limit")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise ValueError("frame SHA-256 does not match request")


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
