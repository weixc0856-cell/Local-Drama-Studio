# 09 · 视觉风格引擎与风格规范

> 状态：`DECISION` / 2026-11-12 由 `VISUAL_STYLE_SPEC.md`、`VISUAL_STYLE_ENGINE.md`、`STYLE_BOARD_STATUS.md` 及四份风格笔记合并。
> 原始文档归档在 `D:\DramaStudio\archive\docs\2026-11-12\`（见 [ARCHIVE.md](ARCHIVE.md)）。

## 1. 原则

- 风格是**配置**，不是代码分支。任何风格差异只能来自 `config/style_packs/` 与 `config/styles.yaml`；不允许在代码里写 `if style == ...`。
- 两条核心管线共享一套技术栈：**A = 水墨 `oriental.ink_wash`**，**B = 宋代院体青绿工笔 `oriental.court_green_fine_line`**。
- 风格必须同时作用于 FLUX（首帧/静帧）与 Wan（视频提示词），否则同一片会分裂成两种质感。
- 人工审美评审是唯一的质量裁决；客观检查只做守门，不给 `PASS_VERIFIED`。

## 2. Style Pack 结构

```
config/style_packs/<group>/<name>/
  style.yaml              id / name / group / version / status / summary / layers
  image_prompt.yaml       identity, medium, materials, composition, prompt_order, positive_anchors
  video_prompt.yaml       镜头运动与物理感约束
  color_profile.yaml      anchors(hex, 仅校验用) + saturation/edge/value 区间
  lighting_profile.yaml   key / temperature / contrast
  material_profile.yaml   材质与纹理线索
  camera_profile.yaml     允许机位运动、焦段、景深
  motion_profile.yaml     确定性运动策略
  negative_constraints.yaml  禁止项（校验与人工清单用，CFG 1.0 下不进 prompt）
  reference_board/        manifest.json、评审记录（图片在产出根，不进 Git）
```

`src/drama_studio/domain/style/`：`schemas.py`（严格 Pydantic）、`registry.py`（id/version 校验）、`compiler.py`（按 `prompt_order` 编译 FLUX/Wan 提示词并强制机位词汇）、`consistency.py` + `metrics.py`（客观一致性）。

常用命令：

```powershell
.venv\Scripts\drama.exe style list
.venv\Scripts\drama.exe style show animation.xuanji_3d
.venv\Scripts\drama.exe style validate
.venv\Scripts\drama.exe style check-image --style animation.xuanji_3d --image <png>
```

## 3. 23 套风格

| 组 | 风格 | 备注 |
|---|---|---|
| oriental | `ink_wash` 水墨、`gongbi` 工笔、`modern_chinese` 当代新中式 | 核心管线 A/B |
| artistic | `impasto_oil`、`impressionism`、`japanese_soft`（新海诚式）、`surrealism`、`ukiyo_e` | 参考板已完成 |
| retro | `collage`、`pop_art`、`synthwave`、`y2k` | 参考板已完成，返工一轮 |
| realism | `documentary`、`new_topographics` | 参考板已完成 |
| animation | `pixar` 皮克斯式 3D、`xuanji_3d` 玄机式 3D 国漫、`mushenji_dark` 牧神记·暗黑国风 | 3D 质感方向 |
| advertising | `acid_pop`、`clay_3d`、`lifestyle_film`、`oriental_minimal`、`product_macro`、`swiss_minimal` | 参考板已完成 |

`style list` 是唯一权威清单（含版本与状态）。

## 4. 两条核心管线

### A · 水墨 `oriental.ink_wash`

- 宣纸颗粒、干湿笔触、大面积留白、墨分五色；边缘密度低、饱和度低。
- 构图靠留白与虚实，不靠满画面细节；Wan 只用于纯风景/云雾/水面。
- 运动：慢推 8–12%、云/雾/水/树叶局部微动、0.5 s 叠化；禁止快速位移。

### B · 宋代院体青绿工笔 `oriental.court_green_fine_line`

- 石青石绿、泥金、绢本底色、细线勾勒；高频边缘、较低饱和但色彩层次清楚。
- 构图强调界画式结构（亭台、栏杆、山石）与可读的服饰纹样。
- 运动：同一套确定性运镜；建筑镜头必须避免 Wan 直接生成（结构会坏），改用 2.5D 分层视差。

两套风格的机位词汇、焦段、景深与 `.yaml` 阈值都在 `config/styles.yaml` 与各自 style pack 中；代码只读取策略，不写死风格。

## 5. 参考板生产

每套 12 个主体，流程：

```powershell
.venv\Scripts\python.exe scripts\gen_style_packs.py --only <style.id>       # 重新生成 pack（改 STYLES 条目后）
.venv\Scripts\python.exe scripts\gen_reference_board.py --style <style.id> --limit 12
.venv\Scripts\python.exe scripts\r1_batch.py --jobs <board>/candidates/jobs.json --timeout 7200
.venv\Scripts\python.exe scripts\board_contact_sheet.py --style <style.id>
.venv\Scripts\drama.exe style check-image --style <style.id> --image <png>
```

产出位置：`D:\DramaStudio\style_boards\<group>\<pack>\candidates\`（图片本地，不进 Git）；仓库保留 `reference_board/manifest.json` 与评审记录。

**当前状态（2026-11-12）**：23 套风格全部完成 12 张参考板与至少一轮返工，客观检查全过；**人工审片仍为 `PENDING_REVIEW`**（水墨/工笔为历史 `REVIEWED/ACCEPTED`）。2026-11-04 已批准 4 个测试镜头的 A/B 选择（court `A/A`、ink `B/A`），全片审美评审仍待做。客观阈值按实测每套调整并写入评审记录（例：新海诚式饱和度上限 0.38 → 0.50；玄机式边缘密度 0.05–0.11）。

## 6. 风格要点（研究记录）

- **玄机式 3D 国漫 `animation.xuanji_3d`**：UE5 风格化三维、瓷肌次表面散射、发丝逆光、织金重彩与黑漆鳞甲、体积光与云海大景；冷暖对撞（深青/靛蓝 + 暖金）；竖构图 9:16 直接组织。已知风险：人物占比偏高、面部偏偶像化、发际线偶有接片感。
- **新海诚式 `artistic.japanese_soft`**：高饱和天空、逆光薄雾、城市光斑、细腻云层；只做风格研究，不复制具体影片镜头。
- **当代新中式 `oriental.modern_chinese`**：宋韵极简、留白、器物与材质，不做古画赝品；参考宋氏美学研究（器物、色釉、版式）。
- **超现实主义 `artistic.surrealism`**：写实梦境、尺度错置、安静的不合理；避免恐怖化。
- **方向教训**：把「新中式」做成古画赝品会失败；方向先定，再调提示词。

## 7. 客观一致性与阈值

`domain/style/consistency.py` 检查：色板 LAB 距离、平均饱和度、平均明度、边缘密度、黑边/letterbox、序列漂移。阈值来自各 pack 的 `color_profile`，初值沿用工笔类（edge 0.12–0.35），实测后按风格下调（水墨/3D 类 0.05–0.11）。差异必须在评审记录里说明原因。

## 8. 已知限制

- **无同脸能力**：项目只锁定质感/光照/构图，不承诺跨镜头角色一致性；参考图/角色 LoRA/首尾帧均未接入。
- **CFG 1.0 下负向词不生效**：`negative_constraints` 只用于校验与人工清单，必须用正向约束压制（如「mature heroic face, natural skin, not a doll face」）。
- **空镜会被拉回人物**：编译器固定追加 hero silhouette / expressive face 锚点；真正的空镜需要引擎级开关（未实现）。
- **Wan 建筑/人物不可靠**：结构类镜头改用静帧 + 2.5D 分层视差。
- 任何风格质量在人工评审记录之前不得标 `PASS_VERIFIED`。
