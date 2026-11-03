# S3-B.1 字体候选验证与最小素材集

> 执行日期：2026-11-03
> 范围：仅字体来源、许可证、字符覆盖、竖屏排版预览和资产登记
> 候选：思源宋体 CN / Source Han Serif CN；思源黑体 CN / Source Han Sans CN
> 当前状态：来源/许可证/覆盖/预览已验证；排版角色仍为 `DECISION`，等待人工审查
> S3-B.2：字体配置已接入正式构建的字幕入口（标题/诗词/现代解说仍为 preview-only）
> 未修改 R3-B 成片、未替换历史字幕字体、未安装系统字体、未提交 Git

## 1. 官方来源与下载

| 项 | 思源宋体 CN | 思源黑体 CN |
|---|---|---|
| 官方仓库 | https://github.com/adobe-fonts/source-han-serif | https://github.com/adobe-fonts/source-han-sans |
| Release | `2.003R`（2024-07-30） | `2.005R`（2025-06-18） |
| CN 资产 | `14_SourceHanSerifCN.zip` | `19_SourceHanSansCN.zip` |
| 下载大小 | 68,961,106 bytes | 50,700,226 bytes |
| 压缩包 SHA-256 | `aa3f9134809de83bb2add0bd965e61421772ce2fd8628fe98516b77c93e1d819` | `3a769d1b082ebd813cdb4c06ea57d29b340bce548edcc8e61976b78ca28e6236` |
| 下载日期 | 2026-11-03 | 2026-11-03 |
| 保存位置 | `logs/s3b_download/`（Git 忽略） | 同左 |

只下载 CN 专用包，未下载完整多语言包；未使用第三方字体站、网盘或镜像；未安装到 Windows 系统字体目录；未修改字体文件。

## 2. 保留的字体文件

为了形成最小素材集，只提取 Regular / Medium / Bold 三个字重：

| 字体 | 字重 | 文件大小 | SHA-256 |
|---|---|---:|---|
| Source Han Serif CN | Regular | 11,626,108 | `3754ea669c530e2473354f8f6d9f79680a44d7e26ec7d00eeabee4a7e0753c5d` |
| Source Han Serif CN | Medium | 11,734,704 | `f7906890686d17e122980efd2d6097d1caefed76312994baeaf220819e818f3a` |
| Source Han Serif CN | Bold | 12,094,680 | `4ee555ae58b3d22f6a95c2c494f2c36b7cccfc1d2224635f6461a03756f0e3c1` |
| Source Han Sans CN | Regular | 8,429,224 | `e2bc8a2e7f37474b774fff8db758681ece40bb6947a90d571bce9dd60671a8e4` |
| Source Han Sans CN | Medium | 8,406,556 | `a94e558a2fe972bee4f46bce0843abff37063fd68c33f1e7d9058f6f09432b01` |
| Source Han Sans CN | Bold | 8,569,308 | `62383707c086a32f3afd5e293f34c7eff64c7fea31f579fdc6cbe34d920519a6` |

完整清单见 [assets/fonts/font_manifest.json](../assets/fonts/font_manifest.json)。六个 OTF 与官方压缩包内对应条目逐字节一致；`LICENSE.txt` 也逐字节一致。

### 内部名称与版本

| 字体族 | 内部 family | Version | 字重 |
|---|---|---|---|
| Source Han Serif CN | `Source Han Serif CN` / `思源宋体 CN` | 2.003 | 400 / 500 / 700 |
| Source Han Sans CN | `Source Han Sans CN` / `思源黑体 CN` | 2.005 | 400 / 500 / 700 |

Medium 的内部 family 分别为 `Source Han Serif CN Medium` / `Source Han Sans CN Medium`；ASS 预览使用该 exact family 选择 Medium，而不是合成粗体。

## 3. 许可证核验

实际字体目录内均保存完整 `LICENSE.txt`：

| 项 | 结论 |
|---|---|
| 许可证名称 | SIL Open Font License 1.1（2007-02-26） |
| 版权声明 | Serif：`Copyright 2017-2022 Adobe`；Sans：`Copyright 2014-2025 Adobe` |
| Reserved Font Name | `Source` |
| 商业使用 | OFL 1.1 允许，按许可证条款 |
| 视频/软件嵌入 | 允许嵌入/打包；用字体创建的文档不受 OFL 限制 |
| 随项目分发字体 | 允许；必须保留版权声明和许可证文本 |
| 单独销售字体 | 不允许 |
| 修改字体 | 未修改；修改版不得使用 Reserved Font Name |
| 许可证文件 SHA-256 | Serif `9ff5bb567e1b92c801fc1069e5fbf992ff8efccacb9db94e5959a5b3ba9bb903`；Sans `fcac737e761ec63dbfbdce11030a1780161920d80315edba9c8beff1c2bac5a2` |

结论基于实际下载包内的 `LICENSE.txt`，不是仓库介绍页。字体授权不等同于模型、音色、图片、音乐或其他素材的授权；本报告不构成法律意见。

## 4. 字符覆盖

测试语料：`experiments/r3d/fonts/corpus.txt`，共 120 个唯一字符，包含：

- 《春江花月夜》诗句；
- 《洛神赋》候选句，含「翩若惊鸿」「髣髴」「飘飖」「秾纤」等；
- 现代中文长句、标点、数字和中英文混排；
- 常见符号。

使用本机已有的 fontTools 4.62.1 读取实际 OTF 的 cmap，检查六个文件：

| 字体 | glyphs | cmap codepoints | 缺字 |
|---|---:|---:|---:|
| Source Han Serif CN Regular/Medium/Bold | 31,058 | 30,930 | 0 |
| Source Han Sans CN Regular/Medium/Bold | 31,072 | 30,926 | 0 |

详细结果：[coverage_report.json](../experiments/r3d/fonts/coverage_report.json)。

**限制：**这是 120 字符语料检查，不等同于全量 CJK 字符审查；当前实际 cmap 覆盖约 3.1 万码位。

## 5. 竖屏排版预览

画布 1080×1920；渲染器 FFmpeg 8.1 + libass；字体通过 `fontsdir` 从 `assets/fonts/` 本地加载；未安装系统字体。

| 组 | 文件 | 字体/字重 | 主要参数 |
|---|---|---|---|
| A1 | [A1_title_centered.png](../experiments/r3d/fonts/previews/A1_title_centered.png) | Serif CN Bold | 170 px，居中 |
| A2 | [A2_title_left.png](../experiments/r3d/fonts/previews/A2_title_left.png) | Serif CN Regular | 120 px，左对齐 |
| A3 | [A3_title_weights.png](../experiments/r3d/fonts/previews/A3_title_weights.png) | Serif CN Regular/Medium/Bold | 120 px，三字重对比 |
| B1 | [B1_poem_light.png](../experiments/r3d/fonts/previews/B1_poem_light.png) | Serif CN Regular | 72 px，行距 130 px，浅底 |
| B2 | [B2_poem_dark.png](../experiments/r3d/fonts/previews/B2_poem_dark.png) | Serif CN Medium | 64 px，行距 120 px，深底 |
| B3 | [B3_poem_scale.png](../experiments/r3d/fonts/previews/B3_poem_scale.png) | Serif CN Regular | 64/76/88 px，字间距 0/2/4 |
| C1 | [C1_subtitle_outline.png](../experiments/r3d/fonts/previews/C1_subtitle_outline.png) | Sans CN Regular | 56 px，描边 3 px，底部安全 180 px |
| C2 | [C2_subtitle_box.png](../experiments/r3d/fonts/previews/C2_subtitle_box.png) | Sans CN Regular | 52 px，半透明底板，底部安全 180 px |
| C3 | [C3_subtitle_weights.png](../experiments/r3d/fonts/previews/C3_subtitle_weights.png) | Sans CN Regular/Medium/Bold | 50 px，三字重对比 |
| D | [D_mixed_title_subtitle.png](../experiments/r3d/fonts/previews/D_mixed_title_subtitle.png) | Serif CN + Sans CN | 标题/字幕分工示例 |

C1 另生成 3 秒 1080×1920 视频：[C1_subtitle_outline_demo.mp4](../experiments/r3d/fonts/previews/C1_subtitle_outline_demo.mp4)，ffprobe 为 3.000 s / 24 fps / H.264，解码退出码 0。

预览清单、尺寸、SHA-256 和排版参数见 [preview_manifest.json](../experiments/r3d/fonts/preview_manifest.json)。

### libass 字体选择证据

使用 `-loglevel debug` 渲染 A3/C3，日志显示实际加载本地 OTF 并选中：

```text
Loading font file 'assets/fonts/source-han-serif-cn\SourceHanSerifCN-Bold.otf'
fontselect: (Source Han Serif CN, 400, 0) -> SourceHanSerifCN-Regular
fontselect: (Source Han Serif CN Medium, 400, 0) -> SourceHanSerifCN-Medium
fontselect: (Source Han Serif CN, 700, 0) -> SourceHanSerifCN-Bold
fontselect: (Source Han Sans CN, 400, 0) -> SourceHanSansCN-Regular
fontselect: (Source Han Sans CN Medium, 400, 0) -> SourceHanSansCN-Medium
fontselect: (Source Han Sans CN, 700, 0) -> SourceHanSansCN-Bold
```

日志保存在 `logs/s3b_render/fontselect_*.log`。libass 还会尝试把同目录的 `LICENSE.txt` 当字体读取并产生一条非致命的 “Error opening memory font” 警告；OTF 的 fontselect 结果不受影响。

## 6. 字体角色与排版建议

以下是基于本轮合成预览的**候选规范**，不是最终批准：

| 角色 | 候选字体 | 推荐字重 | 推荐字号/间距 | 备注 |
|---|---|---|---|---|
| 古典标题 | Source Han Serif CN | Bold；长标题用 Medium | 120–170 px | 居中或左对齐；深底用象牙白 |
| 诗词正文 | Source Han Serif CN | Regular/Medium | 64–76 px；行距 120–140 px | 浅底用深墨色，深底用浅色；不默认加描边 |
| 现代解说 | Source Han Sans CN | Regular/Medium | 50–56 px | 长句优先语义换行 |
| 字幕 | Source Han Sans CN | Regular/Medium | 52–56 px；底部安全 180 px | 默认 3 px 黑边；复杂/明亮背景才用半透明底板 |
| 字号强调 | 同族 Bold | Bold | 比正文高 1 级 | 不把 Bold 当正文默认 |

角色原则：

- 宋体负责标题、诗词、文化性文字；黑体负责现代解说、字幕、信息文字。
- 两种字体可以同屏分工（D 预览），但不在同一行内混排；标题与字幕之间保留明显层级。
- 字幕不使用宋体长句；古典标题不使用黑体，以免角色冲突。
- 不引入第三种装饰字体。

## 7. 状态表

| 项 | 状态 | 说明 |
|---|---|---|
| 官方来源确认 | `PASS_VERIFIED` | Adobe 官方 GitHub Release |
| 字体文件/哈希登记 | `PASS_VERIFIED` | `font_manifest.json` |
| 许可证文件 | `PASS_VERIFIED` | 实际 `LICENSE.txt`，OFL 1.1 |
| 商业/嵌入/分发条款 | `PASS_STATIC` | 基于 OFL 文本；不替代法律意见 |
| 字符覆盖 | `PASS_VERIFIED` | 120 字测试语料，0 缺字 |
| 竖屏预览 | `PASS_VERIFIED` | 10 张 PNG + 1 段 3 s 视频 |
| 字体角色/字号选型 | `DECISION` | 待人工审查，未批准 |
| R3-B 历史成片重渲染 | `NOT_RUN` | 未覆盖；新构建字幕已接入 Source Han Sans CN |
| 真机/手机播放测试 | `NOT_RUN` | 仅合成画布预览 |
| 系统字体安装 | 未执行 | 仅本地 `fontsdir` |
| Git 提交/LFS | 未执行 | 字体文件未提交 |

## 8. 已知限制

- 只验证 120 字符测试语料，不是全量 CJK 覆盖审计。
- 预览使用合成渐变背景，未覆盖真实 R3-B 画面和复杂高光背景。
- 未在真实手机上播放；手机可读性仍需人工审查。
- R3-B 历史成片仍使用 Microsoft YaHei；S3-B.2 已让新构建字幕使用本地 Source Han Sans CN，但没有重渲染 R3-B。标题/诗词/现代解说仍未进入正式构建。
- 商业使用结论仅为 OFL 条款阅读结果，发布前仍需按项目流程复核。
- 字体文件是否纳入 Git/LFS 尚未决定；本阶段未提交任何字体文件。

## 9. S3-B.2 正式构建接入

### 配置入口

| 项 | 路径 |
|---|---|
| 字体角色配置 | `config/fonts.yaml` |
| 配置/完整性加载器 | `src/drama_studio/fonts.py` |
| 字体资产清单 | `assets/fonts/font_manifest.json` |
| 正式构建入口 | `scripts/r3_build.py` |

`load_font_config()` 读取配置与 manifest，逐个校验字体文件存在性和 SHA-256；缺失或哈希不符时抛出 `FontConfigurationError`，`r3_build.py` 将其转为明确的构建错误，不静默 fallback。

### 角色与接入状态

| 角色 | 字体/字重 | 正式构建 |
|---|---|---|
| 古典标题 | Source Han Serif CN Bold/Medium | `preview_only` |
| 诗词正文 | Source Han Serif CN Regular/Medium | `preview_only` |
| 现代解说 | Source Han Sans CN Regular/Medium | `preview_only` |
| 字幕 | Source Han Sans CN Regular | **已接入** `r3_build.py` |

当前正式构建只有字幕样式入口，因此没有为标题/诗词强行重构渲染系统；这三个角色已在 `config/fonts.yaml` 定义并在预览中验证，但尚未进入 `r3_build.py`。`build_manifest.json` 的 `font.roles_preview_only` 会记录这一限制。

### 正式构建调用关系

```text
scripts/r3_build.py
  -> load_font_config() from drama_studio.fonts
  -> subtitle face: Source Han Sans CN Regular
  -> stage fonts/SourceHanSansCN-Regular.otf into <out>/fonts/
  -> ASS style Fontname = "Source Han Sans CN"
  -> ffmpeg ass=...:fontsdir='fonts'
  -> parse libass fontselect log; expected SourceHanSansCN-Regular
  -> final_9x16.mp4 / final_9x16_burned.mp4
```

- 字幕字号 56、描边 3 px、底部安全 180 px 来自 `config/fonts.yaml`，没有散落在脚本中的字体名称/路径。
- 字体文件不安装到 Windows；libass 只读取 `<out>/fonts/` 中从项目 OTF 复制的渲染副本。
- 正式构建仍使用既有时间轴、分辨率、帧率、编码、响度和 True Peak 参数。

### S3-B.2 预览

| 文件 | 内容 | 状态 |
|---|---|---|
| [S3B2_01_classical_title_poem_subtitle.png](../experiments/r3d/fonts/s3b2_previews/S3B2_01_classical_title_poem_subtitle.png) | 宋体标题 + 宋体诗词 + 黑体字幕 | 生成通过 |
| [S3B2_02_modern_narration_subtitle.png](../experiments/r3d/fonts/s3b2_previews/S3B2_02_modern_narration_subtitle.png) | 黑体现代解说 + 黑体字幕 | 生成通过 |
| [S3B2_03_light_complex_subtitle.png](../experiments/r3d/fonts/s3b2_previews/S3B2_03_light_complex_subtitle.png) | 浅色复杂背景字幕 | 生成通过 |
| [S3B2_04_dark_complex_subtitle.png](../experiments/r3d/fonts/s3b2_previews/S3B2_04_dark_complex_subtitle.png) | 深色复杂背景字幕 | 生成通过 |
| [S3B2_05_mixed_long_wrap.png](../experiments/r3d/fonts/s3b2_previews/S3B2_05_mixed_long_wrap.png) | 中英文/数字/标点长句 | 生成通过 |
| [S3B2_00_all_faces.png](../experiments/r3d/fonts/s3b2_previews/S3B2_00_all_faces.png) | 六个 OTF 字重的 libass 选择探针 | 生成通过 |

所有图像为 1080×1920；每张图的 `fontselect` 日志均在 [s3b2_previews/](../experiments/r3d/fonts/s3b2_previews/) 中，预期的本地 PostScript 名称全部出现。完整清单见 [s3b2_preview_manifest.json](../experiments/r3d/fonts/s3b2_preview_manifest.json)。

### 测试结果

```text
.venv/Scripts/python.exe -B -m pytest tests/test_fonts.py experiments/r3d/voice/test_production_build.py -q -p no:cacheprovider
```

结果：**8 项通过，退出码 0**。完整回归（原有 `tests/` + 时间轴 + 正式构建）共 **33 项通过，退出码 0**。

- 字体配置 3 项：六个 face 加载、缺字文件明确失败、SHA-256 不符明确失败。
- 正式构建 5 项：3 种内容类型、防覆盖、历史资产哈希。
- 正式构建夹具返回 0；`fontselect` 选中 `SourceHanSansCN-Regular`；`mixed.wav` 与 `final_9x16.mp4` 均为 6.0 s。
- 六字体探针日志包含六个预期 PostScript 名称。
- 字体文件 SHA-256 与 S3-B.1 manifest 一致。
- 证据：[s3b2_validation.json](../experiments/r3d/fonts/s3b2_validation.json)。

### 字体分发与 Git 建议

- 六个 OTF 合计 **60,860,580 bytes（约 58.04 MiB）**；连同 LICENSE/manifest/README 约 58.04 MiB。
- 普通 Git 足以承载当前字体集；**不需要为当前 6 个 OTF 引入 Git LFS**。
- 不把 119 MB 的 CN 源压缩包纳入 Git；压缩包仅保留在忽略的 `logs/s3b_download/`。
- 建议将 6 个 OTF、2 份 LICENSE、`font_manifest.json` 和 `README.md` 随项目分发/纳入 Git；OFL 1.1 允许随软件/项目分发，但必须保留版权和许可证文本。
- 如果未来字体资产超过约 200–300 MiB，或远程仓库有二进制大小限制，再评估 LFS；本阶段没有初始化 LFS、没有修改 `.gitattributes`。
- 当前未提交、未暂存；字体是否最终纳入 Git 仍待人工决定。

### 状态表（S3-B.2）

| 项 | 状态 | 说明 |
|---|---|---|
| 字体配置入口 | `PASS_VERIFIED` | `config/fonts.yaml` + `drama_studio.fonts` |
| 六字体 SHA-256 校验 | `PASS_VERIFIED` | 3 项配置测试 |
| 字幕正式接入 | `PASS_VERIFIED` | 合成夹具，`fontselect` 匹配 |
| 标题/诗词/现代解说正式接入 | `PARTIAL` | 配置与预览已做，`r3_build.py` 尚未渲染这些角色 |
| 无静默 fallback | `PASS_VERIFIED` | `fontselect` 断言 + 缺失/哈希失败测试 |
| 五组竖屏预览 | `PASS_VERIFIED` | 1080×1920 + 六字体探针 |
| 六 OTF 实际选择 | `PASS_VERIFIED` | `S3B2_00_all_faces.fontselect.log` |
| 历史资产保护 | `PASS_VERIFIED` | 既有哈希测试通过 |
| 普通 Git 可行性 | `PASS_STATIC` | 58.04 MiB，无需 LFS；未提交验证 |
| Git LFS | `NOT_RUN` | 未初始化、未修改配置 |
| 真机/手机播放 | `NOT_RUN` | 仅合成预览 |
| 《洛神赋》完整生产 | `NOT_RUN` | 未开始 |
