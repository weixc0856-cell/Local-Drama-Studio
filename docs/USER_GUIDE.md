# 生产工作台用户手册

> 文档状态：Phase B 操作手册（2026-11-04）
> 读者：不需要读源码的实际制作者
> 适用：Windows 11、本机已安装本仓库、模型在 `D:\AI\models`
> 原则：只写真实存在的页面/按钮/命令；不存在的能力明确标注“当前没有”。

---

## 0. 先读这三条

1. **PRD 默认 TTS 是 CosyVoice2-0.5B zero-shot**；300M SFT「中文女」仅显式可选。当前代码/配置默认仍是 SFT（`PRD-TTS-001` = `PARTIAL`）。现在要按 PRD 跑 zero-shot：启动 `-Model cosyvoice2`，并显式 `--tts-mode zero_shot`；要跑 SFT：启动 `-Model sft`，显式 `--tts-mode sft`。两种运行时不能混用。
2. **工作台的“合成重建”只重合成，不重新生成图片/配音**。它读取期数产物目录里的 `segments.json` + `audio_manifest.json`。
3. **不要覆盖历史成片**。工作台每次写新的 `renders/build-<时间>/`；不要手动改旧目录。

---

## 1. 环境准备

### 1.1 必须满足

| 项 | 要求 |
|---|---|
| 系统 | Windows 11 |
| Python | 3.12（根 `.venv` 由 uv 创建） |
| uv | 0.10.x |
| FFmpeg / ffprobe | 8.1-full_build（PATH 可用） |
| 磁盘 | 项目盘与 `D:\AI\models` 至少 40 GiB 空闲 |
| 模型 | `D:\AI\models` 下 FLUX / Wan / 文本编码器 / VAE，大小与 `config/models.yaml` 一致 |
| 字体 | `assets/fonts` 下 6 个 OTF（可由 `fetch_fonts.py` 重建） |
| ComfyUI | `runtime/ComfyUI` 独立 venv，torch XPU 可用 |
| CosyVoice | `D:\AI\CosyVoice-Runtime`，端口 50000 |
| LLM | `D:\AI` 的 llama.cpp，端口 8080 |

### 1.2 首次安装

```powershell
cd D:\Local-Drama-Studio

# 1) 调度环境
uv sync --python 3.12

# 2) 生成环境（首次很重：PyTorch XPU + ComfyUI）
scripts\setup.ps1 -WithComfyUI

# 3) 字体（OTF 不进 Git，按 manifest 下载并校验）
.venv\Scripts\python.exe scripts\fetch_fonts.py --check
.venv\Scripts\python.exe scripts\fetch_fonts.py

# 4) 环境诊断（写 logs\doctor-*.json）
scripts\doctor.ps1
```

验收：`doctor` 的必需项无 `FAIL`；`comfy.xpu` 显示 `torch 2.15.0+xpu` 和 Arc A750。

### 1.3 模型与字体位置（不要移动）

```text
D:\AI\models\
├─ flux-2-klein-4b-Q4_K_M.gguf          # 必须在顶层
├─ Wan2.2-TI2V-5B-Q4_K_M.gguf           # 必须在顶层
├─ text_encoders\qwen_3_4b.safetensors
├─ text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors
└─ vae\flux2-vae.safetensors
   vae\wan2.2_vae.safetensors
```

`D:\AI\start_server.bat` 只扫描顶层 `*.gguf`；不要移动这两个扩散模型。

---

## 2. 日常启动

### 2.1 启动顺序

```powershell
cd D:\Local-Drama-Studio

# 1) 启动 ComfyUI（8188）
scripts\start.ps1

# 2) 启动本地 LLM（8080，CPU-only，64K）
scripts\llm_server.ps1 -Action start

# 3) 启动 CosyVoice（50000）
#    PRD 默认：CosyVoice2-0.5B zero-shot（当前代码默认仍是 SFT，见 §0）
scripts\cosyvoice_server.ps1 -Action start -Model cosyvoice2

# 4) 启动工作台（8765）
.venv\Scripts\drama.exe serve --port 8765
```

浏览器打开 `http://127.0.0.1:8765`。

### 2.2 检查状态

```powershell
scripts\doctor.ps1
scripts\llm_server.ps1 -Action status
scripts\cosyvoice_server.ps1 -Action status
```

| 服务 | 端口 | 正常表现 |
|---|---|---|
| ComfyUI | 8188 | `/system_stats` 返回 XPU |
| LLM | 8080 | `/health` 返回 `status=ok` |
| CosyVoice | 50000 | `/health` 返回 `status=ready`，SFT 时 `speakers` 含中文女 |
| 工作台 | 8765 | 页面能打开，右上角服务胶囊变绿 |

### 2.3 正常关闭

```powershell
scripts\stop.ps1
scripts\llm_server.ps1 -Action stop
scripts\cosyvoice_server.ps1 -Action stop
# 工作台：Ctrl+C
```

规则：**谁启动，谁停止**。8080 与 50000 都是单实例，空闲时不要占着。

### 2.4 两个 CosyVoice 运行时（互斥）

| 命令 | 模型 | 用途 |
|---|---|---|
| `scripts\cosyvoice_server.ps1 -Action start -Model cosyvoice2` | CosyVoice2-0.5B | **PRD 默认**：zero-shot 参考音克隆 |
| `scripts\cosyvoice_server.ps1 -Action start -Model sft` | CosyVoice-300M-SFT | 显式可选：预置音色（中文男/中文女） |

同一时间只能跑一个。切换前先 `-Action stop`。

---

## 3. 生产工作台怎么用

### 3.1 页面

左侧导航：

```text
生产：工作台 / 期数管理 / 生产工作流 / 任务中心
内容：内容项目 / 素材库 / 风格管理
系统：系统设置
```

期数工作区有 7 个 Tab：**概览 / 内容 / 分镜 / 视觉 / 音频 / 素材 / 成片**。

### 3.2 创建项目

1. 进入 `#/projects`（内容项目）。
2. 点“新建项目”。
3. 填写名称、简介、定位、默认风格、默认音色、画幅（9:16）、目标平台。
4. 保存。

项目本身不生成内容；它只是期数的容器。

### 3.3 创建期数

1. 进入 `#/episodes`（期数管理）或项目卡片上的“新建期数”。
2. 选择所属项目、期数编号、标题、生产类型（`video` / `literary`）。
3. **选择视觉风格**（必选，才能生成）。
4. 填“真实产物目录”（`artifact_root`）：
   - 新建生产：建议 `projects/<project>/episodes/<episode>/work`
   - 复用已有产物：填已有目录（如 `experiments/r3b`，但该目录当前已缺失）
5. 保存。

期数创建时会把所选风格冻结为 `style_snapshot`；之后改全局风格不会自动改历史期数。

### 3.4 选择/更换风格

- 在期数“视觉”Tab 可以看到当前快照、色板、参考资产、正/负提示词。
- “应用新风格快照”会**替换**当前期数快照；已有成片/manifest 不变。
- 当前没有“风格版本历史”；更换前请自己记录旧 `style_id`/`style_sha256`。
- 当前 UI 的风格是 DB 风格，**不会自动同步到 `config/styles.yaml` 的运动/美学 preset**。要做 `motion.plan`/`aesthetic.plan`，风格 id 必须是 `court_green_fine_line` 或 `ink_wash`（或显式 `--style`）。

### 3.5 创建任务

进入 `#/tasks`（任务中心）→ 选择任务类型 → 填参数 → 勾选确认（危险任务）→ “启动任务”。

可用的任务类型（21 种）：

```text
doctor.run                 环境诊断
build.rebuild              合成重建（新目录）
comfy.batch                ComfyUI 批处理
li.run                     文学分析五轮
service.comfy.start        启动 ComfyUI
service.comfy.stop         停止 ComfyUI
package.build              内容包构建
script.generate            文案与分镜生成
segments.build             生产分段适配
motion.plan                动态分镜计划
motion.render              动态片段渲染
audio.qa                   音频质量检查
aesthetic.plan             镜头美学计划
aesthetic.compare          美学 A/B 对照
aesthetic.review           美学人工结论
static.check               静态质量门（单镜头）
story.check                故事圣经连续性检查
quality.check              技术质量检查
tts.synthesize             配音合成
review.accept              人工验收·通过
review.reject              人工验收·拒绝
```

任务中心可以看状态、日志、取消、用相同参数重跑。任务日志在 `logs/workspace/tasks/`。

`tts.synthesize` 任务的“合成模式”选择：留空读 `config/audio.yaml`（默认 `zero_shot`）；`sft` 预置音色；`zero_shot` 参考音克隆。任务结果会记录实际 `tts_mode/model_class/speaker_id`；填 `voice_profile` 可选用 `config/voices.yaml` 的档案（逐行 `voice_profile` 优先）。

### 3.6 查看进度

- 期数“概览”：生产步骤（原文/文学分析/文案/分镜/图片/视频/配音/字幕/合成/成片/人工验收）。
- 进度只统计**必需步骤的 PASS_VERIFIED**；`PARTIAL` 不计入完成。
- 构建记录表显示目录、manifest 版本、成片哈希、质量、字体。
- 人工验收按钮在“概览”右侧；“标记通过/拒绝”会写 `human_review.json`。

### 3.7 查看成片与历史

- 期数“成片”Tab：最新构建、final、字幕轨、分段数、字体、解码校验、构建历史。
- 每次“合成重建”写新的 `renders/build-<时间>/`；旧目录保留。
- 历史 manifest 缺 `content_type/timeline/font` 会标 `legacy`，仍可查看。

### 3.8 工作台当前没有的能力

| 能力 | 现状 |
|---|---|
| 编辑文案/分镜/提示词 | 没有；只读展示；请用 CLI 文件 |
| 触发静态质量门 | 任务中心 `static.check`（单镜头）；`motion.plan` 默认要求报告，缺失即失败 |
| 从 UI 跑运动质量门 | 没有 `motion_manifest` 字段；只能 API/CLI |
| 美学 A/B 结果专门视图 | 没有；任务结果/文件在 `experiments/aesthetic/...` |
| 风格版本历史 | 没有 |
| 批处理/断点续跑 | 没有 |
| 自动发布 | 没有 |

---

## 4. 完整做一篇视频

### 4.1 案例 A：P1 短文本（最快验证全链路）

**用途**：验证内容包 → LLM → TTS → FLUX → segments → build → quality。
**前置**：8188 / 8080 / 50000 都启动。**P1 是历史 SFT 案例复现**：必须 `-Model sft`；当前 `p1_e2e.py` 没有 `--tts-mode` 参数，默认配置为 `sft` 时才可运行。按 PRD 的新默认 zero-shot，请用 §4.3 手工链并显式 `--tts-mode zero_shot`（启动 `-Model cosyvoice2`）。

```powershell
cd D:\Local-Drama-Studio

# 服务（另开窗口或已启动）
scripts\start.ps1
scripts\llm_server.ps1 -Action start
scripts\cosyvoice_server.ps1 -Action start -Model sft

# 端到端（会创建/复用 proj_p1_short / ep_p1_short）
.venv\Scripts\python.exe scripts\p1_e2e.py
```

脚本依次执行：

```text
package.build → script.generate → tts.synthesize → comfy.batch
→ segments.build → build.rebuild → quality.check
```

产物：

```text
projects/proj_p1_short/episodes/ep_p1_short/work/
  content_package.json
  production_script.json
  narration.json
  audio_manifest.json
  assets/images/shot_*/
  segments.json
projects/proj_p1_short/episodes/ep_p1_short/renders/build-<时间>/
  final_9x16.mp4
  final_9x16_burned.mp4
  quality_report.json
```

验收：

- `final_9x16.mp4` 为 1080×1920 / 24 fps / 约 14 s；
- `quality_report.json` `status=PASS`；
- 4 行音频哈希一致；
- 浏览器 `#/episodes/ep_p1_short` 能看到步骤/成片。

失败时看 `logs/workspace/tasks/task_*.log` 与 `logs/` 服务日志；不要删半成品。

### 4.2 案例 B：重建 81.373 s 工笔成片（纯 FFmpeg）

**用途**：最快看到完整生产案例；不需要 ComfyUI/LLM/CosyVoice。
**事实**：81.373 s / 1080×1920 / 13 段 / 18 句；实现是 `scroll_shot.py` + 预渲染 clips，**不是 motion.plan**。

工作台操作：

1. 打开 `#/episodes/ep_chunjiang_gongbi_01`。
2. 点“合成重建（新目录）”。
3. 确认；任务写入 `projects/proj_chunjiang_gongbi/episodes/ep_chunjiang_gongbi_01/renders/build-<时间>/`。
4. 在“成片”Tab 看结果；在“概览”看质量。

等价 CLI：

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "projects\proj_chunjiang_gongbi\episodes\ep_chunjiang_gongbi_01\renders\build-$stamp"
.venv\Scripts\python.exe scripts\r3_build.py `
  --segments projects\proj_chunjiang_gongbi\episodes\ep_chunjiang_gongbi_01\work\segments.json `
  --audio    projects\proj_chunjiang_gongbi\episodes\ep_chunjiang_gongbi_01\work\audio_manifest.json `
  --out      $out
.venv\Scripts\python.exe -m drama_studio.quality --manifest "$out\build_manifest.json" --root .
```

验收：

- `total_seconds` ≈ 81.373 s（新构建可能因当前 `soundscape.enabled=true` 音频链路不同而略有差异）；
- `quality_report.json` PASS；
- `verification_report` 不会由 `r3_build` 自动生成；历史目录里的那份是人工验证产物，不覆盖。

注意：当前 `config/audio.yaml` `soundscape.enabled=true`，新构建会走声景母带；历史 81.373 构建的 `soundscape` 为 `null`，声音不会逐字节相同。

### 4.3 案例 C：手工做一篇新短文本（CLI）

> 适合需要控制文案/分镜/素材的制作者。所有命令从仓库根执行。

**步骤 1：准备语料目录**

```text
my_case/source/
  original_text.txt
  normalized_text.txt
  normalization_map.json
  segments.json
  source_registry.json
  claims.json
  reviews.json
```

要求：`source_registry.json` 的 `locator` 必须能在 `segments.json` 找到；`claims.json` 的 quote 必须出现在原文。

**步骤 2：ContentPackage**

```powershell
.venv\Scripts\python.exe -m drama_studio.content_package `
  --corpus my_case\source `
  --out my_case\work\content_package.json
```

**步骤 3：风格快照**

从期数 DB 快照导出，或手写一个严格风格 JSON（至少含 `id/name/visual_language/positive_prompt/negative_prompt`）：

```powershell
# 如果期数已绑定风格，工作台 script.generate 会自动写 style_snapshot.json
# CLI 手写示例：my_case\work\style_snapshot.json
```

**步骤 4：文案/分镜**

```powershell
.venv\Scripts\python.exe -m drama_studio.script_engine `
  --package my_case\work\content_package.json `
  --style my_case\work\style_snapshot.json `
  --out my_case\work\production_script.json `
  --base-url http://127.0.0.1:8080/v1 `
  --model Qwen3-30B-A3B-Instruct-2507 `
  --api-key sk-local `
  --timeout 900 --max-tokens 2000
```

**步骤 5：TTS**

```powershell
scripts\r3_tts.py `
  --narration my_case\work\narration.json `
  --out my_case\work\audio `
  --manifest my_case\work\audio_manifest.json `
  --tts-mode zero_shot --mode recitation
```

PRD 默认是 zero-shot：先启动 `-Model cosyvoice2`。SFT 是显式可选：`-Model sft` + `--tts-mode sft`；`--speaker` 只在 SFT 下有效。

多音色：在 `narration.json` 的顶层或逐行写 `"voice_profile": "narrator_self"`，或加 `--voice-profile narrator_self`。档案定义在 `config/voices.yaml`；只有 `APPROVED` 档案可进生产，`sft` 与 `zero_shot` 不能在同一次运行混用。

**步骤 5.1：故事圣经连续性检查（可选）**

```powershell
.venv\Scripts\python.exe -m drama_studio.bible `
  --script my_case\work\production_script.json `
  --characters my_case\work\character_bible.yaml `
  --shots my_case\work\shot_bible.yaml `
  --voices config\voices.yaml `
  --out my_case\work\story_bible_report.json
```

检查：每个脚本镜头是否被 Shot Bible 覆盖、人物引用是否存在、风格 id 是否一致、
角色声音档案是否为 `APPROVED`。报告明确写 `same_face_guarantee: false`；它不检查
“同一角色是否同一张脸”，那仍需人工视觉复核。

**步骤 6：FLUX jobs**

`script.generate` 的 CLI 不会自动建 jobs；用工作台 `script.generate` 任务，或手写 jobs JSON：

```json
[
  {"id":"shot_001","workflow":"workflows/r0_flux_t2i_api.json",
   "params":"my_case/work/comfy/params/shot_001.json",
   "out":"my_case/work/assets/images/shot_001"}
]
```

`params` 至少包含 `positive_prompt/negative_prompt/seed/width/height/steps/cfg/filename_prefix`。

```powershell
scripts\r1_batch.py --jobs my_case\work\comfy\jobs.json --timeout 1800
```

**步骤 7：segments**

```powershell
.venv\Scripts\python.exe -m drama_studio.production `
  --script my_case\work\production_script.json `
  --images my_case\work\assets\images `
  --audio my_case\work\audio_manifest.json `
  --out my_case\work\segments.json
```

**步骤 8：合成 + 质量**

```powershell
$out = "my_case\renders\build-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
.venv\Scripts\python.exe scripts\r3_build.py `
  --segments my_case\work\segments.json `
  --audio my_case\work\audio_manifest.json `
  --out $out
.venv\Scripts\python.exe -m drama_studio.quality --manifest "$out\build_manifest.json" --root .
```

**验收**：同案例 A/B。若失败，按 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 定位。

---

## 5. 做下一篇：复用与隔离

### 5.1 复用

| 复用项 | 做法 |
|---|---|
| 项目 | 同一项目下新建期数，编号 +1 |
| 视觉风格 | 期数创建时选同一风格；快照冻结 |
| 素材 | 新期数 `artifact_root` 指向新 work 目录；不要把旧素材目录写进新期数 |
| 字体/配置 | 全局 `config/` 共享 |
| 文案模板 | 复用 `content_package`/`narration` 结构，不复制作品名到代码 |

### 5.2 不要覆盖

- 新期数用新的 `work/` 目录。
- 合成用新的 `renders/build-<时间>/`。
- 美学计划用新的 `snapshot-<时间>/`。
- 运动渲染用新的 `motion/build-<时间>/`。
- 历史 `experiments/` 不覆盖。

### 5.3 换风格

- 同一作品原则上不换风格；如果必须换，创建**新期数**或新的生产版本，记录旧/新 `style_id`、`style_sha256`、日期、原因。
- 不要把“换风格”做成在同一期数里替换 snapshot 后继续用旧镜头；旧镜头提示词已经写死旧风格。

---

## 6. 故障处理

先看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。最常见的五类：

| 现象 | 先查 |
|---|---|
| ComfyUI 起不来 / 8188 不通 | `logs\comfyui.err.log`；`scripts\doctor.ps1`；XPU |
| FLUX/Wan OOM | 关掉其他 GPU 任务；降低分辨率/帧数；不要同时跑 LLM/Wan |
| CosyVoice 连不上 / 音色不对 | `scripts\cosyvoice_server.ps1 -Action status`；确认 `-Model sft` 或 `cosyvoice2`；当前 TTS 模式 |
| 配音文件缺失/哈希不一致 | `audio_manifest.json` 的 `file/sha256`；重跑 `tts.synthesize --force` |
| 合成失败 | `logs/workspace/tasks/*.log`；字体 fontselect；segments 素材路径 |

---

## 7. 文件位置速查

| 内容 | 路径 |
|---|---|
| 项目/期数/风格/任务 | `projects/workspace.db` |
| 期数产物 | `projects/<project>/episodes/<episode>/work/` |
| 成片构建 | `projects/<project>/episodes/<episode>/renders/build-<时间>/` |
| 任务日志 | `logs/workspace/tasks/task_*.log` |
| doctor 报告 | `logs/doctor-*.json` |
| ComfyUI 日志 | `logs/comfyui.log` / `logs/comfyui.err.log` |
| LLM 日志 | `logs/llm-8080.out.log` / `.err.log` |
| CosyVoice 日志 | `D:\AI\CosyVoice-Runtime\logs\server.log` / `server-sft.log` |
| 实验产物 | `experiments/` |
| 视觉资产 | `assets/keyframes/`、`assets/vertical/`、`assets/visual_style/` |
| 字体 | `assets/fonts/` |
| 配置 | `config/*.yaml` |

---

## 8. 状态含义（工作台）

| 状态 | 含义 |
|---|---|
| 已验证 / `PASS_VERIFIED` | 有真实文件/哈希/任务证据 |
| 静态验证 / `PASS_STATIC` | 规范/静态检查通过，未做动态/人工 |
| 部分 / `PARTIAL` | 部分完成 |
| 未运行 / `NOT_RUN` | 没有执行证据 |
| 受阻 / `BLOCKED` | 前置条件不满足 |
| 失败 / `FAILED` | 执行失败 |
| 运行中 / `RUNNING` | 正在跑 |
| 等待 / `PENDING` | 排队 |
| 已成片 / `completed` | 有通过哈希的 final |
| 待合成 / `ready` | 必需步骤基本完成 |
| 草稿 / `draft` | 未开始或证据不足 |
