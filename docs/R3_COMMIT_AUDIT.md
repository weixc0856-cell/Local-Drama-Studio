# R3 提交前审查

> 审查日期：2026-11-03
> 范围：R3-A/B/C 报告、成片、字幕、脚本、竖屏资产与实验数据。
> 约束：不提交、不运行生成、不改工作流/模型/生产脚本、不删除历史数据。

## 1. 结论

| 项目 | 结果 |
|---|---|
| R3-A/B/C 报告与文件对应 | ✅ 一致 |
| 成片/字幕/脚本/资产索引 | ✅ 完整 |
| R3 测试数据与报告 | ✅ 一致（抽查 V1/V2/V5/V6/V7/V3 与最终成片） |
| 是否误含模型/缓存 | ✅ 无 |
| 是否误含原始帧 | ✅ 原始帧均被 `.gitignore` 排除 |
| 临时文件 | ⚠️ `renders/concat.txt`、`renders/final_check_3s.png` 未被忽略，**不得提交** |
| 是否可独立提交 | ✅ 可以；需显式排除上述 2 个临时文件，且不要把 README/CLAUDE 混入 |

**R3 证据链完整，可以形成独立提交；当前不能直接 `git add experiments/r3b`，否则会带入 2 个临时文件。**

## 2. 应包含的文件

### 文档

```text
docs/R3_TEST_PLAN.md
docs/R3_TEST_REPORT.md
docs/R3_COMMIT_AUDIT.md      # 本文件
docs/ENVIRONMENT.md          # R3 实测数据（已修改）
.gitignore                   # R2/R3 帧与中间产物规则（已修改）
```

### 竖屏资产

```text
assets/vertical/index.json
assets/vertical/01_river_dusk.png
assets/vertical/02_flower_forest.png
assets/vertical/03_distant_mountains.png
assets/vertical/04_lone_boat.png
assets/vertical/05_dawn.png
assets/vertical/06_flower_pushin_wan.mp4
```

### R3-A 实验

```text
experiments/r3a/jobs_flux.json
experiments/r3a/jobs_flux_extra.json
experiments/r3a/jobs_wan.json
experiments/r3a/*_manifest.json
experiments/r3a/params/V1,V2,V3,V5,V6,V7.json
experiments/r3a/runs/V{1,2,3,5,6,7}/{job,run,history,workflow.submitted}.json
experiments/r3a/runs/V3/{clip.mp4,quality.json}
experiments/r3a/flux_batch.out / flux_extra.out / wan_batch.out
```

### R3-B 实验与成片

```text
experiments/r3b/narration.json
experiments/r3b/audio_manifest.json
experiments/r3b/segments.json
experiments/r3b/audio/line_01..07.wav (+ raw)
experiments/r3b/renders/final_9x16.mp4
experiments/r3b/renders/final_9x16_burned.mp4
experiments/r3b/renders/drama.srt
experiments/r3b/renders/drama.ass
experiments/r3b/renders/build_manifest.json
experiments/r3b/tts.log / build.log（若希望保留）
```

### 脚本

```text
scripts/r3_tts.py
scripts/r3_build.py
```

## 3. 必须排除的文件

| 文件/模式 | 原因 |
|---|---|
| `experiments/r3b/renders/concat.txt` | FFmpeg 临时 concat 列表，可重建 |
| `experiments/r3b/renders/final_check_3s.png` | 人工抽帧临时检查图，可重建 |
| `experiments/r3a/runs/*/*_[0-9][0-9][0-9][0-9][0-9]_.png` | 原始帧，已忽略 |
| `experiments/r3b/renders/frame_*.png` | 抽帧，已忽略 |
| `experiments/r3b/renders/segments/` | 中间片段，已忽略 |
| `experiments/r3b/renders/video_raw.mp4` | 中间视频，已忽略 |
| `experiments/r3b/renders/video_faded.mp4` | 中间视频，已忽略 |
| `experiments/r3b/renders/mixed.wav` | 中间混音，已忽略 |
| `logs/`、`*.log` | 日志，已忽略 |
| 任何模型文件（GGUF/SafeTensors/CKPT） | 模型仓库外置，禁止入 Git |

排除后 R3 实验/资产/脚本候选约 **72 个、约 55.6 MB**（含两个成片约 38.7 MB；另加 R3 文档）。

## 4. 数据一致性抽查

### R3-A

| Job | 报告耗时 | job.json | 报告峰值 | job.json | 帧数 |
|---|---|---|---|---|---|
| V1 | 52.9 s | 52.92 | 2.63 GiB | 2.63 | 1 图 |
| V2 | 24.1 s | 24.14 | 2.79 GiB | 2.79 | 1 图 |
| V5 | 22.1 s | 22.11 | 2.79 GiB | 2.79 | 1 图 |
| V6 | 22.2 s | 22.19 | 3.53 GiB | 3.53 | 1 图 |
| V7 | 22.2 s | 22.19 | 2.79 GiB | 2.79 | 1 图 |
| V3 | 2185.0 s | 2184.99 | 5.48 GiB | 5.48 | 73 帧 |

### R3-B 成片

| 项 | 报告 | 实际 |
|---|---|---|
| 时长 | 38.042 s | 38.0417 s |
| 分辨率 | 1080×1920 | 1080×1920 |
| 帧率/帧数 | 24fps / 913 | 24fps / 913 |
| 视频/音频/字幕流 | H.264 + AAC + mov_text | 一致 |
| 全帧解码 | 0 | 0（软字幕与烧录版均 0） |
| 音频 | mean -17.7 dB / max -1.4 dB | 一致 |
| 成片哈希 | — | `fbf2b9430465ae99…`（build_manifest） |

- 7 句朗诵总语音 29.99 s；句首时间与 SRT/ASS 一致。
- 竖屏资产索引包含 5 张静帧 + 1 段 Wan，哈希存在。
- 没有使用 H3 主体位移镜头；孤舟为静帧推拉，与 R2-B 结论一致。

## 5. 跨提交依赖

`README.md`、`CLAUDE.md` 同时包含：

- R3 的状态/命令/结论；
- v1.0 产品定位与文档地图。

因此**不能把 README/CLAUDE 干净地放进 R3 单独提交**：

- 方案 A（推荐）：R3 提交不包含 README/CLAUDE；v1.0 提交统一包含它们。代价是 R3 提交后 README 暂时不显示 R3，但 R3 文档自洽。
- 方案 B：用 hunk 级 `git add -p` 拆分，操作复杂且容易出错。
- 不建议把 README/CLAUDE 整体塞进 R3 提交，否则 v1.0 内容提前进入历史。

`docs/ARCHITECTURE.md` 只含 v1.0 的编号说明，归 v1.0 提交。

## 6. 建议的提交边界（未执行）

```text
R3 提交：
  docs/R3_TEST_PLAN.md
  docs/R3_TEST_REPORT.md
  docs/R3_COMMIT_AUDIT.md
  docs/ENVIRONMENT.md
  .gitignore
  assets/vertical/
  experiments/r3a/
  experiments/r3b/（排除 renders/concat.txt、renders/final_check_3s.png）
  scripts/r3_tts.py
  scripts/r3_build.py
```

建议提交信息：

```text
feat(r3): add vertical capability test and 38s finished short

- 576x1024 FLUX/Wan capability test
- 38.04s 1080x1920 piece with CosyVoice narration and subtitles
- 43.8 min end-to-end cost recorded
- vertical assets and build scripts
```

## 7. 安全提交条件

| 条件 | 结果 |
|---|---|
| R3 报告/数据/产物一致 | ✅ |
| 无模型/缓存/原始帧 | ✅ |
| 临时文件已排除 | ⚠️ 需显式排除 2 个文件 |
| 工作流未被改动 | ✅ |
| 可独立 revert | ✅ |
| 是否可立即提交 | ✅ 可以（按 §6 边界）；**本次未提交** |

**结论：R3 具备独立提交条件，但提交时必须显式排除 `concat.txt` 与 `final_check_3s.png`，并避免把 README/CLAUDE 混入。**
