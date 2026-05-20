"""Loopback-only ComfyUI HTTP bridge for the desktop VFX Factory surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import asyncio
import json
import time
import uuid

__all__ = [
    "ComfyUIEndpointRejected",
    "VfxPromptRequest",
    "VfxSubmissionError",
    "VfxSubmissionResult",
    "build_text_to_image_dag",
    "submit_prompt",
]

DEFAULT_COMFYUI_BASE_URL: Final[str] = "http://127.0.0.1:8188"
_LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1"})
_MAX_HTTP_RESPONSE_BYTES: Final[int] = 1_048_576
_MIN_DIMENSION: Final[int] = 64
_MAX_DIMENSION: Final[int] = 4096


class ComfyUIEndpointRejected(ValueError):
    """Raised when an endpoint is not an explicit localhost HTTP target."""


class VfxSubmissionError(RuntimeError):
    """Raised when the ComfyUI loopback node rejects or fails a request."""


@dataclass(frozen=True, slots=True)
class VfxPromptRequest:
    """User-facing VFX request converted to a ComfyUI JSON DAG."""

    positive_prompt: str
    negative_prompt: str = (
        "low quality, blurry, text artifacts, watermark, malformed geometry, "
        "overexposed highlights"
    )
    checkpoint_name: str = "sd_xl_base_1.0.safetensors"
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    seed: int = 1_337
    steps: int = 28
    cfg: float = 7.0
    sampler_name: str = "dpmpp_2m"
    scheduler: str = "karras"
    denoise: float = 1.0
    filename_prefix: str = "sovereign_vfx"
    client_id: str = field(default_factory=lambda: f"sovereign-desktop-{uuid.uuid4()}")

    def validated(self) -> VfxPromptRequest:
        _require_nonempty("positive_prompt", self.positive_prompt, max_length=4_000)
        _require_nonempty("negative_prompt", self.negative_prompt, max_length=4_000)
        _require_nonempty("checkpoint_name", self.checkpoint_name, max_length=512)
        _require_nonempty("sampler_name", self.sampler_name, max_length=128)
        _require_nonempty("scheduler", self.scheduler, max_length=128)
        _require_nonempty("filename_prefix", self.filename_prefix, max_length=128)
        _require_nonempty("client_id", self.client_id, max_length=256)
        _validate_dimension("width", self.width)
        _validate_dimension("height", self.height)
        if self.batch_size < 1 or self.batch_size > 8:
            raise ValueError("batch_size must be between 1 and 8")
        if self.seed < 0 or self.seed > 18_446_744_073_709_551_615:
            raise ValueError("seed must fit ComfyUI uint64 range")
        if self.steps < 1 or self.steps > 150:
            raise ValueError("steps must be between 1 and 150")
        if self.cfg < 0.0 or self.cfg > 30.0:
            raise ValueError("cfg must be between 0.0 and 30.0")
        if self.denoise <= 0.0 or self.denoise > 1.0:
            raise ValueError("denoise must be within (0.0, 1.0]")
        return self


@dataclass(frozen=True, slots=True)
class VfxSubmissionResult:
    """Bounded response metadata returned to the Qt GUI."""

    endpoint: str
    prompt_id: str | None
    client_id: str
    elapsed_seconds: float
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]

    @property
    def accepted(self) -> bool:
        return self.prompt_id is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "client_id": self.client_id,
            "elapsed_seconds": self.elapsed_seconds,
            "endpoint": self.endpoint,
            "prompt_id": self.prompt_id,
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
        }


def build_text_to_image_dag(request: VfxPromptRequest) -> dict[str, dict[str, Any]]:
    """Construct a minimal ComfyUI text-to-image DAG without loading any models."""

    request = request.validated()
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": request.checkpoint_name,
            },
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": request.positive_prompt,
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1],
                "text": request.negative_prompt,
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": request.batch_size,
                "height": request.height,
                "width": request.width,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "cfg": request.cfg,
                "denoise": request.denoise,
                "latent_image": ["4", 0],
                "model": ["1", 0],
                "negative": ["3", 0],
                "positive": ["2", 0],
                "sampler_name": request.sampler_name,
                "scheduler": request.scheduler,
                "seed": request.seed,
                "steps": request.steps,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": request.filename_prefix,
                "images": ["6", 0],
            },
        },
    }


async def submit_prompt(
    request: VfxPromptRequest,
    *,
    base_url: str = DEFAULT_COMFYUI_BASE_URL,
    timeout_seconds: float = 12.0,
) -> VfxSubmissionResult:
    """Submit a DAG to a local ComfyUI node without blocking the Qt event loop."""

    endpoint = _validated_base_url(base_url)
    prompt = build_text_to_image_dag(request)
    payload: dict[str, Any] = {
        "client_id": request.client_id,
        "prompt": prompt,
    }
    start = time.monotonic()
    response_payload = await asyncio.to_thread(
        _post_json,
        f"{endpoint}/prompt",
        payload,
        timeout_seconds,
    )
    elapsed = time.monotonic() - start
    prompt_id = response_payload.get("prompt_id")
    if prompt_id is not None and not isinstance(prompt_id, str):
        raise VfxSubmissionError("ComfyUI response prompt_id was not a string")
    return VfxSubmissionResult(
        endpoint=endpoint,
        prompt_id=prompt_id,
        client_id=request.client_id,
        elapsed_seconds=elapsed,
        request_payload=payload,
        response_payload=response_payload,
    )


def _validated_base_url(base_url: str) -> str:
    parsed = urlparse(base_url.strip())
    if parsed.scheme != "http":
        raise ComfyUIEndpointRejected("ComfyUI endpoint must use http://")
    if parsed.hostname not in _LOOPBACK_HOSTS:
        raise ComfyUIEndpointRejected("ComfyUI endpoint must be explicit loopback")
    if parsed.username or parsed.password:
        raise ComfyUIEndpointRejected("ComfyUI endpoint credentials are not allowed")
    if not parsed.port:
        raise ComfyUIEndpointRejected("ComfyUI endpoint must include an explicit port")
    if parsed.path not in {"", "/"}:
        raise ComfyUIEndpointRejected("ComfyUI base URL must not include a path")
    host = parsed.hostname
    if host is None:
        raise ComfyUIEndpointRejected("ComfyUI endpoint host is required")
    rendered_host = f"[{host}]" if ":" in host else host
    return f"http://{rendered_host}:{parsed.port}"


def _post_json(url: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise VfxSubmissionError("timeout_seconds must be positive")
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "sovereign-desktop-vfx/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(_MAX_HTTP_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raw_error = exc.read(8192).decode("utf-8", errors="replace")
        raise VfxSubmissionError(f"ComfyUI HTTP {exc.code}: {raw_error}") from exc
    except URLError as exc:
        raise VfxSubmissionError(f"ComfyUI endpoint unavailable: {exc.reason}") from exc
    except TimeoutError as exc:
        raise VfxSubmissionError("ComfyUI endpoint timed out") from exc
    except OSError as exc:
        raise VfxSubmissionError(f"ComfyUI transport failed: {exc}") from exc
    if len(raw) > _MAX_HTTP_RESPONSE_BYTES:
        raise VfxSubmissionError("ComfyUI response exceeded maximum size")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise VfxSubmissionError("ComfyUI response was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise VfxSubmissionError("ComfyUI response JSON was not an object")
    return decoded


def _require_nonempty(field_name: str, value: str, *, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a nonempty string")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    if "\x00" in value:
        raise ValueError(f"{field_name} may not contain NUL bytes")


def _validate_dimension(field_name: str, value: int) -> None:
    if value < _MIN_DIMENSION or value > _MAX_DIMENSION:
        raise ValueError(f"{field_name} must be between {_MIN_DIMENSION} and {_MAX_DIMENSION}")
    if value % 8 != 0:
        raise ValueError(f"{field_name} must be divisible by 8")
