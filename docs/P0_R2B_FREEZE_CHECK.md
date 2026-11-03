# P0 现状核对：R2-B 固化与仓库状态

> 执行日期：2026-11-03
> 范围：只核对 P0（R2-B 固化与 Git 状态）；不开始 P1，不提交新内容，不运行生成任务，不安装依赖，不改工作流/模型。
>
> **后续状态（2026-11-03）：R3 已于 `0204979` 提交；本文件保留 P0 时点快照。**

## 1. 结论摘要

| 项目 | 结果 |
|---|---|
| R1 提交 | ✅ `4d72a0b` |
| R2-A 提交 | ✅ `226fdf3` |
| R2-B 提交 | ✅ **`026509b`（已存在，无需再次提交）** |
| R2-B 报告/数据/追踪脚本 | ✅ 均在提交内，数据一致 |
| R0/R1/R2 工作流是否被改动 | ✅ 否（`4d72a0b..HEAD -- workflows/` 为空） |
| R2-B 是否误含原始帧/模型/临时文件 | ✅ 否 |
| 工作区是否 clean | 当时否：R3 与 v1.0 文档未提交；R3 后已于 `0204979` 提交，v1.0 仍待提交 |
| 本次是否新建提交 | ❌ 否（P0 要求只固化 R2-B；它已提交，未做多余提交） |

**P0 对 R2-B 本身已满足；计划中“R2-B 尚未提交”的前提与现状不符。**
工作区不 clean 的原因是后续 R3 与 v1.0 文档，而不是 R2-B 残留。

## 2. P0 逐项核对

### 2.1 仓库根目录、分支、状态

- 根目录：`D:\Local-Drama-Studio`
- 分支：`main`
- 最近提交：

```text
026509b feat(r2b): add four hero-shot validation and subject-motion audit
226fdf3 feat(r2a): add 1024x576 Wan boundary test and production budget
4d72a0b feat(r1): add poem visual assets, reference editing, and batch automation
6a486b4 chore: initialize Local-Drama-Studio with R0-verified environment
```

- 工作区：有未提交修改/未跟踪文件（详见 §3）。

### 2.2 R2-B 提交内容

`026509b` 包含 42 个文件、7714 行新增，关键文件：

```text
docs/R2B_TEST_PLAN.md
docs/R2B_TEST_REPORT.md
experiments/r2b/runs/H1..H4/{job.json,run.json,quality.json,workflow.submitted.json,clip.mp4}
experiments/r2b/r2b_contact_sheet.png
experiments/r2b/h3_boat_track.png
experiments/r2b/runs/H3/h3_boat_track.json
experiments/r2b/summary.json
scripts/r2b_track_boat.py
```

### 2.3 是否误含原始帧、模型或临时文件

- 提交内没有 `*.gguf`、`*.safetensors`、`*.ckpt`、`*.pth`。
- 没有 73 帧原始 PNG；只保留对比图/追踪图与质量 JSON。
- 未发现模型目录或缓存。

### 2.4 报告与实验数据是否对应

| 镜头 | job.json 耗时 | 报告耗时 | job.json 峰值 | 报告峰值 |
|---|---|---|---|---|
| H1 | 32.6 min | 32.6 min | 5.66 GiB | 5.66 GiB |
| H2 | 38.5 min | 38.5 min | 5.51 GiB | 5.51 GiB |
| H3 | 46.4 min | 46.4 min | 5.50 GiB | 5.50 GiB |
| H4 | 39.6 min | 39.6 min | 5.52 GiB | 5.52 GiB |

H3 位移：24.6 px（dx +23.1 / dy +8.6），报告与追踪 JSON 一致。

### 2.5 工作流是否被非预期修改

```text
git diff --name-only 4d72a0b..HEAD -- workflows/
# 输出为空
```

R0/R1/R2 已验证工作流未改动。

## 3. 工作区未提交内容（不属于 R2-B）

当前 `git status`：

```text
 M .gitignore
 M CLAUDE.md
 M README.md
 M docs/ARCHITECTURE.md
 M docs/ENVIRONMENT.md
?? assets/vertical/
?? docs/ASSET_AND_LICENSE_REGISTRY.md
?? docs/CONTENT_SPEC.md
?? docs/PLATFORM_PUBLISHING_SPEC.md
?? docs/PRD.md
?? docs/PRODUCTION_WORKFLOW.md
?? docs/QUALITY_AND_METRICS.md
?? docs/R3_TEST_PLAN.md
?? docs/R3_TEST_REPORT.md
?? docs/README.md
?? docs/ROADMAP.md
?? docs/TECH_STACK.md
?? docs/V1_FREEZE_AUDIT.md
?? experiments/r3a/
?? experiments/r3b/
?? scripts/r3_build.py
?? scripts/r3_tts.py
```

这些是：

1. **R3**：竖屏测试、38 秒成片、脚本与资产（已于 `0204979` 提交）。
2. **v1.0 产品文档**：PRD / TECH_STACK / CONTENT_SPEC 等（上一轮完成，未提交）。

它们不是 P0 的一部分；本次未提交、未修改其内容。

## 4. 计划前提与现状的差异

| 计划假设 | 现状 | 处理 |
|---|---|---|
| R2-B 尚未提交 | 已提交 `026509b` | P0 无需重复提交；保留现有提交 |
| P0 后工作区 clean | 当时因 R3 + v1.0 文档未提交而不 clean | R3 已提交；v1.0 待提交 |
| P1 能力审计未做 | 未做（v1.0 文档有部分能力状态，但不是 CAPABILITY_MATRIX） | 未开始 |
| P2 生态检索未做 | 未做 | 未开始 |
| P3 技术方案定稿未做 | 已有 v1.0 文档（PRD/TECH_STACK/CONTENT_SPEC），但未按 P1/P2 的新证据重审 | 未开始 |
| P4 竖屏实验未做 | **已执行**（R3-A，576×1024 FLUX/Wan） | 后续计划需与现状对齐，避免重复 |
| P5 洛神赋未做 | 未做（已完成的是《春江花月夜》38 秒样片） | 未开始 |
| P6 成本验收未做 | 已有《春江》单篇 43.8 分钟数据；洛神赋/多篇未验收 | 未开始 |

## 5. 未执行的动作

- 未重新运行 Wan / FLUX。
- 未安装/升级依赖。
- 未改工作流/模型。
- 未提交 R2-B（已存在）。
- 当时未提交 R3 或 v1.0 文档；R3 后已提交 `0204979`。
- 未开始 P1。

## 6. 建议的下一步（待人工决定）

当前工作区有两批未提交成果，建议分两次提交以保持历史清晰：

1. **R3 基线**

```text
feat(r3): add vertical capability test and 38s finished short
```

包含：`docs/R3_TEST_*`、`assets/vertical/`、`experiments/r3a/`、`experiments/r3b/`、`scripts/r3_tts.py`、`scripts/r3_build.py`、`docs/ENVIRONMENT.md`、`.gitignore`。

2. **v1.0 产品基线**

```text
docs(v1): freeze product baseline v1.0
```

包含：8 份产品文档、`docs/README.md`、`docs/V1_FREEZE_AUDIT.md`、`README.md`、`CLAUDE.md`、`docs/ARCHITECTURE.md`。

完成后再决定：

- 是否按新计划做 P1（只读能力审计，输出 `docs/CAPABILITY_MATRIX.md`）；
- 是否把 P4 视为已完成（R3-A 已实测竖屏），避免重复做同一实验；
- 是否在 P1 前先审查 v1.0 文档与 P1-P6 的重叠。

## 7. 最终状态

```text
P0（R2-B 固化）: PASS_VERIFIED（提交 026509b 已存在）
工作区 clean:    当时 NO（R3 + v1.0 未提交）；现 R3 已提交，v1.0 待提交
P1-P6:           NOT_RUN
```

本次只输出现状核对，不自动提交、不进入 P1。
