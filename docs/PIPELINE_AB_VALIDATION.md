# 双视觉管线首批验证：实施方案与执行记录

> 执行日期：2026-11-03
> 环境：Intel Arc A750 8 GB / ComfyUI 0.43.0 / FLUX.2 klein 4B Q4_K_M / FFmpeg 8.1
> 规范：[VISUAL_STYLE_SPEC.md](VISUAL_STYLE_SPEC.md)；状态词典见 `docs/PRD.md` §0.2。
> 结论：两条管线各完成 1 张静态图 + 1 段 15-30 秒样片；技术检查通过，静态质量门为 `PARTIAL`（山体纹理仍有重复），人工审美待审。

## 1. 现状核对与最小方案

### 1.1 已有能力

| 能力 | 现状 | 证据 |
|---|---|---|
| P1 生产闭环 | 已完成，不阻塞本次验证 | PRD §21；`projects/workspace.db` |
| ComfyUI + FLUX 文生图 | 已有，API 工作流 | `workflows/r0_flux_t2i_api.json`；本轮 4 张水墨候选 + 1 张工笔静帧 |
| R3 FFmpeg 合成 | 已有分段、混音、字幕、1080×1920 母版 | `scripts/r3_build.py` |
| 长卷横移 + 纸纹 | S2 已实现实验链路 | `scripts/s2_build.py` |
| 双风格配置 | S1 已落地 | `config/styles.yaml`、`style_presets.py` |

### 1.2 本轮确实缺失、需要补的

1. **静态质量门**：此前只有空图/黑帧/尺寸检查，没有飞鸟、皴法、水面、舟体、线条、建筑等语义缺陷记录。
2. **水墨分层动画**：S2-水墨 只有整幅墨迹显现，没有“山体冻结 + 云气横移 + 水面微动 + 孤舟微移”。
3. **每样片图层定义**：没有把云带、水面、舟体区域显式记录为可复核的图层参数。
4. **工笔更慢的横移样片**：S2-工笔 为 20 秒 / 42 px/s；本轮补一条 28 秒 / 30 px/s 的样片。

### 1.3 最小改动

- 新增 `scripts/static_quality.py`：客观指标 + 两套独立人工检查表；没有人工记录时状态只能是 `PENDING`。
- 新增 `scripts/pipeline_ink.py`：按 `layers.json` 生成云层、水层、舟体图层，一次 FFmpeg 合成；不新增依赖，不建动画框架。
- 复用 `scripts/s2_build.py` 生成工笔长卷样片。
- 证据目录：`experiments/pipeline_a/`、`experiments/pipeline_b/`。
- 不新增 ComfyUI/FFmpeg/模型/配置系统；P1 顺序未改变。

## 2. 管线 A · 东方写意水墨

### 2.1 静态候选与质量门

生成 4 张 576×1024 候选（seed 5301-5304，同一套水墨提示词，第 3/4 张加入“避免重复平行线条/淡墨渲染”约束）。逐张人工查看后选择 **IA4**：

- 构图：上部天空留白、中远景双峰、中景坡岸杂木、前景孤舟、水面倒影，符合 9:16 空镜要求。
- 飞鸟：无，规避机械排列问题。
- 水面/倒影：留白为主，倒影有偏移与虚化，不是机械镜像。
- 主缺陷：左右山体坡面仍有少量重复平行皴线，放大可见。

静态质量门输出：`experiments/pipeline_a/static/IA4/static_quality.json`

| 检查 | 结果 | 说明 |
|---|---|---|
| 飞鸟 | `PASS` | 无飞鸟 |
| 山石 | `PARTIAL` | 少量重复平行皴线；未形成大面积机械条纹，当前无局部 inpaint 工作流 |
| 树木 | `PASS` | 疏密与枝干结构有变化 |
| 水面 | `PASS` | 留白与淡墨边界，无数字渐变条带 |
| 倒影 | `PASS` | 偏移/虚化，不是机械镜像 |
| 云烟 | `PASS` | 与山体衔接柔和 |
| 远景 | `PASS` | 淡墨虚化 |
| 整体材质 | `PASS` | 生宣墨色层次存在 |
| 构图 | `PASS` | 留白与三层空间清楚 |
| **总状态** | **`PARTIAL`** | 仅山石一项不通过；其余通过 |

客观指标：576×1024，均值 221.45，标准差 55.21，留白（L≥240）60.1%，边缘密度 0.0594，高频比 0.0252，饱和度 0.0067（灰度水墨）。

### 2.2 分层与动画

图层参数：`experiments/pipeline_a/layers.json`（按样片手工定义，不是通用分割模型）。

| 层 | 区域/参数 | 运动 |
|---|---|---|
| 主山体 / 岸线 | 不进入任何运动层 | 冻结（首帧→10 s 区域差异 0.002/255） |
| 山腰云气 | y 0.64-0.76；模糊亮度 235-252 | 水平 ±24 px，周期 14 s |
| 水面 | y 0.72-1.0；排除舟体包围盒 | 水平 ±4 px，周期 8 s |
| 孤舟 | 归一化 bbox `[0.3125, 0.7324, 0.9549, 0.9473]`，30 px 羽化 | 20 s 内右移 8 px + ±1.5 px 起伏 |
| 纸本纹理 | 程序生成生宣纹理，`overlay` 0.14 | 静态 |

实现方式：Pillow 生成 RGBA 图层，FFmpeg 逐层 `overlay` 后用一次 `blend` 叠纸纹；没有 Wan、没有新依赖。

### 2.3 结果

- 产物：`experiments/pipeline_a/renders/build-20261103-212100/final_9x16.mp4`
- 20.000 s / 1080×1920 / 24 fps / H.264 yuv420p / AAC 48 kHz 单声道
- 1,408,479 B；SHA-256 `88efb387…adc2ca`
- 全片解码退出码 0；`blackdetect` 0 段；6 个抽样帧全部非空
- 运动量：云带区域首帧→10 s 平均差异 5.31/255；水面 7.55/255；舟体暗像素质心首帧→15 s 从 392.85 移到 398.83（约 6 px，20 s 配置位移为 8 px）；山体静态区域 0.002/255

验收核对：

| 验收项 | 结果 | 说明 |
|---|---|---|
| 没有机械排列的飞鸟 | `PASS` | 画面无飞鸟 |
| 没有明显重复的山石条纹 | **`PARTIAL`** | 少量重复皴线仍在；见静态门 |
| 没有高频纹理闪烁 | `PASS`（技术） | 无逐帧噪声；纸纹与图层静态或缓慢平移 |
| 水面有纸性和墨色层次 | `PARTIAL` | 纸纹叠加 0.14；未比较 multiply/softlight 等混合方式 |
| 舟体不变形、不自转、不融化 | `PASS`（技术） | 舟体作为刚性图层平移，无形变 |
| 山体主体稳定 | `PASS` | 静态区域差异 0.002/255 |
| 云气运动自然、克制 | `PARTIAL` | 云带位移 ±24 px/14 s；人工看片待审 |
| 保留留白和呼吸感 | `PASS` | 末帧留白约 59%（源图 60%） |
| 人工看片 | **PENDING** | 需确认云气速度、水面幅度、纸纹强度 |

## 3. 管线 B · 宋代院体工笔与青绿设色

### 3.1 静态质量门

沿用 A1（1024×1024，seed 5201）。输出：`experiments/pipeline_b/static/A1_static_quality.json`

| 检查 | 结果 | 说明 |
|---|---|---|
| 线条 | `PASS` | 细线整体连续，未见大面积断裂 |
| 建筑 | `PASS` | 楼阁屋顶/栏杆/台基结构可辨 |
| 山石 | `PARTIAL` | 坡面有重复横向纹理/带状设色；无设色溢出 |
| 树木 | `PASS` | 枝干结构有变化 |
| 人物 / 花鸟 | `PASS`（N/A） | 画面无人物/花鸟 |
| 色彩 | `PASS` | 石青石绿赭石稳定，无荧光色 |
| 材质 | `PASS` | 绢本/纸本底色与矿物设色层次存在 |
| 整体 | `PASS` | 细节可放大查看；主要缺陷是山体纹理略重复 |
| **总状态** | **`PARTIAL`** | 仅山石一项不通过 |

### 3.2 动画与结果

- 做法：1024×1024 静帧按高度放大到 1920，裁切 1080×1920 窗口在 28 s 内横移 840 px（约 30 px/s）；绢纹以 0.12 叠加。
- 分层视差：`NOT_RUN`（没有可靠分层素材，未把单图平移冒充 2.5D）。
- 线描显现 / 局部微动：`NOT_RUN`（本轮不必要）。
- 产物：`experiments/pipeline_b/renders/build-20261103-212022/final_9x16.mp4`
- 28.000 s / 1080×1920 / 24 fps / H.264 yuv420p / AAC 48 kHz 单声道
- 7,296,258 B；SHA-256 `b7dbcc3e…6a733d`
- 解码 0；黑帧 0；首/中/末帧非空

| 验收项 | 结果 | 说明 |
|---|---|---|
| 线条清晰、无明显断裂 | `PASS`（技术） | 横移不缩放，不引入新断线；人工待审 |
| 设色稳定、无色彩溢出 | `PASS`（技术） | 首/中/末帧色相稳定 |
| 建筑和主体结构不变形 | `PASS`（技术） | 裁切不缩放；人工待审 |
| 长卷移动平稳 | `PASS` | 线性裁切，30 px/s |
| 视差不产生边缘空洞 | `NOT_RUN` | 未启用视差 |
| 细节不因运动明显损失 | `PASS`（技术） | 1080×1920 源裁切，无逐帧重采样 |
| 保留宋代院体秩序感 | **PENDING** | 需人工看片 |
| 人工看片 | **PENDING** | — |

## 4. 共享与隔离边界

| 项目 | 本轮做法 |
|---|---|
| 共享 | 同一个 ComfyUI、FLUX/Wan 工作流、FFmpeg、`config/styles.yaml`、证据/日志机制 |
| 独立 | 水墨与工笔各自提示词、静态检查表、图层参数、动画策略；未合并成大提示词 |
| 不新建 | 没有第二套 ComfyUI、第二套 FFmpeg 封装、新模型、新 LoRA、新依赖 |
| 代码边界 | `static_quality.py` 用两张独立检查表；`pipeline_ink.py` 只走水墨图层；工笔复用 `s2_build.py` 的横移路线 |

## 5. 遗留问题与下一步

1. **山体纹理重复**：两条管线的静态门都为 `PARTIAL`。当前工作流没有局部 inpaint；下一轮应先补“局部重绘/修复”入口，或继续调提示词与 seed，而不是直接放行到正式生产。
2. **纸纹强度与混合方式**：本轮只用 `overlay 0.14`。规范要求比较正片叠底/柔光等效果；该比较 `NOT_RUN`。
3. **云层边缘**：云带使用模糊亮度掩码，已避开主山体轮廓，但树冠亮隙可能被轻微带动；需人工看片确认是否有“树在动”的感觉。
4. **Wan 局部动态**：本轮刻意不用，`NOT_RUN`。下一步只对云烟、水面、飞鸟做局部 I2V 对照，不把整幅山水送入 Wan。
5. **工笔视差/线描**：`NOT_RUN`；需要可靠分层或独立线稿后才做。
6. **人工审查**：两段样片都停在 `PARTIAL`，需人工看片后才能决定升为 `PASS_VERIFIED` 或调整重跑。
7. **S3 前置**：本轮结束时 8080 已空闲（此前占用它的外部实例已停止，本项目未操作该进程）；按规范仍先等人工审查，不启动项目 LLM、不进入 S3。

## 6. 复现

```powershell
# 静态候选（需要 ComfyUI 8188）
scripts\start.ps1
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/pipeline_a/jobs.json --timeout 1800
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/pipeline_a/jobs_ia3.json --timeout 1800
.venv\Scripts\python.exe scripts\r1_batch.py --jobs experiments/pipeline_a/jobs_ia4.json --timeout 1800
scripts\stop.ps1

# 静态质量门
.venv\Scripts\python.exe scripts\static_quality.py `
  --image experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png `
  --style ink_wash --manual experiments/pipeline_a/static/IA4/manual_review.json `
  --out experiments/pipeline_a/static/IA4/static_quality.json

# 水墨分层样片
.venv\Scripts\python.exe scripts\pipeline_ink.py `
  --source experiments/pipeline_a/static/IA4/IA4_ink_landscape_00001_.png `
  --layers experiments/pipeline_a/layers.json `
  --static-quality experiments/pipeline_a/static/IA4/static_quality.json `
  --duration 20 --out experiments/pipeline_a/renders

# 工笔长卷样片
.venv\Scripts\python.exe scripts\s2_build.py --style court_green_fine_line `
  --source experiments/s2a/runs/A1/A1_court_green_00001_.png `
  --duration 28 --out experiments/pipeline_b/renders
```
