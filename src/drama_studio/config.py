"""Configuration loading.

All configuration lives in ``config/*.yaml``. Paths are resolved against the
project root, which is located by walking up to the directory containing
``pyproject.toml`` (or by setting ``DRAMA_ROOT``).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
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
    runtime: str = "cosyvoice2"   # which runtime must be up on 50000


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

    models_root: Path = Path("D:/AI/models")
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

    def resolve_against(self, root: Path) -> "ModelRegistry":
        resolved: dict[str, ModelSpec] = {}
        for key, spec in self.models.items():
            files = {
                name: (p if p.is_absolute() else (root / p)).resolve()
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
    raw = _read_yaml(root / "config" / "settings.yaml")
    raw["root"] = root
    raw["paths"] = PathsSettings(**raw.get("paths", {})).resolve_against(root)
    return Settings(**raw)


def load_models(root: Path | None = None) -> ModelRegistry:
    root = (root or find_project_root()).resolve()
    raw = _read_yaml(root / "config" / "models.yaml")
    return ModelRegistry(**raw).resolve_against(root)


def load_generation(root: Path | None = None) -> dict:
    root = (root or find_project_root()).resolve()
    return _read_yaml(root / "config" / "generation.yaml")


def load_audio(root: Path | None = None) -> dict:
    root = (root or find_project_root()).resolve()
    return _read_yaml(root / "config" / "audio.yaml")
