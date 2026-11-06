r"""Regenerate runtime/ComfyUI/extra_model_paths.yaml from the repo template.

ComfyUI does not expand environment variables, so the template placeholder is
resolved here (or by scripts/setup.ps1) before ComfyUI reads the file.

    .venv\Scripts\python.exe scripts\sync_comfyui_paths.py
"""

from __future__ import annotations

from drama_studio.config import find_project_root, load_settings


def main() -> int:
    root = find_project_root()
    settings = load_settings(root)
    template = (root / "config" / "comfyui_extra_model_paths.yaml").read_text(encoding="utf-8")
    text = template.replace("${DRAMA_MODELS_ROOT}", settings.paths.models_root.as_posix())
    target = root / "runtime" / "ComfyUI" / "extra_model_paths.yaml"
    if not target.parent.is_dir():
        raise SystemExit(f"ComfyUI runtime not found: {target.parent}")
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
