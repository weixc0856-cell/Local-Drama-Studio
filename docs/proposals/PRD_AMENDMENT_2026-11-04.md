# PRD 变更提案：音频、多音色、运动、故事圣经与视听 QA

> 状态：**待项目所有者批准**。本文件不是正式 PRD，不改变 `docs/PRD.md` 的现行需求。
> 目的：把 `docs/proposals/` 中分散的 AUDIO / VOICE-ASSET / TTS-007 / MOTION / STORY / QA 需求合并成**一个**可批准、可追踪、无重复建设的变更包。
> 原则：正式 PRD 是唯一 SSOT；批准前，实现只能标 `IMPLEMENTED_NOT_VERIFIED` 或 `PARTIAL`，不得标 `PASS_VERIFIED`。

---

## 1. 为什么要合并

当前提案已经分别存在于：

- `PRD_AUDIOVISUAL_UPGRADE_PROPOSAL.md`：需求矩阵、音频/声音/运动/故事/QA；
- `AUDIOVISUAL_GAP_AUDIT.md`：代码缺口与数据流；
- `VOICE_ASSET_SOURCE_REVIEW.md`：外部声音来源与许可阻断。

如果分别批准，会出现两套音频资产台账、两套音色映射、两套 QA 口径。本变更包规定：

| 领域 | 唯一实现 | 禁止的重复建设 |
|---|---|---|
| 音频资产 | `assets/audio/manifest.json` + `voice/audio_assets.py` | 另建 BGM/SFX 数据库或第二份 manifest |
| 多轨时间线 | `voice/audio_timeline.py` sidecar | 改 `segments.json` 数组或把 BGM 写进 TTS manifest |
| 音色档案 | `config/voices.yaml` + `voice/profiles.py` | 在 `ProductionScript` 里塞 speaker，或按角色写代码分支 |
| 逐行选角 | `narration.json` 的 `voice_profile` 或 `voice_cast.yaml` sidecar | 第二套 cast JSON schema 与第一套并存 |
| 运动 | 现有 `motion/`（CameraMove / RegionSpec / PlateSpec） | 新建运动引擎或把运动决策交给 Wan |
| 故事圣经 | `bible.py` 的 CharacterBible / ShotBible sidecar | 改 LLM 的 `ProductionScript` 合同来承载角色表 |
| 视听 QA | `quality.py` + 结构化人工检查 sidecar | 用技术 PASS 代替听感/审美通过 |

---

## 2. 编号与冲突

正式 PRD 已使用：

- `PRD-TTS-001`：默认 0.5B zero-shot；
- `PRD-TTS-002`：SFT 显式可选；
- `PRD-TTS-003`：禁止静默回退；
- `PRD-TTS-004`：记录实际模式/模型；
- `PRD-TTS-005`：zero-shot 参考音/逐字文本；
- `PRD-TTS-006`：商用授权开放问题。

因此：

- 多音色/ Voice Profile 使用 **`PRD-TTS-007`**，不得复用 TTS-002；
- 音频系统使用 **`PRD-AUDIO-001..006`**；
- 声音资产治理使用 **`PRD-VOICE-ASSET-001..012`**；
- 运动使用 **`PRD-MOTION-001..004`**；
- 故事圣经使用 **`PRD-STORY-001..002`**；
- 视听 QA 使用 **`PRD-QA-001..002`**。

---

## 3. 需求矩阵（建议写入正式 PRD 的文本）

### 3.1 多音色（`PRD-TTS-007`）

| 项 | 内容 |
|---|---|
| 需求 | 一篇作品可混排 ≥2 个音色；每句可追溯到 `voice_profile_id`、实际模式、参考音哈希或 SFT speaker |
| 验收 | `config/voices.yaml` 严格加载；逐行/ sidecar 选角；同一次运行只允许一种后端（SFT 或 zero-shot）；未 `APPROVED` 档案默认拒绝；manifest 写 `voice_cast` |
| 当前实现 | `voice/profiles.py`、`config/voices.yaml`、`narration.json` 逐行 `voice_profile`、`voice_cast.yaml` sidecar、`audio_manifest.json.voice_cast`；10 个单测 + 2 行真实 zero-shot |
| 状态 | `IMPLEMENTED_NOT_VERIFIED`（缺完整多角色成片/UI 端到端） |

### 3.2 音频系统（`PRD-AUDIO-001..006`）

| 编号 | 需求 | 验收 | 当前实现 | 状态 |
|---|---|---|---|---|
| `PRD-AUDIO-001` | 多轨时间线（旁白/对白/BGM/SFX） | 严格 ms 时间、轨道类型、事件边界、重复 ID 拒绝 | `voice/audio_timeline.py` | `IMPLEMENTED_NOT_VERIFIED` |
| `PRD-AUDIO-002` | BGM 自动 ducking | narration/dialogue 触发；参数可记录 | `voice/mix.py` `sidechaincompress`；合成测试 | `IMPLEMENTED_NOT_VERIFIED` |
| `PRD-AUDIO-003` | SFX 定时与增益/淡入淡出 | 事件级时间、gain、fade | `voice/mix.py` | `IMPLEMENTED_NOT_VERIFIED` |
| `PRD-AUDIO-004` | 音频资产台账 | 单一 `assets/audio/manifest.json`；状态/许可/hash；生产只用 `VERIFIED/APPROVED` | `voice/audio_assets.py` | `IMPLEMENTED_NOT_VERIFIED` |
| `PRD-AUDIO-005` | 成片音频质量门 | 轨道存在、事件在界内、资产就绪、时长匹配 | `quality.check_audio_timeline` | `PARTIAL`（真实 BGM/SFX 听感未验） |
| `PRD-AUDIO-006` | 旧旁白路径兼容 | 不给 timeline 时行为不变 | `r3_build.py` 保留旧分支；真实 P1 14.0 s PASS | `PASS_VERIFIED`（兼容性） |

### 3.3 声音资产治理（`PRD-VOICE-ASSET-001..012`）

沿用 `VOICE_ASSET_SOURCE_REVIEW.md` 的 12 项，批准时只写入以下硬规则：

1. 外部声音来源必须有 `source_url`、许可类型、许可证据、`commercial_allowed`；
2. 只有 `APPROVED` 可进入正式 TTS；`TECHNICALLY_VALIDATED` / `LICENSE_VERIFIED` 只是候选；
3. 不镜像/再分发数据集；Common Voice 需 Mozilla Data Collective 账号与条款；
4. AISHELL-3 的 Apache-2.0 与第三方“学术-only”说法冲突，商用前必须书面澄清；
5. LibriVox 的公有领域结论按辖区复核；
6. 不根据音频推断性别/年龄/身份；只用数据集标签；
7. 3–8 s 是项目筛选规则，不是模型硬限制（CosyVoice 本地硬限制约 30 s）；
8. 声音资产引用 `asset_id`，不复制文件；Voice Profile 不另建资产库。

状态：`PARTIAL`；当前 0 个外部 `APPROVED` 声音，4 个候选。

### 3.4 运动产品化（`PRD-MOTION-001..004`）

| 编号 | 需求 | 当前实现 | 状态 |
|---|---|---|---|
| `PRD-MOTION-001` | 运镜模板可复用（static / push / pull / scroll / lateral / parallax） | `CameraMove` + `resolve_camera`；M1–M7 真实 | `PASS_VERIFIED`（技术） |
| `PRD-MOTION-002` | 局部微动区域合同 | `RegionSpec` + 刚体/时间门 | `PASS_VERIFIED`（技术） |
| `PRD-MOTION-003` | 局部动态类型（水/云/叶/芦苇/倒影/墨扩散） | `LocalMotionSpec` + M7 | `PASS_VERIFIED`（技术） |
| `PRD-MOTION-004` | 结构保护 | authored regions + rigid gate；无自动分割 | `PARTIAL` |

批准后只补“模板/参数文档 + UI 可选面”，不新建运动引擎，不把 Wan 作为默认运镜手段。

### 3.5 故事圣经（`PRD-STORY-001..002`）

| 编号 | 需求 | 验收 | 当前实现 | 状态 |
|---|---|---|---|---|
| `PRD-STORY-001` | 人物视觉锚点 | 角色 id/发型/服装/色板/道具/声音档案；不承诺同脸 | `bible.CharacterBible`；严格校验 | `PARTIAL` |
| `PRD-STORY-002` | 分镜连续性 | Shot Bible 覆盖全部脚本镜头；人物引用可解析；风格 id 一致 | `bible.ShotBible` + `check_story_bibles`；`story.check` 任务 | `PARTIAL` |

报告必须包含 `same_face_guarantee: false`。跨镜头同脸是人工视觉复核项，不是本需求的自动验收。

### 3.6 视听 QA（`PRD-QA-001..002`）

| 编号 | 需求 | 当前实现 | 状态 |
|---|---|---|---|
| `PRD-QA-001` | 技术检查：黑帧、时长、帧率、音画同步、轨道缺失、授权素材 | 现有图片/视频/音频/时间线技术门；缺音画同步与授权素材门 | `PARTIAL` |
| `PRD-QA-002` | 结构化人工视听验收 | `review.accept/reject` 写 `human_review.json`；无结构化听感清单 | `PARTIAL` |

建议的人工检查项：BGM 是否压过旁白、ducking 是否自然、SFX 是否对点、响度是否平台合规、音色是否符合角色、字幕是否与语音同步。

---

## 4. 提议写入 `docs/PRD.md` 的位置

| PRD 位置 | 变更 |
|---|---|
| §9.3（新增） | 运动产品化与结构保护 |
| §10.1（新增） | Character/Shot Bible 与“不承诺同脸” |
| §11.2（新增） | 多音色 / Voice Profile / `voice_cast` |
| §11.3（新增） | 多轨音频、ducking、SFX、资产台账 |
| §11.4（新增） | 声音资产治理与许可状态 |
| §17.1（新增） | 结构化视听 QA |
| §21 / §23 | 按证据更新状态；不得把提案实现写成 `PASS_VERIFIED` |

---

## 5. 批准后的执行顺序

1. 把 §3 的编号/验收/状态写入 `docs/PRD.md`；
2. 更新 `docs/REQUIREMENT_TRACEABILITY.md` 的正式矩阵与数量；
3. 把 `docs/proposals/` 标为“已合并”，保留历史；
4. 只对已有真实证据的项标 `PASS_VERIFIED`；其余保持 `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL`；
5. 再排 P2/P3 代码任务：真实 BGM/SFX 授权与听感、完整多角色成片、故事圣经作者 UI、视听人工清单。

---

## 6. 批准检查表

- [ ] 同意 `PRD-TTS-007` 编号（不复用 TTS-002）。
- [ ] 同意音频资产只保留 `assets/audio/manifest.json` 一套台账。
- [ ] 同意 Voice Profile 只引用 `asset_id`，不复制音频。
- [ ] 同意同一次 TTS 运行只能加载一种后端（SFT 或 zero-shot）。
- [ ] 同意外部声音只有 `APPROVED` 可进生产。
- [ ] 同意“同脸”不是自动验收项，必须人工复核。
- [ ] 同意提案实现不得在批准前标 `PASS_VERIFIED`。

未勾选前：本文件保持提案状态，不修改正式 PRD 的需求正文。
