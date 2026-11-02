# 系统设计

> 状态：设计稿。R0 只实现配置、数据契约与 `doctor`；下述 R1-R7 组件在对应阶段验收后才落地。

## 1. 目标与非目标

### 目标

把一部短剧拆成**可独立生成、独立重试、独立验收**的镜头，由 Python 调度本地模型完成重复劳动，只在三个位置让人介入：

1. **人物定妆确认** —— 角色参考图锁定。
2. **首帧批量确认** —— 视频生成前先审所有静态首帧。
3. **最终成片验收** —— 技术合格不等于内容合格。

### 非目标

- 不做网页后台、不做多 Agent 编排、不做向量数据库。
- 不追求首阶段的电影级人物一致性、口型同步、长镜头连续运动。
- 不在 8GB 显存上并行加载多个生成模型。

---

## 2. 系统边界

```text
┌──────────────────────────── Local-Drama-Studio（Python 调度层） ────────────────────────────┐
│                                                                                            │
│  script_engine ──► storyboard ──► generation ──► audio ──► subtitles ──► editing ──► MP4   │
│       │                │              │             │                       │               │
│       ▼                ▼              ▼             ▼                       ▼               │
│  D:\AI llama.cpp   Pydantic       ComfyUI HTTP    CosyVoice            FFmpeg               │
│  (OpenAI API)      契约 + SQLite   + WebSocket     HTTP                 subprocess           │
│                                        │                                                   │
│                                        ▼                                                   │
│                              runtime/ComfyUI/.venv                                         │
│                              PyTorch XPU + GGUF                                            │
│                              FLUX.2 klein / Wan2.2                                         │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

边界规则：

- Python 调度层**不 import torch**，只通过 HTTP/WebSocket 和子进程操作外部引擎。
- ComfyUI **不承担业务状态**：不存分镜、不管重试、不管人物资产版本。
- FFmpeg 是唯一合成工具，不引入 MoviePy/Remotion。
- 本地 LLM 与 TTS 复用 `D:\AI` 已有运行时，不重复安装。

---

## 3. 端到端流水线

| 阶段 | 名称 | 输入 | 输出 | 人工门 |
|---|---|---|---|---|
| S0 | 建项目 | 标题 / 原始故事 | 项目目录、`state.db` | — |
| S1 | 剧本结构化 | `input/story.md` | `script/storyboard.json`（通过 Schema） | — |
| S2 | 角色/场景资产 | storyboard | `assets/characters/*`、`assets/locations/*` | **H1 定妆确认** |
| S3 | 分镜首帧 | storyboard + 资产 | `shots/shot_xxx/keyframe.png` | **H2 首帧确认** |
| S4 | 视频片段 | 已批准首帧 | `shots/shot_xxx/clip.mp4` | — |
| S5 | 配音 | 对白行 | `audio/dialogue/*.wav` | — |
| S6 | 字幕 | 对白 + 实际音频时长 | `subtitles/drama.srt` / `.ass` | — |
| S7 | 剪辑 | 片段 + 音轨 + 字幕 | `renders/final.mp4` | **H3 成片验收** |
| S8 | 归档 | 全部产物 | `manifest.json` + 质量报告 | — |

关键顺序约束：

1. **先出全部首帧，再审，再批量出视频。** 避免生成完 10 段视频后才发现人物衣服不一致。
2. 每个镜头是独立任务，失败只重跑该镜头。
3. 配音在视频之后、剪辑之前：以实际视频时长和音频时长共同决定镜头时间轴。

---

## 4. 数据契约

编码在 [src/drama_studio/models.py](../src/drama_studio/models.py)，Pydantic 严格模式（`extra="forbid"`）。

### 4.1 命名

| 实体 | 规则 | 示例 |
|---|---|---|
| 角色 | `char_\d{3}` | `char_001` |
| 场景 | `loc_\d{3}` | `loc_001` |
| 道具 | `prop_\d{3}` | `prop_001` |
| 镜头 | `shot_\d{3}` | `shot_001` |

ID 是跨阶段、跨文件的唯一键。禁止用中文名、随机 UUID 或数组下标作为键。

### 4.2 Storyboard

```json
{
  "title": "最后一通电话",
  "logline": "深夜接到去世三年的父亲来电。",
  "duration_target_seconds": 45,
  "style": "cinematic, realistic",
  "characters": [
    {
      "id": "char_001",
      "name": "男主",
      "age": 32,
      "appearance": "黑色短发，深色外套",
      "wardrobe": "深灰色家居服",
      "voice_id": "male_01"
    }
  ],
  "locations": [
    { "id": "loc_001", "name": "公寓客厅", "description": "深夜，只有手机屏幕的光", "time_of_day": "night" }
  ],
  "props": [],
  "shots": [
    {
      "shot_id": "shot_001",
      "index": 1,
      "character_ids": ["char_001"],
      "location_id": "loc_001",
      "prop_ids": [],
      "duration_seconds": 5,
      "camera": "close-up",
      "action": "男人看着手机，表情逐渐惊讶",
      "dialogue": "喂？",
      "image_prompt": "…",
      "video_prompt": "…",
      "status": "PENDING",
      "notes": ""
    }
  ]
}
```

校验规则（已实现并有测试）：

- 所有 ID 格式合法且唯一。
- `shot_id` 必须等于 `shot_{index:03d}`；`index` 从 1 连续递增。
- 镜头的 `character_ids` / `prop_ids` / `location_id` 必须指向已声明实体。
- 单镜头 1-15 秒；目标片长 10-180 秒；镜头数 1-40。

LLM 输出不合法时：**校验 → 把错误信息回喂 → 最多修复 2 次 → 仍失败则整阶段失败并保留原始输出**。绝不让自由文本进入下游。

---

## 5. 项目目录与状态库

```text
projects/demo_drama/
├─ project.yaml                 # 用户输入 + 本项目覆盖配置
├─ input/story.md               # 原始故事
├─ script/
│  ├─ storyboard.json           # 唯一结构化剧本
│  ├─ storyboard.raw.json       # LLM 原始输出（排错用）
│  └─ storyboard.review.json    # 校验/修复记录
├─ assets/
│  ├─ characters/char_001/
│  │  ├─ sheet.png              # 定妆四视图（H1 锁定）
│  │  ├─ front.png / side.png
│  │  └─ meta.json              # prompt / seed / model / sha256
│  ├─ locations/loc_001/
│  └─ props/
├─ shots/shot_001/
│  ├─ keyframe.png
│  ├─ keyframe.meta.json
│  ├─ clip.mp4
│  ├─ clip.meta.json
│  └─ review.json               # 自动检查 + 人工结论
├─ audio/
│  ├─ dialogue/shot_001_line_01.wav
│  ├─ bgm/
│  └─ timing.json               # 对白与镜头的实际时间轴
├─ subtitles/drama.srt
├─ renders/final.mp4
├─ state.db
└─ manifest.json
```

### SQLite 表

```sql
PRAGMA journal_mode = WAL;

CREATE TABLE projects (
  project_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  stage TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE shots (
  shot_id TEXT PRIMARY KEY,
  idx INTEGER NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  keyframe_path TEXT,
  clip_path TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,              -- image | video | tts | render
  target TEXT NOT NULL,            -- shot_001 / char_001 / final
  status TEXT NOT NULL,            -- queued | running | succeeded | failed | cancelled
  prompt_id TEXT,                  -- ComfyUI prompt_id
  params_json TEXT NOT NULL,
  workflow_sha256 TEXT,
  started_at TEXT,
  finished_at TEXT,
  exit_code INTEGER,
  error TEXT,
  log_path TEXT
);

CREATE TABLE assets (
  asset_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  target TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  prompt TEXT,
  negative_prompt TEXT,
  seed INTEGER,
  model TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  entity TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT,
  detail TEXT
);
```

`state.db` 是唯一权威状态；`manifest.json` 是从它导出的只读摘要。

---

## 6. 镜头状态机与失败恢复

```text
PENDING
  └─► IMAGE_GENERATING ─► IMAGE_REVIEW ─┬─► VIDEO_GENERATING ─► VIDEO_REVIEW
                                          │                          │
                                          │                          ├─► AUDIO_READY ─► COMPLETED
                                          │                          │
                                          └─ 拒绝 ─► NEEDS_REVIEW    └─ 拒绝 ─► NEEDS_REVIEW

任何生成中状态 ──► FAILED ──(attempts < 2)──► RETRY_PENDING ──► 对应 GENERATING
FAILED ──(attempts >= 2)──► NEEDS_REVIEW
任意非终态 ──► CANCELLED
```

规则：

- `attempts` 在每次真正提交生成任务时 +1，缓存命中不计。
- 最多 2 次自动重试，退避 30s / 90s；**不做无限重试**。
- OOM、模型加载失败不自动降分辨率：保留日志，转 `NEEDS_REVIEW`，由人决定改参数。
- 超时即失败，超时阈值写入 `config/generation.yaml`。
- 每次状态迁移写 `events`，可在 `drama doctor` / `drama resume` 中回溯。

`drama resume` 的语义：读取 `shots.status`，只会执行未到达目标终态的镜头；已完成的镜头直接复用 `clip.mp4` 与缓存键。

---

## 7. ComfyUI 集成协议

### 7.1 使用的接口

| 接口 | 用途 |
|---|---|
| `POST /prompt` | 提交 API 格式工作流，返回 `prompt_id` |
| `GET /queue` | 确认排队与运行状态 |
| `GET /history/{prompt_id}` | 取执行结果、输出文件名、错误 |
| `GET /view?filename=…&subfolder=…&type=output` | 下载产物 |
| `WS /ws?clientId=…` | 实时进度 / `execution_error` |
| `POST /interrupt` | 取消当前任务 |
| `POST /free` | `{"unload_models": true, "free_memory": true}`，切换模型族前释放显存 |

每个 `prompt_id` 的 `/history` 原始 JSON 与最终工作流 JSON 一起归档到 `logs/comfyui/`，作为复现证据。

### 7.2 工作流

- 工作流必须是 **API 格式**（ComfyUI 菜单 `Save (API Format)`），不是 UI 格式。
- 文件命名：`workflows/flux_character_api.json`、`workflows/flux_keyframe_api.json`、`workflows/wan_i2v_api.json`、`workflows/wan_t2v_api.json`。
- 参数化：占位符放在节点 `inputs` 的值里，例如 `"seed": "{{seed}}"`、`"text": "{{positive_prompt}}"`。调度层做 **JSON 树遍历替换**，不做字符串拼接，避免引号/中文转义破坏 JSON。
- 每个工作流与其模型文件 sha256、ComfyUI commit、节点版本一起登记；模型或节点升级后，旧工作流必须重新验收。

### 7.3 模型加载策略

- 图像阶段只加载 FLUX.2；视频阶段只加载 Wan2.2。
- 切换族之前调用 `/free`，并比对 `/system_stats` 的显存回收；若未回收，重启 ComfyUI 而不是继续叠加。
- 全局生成并发固定为 1（`limits.max_concurrent_generation_jobs`）。

---

## 8. 提示词与人物一致性

### 8.1 人物资产

每个角色生成并锁定一张**定妆参考图**，记录：

```json
{
  "character_id": "char_001",
  "locked": true,
  "prompt": "…",
  "negative_prompt": "…",
  "seed": 123456,
  "model": "flux-2-klein-4b-Q4_K_M",
  "model_sha256": "…",
  "reference_path": "assets/characters/char_001/sheet.png",
  "sha256": "…"
}
```

### 8.2 一致性的现实边界

仅重复提示词无法保证跨镜头完全一致。项目采用三层策略：

1. **固定描述词**：角色的 appearance/wardrobe 由资产文件拼进每条提示词，不由 LLM 每镜头自由发挥。
2. **参考图条件**：首帧生成优先把锁定的角色图作为图像参考/编辑输入（FLUX.2 klein 的图生图能力），而不是只靠文字。
3. **人工门 H1/H2**：接受"同一角色、服装与气质稳定"，不接受"每镜头换一张脸"。

**明确不承诺**：像素级同一张脸、任意角度、任意光照。R5 的验收标准是"多镜头可辨认且服装连续"，不是电影级。

### 8.3 提示词组装

```text
[global style] + [character bible tokens × N] + [location description]
+ [shot.camera] + [shot.action] + [lighting/time] + [consistency suffix]
```

负面提示词统一维护在配置中；FLUX.2 klein 按官方参数 **CFG 1.0、4 步、euler/simple**，默认不加负面提示词，需要时单独开实验分支，不混入主流程。

---

## 9. 显存租约（8GB 的核心约束）

三个 GPU 租户**互斥**：

| 租户 | 服务 | 典型占用 | 处理 |
|---|---|---|---|
| LLM | llama.cpp :8081 | 30B-A3B 在 8K 上下文约数 GB，长上下文可达 7GB+ | 剧本阶段独占；或使用 CPU-only 配置 |
| 图像 | ComfyUI + FLUX.2 | 模型 2.6GB + 编码器/VAE/激活 | 独占 |
| 视频 | ComfyUI + Wan2.2 | 模型 3.4GB + VAE 解码峰值 | 独占 |

策略：

1. 流水线按阶段推进，不并行调用不同租户。
2. 剧本阶段建议用 **CPU-only 的 llama.cpp 实例**（`-ngl 0`），从根上避免与 ComfyUI 抢显存；8GB 显存不应该同时承担 LLM 与视频生成。
3. `doctor` 会报告 8081/8188 是否同时在线；编排层在启动图像/视频阶段前做同样的检查，发现冲突直接拒绝执行。
4. TTS 是 CPU 推理，可与生成共存，但为了可复现仍串行。

---

## 10. 音频、字幕与剪辑规范

### 10.1 配音

- 对白按 **行** 生成，不按镜头整段生成；一行失败只重跑一行。
- CosyVoice 输出 24kHz（CosyVoice2）或 22.05kHz（SFT），统一用 FFmpeg 重采样到 **48kHz 单声道**。
- 实际语音时长写入 `audio/timing.json`。

时间轴规则：

- 语音短于镜头：补静音，镜头时长不变。
- 语音长于镜头：优先把镜头延长到语音时长（不超过 15 秒）；超过则 `atempo` 加速，上限 1.15；仍超出则标记 `NEEDS_REVIEW`，不硬切语音。

### 10.2 字幕

- 源数据：`dialogue` + 实际音频起止时间。
- 中文每行 ≤ 18 字，最多 2 行。
- 默认软字幕（SRT 封装）；烧录用 ASS + libass，作为可选步骤。
- 字幕时间轴与最终混音一致，不单独手改。

### 10.3 剪辑

1. 每个片段先归一化：统一分辨率、24fps、SAR 1:1、`yuv420p`。
2. `concat demuxer` 拼接（`-c copy`），随后整体重编码为 H.264 CRF 18。
3. 音频链：对白 `loudnorm I=-16`，BGM `-26 LUFS`，sidechain ducking，真峰值 ≤ -1.5 dBTP。
4. 输出：H.264 + AAC 48kHz 立体声，`+faststart`。

所有 FFmpeg 命令以 argv 数组形式记录到 `logs/`，不拼接 shell 字符串。

---

## 11. 质量门

### 技术成功（自动）

| 产物 | 检查 |
|---|---|
| 图片 | 可解码、尺寸正确、非全黑/全白（像素标准差阈值） |
| 视频 | `ffprobe` 时长/帧率/分辨率；`ffmpeg -f null -` 全帧解码无错误；文件非空 |
| 音频 | 时长、采样率、峰值不削波 |
| 成片 | 时长与目标偏差 ≤ 10%；音视频轨道都存在；字幕可解析 |

### 内容合格（人工）

- H1：角色是否可辨认、服装是否正确。
- H2：构图、场景、人物数量、动作方向是否符合分镜。
- H3：节奏、字幕、音量、整体可看性。

**技术通过不等于内容通过。** `review.json` 分开记录 `technical` 与 `human` 两个结论。

---

## 12. 缓存与幂等

生成缓存键：

```text
sha256(
  workflow_sha256
  + model_file_sha256
  + 规范化参数（prompt/negative/seed/width/height/frames/steps/cfg）
  + 输入图片 sha256（I2V / 图生图时）
)
```

- 命中且产物仍存在 → 直接复用，不提交 ComfyUI。
- 产物被删除 → 缓存失效，重新生成。
- 工作流或模型变化 → 键变化，自然失效。
- 随机性通过 seed 固定；"重摇"是显式命令，不是静默行为。

---

## 13. 配置分层

优先级从低到高：

1. `config/settings.yaml`（全局）
2. `config/models.yaml`（模型路径与配套文件）
3. `config/generation.yaml`（R0 最小参数、并发、超时）
4. `config/audio.yaml`（音色、响度、字幕）
5. `projects/<id>/project.yaml`（项目覆盖）
6. 环境变量 `DRAMA_ROOT`、`DRAMA_LLM_BASE_URL` 等（仅路径/端点）
7. CLI 参数（单次运行）

所有配置加载后转成 Pydantic 模型；未知字段忽略但不静默吞掉关键缺项。

---

## 14. 模块划分与实现顺序

```text
src/drama_studio/
├─ cli.py               [已实现] doctor
├─ config.py            [已实现]
├─ models.py            [已实现] 数据契约
├─ doctor.py            [已实现]
├─ state.py             [R3] SQLite 状态机
├─ comfy_client.py      [R3] HTTP + WebSocket + /free
├─ generation/          [R3] 工作流渲染、提交、取回、缓存
├─ quality/             [R3] ffprobe/解码/空图检查
├─ script_engine/       [R4] LLM 客户端、Schema、修复循环
├─ character_manager/   [R5] 资产 bible 与锁定
├─ storyboard/          [R4/R5] 镜头规划
├─ audio/               [R6] CosyVoice 客户端、时间轴
├─ subtitles/           [R6] SRT/ASS
├─ editing/             [R6] FFmpeg 图
├─ storage/             [R3] 路径、哈希、manifest
└─ orchestrator.py      [R7] 阶段图与断点续跑
```

实现纪律：**上一阶段没有在本机跑通，不写下一阶段。** 每个模块先有可执行验收，再有单元测试。

---

## 15. 日志、错误与安全

- 每个外部调用记录：argv、开始/结束时间、退出码、耗时、stdout/stderr 路径。
- ComfyUI 提交记录：workflow sha256、prompt_id、`/history` 原文。
- 不在日志中写入 API Key（本地服务默认无 key；如启用，用环境变量传入）。
- 不使用 shell=True；所有路径用 `Path`，参数以列表传递。
- 项目内不保存模型权重；`.gitignore` 已排除模型、产物、日志、运行时。

---

## 16. 验收路线

| 阶段 | 退出条件 |
|---|---|
| R0 | XPU 可用；FLUX 与 Wan 各自能出图/出片；切换模型不 OOM |
| R1 | 512×512 角色图与场景图可重复生成，参数落盘 |
| R2 | 512×512、33 帧 T2V 与 I2V 均可播放 |
| R3 | 同一工作流连续提交 3 次，成功率 100%，失败可重试并保留证据 |
| R4 | 10 次剧本解析全部通过 Pydantic；非法输出有修复记录 |
| R5 | 3 个镜头复用同一角色资产，人工判定可辨认 |
| R6 | 3-5 镜头自动输出带配音/字幕的 MP4 |
| R7 | 断点续跑：中断后只补未完成镜头，产物哈希不变 |
