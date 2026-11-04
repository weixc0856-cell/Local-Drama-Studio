# 后续开发路线评估

> 文档状态：Phase B 路线文档（2026-11-04）
> 依据：Phase A 审计 + 2026-11-04 三项产品决策
> 原则：**先修生产可靠性，再完成单篇闭环，再谈效率/短剧/商业化。** 不因为技术可行就加功能。
> 执行方式：Phase C 一次只做一个明确任务；每次提供修改文件、原因、内容、测试、验收、遗留。

---

## 0. 优先级总表

| 级别 | 主题 | 任务数 | 目标 |
|---|---|---|---|
| **P0** | 生产可靠性/事实一致性 | 5 | 用户看到的模式、风格、质量门与实际一致 |
| **P1** | 完成现有单篇闭环 | 7 | 把已验证路径变成可重复、可审计的操作 |
| **P2** | 效率/复用/质量 | 6 | 资产台账、任务事件、批处理、风格一致性 |
| **P3** | 完整 AI 短剧能力 | 4 | 镜头状态、自动分镜、人物一致性、口型 |
| **P4** | 商业化/扩展 | 4 | BGM/SFX 授权、商用声音、平台发布/数据、多用户 |

---

## 1. P0：影响当前生产可靠性

### P0-1 TTS 默认模式与显式选择

| 项 | 内容 |
|---|---|
| **状态** | **PASS_VERIFIED（PRD-TTS-001）**：默认 0.5B zero-shot 已真实跑通；SFT 显式可选 |
| **目标** | **默认 CosyVoice2-0.5B zero-shot**；300M SFT 仅显式可选；UI/CLI/任务/manifest 记录实际 mode/model/voice；0.5B 失败不得回退 300M |
| **当前状态** | 默认 `tts.mode: zero_shot`；默认任务真实 0.5B；显式 SFT 仍可用；`PRD-TTS-001` 已关闭 |
| **涉及模块** | `src/drama_studio/voice/tts.py`、`src/drama_studio/config.py`、`scripts/r3_tts.py`、`workspace/tasks.py`、`web/js/pages/tasks.js`、`config/audio.yaml`、`config/settings.yaml`、`tests/test_voice_tts.py` |
| **前置** | 无；CosyVoice 两个运行时已在 `D:\AI\CosyVoice-Runtime` 核实 |
| **交付** | 默认切 `zero_shot`；默认启动/任务加载 0.5B；SFT 仍显式可选；manifest/UI/任务记录实际 mode/model/voice；0.5B 不可用即失败 |
| **验收（目标）** | 默认配置/默认任务真实加载 0.5B，manifest 记录 `zero_shot/CosyVoice2/0.5B/prompt`；SFT 必须显式且记录；0.5B 失败不回退；真实 1 行以上端到端；测试覆盖默认与显式两种 |
| **风险** | 改默认会影响现有任务/旧 manifest；需要兼容旧字段；UI 改动 |
| **工作量** | 剩余约 0.5 人日（改默认 + 测试/文档 + 真实 0.5B 复验） |
| **是否值得** | **是，P0 第一优先**。声音是内容的一部分，且当前证据与配置不一致 |

### P0-2 作品级风格锁定

| 项 | 内容 |
|---|---|
| **状态** | `IMPLEMENTED_NOT_VERIFIED`：`style_lock.py` 写 `_style_lock{revision,sha256,history}`；`motion.plan` / `aesthetic.plan` / `static.check` 拒绝不同 style；输出回查 lock |
| **目标** | 作品/期数 `style_id` 单一来源；期数/ProductionScript/Shot/资产继承；生成任务不得覆盖；改风格走新版本 |
| **当前问题** | DB 风格与 YAML preset 仍脱节；`comfy.batch` 不校验；新风格 UI 入口与真实改版生产未做 |
| **涉及模块** | `style_presets.py`、`production.py`、`workspace/tasks.py`、`workspace/store.py`、`workspace/discovery.py`、`aesthetic_plan.py`、`motion_build.py`、`config/styles.yaml`、DB schema |
| **前置** | P0-1 不依赖；可并行 |
| **交付** | 建立 DB 风格 ↔ YAML preset 映射；`ProductionScript` 已有 `style_id/style_sha256`，补 Shot/资产继承；任务参数移除或限制 `style` 覆盖；改风格创建新 snapshot/新 production 版本并记录；质量门校验同一 style_id |
| **验收** | 同一期数两次生成任务不能使用不同 style_id；改风格必须新建版本；P1 不需要手动 `--style ink_wash`；测试覆盖拒绝覆盖 |
| **风险** | 影响现有 P1/gongbi 风格 id；DB 迁移；工作台 UI |
| **工作量** | 3–5 人日 |
| **是否值得** | **是**。双风格是正式产品能力；不锁定就无法保证全片一致 |

### P0-3 静态质量门必须可执行、不可绕过

| 项 | 内容 |
|---|---|
| **状态** | `IMPLEMENTED_NOT_VERIFIED`：`motion.plan` 默认强制静态报告，缺失即失败；`--skip-static-gate` / 任务 `skip_static_gate` 显式跳过；`static.check` 任务已注册；真实端到端待跑 |
| **目标** | 动图前必须过静态门；工作台可触发；`motion.plan` 找不到报告时拒绝或显式跳过 |
| **当前问题** | `static_quality.py` 仍只在 CLI；`TASK_KINDS` 无静态任务；工作台不能直接触发 |
| **涉及模块** | `scripts/static_quality.py`、`workspace/tasks.py`、`web/js/pages/tasks.js`、`production.py`、`motion/render.py`、`discovery.py` |
| **前置** | 无 |
| **交付** | 注册 `static.check` 任务；`motion.plan` 读取显式 static 报告或 `--skip-static-gate`；工作台显示静态状态；报告路径可配置 |
| **验收** | 未过静态门时 `motion.plan` 默认失败；`--skip-static-gate` 需显式；工作台能跑；测试覆盖 |
| **风险** | 现有 P1/M7 没有 static 报告，会失败；需要兼容/显式跳过 |
| **工作量** | 1–2 人日 |
| **是否值得** | **是**。这是文档承诺的质量门，当前可静默绕过 |

### P0-4 工作流页与真实任务/状态对齐

| 项 | 内容 |
|---|---|
| **目标** | 工作流节点/边/文案反映 package/script/motion/aesthetic/static/quality 真实入口；不再写“未实现” |
| **当前问题** | `discovery.py:1061-1062,1082` 仍写“写入路径未实现”“分镜生成器未实现”“r3_tts.py 尚未参数化”；节点不含 package/script/motion/aesthetic |
| **涉及模块** | `workspace/discovery.py`、`web/js/pages/workflow.js`、`web/js/pages/tasks.js`、`workspace/tasks.py` |
| **前置** | P0-3（static 任务）可一起 |
| **交付** | 从 `TASK_KINDS`/真实产物生成节点；每节点 `task_kind` 可执行或明确“CLI only”；加 package/script/motion/aesthetic/static 节点 |
| **验收** | 页面不再出现过期文案；点击节点能到对应任务/说明；测试/截图 |
| **风险** | UI 改动；节点图变复杂 |
| **工作量** | 1–2 人日 |
| **是否值得** | **是**。UI 是最直观状态来源，当前会误导 |

### P0-5 证据索引与文档状态一致性

| 项 | 内容 |
|---|---|
| **目标** | 文档不再引用不存在的 run 路径；S3/M8-E/validation_status 状态统一；测试数/环境说明更新 |
| **当前问题** | `experiments/r0..r3b`、`s2a/s2b` 缺失；`docs/README.md` S3 PARTIAL vs ROADMAP/PRD NOT_RUN；ROADMAP M8-E 重复；`styles.yaml validation_status: NOT_RUN`；PRD/WORKSPACE_REPORT 测试数过期 |
| **涉及模块** | `docs/**`、`config/styles.yaml`（仅状态字段） |
| **前置** | 无 |
| **交付** | 本 Phase B 文档 + 更新 docs/README/root README；历史报告保留；路径加“已缺失/替代证据”；状态按 §2 三件事拆分 |
| **验收** | 文档链接全可解析；状态不再自相矛盾；历史报告不删不改结论 |
| **风险** | 大量文档改动；需人工核对 |
| **工作量** | 剩余约 0.5 人日（改默认 + 测试/文档 + 真实 0.5B 复验） |
| **是否值得** | **是**。避免后续把报告路径当可复跑入口 |

---

## 2. P1：完成现有单篇闭环

### P1-1 工作台“新生成”路径重新实证

| 项 | 内容 |
|---|---|
| **目标** | 修复后 `script.generate` 能在工作台真实调用 LLM 并成功（不是 `--reuse`） |
| **当前问题** | P1 真实 LLM 任务被后置校验标 FAILED；成功任务是 `--reuse` |
| **涉及模块** | `workspace/tasks.py`、`script_engine.py`、`production.py`、测试 |
| **前置** | 8080 启动 |
| **交付** | 新任务记录 + 真实 LLM 输出 + 后置 jobs 成功 |
| **验收** | 任务 SUCCEEDED、`script_raw_attempt*` 新、production_script 新、jobs 生成 |
| **风险** | LLM 输出不稳定；需要 2 次修复 |
| **工作量** | 0.5–1 人日（含运行） |
| **是否值得** | 是 |

### P1-2 `quality.check` 支持 motion manifest（UI+API）

| 项 | 内容 |
|---|---|
| **目标** | UI 能选/自动找 motion manifest，跑运动质量门 |
| **当前问题** | `QualityParams` 支持，`tasks.js` 只给 `manifest` |
| **涉及模块** | `tasks.js`、`tasks.py`、`discovery.py` |
| **前置** | 无 |
| **交付** | 表单字段/自动最新 motion manifest；结果展示 |
| **验收** | UI 能跑 `--motion-manifest`；报告可见 |
| **工作量** | 0.5 人日 |
| **是否值得** | 是 |

### P1-3 美学/运动结果进入派生状态

| 项 | 内容 |
|---|---|
| **目标** | 工作台能看到 A/B 对照、人工结论、motion plan 状态 |
| **当前问题** | `discovery` 不读 aesthetic/motion 文件；只有任务日志 |
| **涉及模块** | `discovery.py`、`api.py`、`episode.js` |
| **前置** | P0-2 风格锁定可一起 |
| **交付** | `aesthetic`/`motion` 派生字段 + 页面 |
| **验收** | 期数页显示 A/B 状态/联系表/结论；motion 计划/质量 |
| **工作量** | 1–2 人日 |
| **是否值得** | 是 |

### P1-4 81.373 s 工笔案例纳入索引与可重建

| 项 | 内容 |
|---|---|
| **目标** | 文档/工作台/案例库明确它是生产案例；可一键重建 |
| **当前问题** | 已纳入 docs/audit 与本 Phase B，但主 README/docs README 尚未索引；工作台未专门展示 |
| **涉及模块** | `docs/README.md`、根 `README.md`、`projects/.../PRODUCTION_REPORT.md`、工作台派生 |
| **前置** | 无 |
| **交付** | 文档索引 + 重建步骤 + 验收 |
| **验收** | 用户能从 README 找到案例并重建；路径/哈希/81.373 s 一致 |
| **工作量** | 0.5 人日 |
| **是否值得** | 是 |

### P1-5 文档状态统一（S3/M8-E/validation_status/测试数）

| 项 | 内容 |
|---|---|
| **目标** | 所有文档同一状态口径 |
| **当前问题** | 见 P0-5 |
| **涉及模块** | `docs/**`、`config/styles.yaml` |
| **前置** | 本 Phase B |
| **交付** | 状态词典引用唯一来源；S3 三件事；M8-E 去重 |
| **验收** | grep 不再有互相矛盾的状态 |
| **工作量** | 1 人日 |
| **是否值得** | 是 |

### P1-6 `doctor` 校验 styles/pronunciation/fonts

| 项 | 内容 |
|---|---|
| **目标** | 配置坏了 doctor 能发现 |
| **当前问题** | `_config_checks` 只 4 份 |
| **涉及模块** | `doctor.py`、`style_presets.py`、`fonts.py`、`pronunciation.py` |
| **前置** | 无 |
| **交付** | `cfg.load` 扩展或新检查 |
| **验收** | 故意破坏 styles.yaml/fonts.yaml 时 doctor FAIL |
| **工作量** | 0.5–1 人日 |
| **是否值得** | 是 |

### P1-7 死配置接线或删除

| 项 | 内容 |
|---|---|
| **目标** | `subtitles.*`、`narration_modes.leading_ms`、`generation.profiles` 不再是“看起来能改但无效”；TTS 模式已在 P0-1 接线 |
| **当前问题** | 见配置手册 §10 |
| **涉及模块** | `config/*.yaml`、`tts.py`、`r3_build.py`、`production.py`、`doctor.py` |
| **前置** | P0-1 已完成；可独立做 |
| **交付** | 接线或删字段 + 文档 |
| **验收** | 改配置有可观察效果；文档不再误导 |
| **工作量** | 1–2 人日 |
| **是否值得** | 是 |

---

## 3. P2：效率、复用、质量

### P2-1 统一资产台账/版本号

| 项 | 内容 |
|---|---|
| **目标** | 资产 ID、版本、来源、哈希、授权、引用关系统一 |
| **当前问题** | 只有目录扫描 + `assets/audio/manifest.json` 局部清单 |
| **涉及模块** | `workspace/discovery.py`、`assets/**`、新 schema |
| **前置** | P1 完成 |
| **交付** | 资产 manifest + 扫描/引用/临时分类 |
| **验收** | 每个成片可追溯素材/字体/音频/模型 |
| **风险** | 大范围数据迁移 |
| **工作量** | 3–5 人日 |
| **是否值得** | 中高；复用和授权都需要 |

### P2-2 任务事件/成本聚合

| 项 | 内容 |
|---|---|
| **目标** | 每个任务记录耗时/成本/重试/失败原因；批次摘要 |
| **当前问题** | 任务表只有状态/结果/日志；无成本字段 |
| **涉及模块** | `workspace/store.py`、`tasks.py`、UI |
| **前置** | P1 |
| **交付** | `task_events`/成本字段 + 汇总 |
| **验收** | 能按篇/阶段统计机器秒、重试、失败 |
| **工作量** | 剩余约 0.5 人日（改默认 + 测试/文档 + 真实 0.5B 复验） |
| **是否值得** | 中；批处理前需要 |

### P2-3 批处理与阶段级续跑

| 项 | 内容 |
|---|---|
| **目标** | 多篇独立目录、失败隔离、断点续跑、早晨清单 |
| **当前问题** | 只有 `r1_batch` job 级；无 orchestrator |
| **涉及模块** | 新 `orchestrator.py`、`tasks.py`、`workspace` |
| **前置** | P2-1/P2-2 |
| **交付** | 批次 runner + 恢复 |
| **验收** | 2 篇连续成功；失败隔离；清单 |
| **风险** | GPU 单飞/服务生命周期复杂 |
| **工作量** | 5–8 人日 |
| **是否值得** | 中；先完成单篇稳定 |

### P2-4 完整长篇 ContentPackage

| 项 | 内容 |
|---|---|
| **目标** | 18 联/36 句完整诗篇内容包，不超 schema 上限 |
| **当前问题** | 只跑 4 句夹具；上限未实测 |
| **涉及模块** | `content_package.py`、schema、语料 |
| **前置** | 语料/claims 审核 |
| **交付** | 完整包 + 限制记录 |
| **验收** | 全篇场景/字幕/claim 完整 |
| **工作量** | 1–2 人日 |
| **是否值得** | 是（M3 前置） |

### P2-5 风格一致性质量指标

| 项 | 内容 |
|---|---|
| **状态** | `IMPLEMENTED_NOT_VERIFIED`：`style_consistency.py` + `style.consistency`；P1 4 镜头技术 `RISK`（ΔE 18.67 / luma 47.23）；人工审片 PENDING |
| **目标** | 跨镜头风格一致性门（色板/材质/线条/风格分类） |
| **当前问题** | 已做调色板/跨镜头 LAB/亮度/饱和度/边缘密度；材质/线条分类仍无自动模型 |
| **涉及模块** | `quality.py`、`static_quality.py`、`aesthetics.py` |
| **前置** | P0-2 |
| **交付** | 风格指标 + 报告 + 阈值 |
| **验收** | 同风格通过、混风格报警 |
| **工作量** | 3–5 人日 |
| **是否值得** | 高（双风格产品核心） |

### P2-6 字幕配置接线

| 项 | 内容 |
|---|---|
| **目标** | `max_chars_per_line/max_lines/format/burn_in` 生效 |
| **当前问题** | 死配置；长句不换行 |
| **涉及模块** | `r3_build.py`、`voice/timeline.py`、`config/audio.yaml` |
| **前置** | P1-7 |
| **交付** | 自动换行/格式/烧录开关 |
| **验收** | 长句按配置换行；burn_in 可控 |
| **工作量** | 1–2 人日 |
| **是否值得** | 中 |

---

## 4. P3：完整 AI 短剧能力

| 任务 | 目标 | 当前问题 | 模块 | 前置 | 交付/验收 | 风险 | 工作量 | 值得 |
|---|---|---|---|---|---|---|---|---|
| P3-1 镜头级状态机 | `PENDING→…→COMPLETED` 持久化 | 只有枚举，无表/迁移 | `store.py`、`models.py`、`discovery.py` | P2-2 | 镜头状态表/迁移/恢复；可断点 | 状态一致性 | 5–8 人日 | 中高（批处理/续跑基础） |
| P3-2 自动文案/分镜增强 | 多镜头、人物/场景绑定 | LLM 只 3–5 镜头；无人物资产 | `script_engine.py`、`content_package.py` | P2-4 | 更稳定分镜 + 资产引用 | 人物一致性 | 5–10 人日 | 中（先有内容再谈） |
| P3-3 人物一致性 | 跨镜头同一张脸 | 未验证；ReferenceLatent 只空间锚点 | `character_manager/`（未实现）、FLUX 工作流 | R1 参考图 + 新模型/LoRA | 角色 bible + 锁 | 8 GB 显存/模型 | 10+ 人日 | 低（v1.0 明确不承诺） |
| P3-4 口型/数字人 | 对白口型 | 未实现 | 新模型/服务 | 人物一致性 | 口型片段 | 技术栈扩张 | 10+ 人日 | 低（v1.0 不做） |

---

## 5. P4：商业化与扩展

| 任务 | 目标 | 当前问题 | 模块 | 前置 | 交付/验收 | 风险 | 工作量 | 值得 |
|---|---|---|---|---|---|---|---|---|
| P4-1 BGM/SFX 授权与接入 | 完整听觉体验 | 空轨道；无授权 | `soundscape.py`、`assets/audio`、授权台账 | 曲目/音效授权 | 1 首 BGM + 1–2 音效；LUFS/TP；授权证据 | 平台/版权 | 2–3 人日 + 采购 | 高（R3-D 剩余） |
| P4-2 商用声音授权 | 中文女/克隆音可商用 | CosyVoice 权重/音色 UNVERIFIED | 授权/法务 | 供应商条款 | 书面许可/替代方案 | 法务 | 不确定 | 高（发布前必须） |
| P4-3 平台发布/数据 | 抖音/小红书包装与数据 | 只有规范 | 新模块 | 内容稳定 | 封面/标题/话题 + 数据记录 | 平台规则 | 3–5 人日 | 中（M4） |
| P4-4 多用户/公网 | 多人使用 | 本地单用户 | 架构 | v1.1 | 权限/部署 | 安全/成本 | 10+ 人日 | 低（v1.0 不做） |

---

## 6. 专题评估（用户点名）

### 6.1 R3-D 女声、BGM、音效与授权

- 女声：SFT 中文女已有人工试听与 P1/gongbi 成片；**默认模式需 P0-1 修复**。
- BGM/音效：`NOT_RUN`；`soundscape` 结构在，但 `ambience.track`/`bgm.track` 为空。
- 授权：字体/模型/自录声音有登记；预置音色/生成音频/商用条款 `UNVERIFIED`。
- 结论：**P0-1 + P4-1 + P4-2**；在授权前不得把音频用于可发布成片。

### 6.2 M3《洛神赋》

- 前置：R3-D（女声/BGM/音效/授权）+ P2-4 完整 ContentPackage。
- 现状：LI 五轮有真实记录，但人工审核 `NOT_RUN`、0 approved claim；视频步骤未开始。
- 结论：`NOT_RUN`，不要提前做“完整样片”。

### 6.3 双视觉管线生产化

- S1 规范/配置 `PASS_STATIC`。
- 每种风格 2 镜头技术样片 `PASS_VERIFIED`（M7）。
- 作品级锁定 `IMPLEMENTED_NOT_VERIFIED`；跨镜头一致性技术门 `IMPLEMENTED_NOT_VERIFIED`，人工审片 PENDING。
- 结论：**P0-2 + P2-5** 是生产化关键；不是再生成更多样片。

### 6.4 镜头级状态管理

- 现状：无表/无迁移/无事件。
- 价值：批处理/续跑/失败隔离的基础。
- 结论：P3-1，P2 之后。

### 6.5 自动文案和分镜

- 现状：LLM 3–5 镜头，真实 4 镜头；工作台新生成未重新实证。
- 结论：P1-1 先证明；再做 P3-2。不要先扩模型/Agent。

### 6.6 资产复用

- 现状：目录扫描 + 构建目录；无正式台账。
- 结论：P2-1；先解决“同一素材/字体/音频可追溯”，再谈跨篇复用。

### 6.7 断点续跑

- 现状：job 级（FLUX/TTS）有；阶段级无。
- 结论：P2-3；先把批处理/阶段状态做好。

### 6.8 批量生产

- 现状：`NOT_RUN`；理论 6–8 篇/夜（43.8 min/篇，未验证）。
- 结论：P2-3；先单篇稳定 + 成本聚合。

### 6.9 质量门

- 技术门强；静态门可绕过；运动/美学/风格门弱。
- 结论：P0-3 + P1-2 + P2-5。

### 6.10 平台发布和数据反馈

- 现状：只有规范；无发布/数据代码。
- 结论：P4-3；在内容稳定后再做。

---

## 7. Phase C 执行顺序（建议）

```text
第 1 步：P0-1 TTS 默认 0.5B zero-shot  ✅ PASS_VERIFIED
第 2 步：P0-2 作品级风格锁定（先做“任务不得覆盖 + DB/YAML 映射”）
第 3 步：P0-3 静态质量门注册/强制
第 4 步：P0-4 工作流页对齐
第 5 步：P1-1 工作台新生成实证
第 6 步：P1-2/P1-3 质量与美学/运动视图
第 7 步：P1-4/P1-5/P1-6/P1-7 索引/状态/doctor/死配置
第 8 步：P2-1/P2-2 资产台账/成本
第 9 步：P2-3 批处理/续跑
第 10 步：P2-4/P2-5 长篇/风格一致性
```

**不要**在 P0/P1 未完成时启动 M3 完整样片或批量生产。

---

## 8. 工作量口径

- 1 人日 ≈ 6 小时有效开发 + 测试 + 文档。
- 不含等待 GPU 生成的时间。
- 运行验证（真实 FLUX/Wan/TTS）另计机器时间。
- 工作量是量级估算，不是承诺；Phase C 每个任务再细化。

---

## 9. 明确不做（v1.0）

- 公网部署、多用户权限、自动发布。
- LangChain/向量库/多 Agent 框架。
- 自训练/微调生成模型。
- 电影级人物一致性、口型同步、跨镜头同一张脸。
- 8 GB 显存同时加载 LLM/FLUX/Wan。
- 自动发布、数字人、SeedVR2、新视频模型。
- 为未验证的市场假设扩大技术栈。
