# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this project is

Local AI short-drama production lab: script → storyboard → keyframes → video → voice → subtitles → MP4.
ComfyUI is **only** the generation engine. Python owns business state, scheduling, retries and quality gates. FFmpeg owns composition. The local LLM (8080) and VoxCPM2 TTS (50000) are external HTTP services.

Current state (2026-11-12):

- R0–R3 technical validation and the v1.0 spec set are complete. The Script-to-Film chain runs end to end: text → narration/storyboard → TTS → FLUX keyframes → Wan frames → clips → deterministic motion → `r3_build` → quality. Last accepted cut: 47.0 s / 1080×1920 / 24 fps, 6 subtitles aligned to narration, `quality.check_build` + `film_acceptance` PASS.
- Two style pipelines share one stack: A = ink wash (`oriental.ink_wash`), B = court green fine-line (`oriental.court_green_fine_line`). 23 Style Packs exist; all 23 reference boards are generated and pass objective checks, but **human aesthetic review is still PENDING** (ink/court are historical `REVIEWED/ACCEPTED`; A/B selection for 4 test shots approved 2026-11-04). Do not mark style quality `PASS_VERIFIED` without a human review record.
- Production capability is a 30–60 s vertical animatic/hybrid film: stills + deterministic camera moves + 1–2 pure-landscape Wan hero shots. Multi-shot all-Wan, building/character Wan motion, 2–5 min all-generated films, and same-face continuity are **BLOCKED**. Full status: `docs/ROADMAP.md`.
- Assets: 13 BGM tracks registered (6 Wikimedia Commons PD/CC BY are the picks; CC BY needs attribution), self-generated SFX, one APPROVED voice profile (`narrator_self` / `my_voice_clean_v2`). Commercial licensing is `NOT_RUN`.
- 2026-11-12: generated artifacts moved out of the checkout (`DRAMA_OUTPUT_ROOT`, default `D:\DramaStudio`); Git history rewritten to drop media; source moved to DDD layers; docs consolidated and 31 historical files archived.

Do not build ahead of the current stage; each stage must be executed on this machine and evidenced before the next starts.

## Hard environment invariants

1. **Two Python environments, never merged.**
   - Root `.venv` (Python 3.12, uv): orchestration only. **Never install torch here.**
   - `runtime/ComfyUI/.venv`: PyTorch XPU + ComfyUI + ComfyUI-GGUF. Never import it from `src/`.
2. **Model store is external** (`DRAMA_MODELS_ROOT`, default `D:/AI/models`). The diffusion GGUFs must stay at the **top level** because `本地 AI 服务\start_server.bat` scans only top-level `*.gguf`. Text encoders/VAEs go in `text_encoders\` and `vae\`; ComfyUI sees them via `extra_model_paths.yaml`.
3. **Do not modify** `本地 AI 服务\start_server.bat` / `bin-*` / `VoxCPM-Runtime`, or other projects' environments. Do not move existing top-level model files.
4. **Ports:** ComfyUI `8188`; local LLM `8080` (single port); VoxCPM2 `50000`; workspace `8765`.
   The project LLM is `Qwen3-30B-A3B-Instruct-2507`, CPU-only `-ngl 0`, `-c 65536` (64K, verified). Scheduled tasks must defer while 8080 is busy — never add a second LLM port or kill someone else's process.
5. **GPU tenants are exclusive** (8 GB A750): LLM, FLUX, Wan — one generation job at a time. The 8080 instance is CPU-only but holds ~19 GB RAM; never start a GPU-backed LLM while ComfyUI generates.
6. **Verified A750 behavior:** text encoders run on CPU; Wan **must use 20 steps** (10 steps gives rainbow artifacts); peak VRAM ≈ 5–6 GiB; ComfyUI auto-unloads after each prompt.
7. Local HTTP probes must bypass the system proxy: `httpx(..., trust_env=False)` in Python, `curl.exe` in PowerShell (`Invoke-RestMethod` returns 502 for localhost).

## Repository layout (read docs/REPO_LAYOUT.md)

Two roots, never mixed:

- **repo**: `src/`, `config/`, `docs/`, `tests/`, `workflows/`, `scripts/`, declared input registries.
- **output** (`DRAMA_OUTPUT_ROOT`, default `D:\DramaStudio`): `projects/`, `experiments/`, `style_boards/`, `logs/`, `literary_intelligence/runs/`, `workspace.db`.

Resolve paths only through `drama_studio.paths` (`repo_root`, `output_root`, `output_path`, `projects_root`, `experiments_root`, `style_boards_root`, `logs_root`, `project_dir`, `config_root`). Never join `ROOT / "projects"` in new code.

DDD layers:

```
src/drama_studio/
  domain/          contracts / style / voice / motion / film / aesthetics / bible   (pure rules)
  application/     film / voice / motion / operations / production / script_engine / quality
  infrastructure/  storage(store, discovery) / media / fonts / locks / envprobe
  interfaces/      cli / film_cli / http(api, film_api)
  web/  paths.py  config.py
```

Dependency direction: `interfaces → application → domain`; `application → infrastructure`. `domain` must not import outer layers (`tests/test_layering.py`). Old module paths remain as compatibility shims (module aliases); new code uses layer paths.

## Commands

```powershell
uv sync --python 3.12
.venv\Scripts\python.exe -m pytest                   # all tests + layering guards
.venv\Scripts\python.exe scripts\check_repo_hygiene.py
scripts\doctor.ps1

scripts\start.ps1                                    # ComfyUI 8188
scripts\llm_server.ps1 -Action start|status|stop     # LLM 8080, CPU-only
scripts\cosyvoice_server.ps1 -Action start|status|stop  # VoxCPM2 50000
.venv\Scripts\drama.exe serve --port 8765

.venv\Scripts\python.exe scripts\fetch_fonts.py --check
.venv\Scripts\drama.exe doctor --json

# Script-to-Film (CPU unless generating)
.venv\Scripts\drama.exe film init --project <id> --text <utf8.txt> --title "<title>" --duration 120
.venv\Scripts\drama.exe film script --project <id> --text <utf8.txt> --write-storyboard
.venv\Scripts\drama.exe film prompts --project <id>
.venv\Scripts\drama.exe film keyframes --project <id>
.venv\Scripts\drama.exe film wan-jobs --project <id> --profile safe8g
.venv\Scripts\python.exe scripts\wan_batch.py --project <id> --shots S02,S03
.venv\Scripts\drama.exe film clips --project <id>
.venv\Scripts\drama.exe film motion --project <id>
.venv\Scripts\drama.exe film voice --project <id>
.venv\Scripts\drama.exe film assemble --project <id>
.venv\Scripts\drama.exe film status --project <id> --write
.venv\Scripts\drama.exe film qc --project <id>
.venv\Scripts\drama.exe film approve --project <id> --kind final --decision approve --note "..."
.venv\Scripts\drama.exe film run --project <id>

# Style engine
.venv\Scripts\drama.exe style list
.venv\Scripts\drama.exe style show animation.xuanji_3d
.venv\Scripts\drama.exe style validate
.venv\Scripts\drama.exe style check-image --style <id> --image <png>

# Generation / assembly
.venv\Scripts\python.exe scripts\r1_batch.py --jobs <jobs.json> [--only <id> --force]
.venv\Scripts\python.exe scripts\r3_build.py --segments <json> --audio <json> --out <dir>
.venv\Scripts\python.exe scripts\motion_build.py --plan <json> --out <dir>
.venv\Scripts\python.exe scripts\static_quality.py --image <png> --style <id> --out <json>
.venv\Scripts\python.exe scripts\aesthetic_plan.py / aesthetic_compare.py
.venv\Scripts\python.exe scripts\make_sfx.py --out-dir <dir>
.venv\Scripts\python.exe scripts\fetch_bgm.py --out-dir <dir>
```

PowerShell scripts are UTF-8 **with BOM**; keep the BOM or PowerShell 5.1 garbles Chinese text.

## Working rules

- Never report `PASS_VERIFIED` without an executed artifact and log path. Downloading/installing is not proof of inference. CPU execution is `PASS_LIMITED`, never presented as GPU.
- Retries are bounded (max 2, backoff 30/90 s); no infinite loops; preserve failure logs.
- Keep seed, prompt, model hash and workflow hash with every asset. Rebuilds write a new `renders/build-<time>/` and never overwrite history.
- Do not upgrade ComfyUI/nodes or replace model files without re-running the relevant R0 checks; record versions in `logs/r0/engine-versions.txt`.
- **Wan:** resolution divisible by 32; 20 steps; 73 frames default (121 has colour drift); default profile `safe8g` 448×768/49 frames; do not rely on Wan for scripted subject movement or building/character shots.
- **Style rule:** styles are config, never code branches. Do not add style models/LoRAs or make preset auto-seeding. Run `static_quality.py` before animating; `motion.plan` requires per-shot `static_quality.json` unless `--skip-static-gate` is explicit.
- **Voice rule:** only `APPROVED` profiles in `config/voices.yaml` may enter production TTS; `zero_shot` only (SFT retired); per-line provenance goes to `audio_manifest.json.voice_cast`. `chant` is unsupported and refused.
- **Audio rule:** BGM/SFX come from `assets/audio/manifest.json`; only `VERIFIED`/`APPROVED` assets with a matching hash may enter a production mix. Never rip film/anime soundtracks.
- **Story rule:** `character_bible.yaml` / `shot_bible.yaml` + `story.check` validate references/coverage/style; they never claim same-face identity.
- **Workspace rule:** the UI never invents state. No file/task evidence means `NOT_RUN` / `UNKNOWN`. Execution only through registered task kinds. Rebuilds go to a new `projects/<project>/episodes/<episode>/renders/build-<time>/`.
- **LLM lifecycle:** one llama-server on 8080, one owner. `scripts/llm_server.ps1` starts/stops the project instance; `literary_intelligence/run_li15.py` stops only what it started. Never leave an idle server holding 8080.
- **Docs:** one fact in one place. Canonical docs are listed in `docs/README.md`; archived material lives in `D:\DramaStudio\archive\docs\<date>\` and is not tracked. Do not copy archived docs back into `docs/`.
- **Artifacts:** never commit media/model binaries or anything under the output root. `scripts/check_repo_hygiene.py` enforces tracked-file and size rules in CI.

## Architecture pointers

- `src/drama_studio/domain/contracts.py` — strict Pydantic data contracts (`extra="forbid"`, contiguous `shot_001…`, all references must resolve).
- `src/drama_studio/domain/style/` — Style Pack schemas, registry, prompt compiler, consistency metrics; `config/style_packs/<group>/<name>/` is the only style source.
- `src/drama_studio/application/film/` — project/screenplay/storyboard/timeline, keyframe and Wan jobs, clips, motion plan, segments, assemble, status, reviews.
- `src/drama_studio/application/operations/tasks.py` — workspace task registry (single-flight, prerequisites, bounded retries, logs).
- `src/drama_studio/infrastructure/storage/discovery.py` — derives state from real files; never guesses.
- `src/drama_studio/interfaces/http/` — FastAPI app and film API; `web/` is a build-free ES-module UI.
- `src/drama_studio/paths.py` — repo/output root resolution; `scripts/migrate_outputs.py` and `scripts/restructure_ddd.py` document the 2026-11-12 migrations.
- `docs/REPO_LAYOUT.md`, `docs/ENVIRONMENT.md`, `docs/PRODUCTION_GUIDE.md`, `docs/VISUAL_STYLE.md`, `docs/AUDIO_AND_LICENSING.md`, `docs/GUIDE.md`.
- `docs/PRD.md` is the requirements SSOT; `docs/DECISIONS.md` is the ADR log; `docs/ARCHIVE.md` indexes archived material.

Planned modules (not implemented; do not assume they exist): `comfy_client.py`, `generation/`, `storyboard/`, `character_manager/`, `audio/`, `subtitles/`, `editing/`, `storage/`, `orchestrator.py` as separate packages. Project/episode state lives in `D:\DramaStudio\projects\workspace.db`; shot target states remain `PENDING → IMAGE_GENERATING → IMAGE_REVIEW → VIDEO_GENERATING → VIDEO_REVIEW → AUDIO_READY → COMPLETED` plus failure/retry states, with human gates only at H1 character lock, H2 keyframe approval, H3 final cut.

## ComfyUI workflows

- Only **API-format** JSON in `workflows/`; placeholders like `{{seed}}` are whole-value strings replaced by JSON-tree traversal, preserving types. `scripts/r0_comfy_probe.py` is the reference implementation.
- Verified graphs: FLUX.3 Klein (`UnetLoaderGGUF` → `CLIPLoader(type=flux3, cpu)` → `Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced`); Wan2.2 TI2V 5B (`Wan22ImageToVideoLatent` 48-ch, `ModelSamplingSD3(shift=8)`, `uni_pc`/`simple`, CFG 5, 20 steps).
- Model switching needs no restart; `/free` is usually a no-op. Restart only to clear the execution cache or recover.
