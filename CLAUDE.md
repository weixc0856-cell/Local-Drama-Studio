# CLAUDE.md

Guidance for Claude Code working in Local-Drama-Studio.

## Project Summary & Current State (v2.0)
Industrial local multi-modal short-drama and technical documentary production pipeline:
- **Image Generation (Dual Engine)**:
  - `z_image_turbo` (Primary): Alibaba 6B single-stream DiT (Q4_K_M), 8 steps, CFG 1.0, euler/simple. **Zero-LoRA candid realism**, natural skin pores, East Asian bone structure.
  - `flux3_klein` (Secondary/Compare): 16 steps, mandatory prompt upsampling. Used for industrial, aerodynamic, and typography AB evaluation.
- **Video Generation**:
  - `wan22_14b_i2v` (Standard): 14B dual-expert GGUF (Q4_K_M) + 6-step LightX2V LoRA + 64GB DDR5 Block Swap (A750 VRAM ~6.5GB) + standard 16-channel `wan_2.1_vae`. **Wan 5B is officially RETIRED (ADR-031)**.
  - **Widescreen Guard**: On 16:9 480P, automatically enforce medium close-up (waist-up) and shallow DoF to prevent latent token dilution.
  - Post-processing: 2x Lanczos super-res to 2K + FFmpeg minterpolate 32fps optical flow interpolation.
- **Commercial Audio (100% Permissive Commercial License)**:
  - `stable_audio_open_1_0`: Stability Community License (<$1M commercial-free). 25 steps pure CPU for ambient BGM and rain/foley SFX.
  - `acestep_1_5_xl`: MIT / Apache 2.0. 8 steps pure CPU for orchestral soundtracks.
  - **Strictly blacklisted**: Meta MusicGen, HKUST YuE (non-commercial CC-BY-NC 4.0 prohibited).

## Path & Storage Invariants (Zero Absolute Paths in Repo)
- **Two physical roots, fully decoupled**:
  - Repo root (`./`): code, config, workflows, docs, small manifests.
  - Content output root (`$DRAMA_OUTPUT_ROOT`, mapped via `./studio_data` junction): `projects/`, `build/`, `deliver/`, `experiments/`, `outputs/`.
- **Path Resolution**: Read from `config/local-paths.yaml` (template: `config/local-paths.example.yaml`) or `drama_studio.paths`. Never hardcode local drive letters (`C:`, `D:`) or usernames into git-tracked files.
- **Model Storage**: Canonical models stored outside repo in `$DRAMA_MODELS_ROOT` (configured via `config/local-paths.yaml`).

## Standard Production Commands
```powershell
# Environment & Status Check
python src/produce.py status
uv sync --python 3.12
.venv\Scripts\python.exe -m pytest

# Image Production (Auto-routed)
# Portrait/Cinematic -> Z-Image Turbo native
python src/produce.py image --project <id> --type portrait --prompt "..."
# Industrial/Typography -> Dual-engine AB Compare -> Deliver SBS board
python src/produce.py image --project <id> --type industrial --prompt "..."

# Video Production (Wan 14B + Widescreen Guard + 2K 32fps + Audio Mux)
python src/produce.py video --project <id> --image studio_data/deliver/<id>/anchor.png --aspect 9:16
python src/produce.py video --project <id> --image studio_data/deliver/<id>/anchor.png --aspect 16:9
```

## Hardware & Runtime Rules (Intel Arc A750 8GB + 64GB DDR5)
- **Environments**: Root `.venv` (Python 3.12, orchestration, no torch); `runtime/ComfyUI/.venv` (PyTorch XPU + ComfyUI).
- **GPU Exclusivity**: Arc A750 (8GB VRAM) runs one Diffusion task at a time. Audio models run concurrently on CPU without VRAM contention.
- **Ports**: ComfyUI `8188`; local LLM `8080`; VoxCPM2 `50000`.
- **Widescreen Rule**: Follow `docs/WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md` for framing and bokeh.
- **Repo Hygiene**: All media binaries (*.mp4, *.wav, *.png) and generated outputs must stay under output root (`studio_data/`). Never commit large files to git.
