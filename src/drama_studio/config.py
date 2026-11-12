"""Configuration loading.

All configuration lives in ``config/*.yaml``. Paths are resolved against the
project root, which is located by walking up to the directory containing
``pyproject.toml`` (or by setting ``DRAMA_ROOT``).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _load_dotenv(root: Path) -> None:
    """Load KEY=VALUE pairs from <root>/.env without overriding real env vars."""
    path = root / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _expand(value):
    """Expand ${VAR} in config values; missing variables fail loudly."""
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            name = match.group(1)
            resolved = os.environ.get(name)
            if not resolved:
                raise ValueError(
                    f"environment variable {name} is not set; copy .env.example to .env"
                )
            return resolved
        return _ENV_RE.sub(replace, value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


_load_dotenv(Path(__file__).resolve().parents[2])
from pydantic import BaseModel, ConfigDict, Field


def find_project_root(start: Path | None = None) -> Path:
    env_root = os.environ.get("DRAMA_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "config").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot locate project root (no pyproject.toml + config/ found). Set DRAMA_ROOT."
    )


class ComfyUISettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8188
    startup_timeout_seconds: int = 180
    request_timeout_seconds: int = 600
    workflow_timeout_seconds: int = 1800
    poll_interval_seconds: int = 2

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_url: str = "http://127.0.0.1:8080/v1"
    api_key: str = "sk-local"
    model: str = "Qwen3-30B-A3B-Instruct-2507"
    model_path: str | None = None
    context_size: int = 65536
    temperature: float = 0.2
    max_repair_attempts: int = 2


class ZeroShotSettings(BaseModel):
    """Reference-audio cloning. Needs a prompt and its exact transcript."""

    model_config = ConfigDict(extra="ignore")

    prompt_audio: str = "assets/audio/prompts/my_voice_clean_v1.wav"
    prompt_text: str = ""
    speed: float | None = None
    runtime: str = "voxcpm2"      # which runtime must be up on 50000


class TTSSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_url: str = "http://127.0.0.1:50000"
    sample_rate: int = 48000
    zero_shot: ZeroShotSettings = Field(default_factory=ZeroShotSettings)


class FFmpegSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    binary: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    threads: int = 8


class PathsSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    models_root: Path = Path("models")
    runtime_root: Path = Path("runtime")
    projects_root: Path = Path("projects")
    logs_root: Path = Path("logs")
    workflows_root: Path = Path("workflows")

    def resolve_against(self, root: Path) -> "PathsSettings":
        def fix(p: Path) -> Path:
            return p if p.is_absolute() else (root / p)

        return PathsSettings(
            models_root=fix(self.models_root).resolve(),
            runtime_root=fix(self.runtime_root).resolve(),
            projects_root=fix(self.projects_root).resolve(),
            logs_root=fix(self.logs_root).resolve(),
            workflows_root=fix(self.workflows_root).resolve(),
        )


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    root: Path
    paths: PathsSettings
    comfyui: ComfyUISettings = Field(default_factory=ComfyUISettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    ffmpeg: FFmpegSettings = Field(default_factory=FFmpegSettings)

    @property
    def comfyui_dir(self) -> Path:
        return self.paths.runtime_root / "ComfyUI"

    @property
    def comfyui_python(self) -> Path:
        return self.comfyui_dir / ".venv" / "Scripts" / "python.exe"


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    family: str
    files: dict[str, Path]
    sizes: dict[str, int] = Field(default_factory=dict)
    loader_node: str | None = None
    notes: str | None = None


class ModelRegistry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    models: dict[str, ModelSpec]

    def resolve_against(self, root: Path, models_root: Path | None = None) -> "ModelRegistry":
        base = models_root or root
        resolved: dict[str, ModelSpec] = {}
        for key, spec in self.models.items():
            files = {
                name: (p if p.is_absolute() else (base / p)).resolve()
                for name, p in spec.files.items()
            }
            resolved[key] = spec.model_copy(update={"files": files})
        return ModelRegistry(models=resolved)


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


def load_settings(root: Path | None = None) -> Settings:
    root = (root or find_project_root()).resolve()
    _load_dotenv(root)
    raw = _expand(_read_yaml(root / "config" / "settings.yaml"))
    raw["root"] = root
    raw["paths"] = PathsSettings(**raw.get("paths", {})).resolve_against(root)
    return Settings(**raw)


def load_models(root: Path | None = None) -> ModelRegistry:
    root = (root or find_project_root()).resolve()
    _load_dotenv(root)
    raw = _expand(_read_yaml(root / "config" / "models.yaml"))
    settings = load_settings(root)
    return ModelRegistry(**raw).resolve_against(root, settings.paths.models_root)


def load_generation(root: Path | None = None) -> dict:
    root = (root or find_project_root()).resolve()
    return _read_yaml(root / "config" / "generation.yaml")


def load_audio(root: Path | None = None) -> dict:
    root = (root or find_project_root()).resolve()
    return _read_yaml(root / "config" / "audio.yaml")
