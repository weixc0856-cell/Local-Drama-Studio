# 风格参考板生产状态（2026-11-06）

> 本文件是跨会话的工作台账：每套风格按「定义 → 12 主体 → 渲染 → 客观检查 → 人工复查 → 评审记录」推进。
> 参考图只在本地，不进 Git；提交的是风格包 YAML、params/jobs、manifest 与 review 文档。
> **2026-11-07 状态：21 套风格全部完成参考板（12 张/套）并返工，客观检查全过，等待人工审片。**
> 2026-11-07 评审返工：按人工评审意见，10 套风格正在逐套修改提示词并重渲（开窗形制、景别/云形/时段、材质反转、刀触、笔触节奏、月亮与船型、拼贴布局、网点与套印、视角与 VHS、Y2K 年代感）。

## 1. 进度

| 风格 | 风格包 | 12 主体 | 渲染 | 客观检查 | 评审记录 | 状态 |
|---|---|---|---|---|---|---|
| `oriental.ink_wash` | 既有 | 既有 | 既有 | 既有 | — | `REVIEWED`（历史） |
| `oriental.gongbi` | 既有 | 既有 | 既有 | 既有 | `review-2026-11-06.md` | `ACCEPTED`（历史） |
| `oriental.modern_chinese` | 已重写（当代新中式） | 已生成 | 12/12（v3） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `artistic.japanese_soft` | 已重写（新海诚式） | 已生成 | 12/12（v3） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `artistic.surrealism` | 已重写（写实梦境） | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `artistic.impasto_oil` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `artistic.impressionism` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `artistic.ukiyo_e` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `retro.collage` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `retro.pop_art` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `retro.synthwave` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `retro.y2k` | 已重写 | 已生成 | 12/12（返工） | 全过 | `reference_board/review-2026-11-06.md` | `PENDING_REVIEW` |
| `realism.documentary` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `realism.new_topographics` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `animation.pixar` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.swiss_minimal` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.product_macro` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.acid_pop` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.lifestyle_film` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.clay_3d` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |
| `advertising.oriental_minimal` | 新增 | 已生成 | 12/12 | 全过 | `reference_board/review-2026-11-07.md` | `PENDING_REVIEW` |

## 2. 每套流程

```powershell
# 1) 定义（改 scripts/gen_style_packs.py 的 STYLES 条目后）
.venv/Scripts/python.exe scripts/gen_style_packs.py --only <style.id>
.venv/Scripts/drama.exe style validate

# 2) 主体与任务
.venv/Scripts/python.exe scripts/gen_reference_board.py --style <style.id> --limit 12

# 3) 渲染（GPU 独占，一次一套）
.venv/Scripts/python.exe scripts/r1_batch.py --jobs config/style_packs/<group>/<name>/reference_board/candidates/jobs.json --timeout 7200

# 4) 接触表与客观检查
.venv/Scripts/python.exe scripts/board_contact_sheet.py --style <style.id>
.venv/Scripts/drama.exe style check-image --style <style.id> --image <png>
```

## 3. 约定

- 接触表取每个候选目录最新 PNG，输出到 `candidates/contact_sheet.png`。
- 发现问题只重渲对应编号：`--only 03 --force`；改提示词后先重新生成 params。
- 每套至少检查：穿模/悬空、透视一致性、重复构件、文字残留、人物意外出现、色板越界。
- 客观阈值按实测调整，但要在评审记录里写明原因（例：新海诚式饱和度上限 0.38 → 0.50）。
