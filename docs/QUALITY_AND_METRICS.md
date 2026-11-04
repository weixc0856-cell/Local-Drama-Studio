# 07 · QUALITY_AND_METRICS — 质量门、成本与数据

> 文档状态：`DECISION` / v1.0 验收与指标规范冻结。
> 原则：技术成功不等于内容合格；平台数据不等于产品已成功。

## 1. 状态词典

需求状态以 `docs/PRD.md` §0.2 为唯一来源：`PASS_VERIFIED` / `IMPLEMENTED_NOT_VERIFIED` / `PARTIAL` / `NOT_IMPLEMENTED` / `BLOCKED` / `OPEN_QUESTION`。

历史证据标签（只用于旧报告/阶段表，不用于需求矩阵）：

| 旧标签 | 映射 |
|---|---|
| `PASS_STATIC` | `IMPLEMENTED_NOT_VERIFIED` |
| `NOT_RUN` | `NOT_IMPLEMENTED` |
| `DEPRECATED` | 历史能力 |
| `PASS_LIMITED` | 仅 `doctor` 诊断标签 |

补充的运行/诊断状态（不用于需求矩阵）：

| 状态 | 用途 |
|---|---|
| `FAILED` | 运行期失败（任务、步骤、校验） |
| `UNKNOWN` | 无法探测（禁止猜成在线/正常） |

禁止把 `NOT_IMPLEMENTED`、`BLOCKED` 或 `OPEN_QUESTION` 写成 `PASS_VERIFIED`。

## 2. 技术质量门

每个成片必须全部满足：

| 检查 | 阈值/方法 |
|---|---|
| 画幅/分辨率 | 1080×1920，9:16 |
| 帧率 | 24fps |
| 时长 | 30-60 秒（90 秒仅实验） |
| 视频解码 | `ffmpeg -v error -i final.mp4 -f null -` 退出码 0 |
| 黑帧 | 亮度 <5 的帧数 = 0 |
| 音频 | AAC 48 kHz；对白 ≈ -16 LUFS；真峰值 ≤ -1.5 dBTP |
| 字幕 | SRT/ASS 可解析；时间与实际音频一致；每行 ≤22 字 |
| 颜色漂移 | 首尾 ΔRGB 任一通道 >8 时人工复核 |
| 闪烁 | 相邻帧差异尖峰 > mean+3σ 时人工看片 |
| 文件 | MP4 faststart；无损坏帧 |

自动指标只做筛查，不替代人工看片。

> R3 的 `mean_volume/max_volume` 来自 FFmpeg `volumedetect`，不是 Integrated LUFS / True Peak。R3-D 必须补测 **Integrated LUFS、True Peak、语音/BGM 相对响度**。

## 3. 内容质量门

### 3.1 镜头级

| 项 | 要求 |
|---|---|
| 主体运动 | 与设计一致；H3 类位移必须单独测量 |
| 相机运动 | 与设计一致；不能用相机运动冒充主体运动 |
| 背景约束 | 河湾/远山/花林/芦苇不漂移、不换岸 |
| 结构 | 无变形、无多手/多船、无结构崩坏 |
| 颜色 | 无明显渐变漂移（A4 案例：ΔR -11.5，肉眼可见） |
| 伪影 | 无彩虹、闪烁、糊化 |

### 3.2 作品级

| 项 | 要求 |
|---|---|
| 叙事 | 主题清楚，镜头顺序成立 |
| 视听 | 朗诵清晰，字幕不挡主体，节奏可看 |
| 文化 | 原文/解释/历史/想象/AI 标识分开 |
| 版权 | 模型、字体、音乐、素材授权已登记 |
| 平台 | 封面/标题/正文/话题与内容一致 |

### 3.3 已知限制

- Wan 精确主体位移不可靠；R2-B H3 船体 24.6 px，方向错误。
- 121 帧花林有颜色漂移风险。
- 人物跨镜头一致性未验证。
- 自动指标捕捉不到渐进颜色漂移，必须人工看首尾帧。

## 4. 成本指标

每个作品记录：

| 字段 | 说明 |
|---|---|
| machine_seconds | 模型/合成机器耗时 |
| human_minutes | 人工审核/返工时间 |
| retries | 重试次数 |
| failures | 失败任务数 |
| degraded_shots | 降级为静帧的镜头数 |
| finished_seconds | 成片时长 |
| cost_per_finished_second | 机器秒/成片秒 |

### R3 单篇基线

| 项 | 数值 |
|---|---|
| 成片 | 38.042 秒 |
| FLUX 5 张 | 2.4 min |
| Wan 1 段 | 36.4 min |
| TTS 7 句 | 2.7 min |
| FFmpeg | ≈2 min |
| 端到端 | 43.8 min |
| 音频实测 | mean -17.7 dB，max -1.4 dB（R3 volumedetect） |
| 机器秒/成片秒 | ≈69 s/s |
| Wan 占比 | ≈83% |

人工时间未单独计时；多篇批处理未运行。

## 5. 平台指标

| 指标 | 用途 |
|---|---|
| 曝光/播放 | 触达 |
| 完播率 | 前几秒与节奏 |
| 平均观看时长 | 内容吸引力 |
| 点赞/评论/收藏/分享 | 互动与价值 |
| 涨粉 | 账号积累 |
| 商品点击/转化 | 后续商业价值 |

记录窗口：24h / 72h / 7d（若平台可得）。

### 实验规则

1. 一次只改一个变量（主题/风格/时长/封面/标题）。
2. 同一变体至少 3-5 条样本，再判断趋势。
3. 不根据 1-2 条视频宣布风格成功或失败。
4. 不用播放量单指标替代完播/互动/涨粉。
5. 记录失败样本，避免只留下“爆款”。

## 6. 数据记录格式

建议 `experiments/analytics/<piece_id>.json`：

```json
{
  "piece_id": "",
  "theme": "",
  "style": "",
  "duration_seconds": 0,
  "cover_variant": "",
  "title": "",
  "platform": "douyin|xhs",
  "published_at": "",
  "windows": {
    "24h": {"views": 0, "completion_rate": 0, "avg_watch_seconds": 0,
             "likes": 0, "comments": 0, "saves": 0, "shares": 0, "follows": 0},
    "72h": {},
    "7d": {}
  },
  "notes": ""
}
```

## 7. 当前质量状态

| 项 | 状态 | 证据 |
|---|---|---|
| R3 视频与音频文件技术检查 | `PASS_VERIFIED` | 解码正常、无黑帧；音频可解码，已记录 mean/max；Integrated LUFS、True Peak 未测 |
| R3 内容质量 | `PASS_VERIFIED`（单篇） | 人工抽帧/看片 |
| 单篇成本 | `PASS_VERIFIED` | 43.8 min |
| 人物一致性 | `NOT_RUN` | — |
| 双核心风格规范与配置 | `PASS_STATIC` | `docs/VISUAL_STYLE_SPEC.md` + `config/styles.yaml` |
| 工笔/水墨生成与动画质量 | `PARTIAL` | S2 与首批管线样片技术检查通过；静态门 `PARTIAL`（山石纹理重复）；人工审美 PENDING；见 `docs/PIPELINE_AB_VALIDATION.md` |
| 多篇批处理 | `NOT_RUN` | — |
| 平台数据 | `NOT_RUN` | — |
| 女声/字体/BGM/音效选型 | `PARTIAL`（字体/字幕完成；女声已入 P1 成片；排版待审；BGM/音效未完成） | R3-D |
| P1 技术质量检查 | `PASS_VERIFIED` | 4/4 图片非空非黑；成片 14.0 s / 1080×1920 / 解码 0 / 哈希一致；音频 48 kHz 单声道，max -1.5 dB | P1 |
| 平台增长/转化 | `NOT_RUN` | — |

## 8. 失败模式清单

- 启动竞态导致连接拒绝（V1 案例）：先等待就绪，再批处理。
- ComfyUI 生成结束但下载失败：保留任务并重试。
- 渐进颜色漂移：人工看首尾帧，必要时校色/重摇。
- 字幕字号被 libass 放大：显式 PlayRes 1080×1920。
- 烧录字体缺失：回退软字幕或换开源 CJK 字体。
- TTS 长句超时：逐句合成，只重跑失败句。
- 平台规则变化：发布前人工复核。
