# 06 · 音频、资产与授权台账

> 状态：`DECISION` / 2026-11-12 由 `ASSET_AND_LICENSE_REGISTRY.md` 与 `AUDIO_ASSET_STRATEGY.md` 合并。
> 台账是记录，不等于法律意见；商业发布前做一次正式授权复核。
> 原始两份文档已归档到 `D:\DramaStudio\archive\docs\2026-11-12\`（见 [ARCHIVE.md](ARCHIVE.md)）。

## 1. 登记规则

新增任何素材必须填全：

```text
asset_id, 类型, 名称, 官方来源 URL, 作者/提供方, 版本,
许可证名称, 商业使用权限, 署名要求, 平台限制,
下载日期, 文件哈希, 审核状态, 证据位置
```

状态口径：`NOT_RUN`（未试听/下载/测试）、`DECISION`（候选未定）、`PASS_VERIFIED`（有证据）、`PARTIAL`（只核实部分条件）、`REJECTED` / `REVOKED`（不可用于生产）。

规则：

- 未登记授权的素材不得进入可发布成片。
- 来源级许可不等于单项许可；不能因为素材来自 Pixabay / Mixkit / 某个开源项目就整站标记为商用通过。
- 模型/工作流升级后更新 sha256 与 `used_in`。
- 不得抽取电影/动画原声、不得使用来源不明的网络图片。

## 2. 模型与权重

权重统一在 `models`（本机默认 `D:/AI/models`），不进入 Git。完整哈希见本地 `logs/model-sha256.txt`。

| 资产 | 文件 | 许可证 | 状态 |
|---|---|---|---|
| FLUX.3 Klein distilled | `diffusion_models/flux3/flux-3-image-klein-Q4_K_M.gguf` | FLUX Kommunity License（年营收 < 500 万美元免费商用；需内容过滤与 AI 标注） | `PASS_LIMITED` |
| FLUX.3 文本编码器 | `text_encoders/qwen3vl_4b_int8_convrot.safetensors` | 随 BFL 仓库分发；Qwen3-VL-4B 本体 Apache-2.0 | `PASS_LIMITED` |
| FLUX VAE（复用） | `vae/flux2-vae.safetensors` | Apache-2.0 | `PASS_VERIFIED` |
| Wan2.2 TI2V 5B | `Wan2.2-TI2V-5B-Q4_K_M.gguf` | Apache-2.0（Comfy-Org 模型卡） | `PASS_VERIFIED` |
| Wan 文本编码器 | `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 随 Comfy-Org 重打包；UMT5 底层待复核 | `PASS_VERIFIED` |
| Wan VAE | `vae/wan2.2_vae.safetensors` | Apache-2.0 | `PASS_VERIFIED` |
| 本地 LLM | `Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf` | 模型卡条款；接入剧本前登记 | 使用中 |

## 3. 运行时与工具

| 工具 | 版本 | 许可证 | 备注 |
|---|---|---|---|
| ComfyUI | 0.43.0（`bb878b9`） | **GPL-3.0** | 内部使用；打包分发需评估 GPL 义务 |
| ComfyUI-GGUF | `6ea2651` / gguf 0.19.0 | Apache-2.0 | — |
| PyTorch | 2.15.0+xpu | BSD-3-Clause | — |
| VoxCPM2 | 2B 运行时（`VoxCPM-Runtime`） | Apache-2.0（代码与权重） | 参考音权利单独核验 |
| FFmpeg / ffprobe | 8.1 full build | **GPLv3 构建** | 内部渲染；分发二进制需评估 GPL |
| llama.cpp | SYCL b12024 | MIT | 模型许可按各模型卡 |

## 4. 字体

OTF 二进制（约 58 MiB）不进 Git，由 `scripts/fetch_fonts.py` 从 Adobe 官方 Release 重建并校验 SHA-256；`assets/fonts/font_manifest.json`、README、LICENSE 纳入版本控制。

| 字体 | 版本 | 许可 | 用途/状态 |
|---|---|---|---|
| Source Han Serif CN（思源宋体） | 2.003R | SIL OFL 1.1 | 标题/诗词候选；`PASS_VERIFIED`（来源/许可/覆盖/预览），最终排版 `DECISION` |
| Source Han Sans CN（思源黑体） | 2.005R | SIL OFL 1.1 | 字幕已接入 `config/fonts.yaml`；现代解说 `PARTIAL` |
| Microsoft YaHei | 系统 | **专有，不可再分发** | R3-B 历史成片；公开发布前必须替换 |

## 5. 音乐与音效

`assets/audio/manifest.json` 是唯一资产清单。当前 13 条 BGM：Keynata 7 条（5 条用户听感否决为「阴间」→ `REJECTED`，2 条保留备用）与 Wikimedia Commons 6 条（4 条 Public domain + 2 条 CC BY 3.0 US，后者**必须署名**）。SFX（wind / water / chime / whoosh）为自生成，无第三方采样。

| 类别 | 当前可用 | 状态 |
|---|---|---|
| BGM · Commons PD | Mozart K.330、Grieg《晨曲》、Mozart K.525、Schubert D.664 | `APPROVED`（人工听感 PENDING） |
| BGM · Commons CC BY | Jason Shaw《Green Leaves》《Serenity》 | `APPROVED`（需署名；听感 PENDING） |
| BGM · Keynata | 2 条备用 | `REJECTED`（听感）/ 备用 |
| SFX | 自生成 4 条 | `APPROVED`（听感 PENDING） |
| 授权未知曲目 | `We Never` 等 | `PENDING_REVIEW`，不得生产 |

音频策略（2026-11-04 决策，仍有效）：

- S2 环境音优先**程序化拟音**（`anoisesrc` + 滤波 + 调制），零素材依赖。
- S3 垫乐只用 CC0 / 公有领域曲库并登记；不碰平台条款受限的曲库。
- S4 参考音频克隆是**声音人格权**问题，不是技术问题；只有取得明确授权的参考音才能进生产。
- `narrator_self` 是唯一 `APPROVED` 生产音色（参考音 `assets/audio/prompts/my_voice_clean_v2.wav`，用户 2026-11-07 确认）。孙道临、雅坤等第三方录像参考音 `BLOCKED`，只能试听研究，不得入成片。
- 旧 CosyVoice SFT 预置音色已退役，仅作历史证据。

## 6. 许可门禁（正式构建路径）

| 编号 | 规则 | 拒绝条件 |
|---|---|---|
| L1 | 被引用音频必须在 manifest 里有条目 | 缺条目 |
| L2 | `commercial_allowed` 必须为 true | 非商用素材进正式成片 |
| L3 | `sha256` 必须与文件一致 | 素材被替换未重新登记 |
| L4 | 非自生成素材必须有 `license_doc` | 只有 URL 没有协议快照 |
| L5 | `usage: mock` 不得出现在正式产物 | mock 混入成片 |
| L6 | `kind: prompt` 必须附 `voice_rights` | 克隆参考音没有权利声明 |

门禁只在正式构建路径（`r3_build` / 工作台 `build.rebuild`）执行，实验脚本不拦。

## 7. 授权缺口与行动

1. UMT5 底层模型与 Comfy-Org 重打包许可一致性。
2. Microsoft YaHei 在公开发布前替换为可商用开源字体。
3. 项目代码许可证（是否开源、采用何种许可证）。
4. ComfyUI / FFmpeg GPL：打包分发整套工具前做合规评估。
5. 本地 LLM 各模型卡的许可证登记。
6. 平台 AI 标识：发布前按平台规则执行并留痕。
7. BGM 人工听感与商用范围逐条确认；SFX 商用授权 `NOT_RUN`。

## 8. 新增资产模板

```json
{
  "asset_id": "",
  "type": "model|image|audio|font|music|workflow|code",
  "path": "",
  "source": "",
  "license": "",
  "license_url": "",
  "sha256": "",
  "created_at": "",
  "used_in": [],
  "commercial_use": "allowed|review|not_allowed|unknown",
  "notes": ""
}
```
