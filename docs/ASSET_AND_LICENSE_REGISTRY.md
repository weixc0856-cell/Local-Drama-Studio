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
| Microsoft YaHei | Windows 系统 | **专有，不可再分发** | R3 烧录字幕 |
| 开源 CJK 候选 | 未选定 | 待登记 | 公开发布建议替换 |

发布前行动：选择一款可商用的开源 CJK 字体（如思源黑体/Noto Sans CJK，需登记其许可证），替换烧录字体。

## 5. 音乐与音效

| 资产 | 状态 |
|---|---|
| BGM | `NOT_RUN` / 待选型（R3-D），当前无 |
| 音效 | `NOT_RUN` / 待选型（R3-D），当前无 |
| 第三方音乐 | 未使用；使用前必须登记授权 |

## 6. 音色

| 音色 | 来源 | 状态 |
|---|---|---|
| 「中文男」SFT 预置音色 | CosyVoice-300M-SFT | `PASS_VERIFIED` 合成；商用/平台使用条款待复核 |
| 「中文女」SFT 预置音色 | CosyVoice-300M-SFT | `NOT_RUN` / 待试听选型 |
| 自定义克隆音色 | 未使用 | `NOT_RUN` |

## 6.1 R3-D 资产选型登记（`DECISION` / `NOT_RUN`）

> R3-D 尚未执行。下表是候选与待核验状态，**不是商用批准**。
> 不能因为素材来自 Pixabay / Mixkit / 某个开源项目，就把整个来源标记为商用通过；必须逐项核验。

| asset_id | 类型 | 名称 | 官方来源 | 提供方 | 版本 | 许可证 | 商业使用 | 署名 | 平台限制 | 下载日期 | 文件哈希 | 状态 | 证据位置 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TTS-COSY-MALE | TTS 音色 | 中文男（基线） | 本地 CosyVoice | CosyVoice-300M-SFT | — | Apache-2.0（代码）；音色条款待核验 | 待核验 | 待核验 | 待核验 | 本地 | 已有音频哈希 | `PASS_VERIFIED`（合成）/ 授权 `PARTIAL` | `experiments/r3b/audio_manifest.json` |
| TTS-COSY-FEMALE | TTS 音色 | 中文女 | 本地 CosyVoice | CosyVoice-300M-SFT | — | 同上 | 待核验 | 待核验 | 待核验 | — | — | `NOT_RUN` | — |
| TTS-ALI-WEN | TTS 音色 | 温怀清 | 阿里云 Qwen TTS | 阿里云 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-ALI-YU | TTS 音色 | 余小云 | 阿里云 Qwen TTS | 阿里云 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV115 | TTS 音色 | 古风少御 BV115 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV104 | TTS 音色 | 温柔淑女 BV104 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-VOLC-BV009 | TTS 音色 | 知性女生 BV009 | 火山引擎 | 火山引擎 | 待确认 | 服务协议 | 待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方音色页 |
| TTS-ELEVEN | TTS 音色 | 中文女性音色（对照） | ElevenLabs | ElevenLabs | 待确认 | 付费套餐条款 | 付费套餐待核验 | 待核验 | 待核验 | — | — | `DECISION` / 未试听 | 官方 Voice Library |
| FONT-SERIF | 字体 | 思源宋体 | https://github.com/adobe-fonts/source-han-serif | Adobe | 待选版本 | SIL OFL 1.1 | 允许（需保存 LICENSE） | 无（OFL） | 不得单独售卖字体 | — | — | `DECISION` / 待下载核验 | 官方仓库 |
| FONT-SANS | 字体 | 思源黑体 | https://github.com/adobe-fonts/source-han-sans | Adobe | 待选版本 | SIL OFL 1.1 | 允许（需保存 LICENSE） | 无（OFL） | 不得单独售卖字体 | — | — | `DECISION` / 待下载核验 | 官方仓库 |
| FONT-WENKAI | 字体 | 霞鹜文楷 | https://github.com/lxgw/LxgwWenKai | LXGW | 待选版本 | SIL OFL 1.1 | 允许（需保存 LICENSE） | 无（OFL） | 不得单独售卖字体 | — | — | `DECISION` / 待下载核验 | 官方仓库 |
| BGM-PIXABAY | 音乐 | 古琴/箫/古筝候选 | https://pixabay.com/music/ | 逐曲作者 | — | Pixabay Content License | 逐曲核验 | 逐曲核验 | 注意 Content ID | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| BGM-MIXKIT | 音乐 | 东方氛围候选 | https://mixkit.co/free-stock-music/ | 逐曲作者 | — | Mixkit License | 逐曲核验 | 逐曲核验 | 使用场景限制 | — | — | `NOT_RUN` / 待选型 | 逐曲页面 |
| SFX-FREESOUND | 音效 | 水流/风声/鸟鸣/衣袂/钟磬 | https://freesound.org/ | 逐条作者 | — | 优先 CC0；CC BY 需署名 | 逐条核验 | CC BY 需要 | 不得用 CC BY-NC | — | — | `NOT_RUN` / 待选型 | 逐条页面 |

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
6. **本地 LLM 模型**（Qwen3.5-4B 等）：接入剧本前登记各自许可证。
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
