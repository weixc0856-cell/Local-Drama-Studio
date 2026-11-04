# PRD 视听生产能力升级提案

> 文档状态：**PROPOSAL / 待审**（2026-11-04）。不是正式 PRD，未批准前不得据此开工。
> 唯一需求来源：[../PRD.md](../PRD.md)。本提案只提出修改方案；批准后才写入 PRD。
> 差距证据：[AUDIOVISUAL_GAP_AUDIT.md](AUDIOVISUAL_GAP_AUDIT.md)。
> 原则：不推倒现有技术栈；不把 Gemini 建议直接当成已完成能力；不改变 A750 8 GB / GPU 单飞 / 双风格定位。

---

## 1. 产品目标调整（建议）

把 PRD §3 的产品目标从“单篇竖屏视频生产”提升为：

> 面向东方历史、人文、诗词与文化故事内容，构建本地优先、可复现、低人工干预的**视听内容生产系统**。系统通过统一内容脚本、分镜规划、视觉风格控制、镜头运动、角色配音、背景音乐、环境音效和时间轴合成，生产具有完整叙事结构与视听表现力的短视频作品。

三个边界：

1. 目标是完整视听表达，不是单纯生成图片/视频。
2. 目标是稳定生产，不是每个镜头都用 AI 视频模型。
3. 目标是逐步接近参考视频的表达质量，不承诺现有硬件/模型能复刻参考视频。

两种正式风格不变：`court_green_fine_line` / `ink_wash`。一篇作品只能选一种主风格；音频、分镜、运动、合成共用，视觉规范独立。

---

## 2. 建议新增的需求域

| 域 | 优先级 | 说明 |
|---|---|---|
| A. 多轨音频 | **P1（最高）** | 旁白/对白/BGM/SFX 统一时间轴、闪避、淡入淡出、授权 |
| B. 角色与多音色 | P1–P3 | Voice Profile、角色映射、参考音/文本、生成记录 |
| C. 镜头运动与图层 | P2 | 复用现有 CameraMove/LocalMotion/PlateSpec，产品化 |
| D. 叙事与分镜连续性 | P3 | Character Bible、Shot Bible；不承诺同脸 |
| E. 视听质量门 | P3 | 音频/视频/同步/授权/人工验收 |

> 编号提醒：正式 PRD 已使用 `PRD-TTS-002` 表示“SFT 显式可选”。本提案的“多音色角色映射”**不得复用 TTS-002**，建议使用 `PRD-TTS-007`。

---

## 3. 建议需求矩阵（初始状态按仓库审计）

> 状态使用 PRD §0.2 六态。`PASS_VERIFIED` 只在有真实运行证据时使用；本表除 MOTION 的既有真实样片外，多数是 `PARTIAL/NOT_IMPLEMENTED`。

| 编号 | 需求 | 优先级 | 依赖 | 验收标准 | 当前状态 | 代码/证据 |
|---|---|---|---|---|---|---|
| `PRD-TTS-001` | 默认 CosyVoice2-0.5B zero-shot；SFT 显式可选 | P0 | 无 | 默认任务真实加载 0.5B；manifest 记录 `zero_shot/CosyVoice2`；SFT 显式且可追溯；失败不回退 | `PASS_VERIFIED` | 正式 PRD 已有；默认 zero-shot 2 行 + 显式 SFT 1 行 PASS |
| `PRD-TTS-007` | 多音色角色映射 | P1/P3 | Voice Profile schema | 一篇作品混排 ≥2 音色；每句可追溯 `voice_profile_id`/参考音哈希 | `IMPLEMENTED_NOT_VERIFIED` | `config/voices.yaml`、`voice/profiles.py`、逐行 `voice_profile`、`voice_cast.yaml` sidecar、`audio_manifest.json.voice_cast`；10 单测 + 2 行真实 zero-shot + 2 行真实 sidecar；完整多角色成片待做 |
| `PRD-AUDIO-001` | 多轨音频数据结构 | P1 | 无 | 能描述 narration/dialogue/bgm/sfx 四类轨道与事件 `start_ms/duration_ms` | `PASS_VERIFIED` | `voice/audio_timeline.py` + 严格校验 + tests |
| `PRD-AUDIO-002` | 统一时间轴混音 | P1 | AUDIO-001 | 多轨素材按时间正确合成；事件边界/时长/缺失素材可校验 | `PASS_VERIFIED` | `voice/mix.py` + 合成 BGM/SFX 实测；`r3_build --audio-timeline` 真实 P1 narration 链路 |
| `PRD-AUDIO-003` | BGM Sidechain Ducking | P1 | AUDIO-001/002 | 旁白期间 BGM 自动降低，结束后平滑恢复；参数有听感/测量记录 | `IMPLEMENTED_NOT_VERIFIED` | `mix.py` 生成 `sidechaincompress`；合成 BGM 测试通过；真实 BGM 听感未做 |
| `PRD-AUDIO-004` | SFX 定位/增益/淡入淡出 | P1 | AUDIO-001/002 | SFX 可独立定位、调增益、淡入淡出；缺失即失败或显式降级 | `PASS_VERIFIED` | `mix.py` + 合成 SFX 实测；asset registry 校验 |
| `PRD-AUDIO-005` | 音频资产与授权台账 | P1 | 无 | 每个 BGM/SFX/参考音有 asset_id、来源、许可、哈希、时长、状态 | `PARTIAL` | `voice/audio_assets.py` 已读取/校验；真实 BGM/SFX 授权资产仍为空 |
| `PRD-AUDIO-006` | 音频质量检查 | P1 | AUDIO-001/002 | 检查静音、削波、时长、响度、轨道缺失、ducking 生效 | `PASS_VERIFIED`（结构/资产） | `quality --audio-timeline` 检查事件/资产；混音响度仍由 `quality --manifest`；ducking 听感未做 |
| `PRD-MOTION-001` | 镜头运动模板 | P2 | 无 | static/push/pull/pan 可用且参数校验；真实样片 | `PASS_VERIFIED`（技术） | `CameraMove` 已有 static/push/pull/scroll/lateral/push+pan；M7/P1 真实 |
| `PRD-MOTION-002` | 图层视差 | P2 | PlateSpec | 前景/中景/背景独立运动；无露洞/漂移 | `PARTIAL` | `motion/plates.py` + M8 真实渲染 PASS_STATIC；opt-in |
| `PRD-MOTION-003` | 局部动态 | P2 | RegionSpec | 限定区域水/云/叶/芦苇/倒影/墨扩散；结构不破坏 | `PASS_VERIFIED`（技术） | M1/M2/M7 真实；区域合同验证 |
| `PRD-MOTION-004` | 结构保护 | P2 | RegionSpec/质量门 | 主体/建筑/线条无明显变形；区域合同可追溯 | `PARTIAL` | authored regions + 刚体门；无自动分割 |
| `PRD-STORY-001` | 人物视觉锚点 | P3 | Character Bible | 年龄段/发型/服饰/朝代特征可复用；不承诺同脸 | `PARTIAL` | `drama_studio/bible.py` 严格 CharacterBible（锚点/服装/色板/声音档案）；无作者 UI/真实作品 Bible |
| `PRD-STORY-002` | 分镜连续性 | P3 | Shot Bible | 镜头与台词/人物/场景/前后镜关系明确 | `PARTIAL` | `ShotBible` + 覆盖/引用/风格校验；`ScriptShot` 仍无角色/地点字段 |
| `PRD-QA-001` | 视频自动检查 | P3 | 无 | 黑帧、时长、帧率、音画同步、轨道缺失、授权素材 | `PARTIAL` | 有解码/尺寸/哈希/逐行音频；无 BGM/SFX/ducking/同步门 |
| `PRD-QA-002` | 人工视听验收 | P3 | QA-001 | 保存结构化审查结果与问题记录 | `PARTIAL` | `review.accept/reject` 写 `human_review.json`；无结构化清单 |

---

## 4. 多轨音频数据结构（建议）

### 4.1 不修改 `segments.json` 的数组形状

`segments.json` 当前是 JSON 数组，`r3_build.py`、`workspace/discovery.py`、`production.build_segments` 都按数组消费。**新增 `audio_tracks` 到数组会破坏所有消费者。**

建议新增 sidecar：

```text
work/
├─ audio_manifest.json        # 旁白/对白 TTS 行（保留现有）
├─ audio_timeline.json        # 新增：多轨事件时间轴
├─ audio_assets.json          # 或 assets/audio/manifest.json（全局资产）
└─ segments.json              # 不变
```

`r3_build.py` 新增可选 `--audio-timeline`；没有该参数时保持旧行为（逐行 adelay/amix），保证历史兼容。

### 4.2 `audio_timeline.json` 建议 schema

```json
{
  "schema_version": "1.0",
  "sample_rate": 48000,
  "duration_ms": 60000,
  "tracks": [
    {
      "track_id": "narration_main",
      "type": "narration",
      "gain_db": 0.0,
      "events": [
        {
          "event_id": "nar_001",
          "asset_id": "voice_001",
          "line_id": "line_001",
          "start_ms": 0,
          "duration_ms": 5200,
          "fade_in_ms": 0,
          "fade_out_ms": 100
        }
      ]
    },
    {
      "track_id": "dialogue_main",
      "type": "dialogue",
      "gain_db": 0.0,
      "events": []
    },
    {
      "track_id": "bgm_main",
      "type": "bgm",
      "asset_id": "bgm_001",
      "gain_db": -18.0,
      "loop": true,
      "fade_in_ms": 1500,
      "fade_out_ms": 3000,
      "ducking": {
        "enabled": true,
        "trigger_track_ids": ["narration_main", "dialogue_main"],
        "threshold": 0.03,
        "ratio": 8.0,
        "attack_ms": 20,
        "release_ms": 500
      }
    },
    {
      "track_id": "sfx_main",
      "type": "sfx",
      "gain_db": -12.0,
      "events": [
        {
          "event_id": "sfx_001",
          "asset_id": "wind_001",
          "start_ms": 3000,
          "duration_ms": 8000,
          "gain_db": -12.0,
          "fade_in_ms": 1000,
          "fade_out_ms": 1500
        }
      ]
    }
  ]
}
```

规则：

1. 所有时间整数毫秒；`start_ms + duration_ms` 不得越过 `duration_ms`（除非显式 `allow_overflow`）。
2. 事件必须引用 `asset_id`；资产必须在 `audio_assets`/manifest 中存在且 `status=VERIFIED`，否则失败或显式 `ALLOW_PENDING_ASSET`（默认不允许）。
3. 轨道参数与事件参数分离；事件可覆盖轨道增益。
4. BGM 可循环/裁剪；SFX 不循环。
5. 旁白/对白事件应由 `audio_manifest.lines` 派生，不允许手工伪造时间。
6. 缺失可选 BGM/SFX 可按规则降级；缺失旁白/对白事件必须失败。

### 4.3 音频资产台账

建议扩展现有 `assets/audio/manifest.json`（不新建第二套清单）：

```json
{
  "schema": "1.1",
  "assets": [
    {
      "asset_id": "bgm_001",
      "asset_type": "bgm",
      "path": "assets/audio/bgm/guqin_calm_01.wav",
      "source_url": "https://...",
      "license_type": "CC0",
      "license_evidence": "assets/audio/licenses/bgm_001.txt",
      "attribution_required": false,
      "file_sha256": "...",
      "duration_ms": 60000,
      "commercial_allowed": true,
      "status": "VERIFIED"
    }
  ]
}
```

字段兼容：现有 `id`/`kind` 可映射为 `asset_id`/`asset_type`；新代码应同时接受旧字段并输出迁移警告。

> 首批只验证：1 首舒缓 BGM、1 首情绪递进 BGM、风声/水声/鸟鸣、1 组转场音效。不要先建大曲库。

---

## 5. Voice Profile 与多音色（建议）

> **2026-11-04 实现状态**：`config/voices.yaml` + `src/drama_studio/voice/profiles.py` 已实现只读档案、`APPROVED` 状态门、SFT/zero-shot 互斥校验、逐行 `voice_profile` 与 `audio_manifest.json.voice_cast`。正式 PRD 尚未批准本编号；完整多角色成片、UI 端到端与写库仍未做。

### 5.1 Voice Profile schema

建议 `config/voices.yaml`（或 `assets/voices/*.json`）：

```yaml
schema_version: "1.0"
profiles:
  - voice_profile_id: voice_narrator_01
    name: 历史旁白
    provider: cosyvoice
    model: CosyVoice2-0.5B
    mode: zero_shot
    reference_audio: assets/voices/narrator.wav
    reference_text: "对应参考音频的逐字文本"
    language: zh
    rights:
      voice_rights: self-owned | licensed
      license_doc: assets/voices/VOICE_RIGHTS.md
    status: VERIFIED
  - voice_profile_id: voice_character_01
    name: 历史人物角色
    provider: cosyvoice
    model: CosyVoice2-0.5B
    mode: zero_shot
    reference_audio: assets/voices/character.wav
    reference_text: "对应参考音频的逐字文本"
    language: zh
    rights:
      voice_rights: licensed
      license_doc: assets/voices/CHARACTER_RIGHTS.md
    status: PENDING
```

规则：

- `mode=zero_shot` 必须是 0.5B；`mode=sft` 必须是 300M-SFT + preset speaker。运行时不匹配 → 失败。
- 参考音/参考文本缺失 → 失败；不得回退到全局 speaker。
- `status=PENDING` 的 profile 不得进入正式生产（除非显式 `allow_pending_voice`）。
- Voice Profile 不写进 `workspace.db` 作为业务状态；可作为配置/资产读取。

### 5.2 台词角色映射

建议不直接改 LLM 的 `DraftScript` 合同，先加 sidecar：

```text
work/
├─ voice_cast.json
└─ narration.json
```

```json
{
  "schema_version": "1.0",
  "cast": [
    {"line_id": "line_001", "role": "narrator", "voice_profile_id": "voice_narrator_01"},
    {"line_id": "line_002", "role": "character", "voice_profile_id": "voice_character_01"}
  ]
}
```

`tts.py` 按 `line_id` 取 profile；`narration.json` 保留向后兼容的全局 `speaker`。后续再决定是否把 `speaker_role`/`voice_profile_id` 写进 `ScriptLine`（需同步 LLM 合同）。

第一阶段只支持：`narrator` / `character` / `poetry_reader`。情绪标签仅作为生成参数/人工指导，不假设 TTS 能准确执行。

---

## 6. 镜头运动与图层（复用现有能力）

### 6.1 命名映射

| 提案名 | 现有 | 处理 |
|---|---|---|
| `static` | `CameraMove.static` | 直接使用 |
| `slow_push_in` | `CameraMove.slow_push_in` | 直接使用 |
| `slow_pull_out` | `CameraMove.slow_pull_out` | 直接使用 |
| `pan_left` / `pan_right` | `scroll_pan` + `direction=ltr/rtl` | 文档别名，不新增枚举 |
| `parallax` | `layered_parallax` + `PlateSpec` | 保持 opt-in；需 plates |
| `local_motion` | `LocalMotionSpec` + `local_policy` | 直接使用 |

### 6.2 镜头运动配置（建议）

在 `motion_shots.json` 的 `ShotSpec` 中已有 `camera`/`local_motion`/`regions`/`plates`；建议增加可选的 `motion_template` 名称只作文档/审计，不新增引擎：

```json
{
  "id": "shot_001",
  "motion": "slow_push_in",
  "camera": {
    "move": "slow_push_in",
    "scale_start": 1.0,
    "scale_end": 1.08,
    "easing": "ease_in_out",
    "focus": [0.5, 0.48]
  },
  "regions": [
    {"id": "architecture", "role": "rigid_object", "permission": "locked", "box": {"x0":0.1,"y0":0.2,"x1":0.9,"y1":0.8}},
    {"id": "main_character", "role": "rigid_object", "permission": "locked", "box": {"x0":0.4,"y0":0.3,"x1":0.6,"y1":0.9}}
  ]
}
```

### 6.3 Wan 定位

Wan 是**可选生成式动态工具**，不是基础运动引擎。仅用于局部水流/云雾/火焰/烟雾/少量氛围镜头；不用于精确人物走位、多人物互动、手部动作、跨镜头身份一致性、严格空间路径。全片 Wan 化不进入 v1.x。

### 6.4 人物一致性等级

| 等级 | 目标 | v1.x |
|---|---|---|
| L1 | 服饰/发型/年龄段/朝代特征基本稳定 | 必须支持 |
| L2 | 主要人物视觉特征在不同镜头较接近 | 尽力改善、人工验收 |
| L3 | 跨镜头同脸/精确身份一致 | **非目标** |

---

## 7. FFmpeg 多轨混音技术方案

> 以下是**技术方案/原型**，不是生产实现；参数需用真实旁白/BGM 调试。

### 7.1 输入

```text
narration/dialogue: 逐行 WAV（audio_manifest.lines）
BGM: 单文件或循环片段
SFX: 每个事件一个 WAV
```

### 7.2 处理顺序

```text
1. 旁白/对白：按 start_ms adelay；必要时 atrim/afade/volume
2. BGM：-stream_loop -1 → atrim → volume → afade in/out
3. SFX：每个事件 adelay → volume → afade in/out
4. Ducking：BGM 与旁白/对白 sidechaincompress；输出 ducked BGM
5. 总混音：amix normalize=0 → alimiter
6. 响度：两遍 loudnorm（现有 soundscape 已有两遍法）
7. 输出：48 kHz mono PCM s16le
8. 检查：峰值/响度/时长/静音/轨道缺失
```

### 7.3 Ducking 原型

```bash
ffmpeg \
  -i bgm.wav \
  -i narration.wav \
  -filter_complex \
  "[0:a]volume=-18dB[bgm]; \
   [bgm][1:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[ducked]; \
   [1:a][ducked]amix=inputs=2:duration=first:normalize=0[mix]" \
  -map "[mix]" -c:a pcm_s16le final_mix.wav
```

注意：

- `sidechaincompress` 的实际闪避由 threshold/ratio/attack/release 决定，不是固定 `-8 dB`。
- 是否让对白也触发 BGM 闪避，需产品确认。
- 生产实现必须加 SFX 事件、轨道增益、淡入淡出、缺失素材/时长不足的明确错误。

### 7.4 兼容旧路径

- 没有 `audio_timeline.json` 时，`r3_build` 保持现有逐行 `adelay/amix` 行为，字节级行为不变。
- 有 `audio_timeline.json` 时，新混音路径接管；旧 `soundscape.enabled` 仍作为母带阶段。
- `build_manifest` 增加 `audio_timeline`（路径+哈希）与 `audio_qa`，旧字段保留。

---

## 8. 叙事连续性与质量门（建议）

### 8.1 Character Bible

```json
{
  "character_id": "char_001",
  "name": "角色名称",
  "period": "宋代",
  "visual_anchors": {
    "age_range": "中年",
    "body_type": "清瘦",
    "hairstyle": "束发",
    "clothing": "深青色交领长袍",
    "accessories": ["冠帽"],
    "art_style": "court_green_fine_line"
  },
  "negative_constraints": ["现代服饰", "现代发型", "明显西式服装"]
}
```

史料约束：服饰/冠帽/器物/建筑形制必须来自来源登记；视觉提示词不能替代史料核验。

### 8.2 Shot Bible

每个镜头记录：人物、地点、时间/季节、景别、主体位置、主色、运动、对应旁白/对白、与前后镜头关系。

### 8.3 质量门

| 层 | 检查 |
|---|---|
| 自动技术 | 文件存在/可解码/时长/峰值/响度/静音/削波/黑帧/帧率/音画同步/事件越界/资产缺失/未授权 |
| 人工视听 | BGM 情绪匹配、旁白自然度、音效突兀、镜头重复、运动破坏主体、风格统一、历史常识 |

人工结论写入 `human_review.json`，技术 PASS 不等于内容通过。

---

## 9. PRD 修改计划（批准后才执行）

| PRD 位置 | 建议修改 |
|---|---|
| §3 产品目标 | 增加“完整视听作品生产”目标与三条边界 |
| §7 内容生产流程 | 增加音频计划/混音阶段；明确音频先于复杂运动 |
| §9 双风格 | 增加两风格的运动/结构保护规范；不混用 |
| §10 媒体生成 | 增加 Motion Template 映射、Layer Composition、Shot Bible；Wan 仅可选 |
| §11 音频 | 扩展为多轨音频：narration/dialogue/bgm/sfx、事件时间轴、ducking、授权、混音 |
| §12 合成 | 统一视频/旁白/对白/BGM/SFX 时间轴；旧路径兼容 |
| §17 质量 | 增加音频/视频/同步/授权/人工视听门 |
| §19 非目标 | 保留不做跨镜头同脸/复杂人物动作/全片 Wan |
| §21 当前状态 | 按审计更新 AUDIO/TTS/MOTION/STORY/QA 状态 |
| §22 优先级 | P0 TTS 默认 → P1 音频 → P2 运动 → P3 连续性/质量 |
| §23/追踪矩阵 | 批准后新增 `PRD-AUDIO-001..006`、`PRD-TTS-007`、`PRD-MOTION-001..004`、`PRD-STORY-001..002`、`PRD-QA-001..002`；不改已有 TTS-001..006 编号 |

> 本提案**没有**把这些需求写入正式 PRD。待你确认后再修改 `docs/PRD.md` 与 `docs/REQUIREMENT_TRACEABILITY.md`。

---

## 10. 实施批次与依赖

### 批次 0（P0，关闭已有缺口）

1. TTS 默认切换为 CosyVoice2-0.5B zero-shot；
2. SFT 保留显式；
3. 参考音/参考文本/失败路径真实复验；
4. 更新 PRD/追踪矩阵。

**完成标准**：真实 0.5B 默认调用、真实音频、可追溯 manifest；不是只改配置字符串。

### 批次 1（P1，多轨音频最小闭环）

1. `audio_timeline.json` schema + 校验；
2. `audio_assets` 台账（先 1 BGM + 1 组 SFX）；
3. `r3_build --audio-timeline` 混音；
4. BGM ducking + SFX 定位；
5. 音频 QA（峰值/响度/静音/事件边界/授权）。

**完成标准**：一条完整作品从脚本到最终混音自动生成；旧路径不回归。

### 批次 2（P2，运动产品化）

1. 复用 CameraMove/LocalMotionSpec/RegionSpec/PlateSpec；
2. 文档化模板别名；
3. 两种风格验证；
4. Wan 只做可选英雄镜头；
5. 结构保护质量门。

**完成标准**：同一篇作品使用 ≥3 种运动，主体/建筑/线条无明显破坏。

### 批次 3（P3，叙事/多音色/质量门）

1. Voice Profile + `voice_cast.json`；
2. Character Bible/Shot Bible；
3. 多音色混排；
4. 连续性检查；
5. 自动技术检查 + 人工视听验收。

**完成标准**：60–90 s 样片可复现、可检查、可定位问题。

---

## 11. 60–90 s 升级样片验收

| 项 | 要求 |
|---|---|
| 时长 | 60–90 s |
| 风格 | 单一主风格（工笔或水墨） |
| 旁白/角色 | ≥2 种音色 |
| 音频 | 旁白 + BGM + SFX；BGM ducking 生效 |
| 运动 | ≥3 种镜头运动；Wan 可选，不要求全片 |
| 检查 | 时间轴对应、ducking、SFX 位置、风格统一、无主体变形/闪烁、授权完整、MP4 可播放、配置/哈希保留 |

> 这是 v1.x 视听升级的验收样片；不要求使用全部模型，也不要求每个镜头都是视频。

---

## 12. 暂不纳入 v1.x

- LoRA 人物训练；
- 跨镜头同脸保证；
- 全自动人物动作；
- 复杂 3D 摄影机；
- 全片 Wan；
- AI 自动判断历史真实性；
- 自动发布；
- 大规模音乐素材库。

---

## 13. VOICE-ASSET：Prompt 音频资产发现、验证与管理（合并提案）

> 来源核验与首批候选：[VOICE_ASSET_SOURCE_REVIEW.md](VOICE_ASSET_SOURCE_REVIEW.md)。
> 目标：把“临时找一段声音”变成可追溯、可授权、可复用的 Prompt 音频资产库；**不把自动检索当成自动授权**。

### 13.1 需求编号

| 编号 | 需求 | 优先级 | 初始状态 |
|---|---|---|---|
| `PRD-VOICE-ASSET-001` | 多来源音频数据集发现（Common Voice / OpenSLR / LibriVox / Internet Archive / 本地） | P1 | `PARTIAL`（人工核验来源已完成；adapter 未实现） |
| `PRD-VOICE-ASSET-002` | 数据集许可证与来源注册 | P1 | `PARTIAL`（来源结论已记录；registry 代码未实现） |
| `PRD-VOICE-ASSET-003` | 合规下载与素材缓存 | P1 | `NOT_IMPLEMENTED` |
| `PRD-VOICE-ASSET-004` | 自动音频切片（3–8 s；16 kHz mono） | P1 | `PARTIAL`（本轮手工切片 1 条；无自动切片器） |
| `PRD-VOICE-ASSET-005` | 原始文本与音频对齐 | P1 | `PARTIAL`（1 条 ASR 匹配；无通用对齐器） |
| `PRD-VOICE-ASSET-006` | 音频质量自动检测（削波/静音/噪声/完整度） | P1 | `PARTIAL`（1 条手工电平/静音检查；无自动门） |
| `PRD-VOICE-ASSET-007` | 授权人工审核工作流 | P1 | `NOT_IMPLEMENTED` |
| `PRD-VOICE-ASSET-008` | Prompt 音频资产注册表 | P1 | `PARTIAL`（候选 registry JSON 已建；未并入正式 manifest） |
| `PRD-VOICE-ASSET-009` | Voice Profile 管理 | P2 | `PARTIAL`（只读加载/状态门/asset_id 引用已实现；无写入 UI/DB） |
| `PRD-VOICE-ASSET-010` | CosyVoice Prompt 试听与效果评测 | P2 | `NOT_IMPLEMENTED` |
| `PRD-VOICE-ASSET-011` | 资产版本、哈希、授权变更追踪 | P2 | `PARTIAL`（单条 meta 有 hash；无版本链） |
| `PRD-VOICE-ASSET-012` | 定期检查数据源更新 | P3 | `NOT_IMPLEMENTED` |

### 13.2 与 AUDIO/TTS 合并（避免两套系统）

- **只保留一套资产注册表**：`PRD-AUDIO-005`（音频资产台账）与 `PRD-VOICE-ASSET-008` 共用 `assets/audio/manifest.json` 扩展；`asset_type` 增加 `tts_prompt`，不新建第二套 registry。
- `VOICE-ASSET` 只管理 `tts_prompt`；BGM/SFX 仍由 `PRD-AUDIO-004/005` 管理。
- Voice Profile（`PRD-TTS-007`）引用 `asset_id`，不复制音频；一个 profile 可关联多个候选，一个候选可被多个 profile 引用。
- `PRD-AUDIO-005` 的授权字段（source/license/hash/status）直接服务 VOICE-ASSET，不重复定义。
- 只有 `APPROVED` 的 prompt 才能进入 `PRD-TTS-001/002/007` 的正式生产；`TECHNICALLY_VALIDATED`/`LICENSE_VERIFIED` 只是候选。

### 13.3 来源优先级（基于本轮核验）

| 来源 | 结论 | 处理 |
|---|---|---|
| Mozilla Common Voice | CC0 数据集，但 MDC 账号/条款、禁止镜像/重新识别 | `BLOCKED`；不下载、不转存；先决定是否注册 MDC |
| AISHELL-3 | OpenSLR 标 Apache-2.0，但第三方“仅学术”说法冲突；19 GB | `BLOCKED`；先取得书面澄清，不批量下载 |
| LibriVox | 美国公有领域、允许商用；其他辖区需复核 | 已拉取 1 条《鹿柴》候选；`TECHNICALLY_VALIDATED`，不批准中国商用 |
| Internet Archive 其他 | 逐条权利 | `DISCOVERED`；逐条审 |
| Piper/Sherpa | 逐 Voice Model Card | 仅测试源 |
| 自录 | 自有权 | `LICENSE_VERIFIED`；人工试听后 `APPROVED` |

### 13.4 状态机

```text
DISCOVERED
  -> TECHNICALLY_VALIDATED
  -> LICENSE_VERIFIED
  -> APPROVED
  -> REVOKED (授权失效/新风险)
任意状态 -> REJECTED / BLOCKED
```

只有 `APPROVED` 可进入正式 TTS 生产。`BLOCKED` 必须写原因；不得把 `BLOCKED` 当 `APPROVED`。

### 13.5 首批种子目标

| 类型 | 目标 | 当前 |
|---|---|---|
| 旁白 | 3–5 | 0 `APPROVED`；2 个 AISHELL-3 Sample 候选（SSB1711 未标性别；SSB0009 female 为第三方标签） |
| 诗词朗诵 | 2–3 | 0 `APPROVED`；1 个 LibriVox 美国公有领域候选 |
| 角色 | 2–3 | 0 `APPROVED`；AISHELL-3 Sample 可作角色基础候选 |
| 合计 | — | 0 `APPROVED`；4 个候选（自录 / LibriVox / AISHELL-3 ×2） |

目标不是当前素材数量；当前没有外部音色被批准进入正式生产。

---

## 14. 待你确认

1. 是否批准本提案的需求域、编号与优先级。
2. 多轨音频用 sidecar `audio_timeline.json`（建议）还是改 `segments.json`。
3. Voice Profile 放 `config/voices.yaml` 还是 `assets/voices/*.json`；是否进 DB。
4. BGM/SFX 首批素材与授权来源。
5. 多音色角色映射放 P1 还是 P3。
6. 60–90 s 样片使用哪篇内容/风格；是否复用 81.373 s 工笔素材。
7. `PRD-TTS-007` 编号是否批准（避免与现有 TTS-002 冲突）。
8. `PRD-VOICE-ASSET-001..012` 是否批准，以及是否与 `PRD-AUDIO-005` 共用同一资产注册表。
9. Common Voice 是否注册 MDC 账号；AISHELL-3 是否向提供方书面澄清 Apache-2.0 商用范围。
10. LibriVox 候选是否接受“美国公有领域、中国辖区待复核”的临时 `TECHNICALLY_VALIDATED` 状态。

**批准前不写入正式 PRD、不开始大规模代码开发。**
