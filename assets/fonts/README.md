# 字体资产（S3-B.1 候选 / S3-B.2 正式接入）

本目录保存 Local-Drama-Studio 的第一组候选字体：

- **思源宋体 CN / Source Han Serif CN**：古典标题、诗词、篇章标题。
- **思源黑体 CN / Source Han Sans CN**：现代解说、字幕、信息文字。

当前只完成来源、许可证、字符覆盖和排版预览验证；**字体角色与排版方案仍待人工审查，不构成最终批准**。

## 官方来源

| 字体 | 官方仓库 | Release | CN 资产 |
|---|---|---|---|
| 思源宋体 CN | https://github.com/adobe-fonts/source-han-serif | `2.003R` | `14_SourceHanSerifCN.zip` |
| 思源黑体 CN | https://github.com/adobe-fonts/source-han-sans | `2.005R` | `19_SourceHanSansCN.zip` |

只下载 CN 专用包，未下载完整多语言发行包；未安装到 Windows 系统字体目录；未修改字体文件。

## 保留文件

为控制素材体积，只提取 Regular / Medium / Bold 三个字重：

```text
assets/fonts/
  font_manifest.json
  source-han-serif-cn/
    SourceHanSerifCN-Regular.otf
    SourceHanSerifCN-Medium.otf
    SourceHanSerifCN-Bold.otf
    LICENSE.txt
  source-han-sans-cn/
    SourceHanSansCN-Regular.otf
    SourceHanSansCN-Medium.otf
    SourceHanSansCN-Bold.otf
    LICENSE.txt
```

完整文件大小、SHA-256、内部名称、版本、字重和 cmap 数量见 [font_manifest.json](font_manifest.json)。提取的 OTF 与官方 CN 压缩包内对应条目逐字节一致。CN 压缩包保留在 `logs/s3b_download/`（已被 Git 忽略），未提交。

## 许可证结论

两个字体包内的 `LICENSE.txt` 均为 **SIL Open Font License 1.1**（实际文件，不是仓库介绍页）：

- 商业使用：允许，按 OFL 1.1 条款。
- 视频/软件嵌入与随项目分发：允许；需保留版权声明和许可证文本。
- 单独销售字体文件：不允许。
- Reserved Font Name：`Source`；不得在修改版中使用。
- 本阶段未修改字体文件。
- 字体授权不等同于模型、音色、图片、音乐或其他素材的授权。

## 字符覆盖

测试语料见 `experiments/r3d/fonts/corpus.txt`，覆盖《春江花月夜》、《洛神赋》候选句、现代长句、标点、数字和 ASCII。

六个实际 OTF 的 cmap 检查结果：**120 个测试字符全部存在，缺字 0**。检查使用本机已有的 fontTools，未向项目新增依赖。

## 排版预览

预览目录：`experiments/r3d/fonts/previews/`

- A：古典标题、字重对比、居中/非居中。
- B：诗词正文、浅色/深色背景、字号和行距/字间距。
- C：现代字幕、长句换行、底部安全区、描边和半透明底板。
- D：宋体标题 + 黑体字幕的分工示例。

预览清单、尺寸、SHA-256 和排版参数见 `experiments/r3d/fonts/preview_manifest.json`。渲染使用 FFmpeg + libass，`fontsdir` 指向本目录；`fontselect` 日志确认实际选中本地 OTF 文件。

## 正式构建接入

- 配置：`config/fonts.yaml`；加载/校验：`src/drama_studio/fonts.py`。
- 正式字幕入口 `scripts/r3_build.py` 使用 `Source Han Sans CN`，从项目字体复制到构建目录的 `fonts/`，通过 `fontsdir` 交给 libass，并解析 `fontselect.log` 拒绝静默 fallback。
- 标题、诗词、现代解说已配置并用于预览，但尚未进入正式构建（`preview_only`）。
- 预览与验证：`experiments/r3d/fonts/s3b2_previews/`、`experiments/r3d/fonts/s3b2_preview_manifest.json`、`experiments/r3d/fonts/s3b2_validation.json`。

## 当前状态

| 项 | 状态 |
|---|---|
| 官方来源 | `PASS_VERIFIED` |
| 许可证文件与条款 | `PASS_VERIFIED` |
| 字符覆盖 | `PASS_VERIFIED` |
| 竖屏排版预览 | `PASS_VERIFIED`（合成预览） |
| 正式字幕接入 | `PASS_VERIFIED`（S3-B.2，本地 `fontsdir` + `fontselect`） |
| 标题/诗词/现代解说接入 | `PARTIAL`（配置与预览已有，正式构建暂未渲染） |
| 字体角色/字号最终选型 | `DECISION`，待人工审查 |
| 商业使用法律结论 | `PASS_STATIC`（基于 OFL 文本，不替代法律意见） |
| 字体修改 | 未修改 |
| 系统字体安装 | 未执行 |
| Git 分发 | OTF 不进入 Git；manifest/README/LICENSE 可跟踪；用 scripts/fetch_fonts.py 重建 |

## Git 与分发建议

- 6 个 OTF 合计 **60,860,580 bytes（约 58.04 MiB）**；连同 LICENSE/manifest/README 约 58.04 MiB。
- 普通 Git 足以承载当前字体集，**当前不需要 Git LFS**；不要提交 119 MB 的 CN 源压缩包（压缩包仅在 `logs/s3b_download/`，已被忽略）。
- 6 个 OTF 不进入 Git；`font_manifest.json`、2 份 `LICENSE.txt` 与本 README 随项目分发。运行 `scripts/fetch_fonts.py` 从 Adobe 官方 Release 重建 OTF，并校验压缩包与每个文件的 SHA-256。OFL 1.1 允许随软件/项目分发，但必须保留版权和许可证文本。
- 若未来字体资产超过约 200–300 MiB，或远程仓库有二进制大小限制，再评估 LFS；本阶段没有初始化 LFS、没有修改 `.gitattributes`。
- 本阶段没有 `git add`、没有提交；字体是否最终纳入 Git 仍待人工决定。
