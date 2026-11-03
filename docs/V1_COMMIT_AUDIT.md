# v1.0 文档提交前审查

> 审查日期：2026-11-03
> 范围：PRD、TECH_STACK、CONTENT_SPEC、PRODUCTION_WORKFLOW、PLATFORM_PUBLISHING_SPEC、ASSET_AND_LICENSE_REGISTRY、QUALITY_AND_METRICS、ROADMAP、docs/README、V1_FREEZE_AUDIT。
> 约束：不提交、不改冻结的产品决策、不改工作流/模型/脚本。
>
> **状态说明（2026-11-03）：本文件 §1/§3/§8/§9 是初次审计时点（S2 终审前）的快照。S2 已修正 4 处 CosyVoice 表述与 R3-D 入口；S2 终审又发现 6 项阻塞问题。当前状态：S2 修订已完成，S2.1 修订后仍需下一轮人工复核，未提交；不得写成“已具备提交条件”。**

## 1. 初次审计时点结论（保留）

| 项目 | 结果 |
|---|---|
| 8 份产品文档 + 索引 + 冻结审计 | ✅ 齐全 |
| 文档内部链接 | ✅ 0 个失效 |
| 已验证 / 部分验证 / 未验证区分 | ✅ 基本准确 |
| 竖屏 576×1024 | ✅ 正确标记 `PASS_VERIFIED`（R3-A） |
| 38.04 秒《春江花月夜》 | ✅ 正确标记 `PASS_VERIFIED`（R3-B/C） |
| 女声音色 | ❌ **过度表述**：只有「中文男」实测；文档多处写成“中文男/女”或笼统的 CosyVoice 已通过 |
| 字体替换 | ⚠️ 已写明 Microsoft YaHei 专有、需开源替代，但未集中标记为“待选型” |
| BGM / 音效 | ⚠️ 已标 `NOT_RUN`，但未集中标记为“待选型” |
| 许可证结论 | ✅ 未发现未经证实的“可商用”结论；待核验项已标注 |
| 跨文档矛盾 | ⚠️ 主要为女声表述；其余已统一 |
| 是否可立即提交 v1.0 | ❌ **否**；需先修正女声状态表述（见 §3） |
| R3 提交是否受影响 | ❌ 否；R3 可独立提交 |

**初次审计时存在一处事实性状态错误：把仅验证过的中文男声，写成了中文男/女或整个 CosyVoice 已验收。该问题已在 S2 修订；此结论保留为审计时点记录，不代表当前提交批准。**

## 2. 状态逐项核对

| 声明 | 位置 | 判定 | 依据 |
|---|---|---|---|
| 竖屏 576×1024 `PASS_VERIFIED` | PRD/TECH_STACK/ROADMAP | ✅ 准确 | R3-A |
| 38.04 s 1080×1920 样片 `PASS_VERIFIED` | PRD/ROADMAP/QUALITY | ✅ 准确 | R3-B/C |
| CosyVoice「预置音色」`PASS_VERIFIED` | PRD §12、TECH_STACK 行、PRODUCTION_WORKFLOW §1 | ❌ 过度 | R3 只用了「中文男」；中文女未试听 |
| 「中文男/女」预置音色 | CONTENT_SPEC §6 | ❌ 过度 | 同上 |
| 自定义音色克隆 `NOT_RUN` | PRD/CONTENT/ASSET | ✅ 准确 | 未做 |
| 人物跨镜头一致性 `NOT_RUN` | PRD/CONTENT/ROADMAP | ✅ 准确 | 未做人物测试 |
| 风格变体（工笔/敦煌/国漫/写实）`NOT_RUN` | PRD/CONTENT | ✅ 准确 | 未做 |
| 洛神赋样片 `NOT_RUN` | PRD/CONTENT/ROADMAP | ✅ 准确 | 只完成春江 |
| BGM/音效 `NOT_RUN` | PRD/CONTENT/ASSET/PLATFORM | ✅ 状态准确，但缺“待选型”任务 | 当前无 |
| 字体：Microsoft YaHei 专有、需替换 | CONTENT/ASSET/PLATFORM | ✅ 准确 | 系统字体 |
| 1080×1920 Lanczos 放大 | PRD/CONTENT/TECH | ✅ 准确 | R3-B |
| 多篇批处理 `NOT_RUN` | ROADMAP/QUALITY | ✅ 准确 | 只做单篇 |
| 平台发布/数据 `NOT_RUN` | PRD/PLATFORM/ROADMAP | ✅ 准确 | 未做 |
| 本地 LLM 剧本/分镜 `PARTIAL`/`DECISION` | PRD/TECH | ✅ 准确 | 服务存在，未接入 |
| Blender/Motion Canvas `DECISION`/`NOT_RUN` | TECH/ROADMAP | ✅ 准确 | 未集成 |

## 3. 初次审计时点必须修复项（保留）

### 3.1 女声状态过度表述

需要修正的表述：

| 文件 | 当前表述 | 应改为 |
|---|---|---|
| `docs/PRD.md:154` | `CosyVoice 预置音色 | PASS_VERIFIED` | 「中文男」预置音色 `PASS_VERIFIED`；「中文女」`NOT_RUN` / 待试听选型 |
| `docs/TECH_STACK.md:31` | CosyVoice `PASS_VERIFIED` | 技术链路 `PASS_VERIFIED`；仅中文男实测；女声待选型 |
| `docs/CONTENT_SPEC.md:111` | CosyVoice SFT 预置音色（中文男/女） | 中文男已验证；中文女待试听；不用“中文男/女”暗示两者都通过 |
| `docs/PRODUCTION_WORKFLOW.md:16` | `PASS_VERIFIED`（预置音色） | `PASS_VERIFIED`（中文男）；女声 `NOT_RUN` |

这不是产品决策变更，而是**状态事实修正**。

### 3.2 女声、字体、BGM、音效的“待选型”集中入口

当前 BGM/音效是 `NOT_RUN`，字体是“开源替代未选定”，女声没有单独条目。建议在 `docs/ROADMAP.md` 的 v1.1 前插入 **R3-D**（详见 §5），并在 ASSET 台账增加：

```text
女声 TTS（候选试听）      NOT_RUN / 待选型
标题字体（思源宋体等）      DECISION / 待核验
正文字幕字体（思源黑体等）  DECISION / 待核验
BGM（Pixabay/Mixkit 等）    NOT_RUN / 待选型
音效（Freesound CC0 等）    NOT_RUN / 待选型
```

这是提交前建议修复的第二项；它不改变 v1.0 冻结的产品方向，只补齐待办状态。

## 4. 许可证审查

### 已核实的许可

| 资产 | 许可证 | 证据 |
|---|---|---|
| ComfyUI | GPL-3.0 | 本地 `runtime/ComfyUI/LICENSE` |
| ComfyUI-GGUF | Apache-2.0 | 本地 LICENSE |
| FLUX.2 Klein 4B | Apache-2.0 | HuggingFace 模型卡 |
| Wan2.2 | Apache-2.0 | Comfy-Org 模型卡 |
| Qwen3-4B | Apache-2.0 | HuggingFace 模型卡 |
| CosyVoice | Apache-2.0 | 本地 `app/LICENSE` |
| FFmpeg 8.1 full build | GPLv3 构建 | `--enable-gpl --enable-version3` |

### 待核验（文档已标注，无未经证实的商用结论）

- UMT5 底层模型许可。
- CosyVoice-300M-SFT 模型与「中文男」预置音色的商用/平台使用权。
- Microsoft YaHei 商用授权（专有字体，不应作为公开发布最终方案）。
- BGM/音效未选型，无授权结论。
- 项目代码许可证未声明（`DECISION`）。
- 抖音/小红书对 AI 内容与音乐跨平台使用的规则。

**未发现“因为 Apache-2.0 所以音色/生成音频一定可商用”的错误结论。** 文档已把代码/模型许可与音色使用权分开，这一点正确。

## 5. 初次审计时点的路线图建议（保留；S2 已部分落实）

### 5.1 R3-D：声音、字体、BGM、音效选型（建议插入，优先于 R4）

**是否进入路线图：是。应作为 R4 的前置门。**

范围：

1. **女声试听**
   - 同一段 20-30 秒《春江花月夜》文本。
   - 候选：阿里云 Qwen TTS（温怀清、余小云）、火山引擎（古风少御 BV115、温柔淑女 BV104、知性女生 BV009）、ElevenLabs 付费对照；CosyVoice「中文男」作为现有基线。
   - 评价：自然度、咬字、停顿、情绪、诗词韵律、是否过度播音腔。
   - 不先改生产脚本；先试听选型。
2. **字体**
   - 标题：思源宋体（Source Han Serif，OFL 1.1）。
   - 正文/字幕：思源黑体（Source Han Sans，OFL 1.1）。
   - 点缀：霞鹜文楷（LXGW WenKai，OFL 1.1）。
   - 保存字体文件、LICENSE、版本、下载日期；替换 Microsoft YaHei。
3. **BGM/音效**
   - BGM：Pixabay / Mixkit 候选；逐首记录页面、作者、许可、下载日期、文件哈希；注意 Content ID 标记。
   - 音效：Freesound 优先 CC0；CC BY 需署名；不用 CC BY-NC。
   - 抖音/小红书跨平台授权分别核验。
4. **混音与字幕样式**
   - 三种字幕样式（标题/正文/点缀）在同一画面上比较。
   - 三种混音版本；测 **LUFS 综合响度、True Peak、语音/BGM 相对响度**，不能只看 volumedetect 的 mean/max。
5. **交付**
   - 选定的音色/字体/BGM/音效及授权证据。
   - 试听/试看对比表。
   - 人工选定结论。

前置条件：

- 保留 R3 男声版本为基线，不覆盖、不删除。
- 不新增本地生成模型；不重构生产流水线。
- 云端 TTS 先用免费试听/试用额度；不先付费。

验收标准：

- 选定 1 个女声音色，完成许可核验。
- 选定 1 套中文字体组合，保存 OFL 文件与授权。
- 选定 1 首 BGM + 1-2 个音效，记录授权。
- 3 组字幕样式、3 组混音的人工对比。
- LUFS/True Peak 达标（对白约 -16 LUFS，TP ≤ -1.5 dBTP）。
- 不改工作流、不进入完整样片制作。

### 5.2 R4：《洛神赋》完整样片

**是否进入路线图：是；必须在 R3-D 之后。**

验收：

- 45-60 秒，9:16，1080×1920。
- 4-6 张静帧 + 1-2 段 Wan；Wan 只用于已验证的推近/环境动态。
- 原文/现代解释/艺术想象/AI 标识清楚。
- 使用 R3-D 选定的女声/字体/BGM/音效。
- 字幕准确；完整播放；无黑帧/破损/音画错位。
- 人工完整看片通过；记录端到端成本。

### 5.3 R5：多篇生产与平台发布测试

**是否进入路线图：是；必须在 R4 之后。**

验收：

- 3-5 条作品，抖音/小红书分别发布（人工）。
- 每条独立封面/标题/正文/话题；记录 24h/72h/7d 数据。
- 不自动发布；不根据 1-2 条数据下结论。
- 失败隔离、断点续跑、降级方案可用。

### 5.4 与现有 ROADMAP 的映射

| 新编号 | 现有 ROADMAP | 关系 |
|---|---|---|
| R3-D | 未列入 | 建议新增，置于 M3 前 |
| R4 | M3《洛神赋》 | 同一目标，增加 R3-D 前置 |
| R5 | M4 平台测试 + M5 批处理 | 可合并为“多篇+发布测试” |

初次审计时点建议；S2 已把 R3-D 加入 `docs/ROADMAP.md` 与 ASSET 台账，当前仍以冻结后的 ROADMAP 为准。

## 6. 重复、矛盾与失效引用

- 文档链接：0 个失效。
- 时长口径：PRD/CONTENT 已统一为“默认 30-60 秒，90 秒仅实验”；ROADMAP M3 用 45-60 秒，不冲突。
- README 旧阶段表、ARCHITECTURE 旧 R0-R7 编号已标注为历史/设计编号，不再声称当前实现。
- 唯一事实性矛盾：女声状态（§3.1）；已在 S2 修正，此处保留审计时点记录。
- 未发现术语混用（`PASS_VERIFIED`/`PASS_LIMITED`/`PARTIAL`/`NOT_RUN`/`DECISION`）之外的旧状态词。

## 7. 提交边界与跨提交依赖

### R3 提交

见 [R3_COMMIT_AUDIT.md](R3_COMMIT_AUDIT.md)。关键：

- 排除 `renders/concat.txt`、`renders/final_check_3s.png`。
- 不包含 README/CLAUDE。

### v1.0 提交

```text
docs/PRD.md
docs/TECH_STACK.md
docs/CONTENT_SPEC.md
docs/PRODUCTION_WORKFLOW.md
docs/PLATFORM_PUBLISHING_SPEC.md
docs/ASSET_AND_LICENSE_REGISTRY.md
docs/QUALITY_AND_METRICS.md
docs/ROADMAP.md
docs/README.md
docs/V1_FREEZE_AUDIT.md
docs/P0_R2B_FREEZE_CHECK.md
docs/V1_COMMIT_AUDIT.md
README.md
CLAUDE.md
docs/ARCHITECTURE.md
```

### 跨提交依赖

1. `README.md` / `CLAUDE.md` 同时含 R3 与 v1.0 改动；R3 提交排除它们，v1.0 提交包含它们。
2. `docs/README.md` 引用 R3 文档；应在 R3 提交之后提交 v1.0，链接才指向已存在的文件。
3. `docs/V1_FREEZE_AUDIT.md` 曾提到 R3 尚未提交；已在 S2 同步为“R3 已提交 `0204979`”，并保留时点说明。
4. `docs/ENVIRONMENT.md`、`.gitignore` 属 R3；不要放进 v1.0 提交。

## 8. 初次审计时点安全提交判断（保留）

| 提交 | 条件 | 判断 |
|---|---|---|
| R3 | 排除 2 个临时文件；不混入 README/CLAUDE | ✅ 可提交 |
| v1.0 | 先修正女声状态表述；补齐 R3-D 待选型入口 | ❌ 暂不可提交 |
| 历史报告 | 不删除、不合并 | ✅ 保持 |

**S2.1 后当前状态：6 项终审问题已修订，仍需下一轮人工复核；未提交，不写“已具备提交条件”。** R3 已提交 `0204979`。

## 9. 初次审计时点最终建议（保留）

1. R3 基线已提交 `0204979`。
2. 修正 4 处女声表述，增加 R3-D 待选型入口。
3. 再提交 v1.0 文档基线。
4. 然后执行 R3-D，而不是直接进入 R4。
5. R3-D 通过后再做《洛神赋》R4；R5 放在真实平台测试之后。

本次只输出审查，不自动提交、不修改冻结文档。

## 10. S2.1 后当前状态（2026-11-03）

- S2 已修正 4 处 CosyVoice 表述，并增加 R3-D 待选型入口。
- S2 终审发现 6 项提交阻塞问题：README 路线、ARCHITECTURE 状态块、V1_FREEZE 提交历史、本文件历史/当前混写、QUALITY 音频表述、TECH_STACK 耗时范围。
- S2.1 已修订上述 6 项；当前仍需下一轮人工终审。
- 未暂存、未提交；不得写成“已具备提交条件”或“可以提交”。
