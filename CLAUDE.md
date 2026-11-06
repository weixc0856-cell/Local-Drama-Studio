# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Local AI short-drama production lab: script → storyboard → character/scene assets → keyframes → video clips → voice → subtitles → MP4.

ComfyUI is **only** the generation engine. Python (`src/drama_studio`) owns business state, scheduling, retries and quality gates. FFmpeg owns composition. The local LLM (`D:\AI`) and VoxCPM2 TTS (`D:\AI\VoxCPM-Runtime`) are external HTTP services.

**Current state: R0-R3 technical validation is complete (`0204979`), v1.0 docs are committed (`ad921ed`), LI-1.6 is committed (`e21dc0d`), and the local workspace is implemented in the working tree. P0 baseline repair is applied. P1 production closure is implemented and executed on a short fixture: ContentPackage → LLM script/storyboard → parameterized TTS → FLUX jobs → segments → build → quality; final 14.0 s / 1080×1920 with 4 shots and female voice, quality PASS. Visual direction has converged to two independent pipelines (A = ink wash, B = court green fine-line) sharing one technical stack; S1 config is `PASS_STATIC`, and S2 plus first-batch pipeline A/B samples have technical checks passing while the static gate and human aesthetic review remain `PARTIAL`/PENDING. R3-D remaining: ambience/SFX licensing and commercial licensing; BGM plus basic SFX are now generated and registered; R4-R7 are intentionally not implemented. 2026-11-04 adds deterministic motion (camera easing, local micro-motion, crossfade/ink transitions) in `src/drama_studio/motion/`, driven only by `config/styles.yaml` motion policy and wired through `production.build_motion_plan` → `scripts/motion_build.py` → `segments --sequence` → `r3_build`; workspace tasks `motion.plan` / `motion.render`. Voice adds `narration` / `recitation` / `classical_recitation`, a phrase-level pronunciation layer, and per-line audio QA; real `chant` is unsupported and refused. The M1–M7 baseline (semantic protection, damped motion, temporal gates, transitions, smooth recitation, dual-style films) passed human review on 2026-11-04; keep `PARTIAL` for unverified extensions (Wan motion mask, chant, BGM/SFX, commercial licensing). 2026-11-04 also adds the shot aesthetic layer: six-dimension designs, A/B variants that differ on exactly one axis, config-driven style profiles, ordered prompt compilation, frozen snapshots, A/B contact sheets and risk metrics. `aesthetic.plan → comfy.batch → aesthetic.compare → aesthetic.review` is wired through the production chain and the workspace; the 4 test shots are `PARTIAL`, but the A/B selection was approved on 2026-11-04 (court `A/A`, ink `B/A`) and recorded in `production_baselines`; full-film aesthetic review is still pending. The 2026-11-04 later batch adds explicit Voice Profile / multi-voice (`config/voices.yaml`, `voice/profiles.py`, per-line `voice_profile`, `voice_cast.yaml`), multi-track audio (`voice/audio_assets.py`, `voice/audio_timeline.py`, `voice/mix.py`), Character/Shot Bible (`bible.py`, task `story.check`), a strict static gate (`motion.plan` requires `static_quality.json`; task `static.check`), and episode style locking (`style_lock.py`; snapshot `_style_lock` revision/hash/history; task-level style override rejected). The workflow page now derives package / static / aesthetic / motion nodes from real files, and `comfy.batch` can bind an `episode_id` to check `production_script.style_id` against the episode lock; `style_consistency.py` + task `style.consistency` add a cross-shot palette/LAB/luma/saturation/edge gate (technical OK is still PARTIAL until human review). `ScriptShot.type=video` + `video_prompt` now create Wan I2V jobs via `scripts/video_jobs.py`; `build_segments` can mix Wan clips with stills via `--clips --allow-partial-clips`; self-generated SFX (wind/water/chime/whoosh) are registered in the audio manifest. `PRD-TTS-001` is `PASS_VERIFIED`; `PRD-QUAL-001` is `IMPLEMENTED_NOT_VERIFIED`; AUDIO / `PRD-TTS-007` / VOICE-ASSET / MOTION / STORY / QA are now formal in `docs/PRD.md` §24 (approved 2026-11-04); implementation statuses still follow evidence. 2026-11-05 adds the two-minute acceptance plan (`ACCEPTANCE-2MIN-001`): three reference films were downloaded with yt-dlp and measured (shot counts, cut rhythm, grammar in `docs/REFERENCE_STUDY.md`); they are study material only, never audio or frames in our output. A 24-shot all-Wan ink film chain (`scripts/run_ink_film.py` -> keyframes -> Wan -> `assemble_ink_film.py`) is queued after the running 24-shot Shinkai Wan batch and uses the Wikimedia Commons PD/CC BY BGM set, which the user auditioned as "much better" (`review_status=ACCEPTED_PENDING_FINAL`). The 24-shot Shinkai film finished as an all-Wan 121.3 s cut (video and experiment directory removed in the 2026-11-06 cleanup; report text remains). 2026-11-06: 图像线切换为 FLUX.3 Klein（ADR-016；GGUF Q4_K_M、16 步、CFG 1.0、`workflows/flux3_t2i_api.json`；官方 9B 提示词放大器在本机不可用，改用本地 Qwen 生成英文 caption）；FLUX.2 工作流与 `scripts/m8_plates.py` 已从项目删除（权重也已删除）；语音目标后端改为 VoxCPM2（48 kHz，CPU RTF≈9.3，盲听 7/7 优于 CosyVoice2-0.5B，XPU 不可用；服务端口仍为 50000，适配层待服务契约）；Wan 视频线不变；MiniMax H3 为 `NOT_RUN`（不评测）。2026-11-06 新增 Script-to-Film 制作层 `src/drama_studio/film/`（严格 Schema、分镜规划、连续性检查、剪辑时间轴；CLI `drama film plan|timeline|validate`；示例项目 `projects/deng_guan_que_lou`），方法见 `docs/FILM_PRODUCTION_GUIDE.md`，需求见 PRD §25（`PRD-FILM-001..006`）。393 tests pass.** Do not build ahead of the current stage; each stage must be executed on this machine and evidenced before the next starts.

## Hard environment invariants

1. **Two Python environments, never merged.**
   - Root `.venv` (Python 3.12, uv): orchestration only. **Never install torch here.**
   - `runtime/ComfyUI/.venv`: PyTorch XPU + ComfyUI + ComfyUI-GGUF. Never import it from `src/`.
2. **Model store is `D:\AI\models`, outside this repo.** The two diffusion GGUFs must stay at the **top level** because `D:\AI\start_server.bat` scans only `%MODELS_DIR%\*.gguf`. New text encoders/VAEs go in `text_encoders\` and `vae\`; ComfyUI sees both through `extra_model_paths.yaml`.
3. **Do not modify** `D:\AI\start_server.bat` / `bin-*` / `VoxCPM-Runtime`, or other projects' environments. Do not move existing top-level model files.
4. **Ports:** ComfyUI `8188`; local LLM **`8080`** (single port); VoxCPM2 `50000`. The project owns 8080 while its llama-server runs. Scheduled tasks (e.g. daily `OpportunityRadar`) must detect the occupied port and defer until it is free — never add a second LLM port.
   The project LLM on `8080` is **`Qwen3-30B-A3B-Instruct-2507`** (`D:\AI\models\Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf`), CPU-only `-ngl 0`, `-c 65536` (64K context, verified usable 2026-11-03). `config/settings.yaml` names the served alias, not the file name.
5. **GPU tenants are exclusive** (8 GB A750): LLM, FLUX, Wan. One generation job at a time. The 8080 instance runs CPU-only (`-ngl 0`), so it does not take VRAM, but it holds ~19 GB of RAM; never start a GPU-backed LLM while ComfyUI is generating.
6. **Verified A750 behavior:** text encoders run on CPU (Qwen3-4B 7.67 GB explicit; UMT5 6.4 GB auto-offloaded). Wan **must use 20 steps** — 10 steps produces rainbow artifacts. Peak VRAM ≈ 5 GiB; ComfyUI auto-unloads after each prompt.
7. Local HTTP probes must bypass the system proxy: `httpx(..., trust_env=False)` in Python, `curl.exe` in PowerShell. `Invoke-RestMethod` returns 502 for localhost here.

## Commands

```powershell
# Orchestration env (idempotent, creates .venv)
uv sync --python 3.12

# Tests (root + literary intelligence; one command)
.venv\Scripts\python.exe -m pytest

# Reconstruct and verify local font OTFs (not stored in Git)
.venv\Scripts\python.exe scripts\fetch_fonts.py --check
.venv\Scripts\python.exe scripts\fetch_fonts.py
.venv\Scripts\python.exe -m pytest tests/test_models.py::test_storyboard_accepts_valid_contract -q

# Project LLM lifecycle: single port 8080, CPU-only, 64K; stop when the calls finish
scripts\llm_server.ps1 -Action start
scripts\llm_server.ps1 -Action status
scripts\llm_server.ps1 -Action stop

# Diagnostics (writes logs/doctor-*.json)
scripts\doctor.ps1
.venv\Scripts\drama.exe doctor --json

# P1 end-to-end acceptance (requires 8080/8188/50000 running; caller owns lifecycle)
.venv\Scripts\python.exe scripts\p1_e2e.py

# Script-to-Film production layer (CPU only, no generation)
.venv\Scripts\drama.exe film plan --project deng_guan_que_lou --beats projects/deng_guan_que_lou/beats.json
.venv\Scripts\drama.exe film timeline --project deng_guan_que_lou
.venv\Scripts\drama.exe film validate --project deng_guan_que_lou
.venv\Scripts\drama.exe film prompts --project deng_guan_que_lou
.venv\Scripts\drama.exe film keyframes --project deng_guan_que_lou
.venv\Scripts\drama.exe film wan-jobs --project deng_guan_que_lou --allow-missing
.venv\Scripts\drama.exe film voice --project deng_guan_que_lou   # needs VoxCPM2 on 50000
.venv\Scripts\drama.exe film assemble --project deng_guan_que_lou --dry-run

# Visual Style Engine
.venv\Scripts\drama.exe style list
.venv\Scripts\drama.exe style show oriental.ink_wash
.venv\Scripts\drama.exe style validate
.venv\Scripts\drama.exe style check-image --style oriental.ink_wash --image projects/deng_guan_que_lou/assets/keyframes/S01/S01_00002_.png

# Local production workspace: read-only derivation + restricted task registry (port 8765)
.venv\Scripts\drama.exe serve --port 8765

# Aesthetic plan + A/B (plan is CPU; generation uses comfy.batch, one GPU job at a time)
.venv\Scripts\python.exe scripts\aesthetic_plan.py --script <production_script.json> --style ink_wash --designs <designs.json> --out <aesthetic_plan.json>
.venv\Scripts\python.exe scripts\r1_batch.py --jobs <snapshot>/A/jobs_A.json --timeout 7200
.venv\Scripts\python.exe scripts\r1_batch.py --jobs <snapshot>/B/jobs_B.json --timeout 7200
.venv\Scripts\python.exe scripts\aesthetic_compare.py --plan <aesthetic_plan.json> --images <snapshot>/images --out <compare_dir>
.venv\Scripts\python.exe scripts\static_quality.py --image <png> --style <style> --aesthetic <shot_aesthetic.json> --out <static_quality.json>
.venv\Scripts\python.exe -m drama_studio.bible --script <production_script.json> --characters <character_bible.yaml> --shots <shot_bible.yaml> --voices config/voices.yaml --out <story_bible_report.json>
.venv\Scripts\python.exe scripts/fetch_bgm.py --out-dir assets/audio/bgm/keynata
.venv\Scripts\python.exe scripts/audio_asset_entry.py <file> --license <license> --source-platform <platform> --status APPROVED
.venv\Scripts\python.exe scripts/make_sfx.py --out-dir assets/audio/sfx
.venv\Scripts\python.exe scripts/video_jobs.py --script <script> --keyframes <images> --out <jobs_video.json>

# Ink 2-minute film: waits for the Shinkai Wan batch, then keyframes -> Wan -> assembly
.venv\Scripts\python.exe scripts/run_ink_film.py
.venv\Scripts\python.exe -m drama_studio.quality --aesthetic-motion <motion_manifest.json>

# Deterministic motion (CPU only; no FLUX/Wan)
.venv\Scripts\python.exe -m drama_studio.production --motion-plan --script <script> --images <images> --audio <audio_manifest> --out <motion_shots.json> --style ink_wash --regions <motion_regions.json> --align-audio --leading-ms 450 --tail-seconds 1.0
.venv\Scripts\python.exe scripts\motion_build.py --plan <motion_shots.json> --out <motion_dir>
.venv\Scripts\python.exe scripts\transition_probe.py --out experiments/mv/transition
.venv\Scripts\python.exe -m drama_studio.quality --audio-manifest <audio_manifest.json> --timeline <timeline.json>
D:\AI\VoxCPM-Runtime\venv\Scripts\python.exe -X utf8 scripts\tts_qa.py --manifest <audio_manifest.json>

# Generation engine (heavy first run: PyTorch XPU + ComfyUI deps)
scripts\setup.ps1 -WithComfyUI
scripts\start.ps1          # port 8188, waits for /system_stats
scripts\stop.ps1           # kills the ComfyUI process tree (venv launcher -> real child)

# R0-only probe: submit API workflow -> poll /history -> download outputs
.venv\Scripts\python.exe scripts\r0_comfy_probe.py `
  --workflow workflows\flux3_t2i_api.json `
  --params workflows\r0_flux_t2i_params.json --out logs\r0\run

# R1 batch: resume-friendly; each run writes run/job.json with provenance
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments\r1\jobs.json
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments\r1\jobs.json --only J1 --force
.venv\Scripts\python.exe scripts\r1_compare.py
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments\r2\jobs_r2a.json --timeout 7200
.venv\Scripts\python.exe scripts\r2_analyze_frames.py --run-dir experiments\r2\runs\A1
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments\r2b\jobs_r2b.json --timeout 7200
.venv\Scripts\python.exe scripts\r2b_track_boat.py --run-dir experiments\r2b\runs\H3
```

PowerShell scripts are UTF-8 **with BOM**; keep the BOM or PowerShell 5.1 will garble Chinese text.

## Architecture that requires reading multiple files

- `src/drama_studio/config.py` — discovers project root via `pyproject.toml`+`config/` (or `DRAMA_ROOT`), loads four YAMLs into Pydantic models, resolves relative paths, and carries exact model `sizes` so partial downloads cannot pass.
- `src/drama_studio/models.py` — **the data contract boundary**. Strict Pydantic (`extra="forbid"`). IDs are `char_001` / `loc_001` / `prop_001` / `shot_001`; a shot's ID must equal `shot_{index:03d}`, indexes are contiguous, and all references must resolve. Local LLM output must validate against `Storyboard` or the stage fails (max 2 repair attempts by design, not implemented yet).
- `src/drama_studio/content_package.py` — registered corpus + evidence-checked claims → strict `ContentPackage` (draft).
- `src/drama_studio/script_engine.py` — local LLM → strict `ProductionScript` (narration lines, shots, style-composed prompts), with bounded repair and raw responses retained.
- `src/drama_studio/style_presets.py` — strict `config/styles.yaml` loading for the two core styles (`court_green_fine_line`, `ink_wash`); exports workspace-style payloads but never writes `workspace.db`.
- `scripts/static_quality.py` — per-pipeline static defect gate (objective metrics + manual checklist JSON).
- `scripts/pipeline_ink.py` — pipeline A per-sample layers (cloud/water/boat/texture) with deterministic FFmpeg motion; `scripts/s2_build.py` covers the gongbi scroll and the earlier reveal build.
- `src/drama_studio/production.py` — `ProductionScript` → ComfyUI jobs and R3 `segments.json`; refuses missing images/audio.
- `src/drama_studio/quality.py` — independent blank/black image, decode, duration, audio-peak and final-hash checks.
- `src/drama_studio/voice/tts.py` — parameterized VoxCPM2 narration; shared by CLI and workspace task. Keeps source/display/TTS text layers apart and writes `pronunciation_report.json`; `zero_shot` only (`sft` retired), per-line `voice_profile`, and `voice_cast.yaml`.
- `src/drama_studio/voice/pronunciation.py` / `recitation.py` — phrase-level reading lexicon (`config/pronunciation.yaml`) and recitation modes; no pitch/phoneme control exists.
- `src/drama_studio/voice/profiles.py` — strict Voice Profile / Voice Cast contracts; only `APPROVED` profiles enter production; one backend per run.
- `src/drama_studio/voice/audio_assets.py` / `audio_timeline.py` / `mix.py` — single audio asset registry, multi-track timeline, and FFmpeg ducking/SFX mix.
- `src/drama_studio/bible.py` — Character/Shot Bible continuity checks; explicitly does not promise same-face identity.
- `src/drama_studio/style_lock.py` — episode-level style hash/revision/history; tasks cannot override a locked style.
- `src/drama_studio/motion/` — camera easing, authored-region local micro-motion, and mask-based transitions. `spec.py` resolves style policy; `render.py` builds one FFmpeg graph per shot and assembles a duration-preserving sequence; `transition.py` builds procedural masks.
- `src/drama_studio/style_engine/` — Visual Style Engine: 12 loadable Style Packs under `config/style_packs/<group>/<name>/` (retro 4, oriental 3, artistic 5), strict schemas, registry with id/version validation, FLUX/Wan prompt compiler with per-style camera enforcement, and objective consistency checks (palette LAB, saturation, edge density, letterbox, sequence drift). Guide: `docs/VISUAL_STYLE_ENGINE.md`.
- `src/drama_studio/film/` — Script-to-Film production layer: strict Pydantic contracts for `project.json`, `screenplay.json`, `narration.json`, `visual_bible.yaml`, `storyboard.json`, `timeline.json`; beat→storyboard planner, continuity checks, edit timeline. Never calls ComfyUI. Guide: `docs/FILM_PRODUCTION_GUIDE.md`.
- `src/drama_studio/aesthetics.py` — six-dimension shot design, A/B variant invariant, style profiles, ordered prompt compiler. `config/styles.yaml` `aesthetic_profile` is the only style-specific source; no style-id branch in code.
- `scripts/aesthetic_plan.py` / `scripts/aesthetic_compare.py` — freeze A/B snapshots + jobs, then build contact sheets and risk metrics. FLUX.2 negative conditioning is zeroed with CFG 1.0: negatives are recorded but not control; use positive constraints.
- `src/drama_studio/workspace/` — local workspace backend: SQLite state (`projects/workspace.db`), derived production state (`discovery.py`), safe media/Range/thumbnails (`media.py`), restricted task registry + single-flight runner (`tasks.py`), FastAPI app (`api.py`). `src/drama_studio/web/` is a build-free ES-module UI served at `/static`.
- `src/drama_studio/doctor.py` — emits `PASS_VERIFIED / PASS_LIMITED / FAIL / NOT_RUN` with evidence. It never guesses: unimplemented services are `NOT_RUN`.
- `docs/ARCHITECTURE.md` — the full target design: SQLite state machine, ComfyUI protocol, prompt locking, GPU rules, FFmpeg pipeline. Implemented modules are only those listed above; everything else there is planned.
- `docs/README.md` — product docs vs technical evidence index; status vocabulary.
- `docs/PRD.md` — v1.0 positioning, scope, non-goals, risks; read before proposing features.
- `docs/TECH_STACK.md` — frozen stack, versions, licenses, performance baseline.
- `docs/CONTENT_SPEC.md` — visual/audio/video/subtitle specs.
- `docs/PRODUCTION_WORKFLOW.md` — 14-step flow and what is actually implemented.
- `docs/PLATFORM_PUBLISHING_SPEC.md` — Douyin/Xiaohongshu packaging and compliance.
- `docs/ASSET_AND_LICENSE_REGISTRY.md` — model/asset/font/music licenses.
- `docs/QUALITY_AND_METRICS.md` — quality gates, cost, platform metrics, status vocabulary.
- `docs/ROADMAP.md` — M3 洛神赋, M4 platform test, v1.1.
- `docs/R0_TEST_REPORT.md` — R0 measured facts and limits. Read §6 before proposing R1/R2 work.
- `docs/R1_TEST_REPORT.md` — R1 assets, reference-edit results, consistency limits, and the /32 constraint for Wan.
- `docs/R2_TEST_REPORT.md` — R2-A measured cost/quality; 73 frames is the default, 121 has color drift.
- `docs/CONTENT_PACKS.md` — shared layer vs per-theme content pack; do not hardcode one poem in code.
- `docs/VISUAL_STYLE_SPEC.md` — the two core aesthetics (court green fine-line, ink wash), config boundary, six deterministic animation primitives, S1-S3 validation plan.
- `docs/R2B_TEST_REPORT.md` — four hero shots; H2 is usable, H3 subject motion direction was wrong.
- `docs/R3_TEST_REPORT.md` — vertical 576×1024 capability and a 38 s 1080×1920 finished piece; 43.8 min end-to-end; committed as `0204979`.
- `docs/ROADMAP.md` — R3-D (female voice/font/BGM/SFX selection) is the gate before a second full sample; fonts/subtitles are done, female voice is auditioned and decided but not in a final cut. BGM has 13 registered tracks: five Keynata tracks are `REJECTED` after the 2026-11-05 "陰間" feedback, and six Wikimedia Commons recordings (four public domain, two CC BY 3.0 US requiring attribution) are the current picks; human listening is still PENDING. SFX are self-generated; commercial licensing is `NOT_RUN`.

Planned modules (not implemented; do not assume they exist): `comfy_client.py`, `generation/`, `storyboard/`, `character_manager/`, `audio/`, `subtitles/`, `editing/`, `storage/`, `orchestrator.py`.

Project state model: `projects/workspace.db` stores projects/episodes/styles/tasks; production state is derived from real files/manifests. The earlier per-project `state.db` / `ProjectManifest` design is not implemented and is not authoritative. Shot-level target states when implemented: `PENDING → IMAGE_GENERATING → IMAGE_REVIEW → VIDEO_GENERATING → VIDEO_REVIEW → AUDIO_READY → COMPLETED`, plus `FAILED`, `NEEDS_REVIEW`, `RETRY_PENDING`, `CANCELLED`. Human gates only at H1 character lock, H2 keyframe approval, H3 final cut.

## ComfyUI workflows

- Only **API format** JSON in `workflows/`; placeholders like `{{seed}}` are whole-value strings replaced by JSON-tree traversal, preserving types. `scripts/r0_comfy_probe.py` is the reference implementation but is R0 test code, not the production client.
- Bundled official templates in `runtime/ComfyUI/.venv/Lib/site-packages/comfyui_workflow_templates_json/templates/` are the source of truth for node parameters.
- Verified R0 graphs:
  - FLUX.2 klein: `UnetLoaderGGUF` → `CLIPLoader(type=flux2, device=cpu)` → `Flux2Scheduler` + `CFGGuider(1.0)` + `SamplerCustomAdvanced`; no `FluxGuidance`.
  - Wan2.2 TI2V 5B: `Wan22ImageToVideoLatent` (48-ch), `ModelSamplingSD3(shift=8)`, `uni_pc`/`simple`, CFG 5, 20 steps.
  - FLUX.2 reference/edit: `LoadImage → VAEEncode → ReferenceLatent(conditioning, latent)` with `EmptyFlux2LatentImage`, `Flux2Scheduler`, `CFGGuider(1.0)`; verified at 768×432 on Q4/XPU.
- R1 asset layout: `assets/visual_style/` (style bible, master reference, scenes, comparison sheet), `assets/keyframes/` (four 16:9 keyframes + `*.meta.json` + `relationships.json`), raw runs in `experiments/r1/runs/<job>/job.json`.
- Model switching does not need a restart; `/free` is usually a no-op because models auto-unload. Restart only to clear the execution cache or recover.

## Working rules

- Never report `PASS_VERIFIED` without an executed artifact and log path. Downloading or installing is not proof of inference.
- Never present CPU execution as GPU execution; mark it `PASS_LIMITED` with the reason.
- Retries are bounded (max 2, backoff 30/90 s); no infinite loops. Preserve failure logs.
- Do not upgrade ComfyUI/nodes or replace model files without re-running the relevant R0 checks; record versions in `logs/r0/engine-versions.txt`.
- Keep seed, prompt, model hash and workflow hash with every asset.
- Pin the goal to a 30-45 s, 3-5 shot episode; measured budget is ~7-10 h of generation per episode.
- Keyframe consistency: use the J2 reference (`assets/visual_style/reference/style_ref_river_16x9.png`) and `ReferenceLatent`; repeated prompts alone are not consistency evidence.
- **Wan video resolution must be divisible by 32.** Keyframes are 768×432 (432/32=13.5), so R2 uses 1024×576 (16:9) before I2V.
- **R2-A measured:** 1024×576 / 73 frames ≈ 40-43 min per 3 s shot; 121 frames ≈ 66-69 min per 5 s shot; peak VRAM ≤6.12 GiB. Default to 73 frames. A4 (flower, 121 frames) showed a visible green color drift; always check first/last frames.
- **Production shape:** don't run Wan on every shot. Budget 4-6 Wan hero shots per 90 s, with stills + slow pan/zoom for the rest (~4-5 h vs ~20 h all-Wan).
- **Style rule:** two independent pipelines share one technical stack: pipeline A = `ink_wash`, pipeline B = `court_green_fine_line`, both defined in `config/styles.yaml` and selected by id. Do not add style branches in code, new style models/LoRAs, or preset auto-seeding into `workspace.db`. Run `scripts/static_quality.py` before animating a still; it records two separate defect checklists. `production.build_motion_plan` now requires a per-shot `static_quality.json` unless `--skip-static-gate` is explicit. Do not mark style quality `PASS_VERIFIED` until a human review is recorded.
- **Voice rule:** only `APPROVED` voice profiles in `config/voices.yaml` may enter a production TTS run; `sft` and `zero_shot` cannot mix in one run; per-line provenance goes to `audio_manifest.json.voice_cast`.
- **Audio rule:** BGM/SFX use `assets/audio/manifest.json` and `audio_timeline.json`; only `VERIFIED`/`APPROVED` assets with a hash may enter a production mix. The old narration-only build path remains the default when no timeline is supplied.
- **Story rule:** `character_bible.yaml` / `shot_bible.yaml` + `story.check` validate references/coverage/style; they never claim same-face identity.
- **R3 measured:** vertical FLUX 576×1024 is 22-53 s/image; vertical Wan 576×1024 / 73 frames is 36.4 min at 5.48 GiB. A 38 s 1080×1920 piece with 5 stills + 1 Wan + 7 TTS lines took 43.8 min end-to-end. 1080×1920 is FFmpeg Lanczos upscale, not native.
- **R2-B measured:** 4 hero shots 32.6-46.4 min each, peak 5.50-5.66 GiB. Slow push-in (H2) works. Precise subject displacement (H3 boat) is unreliable: 24.6 px but toward the camera, not away. Do not rely on Wan for scripted subject movement; use compositing or change the shot.
- **Voice scope (2026-11-06):** the runtime is VoxCPM2 with reference-voice cloning (48 kHz). The old CosyVoice SFT presets (「中文男」/「中文女」) are retired historical evidence only; do not describe them as available. Model/voice/commercial terms are separate checks.
- **R3-D:** fonts/subtitle integration are done; female voice is auditioned and decided but not in a final cut; BGM is registered (Commons PD/CC BY classical set; human listening PENDING), SFX are self-generated, commercial licensing is `NOT_RUN`. Never rip film/anime soundtracks into the asset registry.
- **Workspace rule:** the UI must never invent state. Any value without file or task evidence is `NOT_RUN` / `UNKNOWN`; execution only through the registered task kinds; rebuilds write to a new `projects/<project>/episodes/<episode>/renders/build-<time>/` directory and never overwrite `experiments/r3b/renders`. Workspace runs on port 8765, not an LLM port.
- **LLM lifecycle:** one llama-server on 8080, one owner. `scripts/llm_server.ps1` starts/stops the project instance; `literary_intelligence/run_li15.py` starts it only when down and stops it only if that run started it. Never leave an idle server holding 8080 — the daily task waits for it.
