# 06 · ASSET_AND_LICENSE_REGISTRY — 资产与授权台账

> 文档状态：`DECISION` / v1.0 台账规范冻结。
> 台账是记录，不等于法律意见；商业发布前建议做一次正式授权复核。

## 1. 模型与权重

路径统一在 `D:\AI\models`，不进入 Git。

| 资产 | 文件 | 大小 | sha256 | 许可证 | 状态 |
|---|---|---|---|---|---|
| FLUX.2 Klein 4B | `flux-2-klein-4b-Q4_K_M.gguf` | 2.60 GB | `0b25d143c8469b34…` | Apache-2.0（HF 模型卡） | `PASS_VERIFIED` |
| FLUX 文本编码器 | `text_encoders/qwen_3_4b.safetensors` | 8.04 GB | `6c671498573ac2f7…` | Apache-2.0 | `PASS_VERIFIED` |
| FLUX.2 VAE | `vae/flux2-vae.safetensors` | 336 MB | `868fe7b343cc8f3a…` | Apache-2.0（同仓库） | `PASS_VERIFIED` |
| Wan2.2 TI2V 5B | `Wan2.2-TI2V-5B-Q4_K_M.gguf` | 3.43 GB | `95b19697b7f98e65…` | Apache-2.0（Comfy-Org 模型卡） | `PASS_VERIFIED` |
| Wan 文本编码器 | `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6.73 GB | `c3355d30191f1f06…` | 随 Comfy-Org 重打包；底层 UMT5 待复核 | `PASS_VERIFIED` |
| Wan2.2 VAE | `vae/wan2.2_vae.safetensors` | 1.41 GB | `e40321bd36b97099…` | Apache-2.0（同仓库） | `PASS_VERIFIED` |

完整哈希：`logs/model-sha256.txt`（本地证据，不进入 Git）。

## 2. 运行时与工具

| 工具 | 版本 | 许可证 | 备注 |
|---|---|---|---|
| ComfyUI | 0.43.0（`bb878b9`） | **GPL-3.0** | 内部使用；如打包分发需评估 GPL 义务 |
| ComfyUI-GGUF | `6ea2651` / gguf 0.19.0 | Apache-2.0 | — |
| PyTorch | 2.15.0+xpu | BSD-3-Clause | — |
| torchvision / torchaudio | 0.29.2 / 2.11.1 +xpu | BSD-3-Clause | — |
| CosyVoice | 300M-SFT 运行时 | Apache-2.0（本地 LICENSE） | 模型与预置音色条款待复核 |
| FFmpeg / ffprobe | 8.1-full_build（gyan） | **GPLv3 构建** | 内部渲染；分发二进制需评估 GPL |
| llama.cpp（D:\AI） | SYCL b12024 | MIT | 模型许可按各模型卡 |
| Python 调度依赖 | 见 TECH_STACK | 各包元数据 | 未发现 copyleft 冲突 |

## 3. 视觉资产

| 目录 | 内容 | 状态 |
|---|---|---|
| `assets/visual_style/` | 视觉规范、主参考图、场景图、一致性对比 | `PASS_VERIFIED`（R1） |
| `assets/keyframes/` | 4 张 16:9 关键帧 + meta + relationships | `PASS_VERIFIED`（R1） |
| `assets/vertical/` | 5 张 576×1024 竖屏静帧 + 1 段 Wan + index.json | `PASS_VERIFIED`（R3） |
| `experiments/r3b/audio/` | 7 句 CosyVoice「中文男」WAV + manifest | `PASS_VERIFIED`（R3） |
| `experiments/r3a/` ~ `r3b/` | 原始帧、运行记录、构建清单 | 证据保留 |

图片/视频的 sha256 已写入各自的 `.meta.json`、`index.json` 或 `build_manifest.json`。

## 4. 字体

| 字体 | 来源 | 授权 | 用途 |
|---|---|---|---|
| Microsoft YaHei | Windows 系统 | **专有，不可再分发** | R3-B 烧录字幕（历史） |
| Source Han Serif CN 2.003R | Adobe 官方 GitHub Release | SIL OFL 1.1（实际 `LICENSE.txt`） | 标题/诗词候选 |
| Source Han Sans CN 2.005R | Adobe 官方 GitHub Release | SIL OFL 1.1（实际 `LICENSE.txt`） | 现代解说/字幕候选 |

发布前行动：字体候选已下载并完成来源、许可、字符覆盖和竖屏预览验证；字幕已接入新构建，标题/诗词/现代解说仍为 `preview_only`，排版角色仍为 `DECISION`。R3-B 历史成片未重渲染，仍使用 Microsoft YaHei。

### 4.1 S3-B.1/S3-B.2 字体候选与接入登记

| 项 | FONT-SERIF | FONT-SANS |
|---|---|---|
| 字体 | Source Han Serif CN / 思源宋体 CN | Source Han Sans CN / 思源黑体 CN |
| Release | `2.003R` | `2.005R` |
| 保留字重 | Regular / Medium / Bold | Regular / Medium / Bold |
| 文件与 SHA-256 | `assets/fonts/source-han-serif-cn/`；详见 `font_manifest.json` | `assets/fonts/source-han-sans-cn/`；详见 `font_manifest.json` |
| 许可证 | SIL OFL 1.1；Reserved Font Name `Source` | 同左 |
| 字符覆盖 | 120 字测试语料，0 缺字 | 120 字测试语料，0 缺字 |
| 预览 | `experiments/r3d/fonts/previews/` | 同左 |
| 状态 | `PASS_VERIFIED`（来源/许可/覆盖/预览）；标题/诗词 `PARTIAL`；最终排版 `DECISION` | `PASS_VERIFIED`（来源/许可/覆盖/预览/字幕接入）；现代解说 `PARTIAL`；最终排版 `DECISION` |
| 证据 | `assets/fonts/font_manifest.json`、`docs/R3D_FONT_SELECTION_REPORT.md`、`experiments/r3d/fonts/s3b2_validation.json` | 同左 |

S3-B.2 接入：`config/fonts.yaml` + `src/drama_studio/fonts.py`；`scripts/r3_build.py` 的字幕角色已使用 `Source Han Sans CN`，通过本地 `fontsdir`、`fontselect` 日志和 SHA-256 校验，不依赖系统字体。标题/诗词/现代解说目前是 `preview_only`，尚未由正式构建渲染。

分发方式：OTF 二进制（约 58.04 MiB）不进入 Git；`font_manifest.json`、`README.md` 与 `LICENSE.txt` 纳入版本控制。运行 `scripts/fetch_fonts.py` 从 Adobe 官方 Release 重建，并校验压缩包与每个 OTF 的 SHA-256。不需要 LFS；不提交源压缩包。

## 5. 音乐与音效

| 资产 | 类型 | 文件 | 许可/来源 | 商用 | 状态 |
|---|---|---|---|---|---|
| `bgm_ink_strings_duo` | BGM | `assets/audio/bgm/keynata/ink_strings_duo.wav` | Keynata Commons `classical_duo_24036`；CC0-1.0 | 是 | `APPROVED`（人工听感 PENDING） |
| `bgm_court_strings_duo` | BGM | `assets/audio/bgm/keynata/court_strings_duo.wav` | Keynata Commons `classical_duo_24015`；CC0-1.0 | 是 | `APPROVED`（人工听感 PENDING） |
| `bgm_shinkai_piano` | BGM | `assets/audio/bgm/keynata/shinkai_piano.wav` | Keynata Commons `classical_piano_6134`；CC0-1.0 | 是 | `APPROVED`（人工听感 PENDING） |
| `bgm_ghibli_quartet` | BGM | `assets/audio/bgm/keynata/ghibli_quartet.wav` | Keynata Commons `classical_quartet_25010`；CC0-1.0 | 是 | `APPROVED`（人工听感 PENDING） |
| 旧正弦 drone ×4 | BGM | `assets/audio/bgm/*.wav` | 自生成 | — | `REJECTED`（用户明确拒绝嗡嗡声） |
| SFX（wind/water/chime/whoosh） | SFX | `assets/audio/sfx/*.wav` | 自生成；无第三方采样 | 是 | `APPROVED`（人工听感 PENDING） |
| 第三方音乐 | BGM | — | 未使用；使用前必须逐曲登记来源/许可/SHA-256 | 待核验 | `NOT_RUN` |

## 6. 音色

| 音色 | 来源 | 状态 |
|---|---|---|
| 「中文男」SFT 预置音色 | CosyVoice-300M-SFT | `PASS_VERIFIED` 合成；商用/平台使用条款待复核 |
| 「中文女」SFT 预置音色 | CosyVoice-300M-SFT | 已进入 P1 与 81.373 s 工笔（`PASS_VERIFIED` 技术）；商用待核验 |
| 自定义克隆音色 | 未使用 | `NOT_RUN` |

## 6.1 R3-D 资产选型登记（`DECISION` / `PARTIAL`）

> R3-D 已部分执行：字体候选的来源、许可、字符覆盖和预览验证完成；排版选型仍待人工审查。`narrator_self` 为唯一 `APPROVED` 生产音色；BGM 已替换为 4 条 CC0 Keynata 弦乐/钢琴曲并通过真实混音；旧 drone 全部 REJECTED；SFX/环境音与商用授权仍未完成。
> 下表是候选与待核验状态，**不是商用批准**；不能因为素材来自 Pixabay / Mixkit / 某个开源项目，就把整个来源标记为商用通过。

| asset_id | 类型 | 名称 | 官方来源 | 提供方 | 版本 | 许可证 | 商业使用 | 署名 | 平台限制 | 下载日期 | 文件哈希 | 状态 | 证据位置 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TTS-COSY-MALE | TTS 音色 | 中文男（基线） | 本地 CosyVoice | CosyVoice-300M-SFT | — | Apache-2.0（代码）；音色条款待核验 | 待核验 | 待核验 | 待核验 | 本地 | 已有音频哈希 | `PASS_VERIFIED`（合成）/ 授权 `PARTIAL` | `experiments/r3b/audio_manifest.json` |
| TTS-COSY-FEMALE | TTS 音色 | 中文女 | 本地 CosyVoice | CosyVoice-300M-SFT | — | 同上 | 待核验 | 待核验 | 待核验 | — | — | `PASS_VERIFIED`（技术，P1/81.373）；商用待核验 | `experiments/r3d/voice/` |
| TTS-ALI-WEN | TTS 音色 | 温怀清 | 阿里云 Qwen TTS | 阿里云 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-ALI-YU | TTS 音色 | 余小云 | 阿里云 Qwen TTS | 阿里云 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV115 | TTS 音色 | 古风少御 BV115 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV104 | TTS 音色 | 温柔淑女 BV104 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV009 | TTS 音色 | 知性女生 BV009 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-ELEVEN | TTS 音色 | 中文女性音色（对照） | ElevenLabs | ElevenLabs | 待确认 | 付费套餐条款 | 付费套餐待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方 Voice Library |
| FONT-SERIF | 字体 | 思源宋体 CN | https://github.com/adobe-fonts/source-han-serif | Adobe | 2.003R | SIL OFL 1.1 | 允许（OFL；保留许可证） | 无强制署名；保留版权/许可 | 不得单独售卖字体 | 2026-11-03 | 见 `assets/fonts/font_manifest.json` | `PASS_VERIFIED`（来源/许可/覆盖/预览）；标题/诗词 `PARTIAL`；最终排版 `DECISION` | `assets/fonts/font_manifest.json`；`docs/R3D_FONT_SELECTION_REPORT.md`；`experiments/r3d/fonts/s3b2_validation.json` |
| FONT-SANS | 字体 | 思源黑体 CN | https://github.com/adobe-fonts/source-han-sans | Adobe | 2.005R | SIL OFL 1.1 | 允许（OFL；保留许可证） | 无强制署名；保留版权/许可 | 不得单独售卖字体 | 2026-11-03 | 见 `assets/fonts/font_manifest.json` | `PASS_VERIFIED`（来源/许可/覆盖/预览/字幕接入）；现代解说 `PARTIAL`；最终排版 `DECISION` | `assets/fonts/font_manifest.json`；`docs/R3D_FONT_SELECTION_REPORT.md`；`experiments/r3d/fonts/s3b2_validation.json` |
| FONT-WENKAI | 字体 | 霞鹜文楷 | https://github.com/lxgw/LxgwWenKai | LXGW | 待选版本 | SIL OFL 1.1 | 允许（需保存 LICENSE） | 无（OFL） | 不得单独售卖字体 | — | — | `DECISION` / 待下载核验 | 官方仓库 |
| BGM-PIXABAY | 音乐 | 古琴/箫/古筝候选 | https://pixabay.com/music/ | 逐曲作者 | — | Pixabay Content License | 逐曲核验 | 逐曲核验 | 注意 Content ID | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| BGM-MIXKIT | 音乐 | 东方氛围候选 | https://mixkit.co/free-stock-music/ | 逐曲作者 | — | Mixkit License | 逐曲核验 | 逐曲核验 | 使用场景限制 | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| SFX-FREESOUND | 音效 | 水流/风声/鸟鸣/衣袂/钟磬 | https://freesound.org/ | 逐条作者 | — | 优先 CC0；CC BY 需署名 | 逐条核验 | CC BY 需要 | 不得用 CC BY-NC | — | — | `NOT_RUN` / 待选型 | 逐条页面 |
| SFX-PROGRAMMATIC | 音效 | 江水/夜风/室内底噪 | 本地生成 `scripts/make_ambience.py` | — | — | 自生成，无第三方权利 | 不需要 | 不需要 | 无 | 生成脚本 sha256 | 待实现 | `NOT_RUN` / 方案已定 | [AUDIO_ASSET_STRATEGY.md](AUDIO_ASSET_STRATEGY.md) §2 |
| BGM-FREEPD | 音乐 | 东方氛围/器乐 | https://freepd.com/ | 逐曲作者 | — | 全站 CC0 | 不需要 | 不需要 | 无 | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| BGM-MUSOPEN | 音乐 | 古典器乐 | https://musopen.org/ | 逐曲演奏者 | — | PD / CC0（录音与乐谱分开核验） | 不需要 | 不需要 | 无 | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| TTS-PROMPT-SELF | 语音参考 | 克隆 prompt | 自录 | — | — | 自持声音权 | 已附《声音权声明》 | — | 无 | 录音哈希 | 已有 3.35s 清理版 | `PARTIAL`（时长偏短；待补录 8–10 s） | [AUDIO_ASSET_STRATEGY.md](AUDIO_ASSET_STRATEGY.md) §9 |

登记字段（新增素材时必须填全）：

```text
asset_id, 类型, 名称, 官方来源 URL, 作者/提供方, 版本,
许可证名称, 商业使用权限, 署名要求, 平台限制,
下载日期, 文件哈希, 审核状态, 证据位置
```

状态口径：

- `NOT_RUN`：尚未试听、下载或测试。
- `DECISION`：已列为候选，尚未最终决定。
- `PASS_VERIFIED`：已实际核验并有证据。
- `PARTIAL`：只核实了部分条件。

## 7. 代码与工作流

| 资产 | 许可 | 状态 |
|---|---|---|
| `scripts/*.py`、`src/drama_studio/*` | 项目自有；未声明开源许可证 | `DECISION` |
| `workflows/*.json` | 项目自有/基于官方模板改写 | `DECISION` |
| 官方 ComfyUI 模板 | 随 ComfyUI 分发 | 按其许可证 |

## 8. 授权缺口与行动

1. **UMT5 底层模型**：确认 Comfy-Org 重打包文件与上游许可证一致性。
2. **CosyVoice SFT 模型与预置音色**：确认模型卡与音色商用条款。
3. **Microsoft YaHei**：公开发布/商业使用前替换为可商用开源字体。
4. **项目代码许可证**：决定是否开源、采用何种许可证。
5. **ComfyUI / FFmpeg GPL**：若未来打包分发整套工具，做 GPL 合规评估。
6. **本地 LLM 模型**（当前默认 `Qwen3-30B-A3B-Instruct-2507`；另有 Qwen3-Coder-30B-A3B、Qwen3VL-30B-A3B、Qwen3-8B、Qwen3.5-4B、DeepSeek-R1-8B）：接入剧本前登记各自许可证。
7. **平台 AI 标识**：发布前按平台规则执行，台账留痕。
8. **R3-D 候选素材**：逐项补齐 §6.1 的来源、许可、商用范围与证据；来源级许可不等于单项许可。

## 9. 新增资产登记模板

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

规则：

- 未登记授权的素材不得进入可发布成片。
- 模型/工作流升级后更新 sha256 与 `used_in`。
- 参考图来源必须记录；不得使用来源不明的网络图片。

## 10. 完整模型哈希（2026-11-03）

```text
0b25d143c8469b342bc5af3bce92b783bf6b0636d285f7b2f75e38af63af9a15  flux-2-klein-4b-Q4_K_M.gguf
95b19697b7f98e65b0a543640e9ca7b4dfec32e2a6e3731e8e10708be52655e2  Wan2.2-TI2V-5B-Q4_K_M.gguf
6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a  qwen_3_4b.safetensors
c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68  umt5_xxl_fp8_e4m3fn_scaled.safetensors
868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3  flux2-vae.safetensors
e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156  wan2.2_vae.safetensors
```

本地记录：`logs/model-sha256.txt`（不进入 Git）。
