# LI-2-A 审计与内容包 Schema

> 日期：2026-11-03
> 阶段：LI-2-A only（审计 + Schema）
> 未调用模型、未生成音频/图像/视频、未修改 R3 生产行为、未提交/推送

## 1. 现有实现审计

### 1.1 原文与来源

- `literary_intelligence/corpus/luoshen_fu/` 保存固定原文、规范化文本、字符映射、segments、source registry、claims、reviews。
- 来源：Wikisource `洛神賦`，`oldid=7908816`。
- 原文 SHA-256 和 normalized SHA-256 已登记。
- 古代文本属公有领域；Wikisource 页面转录为 CC BY-SA 4.0/GFDL；商业条款仍需复核。
- `source_registry.py` 校验文件存在、原文/规范化哈希和 locator。

### 1.2 检索

- `retrieval.py` 使用 SQLite FTS5 `trigram`；3 字以上走 FTS5，2 字走 `LIKE`。
- 返回 `source_id`、`locator`、原文和规范化文本。
- 不支持语义检索；不引入向量数据库。

### 1.3 五角色 Pipeline

- `text_analyst`：目标句覆盖；目标 claim 必须 `locator=target`、`scope=target`；邻近句必须 `scope=contextual`。
- `literary_analyst`：解释候选；仍为 `unreviewed`。
- `researcher`：无新来源时必须 `claims=[]` + `research_status=no_source_found`；不回显原文/已有 claim。
- `skeptic`：只审查本轮 `current_claim_ids`；finding 必须指向当前候选；不改变 claim 状态。
- `editor`：只能使用 approved claim；没有 approved 时 `draft_text` 必须为空。
- 真实 30B 64K 回归结果在 `literary_intelligence/runs/li16d/`；该目录被 `.gitignore` 忽略。

### 1.4 数据与审核状态

- `Claim`、`Review`、`SourceRecord`、`LLMPassOutput` 已用 Pydantic strict 模型。
- claim 的 `review_status` 仍只有人工审核可改变；LI-2 不自动批准。
- LI-2 可以基于证据和解释生成内容包，但包本身默认 `verification_status=draft`，不能冒充已审核发布稿。

### 1.5 Local-Drama-Studio 与 R3 接口

- `scripts/r3_build.py` 的实际输入是：
  - `segments.json`：`id/type/source/duration/motion`
  - `audio_manifest.json`：`lines[].file/text/duration_seconds`，可选 `content_type/pause_after_ms`
- `r3_build.py` 负责视频拼接、音频时间轴、SRT/ASS、字体校验和最终 MP4。
- R3 构建不是内容策划接口；LI-2 必须输出独立内容包，再由 Adapter 转成上述两个输入文件。
- 本阶段不修改 `r3_build.py`，不改变时间轴、字体和响度行为。

## 2. LI-2 数据流设计

```text
source registry + FTS5
        ↓
text/literary/researcher/skeptic 结果（保留 claim_id）
        ↓
视频文案与分镜（LI-2-B）
        ↓
ContentPackage（本阶段 Schema）
        ↓
R3 Adapter（LI-2-C）
  ├─ segments.json
  └─ audio_manifest.json
        ↓
现有 r3_build.py
```

## 3. ContentPackage Schema

新增：`literary_intelligence/schemas/content_package.py`

顶层：

| 字段 | 说明 |
|---|---|
| `schema_version` | 内容包版本 |
| `work` | work_id/title/author/dynasty/source_id/source_version/source_license_status |
| `positioning` | target_text/target_locator/surrounding_context |
| `analysis` | text_analysis/literary_interpretation/imagery/emotion/artistic_features/historical_context/uncertainty_notes |
| `video` | title_options/opening_hook/narration/scene_plan/visual_prompts/subtitle_segments/ending/platform_metadata |
| `provenance` | source_refs/claim_refs/verification_status/generated_by/generation_timestamp/warnings |

关键约束：

- `work.source_id` 必须出现在 `provenance.source_refs`。
- 所有 `scene_id` / `segment_id` 唯一。
- `scene_plan[].subtitle_ids` 必须引用已存在的字幕段。
- 字幕段引用的 claim 必须出现在 `provenance.claim_refs`。
- `verification_status` 初始只能为 `draft`；人工审核前不得写成 `human_reviewed/published`。
- 不做“每个 claim 必须 approved”的硬限制；但内容包必须携带 claim_refs 和 warnings，默认 draft。

字段没有加入没有生产用途的装饰性内容。`scene_plan` 直接对应 R3 的视觉分段，`subtitle_segments` 直接对应后续 TTS/SRT 段。

## 4. 修改文件

| 文件 | 原因 |
|---|---|
| `literary_intelligence/schemas/content_package.py` | 新增内容包 Schema |
| `literary_intelligence/schemas/__init__.py` | 导出内容包模型 |
| `literary_intelligence/schemas/export_schemas.py` | 增加 `content_package.schema.json` 导出 |
| `literary_intelligence/tests/test_content_package.py` | 有效包、重复 scene、未知字幕/claim、来源约束、Schema 导出测试 |
| `literary_intelligence/tests/test_schemas.py` | 更新导出清单 |
| `docs/literary_intelligence/LI2_AUDIT.md` | 本审计和设计 |

没有修改 `scripts/r3_build.py`、`src/drama_studio`、字体或历史运行记录。

## 5. 测试

```text
.venv\Scripts\python.exe -B -m pytest literary_intelligence/tests -q -p no:cacheprovider
```

结果：**61 passed，exit 0**。

## 6. 下一阶段

LI-2-B 使用现有 `runs/li16d` 的真实证据/候选和《洛神赋》原文，生成约 60 秒的视频内容包；先生成包，不直接批量生产。随后 LI-2-C 建立 R3 Adapter，LI-2-D 再做一次单篇实际生产。

本阶段不调用 CosyVoice/FLUX/Wan/ComfyUI；不推送 Git；不覆盖 LI-1.5/LI-1.6 历史结果。
