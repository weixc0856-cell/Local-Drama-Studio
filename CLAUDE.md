# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Local AI short-drama production lab: script → storyboard → character/scene assets → keyframes → video clips → voice → subtitles → MP4.

ComfyUI is **only** the generation engine. Python (`src/drama_studio`) owns business state, scheduling, retries and quality gates. FFmpeg owns composition. The local LLM (`D:\AI`) and CosyVoice (`D:\AI\CosyVoice-Runtime`) are external HTTP services.

**Current state: R0 complete and verified. R1-R7 are intentionally not implemented.** Do not build ahead of the current stage; each stage must be executed on this machine and evidenced before the next starts.

## Hard environment invariants

1. **Two Python environments, never merged.**
   - Root `.venv` (Python 3.12, uv): orchestration only. **Never install torch here.**
   - `runtime/ComfyUI/.venv`: PyTorch XPU + ComfyUI + ComfyUI-GGUF. Never import it from `src/`.
2. **Model store is `D:\AI\models`, outside this repo.** The two diffusion GGUFs must stay at the **top level** because `D:\AI\start_server.bat` scans only `%MODELS_DIR%\*.gguf`. New text encoders/VAEs go in `text_encoders\` and `vae\`; ComfyUI sees both through `extra_model_paths.yaml`.
3. **Do not modify** `D:\AI\start_server.bat` / `bin-*` / `CosyVoice-Runtime`, or other projects' environments. Do not move existing top-level model files.
4. **Ports:** ComfyUI `8188`; project LLM `8081`; CosyVoice `50000`. `8080` belongs to an unrelated instance that requires an API key (verified 401) — do not depend on it or kill it.
5. **GPU tenants are exclusive** (8 GB A750): LLM, FLUX, Wan. One generation job at a time. Prefer a CPU-only llama.cpp instance for script work.
6. **Verified A750 behavior:** text encoders run on CPU (Qwen3-4B 7.67 GB explicit; UMT5 6.4 GB auto-offloaded). Wan **must use 20 steps** — 10 steps produces rainbow artifacts. Peak VRAM ≈ 5 GiB; ComfyUI auto-unloads after each prompt.
7. Local HTTP probes must bypass the system proxy: `httpx(..., trust_env=False)` in Python, `curl.exe` in PowerShell. `Invoke-RestMethod` returns 502 for localhost here.

## Commands

```powershell
# Orchestration env (idempotent, creates .venv)
uv sync --python 3.12

# Tests (all / single)
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m pytest tests/test_models.py::test_storyboard_accepts_valid_contract -q

# Diagnostics (writes logs/doctor-*.json)
scripts\doctor.ps1
.venv\Scripts\drama.exe doctor --json

# Generation engine (heavy first run: PyTorch XPU + ComfyUI deps)
scripts\setup.ps1 -WithComfyUI
scripts\start.ps1          # port 8188, waits for /system_stats
scripts\stop.ps1           # kills the ComfyUI process tree (venv launcher -> real child)

# R0-only probe: submit API workflow -> poll /history -> download outputs
.venv\Scripts\python.exe scripts\r0_comfy_probe.py `
  --workflow workflows\r0_flux_t2i_api.json `
  --params workflows\r0_flux_t2i_params.json --out logs\r0\run
```

PowerShell scripts are UTF-8 **with BOM**; keep the BOM or PowerShell 5.1 will garble Chinese text.

## Architecture that requires reading multiple files

- `src/drama_studio/config.py` — discovers project root via `pyproject.toml`+`config/` (or `DRAMA_ROOT`), loads four YAMLs into Pydantic models, resolves relative paths, and carries exact model `sizes` so partial downloads cannot pass.
- `src/drama_studio/models.py` — **the data contract boundary**. Strict Pydantic (`extra="forbid"`). IDs are `char_001` / `loc_001` / `prop_001` / `shot_001`; a shot's ID must equal `shot_{index:03d}`, indexes are contiguous, and all references must resolve. Local LLM output must validate against `Storyboard` or the stage fails (max 2 repair attempts by design, not implemented yet).
- `src/drama_studio/doctor.py` — emits `PASS_VERIFIED / PASS_LIMITED / FAIL / NOT_RUN` with evidence. It never guesses: unimplemented services are `NOT_RUN`.
- `docs/ARCHITECTURE.md` — the full target design: SQLite state machine, ComfyUI protocol, prompt locking, GPU rules, FFmpeg pipeline. Implemented modules are only those listed above; everything else there is planned.
- `docs/R0_TEST_REPORT.md` — measured facts and limits. Read §6 before proposing R1/R2 work.

Planned modules (not implemented; do not assume they exist): `state.py`, `comfy_client.py`, `generation/`, `script_engine/`, `storyboard/`, `character_manager/`, `audio/`, `subtitles/`, `editing/`, `quality/`, `storage/`, `orchestrator.py`.

Project state model when implemented: per-project `state.db` is authoritative; `manifest.json` is derived. Shot states: `PENDING → IMAGE_GENERATING → IMAGE_REVIEW → VIDEO_GENERATING → VIDEO_REVIEW → AUDIO_READY → COMPLETED`, plus `FAILED`, `NEEDS_REVIEW`, `RETRY_PENDING`, `CANCELLED`. Human gates only at H1 character lock, H2 keyframe approval, H3 final cut.

## ComfyUI workflows

- Only **API format** JSON in `workflows/`; placeholders like `{{seed}}` are whole-value strings replaced by JSON-tree traversal, preserving types. `scripts/r0_comfy_probe.py` is the reference implementation but is R0 test code, not the production client.
- Bundled official templates in `runtime/ComfyUI/.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/` are the source of truth for node parameters.
- Verified R0 graphs:
  - FLUX.2 klein: `UnetLoaderGGUF` → `CLIPLoader(type=flux2, device=cpu)` → `Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced`; no `FluxGuidance`.
  - Wan2.2 TI2V 5B: `Wan22ImageToVideoLatent` (48-ch), `ModelSamplingSD3(shift=8)`, `uni_pc`/`simple`, CFG 5, 20 steps.
- Model switching does not need a restart; `/free` is usually a no-op because models auto-unload. Restart only to clear the execution cache or recover.

## Working rules

- Never report `PASS_VERIFIED` without an executed artifact and log path. Downloading or installing is not proof of inference.
- Never present CPU execution as GPU execution; mark it `PASS_LIMITED` with the reason.
- Retries are bounded (max 2, backoff 30/90 s); no infinite loops. Preserve failure logs.
- Do not upgrade ComfyUI/nodes or replace model files without re-running the relevant R0 checks; record versions in `logs/r0/engine-versions.txt`.
- Keep seed, prompt, model hash and workflow hash with every asset.
- Pin the goal to a 30-45 s, 3-5 shot episode; measured budget is ~7-10 h of generation per episode.
