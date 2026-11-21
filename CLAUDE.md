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

# Z-Image Visual Style Atlas (38 recipes + 7-dimension vocabulary + live testbench)
python src/produce.py atlas list -c C                     # browse styles by category
python src/produce.py atlas compile -s song_aesthetics --subject "..."
python src/produce.py atlas vocab -d lighting             # reusable phrase bank
python src/produce.py atlas mix --base song_aesthetics --borrow luxury_product --dims lighting,color_texture
python src/produce.py atlas benchmark --mode recipe --all --seeds 42 --size square --live --resume
python src/produce.py atlas score --run-dir "<run>" --style <id> --mode recipe --seed 42 --purity 4
python src/produce.py image --project <id> --type portrait --style editorial_fashion
```

## Z-Image Style Atlas (config/z_image_styles.yaml)
- **38 recipes** across 9 categories (A portrait / B cinema / C Chinese tradition / D anime / E commercial /
  F graphic / G surreal / H hand media / T 2026 trends), each modeled on **7 dimensions**:
  subject, scene, composition, lighting, medium_style, color_texture, constraints.
- **Zero negative prompt**: Turbo is an 8-step distilled DiT. Encode exclusions as positive language
  (`a clean frame without graphic overlays`), never as a negative prompt. On-screen text goes in `"double quotes"`.
- **One primary medium per prompt.** `atlas mix` warns when `medium_style` is borrowed across styles.
- **Vocabulary bank**: `config/z_image_style_vocabulary.yaml` (72 reusable phrases) for composing new styles.
- **Measured baseline (A750, 1024x1024, 8 steps, CFG 1.0, euler/simple)**: 54/54 images succeeded,
  mean 192s, range 36-250s. The spread is VRAM residency: when DiT + text encoder + VAE all stay
  resident it runs ~36s; when the text encoder spills to CPU it runs ~200-250s. Budget ~200s/image.
- **Known failure modes** (see `docs/Z_IMAGE_STYLE_FINDINGS.md`):
  - Unspecified typography renders as garbled letters (Swiss poster, neon signage, woodblock plaque).
    Always lock on-screen text with `--text`; otherwise crop it out.
  - Naming lighting *equipment* ("large softbox lighting") puts the softbox in frame. Describe light quality.
  - Mountain subjects pull a blue-green landscape prior even when the prompt says monochrome ink.
  - Photographic lighting borrowed into flat-pigment media (gongbi/print) becomes literal light blobs.
  - Turbo diversity is low: two seeds of the same portrait recipe give near-identical framing.
- **Rubric scores are human-entered only** (`atlas score` / `atlas score-import`); never fabricated.
  Scores tagged `reviewer=claude-visual-review` are a model first pass awaiting user confirmation.
- Reference: `docs/Z_IMAGE_TURBO_STYLE_ATLAS.md` (auto-generated by `atlas export-atlas`),
  `docs/Z_IMAGE_STYLE_FINDINGS.md` (measured results), and the run report under
  `studio_data/experiments/z_image_styles/<run>/Z_IMAGE_STYLE_BENCHMARK_REPORT.md`.

## Hardware & Runtime Rules (Intel Arc A750 8GB + 64GB DDR5)
- **Environments**: Root `.venv` (Python 3.12, orchestration, no torch); `runtime/ComfyUI/.venv` (PyTorch XPU + ComfyUI).
- **GPU Exclusivity**: Arc A750 (8GB VRAM) runs one Diffusion task at a time. Audio models run concurrently on CPU without VRAM contention.
- **Ports**: ComfyUI `8188`; local LLM `8080`; VoxCPM2 `50000`.
- **Widescreen Rule**: Follow `docs/WIDESCREEN_VIDEO_GENERATION_GUIDELINES.md` for framing and bokeh.
- **Repo Hygiene**: All media binaries (*.mp4, *.wav, *.png) and generated outputs must stay under output root (`studio_data/`). Never commit large files to git.

## Token Economy & Session Hygiene (measured 2026-11-21)
A 15h atlas session cost ~12.3M billable-input-equivalent tokens (proxy billing DB): 88.8M cache
reads (context grew 46K→366K, never compacted, ~500 calls) + 2.66M cache writes, of which ~1.24M
was four full-context re-writes after >5min idle gaps. Deliverables were all on disk; the context
was pure working memory. Rules to keep that cost down without touching quality:
- **One phase per session.** Benchmark, scoring, and report are separate phases. At phase end,
  persist results (run report / findings doc / scores.csv), then `/compact` or start a fresh session
  that reads the 2-page summary. Never drag >150K tokens of history into a new phase.
  Backstop: `.claude/settings.json` sets `CLAUDE_CODE_AUTO_COMPACT_WINDOW=180000`, so auto-compact
  fires near 180K even though the relay model advertises a 1M window.
- **Long jobs run in background.** Launch generation/benchmarks with `run_in_background` (or a
  single `atlas benchmark --resume` batch) and end the turn; resume on the completion notification.
  No foreground blocking waits, no sleep/tail polling loops, no repeated ComfyUI `/history` curls.
  Idle >5min expires the prompt cache: the next call re-writes the whole context at 1.25x, so a
  small context makes every wait cheap.
- **Board-first image review.** Judge style/purity from the category boards
  (`run_z_image_style_atlas.py board`, 420px labeled tiles). Read an individual full-res image only
  to resolve a specific doubt (typography, skin detail) — a few per phase, not the whole sweep.
  Every image read stays in context and is re-billed on every later call.
- **Read/Grep/Glob over shell peeking.** Use the dedicated tools instead of Bash `cat`/`sed`/`head`
  pipelines; they bound output and keep transcripts lean.

### Enforcement (harness-executed, not model-dependent)
The rules above are enforced by a PreToolUse hook on `Bash|PowerShell|Read`
(`.claude/settings.json` → `scripts/hooks/token_guard.py`, tested in `tests/test_token_guard.py`):
- Foreground `produce.py image/video` and `atlas benchmark --live` calls are **denied**; re-issue
  with `run_in_background=true`. One-off override: append `# token-guard: allow-foreground`.
- Reading an individual image under `experiments/` when the run has `boards/` is **denied**;
  read the board, or crop the region to a file with `crop` in its name.
- Context >150K triggers a one-time phase-boundary reminder per session.
The guard fails open (a guard bug never blocks work). Verify spend with
`python scripts/token_audit.py [--days N | --session <id>]` — it reads the CC Switch proxy
billing DB (authoritative; transcript usage fields overcount 2-3x).
