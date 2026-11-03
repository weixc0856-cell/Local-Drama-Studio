# 内容包（Content Packs）设计

> 目的：Local-Drama-Studio 是通用本地视听内容生产底座，不围绕《春江花月夜》写死。
> 本文件定义“共享能力”与“主题素材”的边界；R2 不重构现有目录，只约束新增实现。

## 1. 分层

```text
共享层（代码 / 工作流 / 引擎）
  ├─ 剧本解析、分镜、状态机、断点续跑
  ├─ ComfyUI API 工作流（FLUX 文生图、参考图编辑、Wan I2V）
  ├─ 配音、字幕、FFmpeg 剪辑
  └─ 质量检查与产物归档

内容包层（每个主题一个目录）
  ├─ 视觉规范 / 色板 / 提示词后缀
  ├─ 参考图与关键帧
  ├─ 剧本 / 诗词 / 文案
  ├─ 镜头清单与运动描述
  └─ 音色、音乐、字幕样式
```

硬规则：

- 共享层不得出现具体诗词、角色名、场景名或作品专属提示词。
- 内容包不得复制工作流 JSON；只提供参数与素材。
- 新增一个主题包，应当只需要新增内容文件与配置，不需要改 Python。

## 2. 目标目录

```text
content/
├─ chunjiang/                    # 春江花月夜
│  ├─ pack.yaml
│  ├─ source/poem.txt
│  ├─ style/
│  │  ├─ style_bible.md
│  │  ├─ style_bible.json
│  │  └─ reference/style_ref.png
│  ├─ keyframes/
│  │  ├─ kf01.png + kf01.meta.json
│  │  └─ relationships.json
│  ├─ shots/
│  │  ├─ shot_001/ (clip.mp4, meta.json, review.json)
│  │  └─ ...
│  ├─ audio/
│  └─ subtitles/
├─ shijing/                     # 诗经
├─ shenhua/                     # 神话志怪
├─ yijing/                      # 易经
└─ history/                     # 历史文化
```

## 3. pack.yaml 契约（草案）

```yaml
id: chunjiang
title: 春江花月夜
source_text: source/poem.txt
language: zh
aspect_ratio: "16:9"
target_duration_seconds: 90
resolution:
  keyframe: [768, 432]
  video: [1024, 576]
style:
  bible: style/style_bible.json
  reference: style/reference/style_ref.png
  prompt_suffix: >
    classical Tang-dynasty China, spring river landscape, ink-wash atmosphere ...
  negative_prompt: >
    modern architecture, power lines, neon, ...
keyframes:
  - id: KF1
    image: keyframes/kf01.png
    time: after sunset
    motion_prompt: >
      Slow cinematic push-in over the river at dusk; ...
shots: []
audio:
  voice: narrator_cn_male
  music: ""
```

## 4. 与 R2 的关系

- R2-A 只验证共享层的视频能力，不新增内容包代码。
- R2-B 生成的实际镜头，元数据应能直接映射到 `content/chunjiang/shots/`。
- R1 的 `assets/` 与 `experiments/` 暂不迁移；等 R3 引入项目/内容包管理时再一次性迁移，避免破坏已提交基线。
- 迁移后，`assets/visual_style/`、`assets/keyframes/` 成为 `content/chunjiang/` 的别名或归档。

## 5. 通用性验收

新增一个主题包时，必须满足：

1. 不修改 `workflows/*.json`。
2. 不修改 `src/drama_studio/` 中的业务代码。
3. 只提供 `pack.yaml`、风格规范、参考图、关键帧/镜头描述、音频配置。
4. 使用同一套批处理与状态机，产出同样的 `job.json` / `quality.json`。

反例（禁止）：

- 在 Python 里写 `if pack == "chunjiang"`。
- 为每部作品复制一套 FFmpeg 命令。
- 把作品名、诗词句子写进工作流参数以外的代码。
