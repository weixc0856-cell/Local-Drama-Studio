from pathlib import Path

from drama_studio.config import find_project_root, load_audio, load_generation, load_models, load_settings


def test_find_project_root_from_package() -> None:
    root = find_project_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "config").is_dir()


def test_paths_resolve_inside_project() -> None:
    root = find_project_root()
    settings = load_settings(root)
    assert settings.paths.runtime_root == (root / "runtime").resolve()
    assert settings.comfyui_python.name == "python.exe"
    assert settings.paths.models_root.is_absolute()


def test_all_config_files_parse() -> None:
    root = find_project_root()
    assert load_settings(root).comfyui.port == 8188
    registry = load_models(root)
    assert {"flux_2_klein_4b", "wan_2_2_ti2v_5b"} <= set(registry.models)
    flux = registry.models["flux_2_klein_4b"]
    assert set(flux.files) == set(flux.sizes)
    assert "profiles" in load_generation(root)
    assert "tts" in load_audio(root)


def test_repository_tts_default_is_zero_shot() -> None:
    """PRD-TTS-001: production default is CosyVoice2-0.5B zero-shot."""
    root = find_project_root()
    tts = load_audio(root)["tts"]
    assert tts["mode"] == "zero_shot"
    assert tts["zero_shot"]["prompt_audio"]
    assert tts["zero_shot"]["prompt_text"]
