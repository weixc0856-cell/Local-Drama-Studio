# 故障排查手册

> 文档状态：Phase B 排障文档（2026-11-04）
> 原则：先取证，再修复；不删除历史产物；不把失败伪装成成功。
> 相关：[USER_GUIDE.md](USER_GUIDE.md)、[PRODUCTION_PIPELINE_GUIDE.md](PRODUCTION_PIPELINE_GUIDE.md)、[PRODUCTION_CONFIG_GUIDE.md](PRODUCTION_CONFIG_GUIDE.md)

---

> **2026-11-06 运行时变更：** 图像线由 FLUX.2 Klein 切换为 FLUX.3 Klein（ADR-016）；TTS 由 CosyVoice2-0.5B 切换为 VoxCPM2（端口 50000 不变，48 kHz，CPU，无 SFT 预置音色）；视频线仍为 Wan2.2 TI2V 5B。历史报告中的 CosyVoice / FLUX.2 描述是当时的事实，不再代表当前栈。

## 0. 排障顺序（固定）

```powershell
cd 项目根目录

# 1) 环境/模型/服务总览
scripts\doctor.ps1

# 2) 端口
Get-NetTCPConnection -LocalPort 8188,8080,50000,8765 -State Listen -ErrorAction SilentlyContinue

# 3) 服务健康
curl.exe -s -m 3 http://127.0.0.1:8188/system_stats
curl.exe -s -m 3 http://127.0.0.1:8080/health
curl.exe -s -m 3 http://127.0.0.1:50000/health

# 4) 最近任务日志
Get-ChildItem logs\workspace\tasks\*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

然后按“服务 → 任务 → 产物 → 配置”顺序排查。不要一上来改配置。

---

## 1. ComfyUI 无法启动 / 8188 不通

| 现象 | 检查 | 处理 |
|---|---|---|
| `start.ps1` 报 runtime 不存在 | `runtime\ComfyUI\.venv\Scripts\python.exe` | `scripts\setup.ps1 -WithComfyUI` |
| 进程退出 | `logs\comfyui.err.log` 末尾 | 常见：torch/XPU 依赖、端口占用、模型路径 |
| 端口已监听 | `Get-NetTCPConnection -LocalPort 8188` | 不要重复启动；`start.ps1` 会直接退出 |
| 180 s 未就绪 | `logs\comfyui.err.log` | 首次加载慢可重试；检查模型/节点 |
| 8188 被其他实例占用 | `Get-Process -Id <pid>` | 不要 kill 非项目进程；`stop.ps1` 只杀 `runtime\ComfyUI` 树 |

安全停止：

```powershell
scripts\stop.ps1
```

`stop.ps1` 会沿父进程走最多 3 层，要求命令行包含 `runtime\ComfyUI`，否则拒绝。

---

## 2. XPU 不可用 / torch 问题

```powershell
runtime\ComfyUI\.venv\Scripts\python.exe -c "import torch; print(torch.__version__, torch.xpu.is_available(), torch.xpu.device_count())"
```

| 结果 | 处理 |
|---|---|
| `ModuleNotFoundError: torch` | `scripts\setup.ps1 -WithComfyUI` |
| `torch.xpu.is_available() == False` | 驱动/XPU 轮子问题；不要装 CUDA 版；查 R0 报告与驱动版本 |
| 根 `.venv` 里 import torch 成功 | 违反边界；不要在根环境装 torch |

当前已验证：torch 2.15.0+xpu / Arc A750 / 1 XPU。

---

## 3. 显存不足（OOM）

8 GB A750 是独占资源。

| 场景 | 处理 |
|---|---|
| FLUX OOM | 降低分辨率；确认没有 Wan/LLM 同时跑；重试 |
| Wan OOM | 用 73 帧/576×1024；不要 121 帧；不要同时跑 FLUX |
| 模型切换后 OOM | ComfyUI 通常自动卸载；必要时重启 ComfyUI |
| 同时跑 LLM + FLUX | LLM CPU-only 不占 VRAM，但占 ~19 GB RAM；不要启动 GPU 模式 LLM |

不要静默降分辨率后把结果当成功；记录降级。

---

## 4. FLUX 生成失败

| 现象 | 检查 | 处理 |
|---|---|---|
| `job.json status=failed` | `probe_attempt*.log`、`history.json` | 看节点错误/模型缺失 |
| 提交成功但无输出 | `history.json` 的 outputs | 检查 `SaveImage` 节点/前缀 |
| 输出下载失败 | 日志中的 `/view` | 保留 job，重试；不要手工伪造 job.json |
| 图片空/黑 | `quality.check_image` / `static_quality` | 重摇；不带入成片 |
| 参考图未生效 | `job.json.reference`、ComfyUI input 目录 | `r1_batch.stage_reference` 复制到 `runtime/ComfyUI/input` |
| 负向提示词无效 | 工作流 `ConditioningZeroOut` + CFG 1.0 | 这是设计；用正向约束，不要以为负向在控制 |

重跑：

```powershell
scripts\r1_batch.py --jobs <jobs.json> --only <job_id> --force
```

---

## 5. Wan 生成失败/质量差

| 现象 | 原因 | 处理 |
|---|---|---|
| 彩虹伪影 | 10 步 | **必须 20 步** |
| 颜色漂移 | 121 帧 | 默认 73 帧；人工看首尾 |
| 主体位移方向错 | Wan 不适合精确位移 | 改分镜/后期；不要当作叙事成功 |
| 分辨率报错 | 未按 32 整除 | 1024×576 / 576×1024 |
| 时间过长 | 36–43 min/段 | 只做英雄镜头；其余静帧+运动 |

---

## 6. CosyVoice 无法连接 / 音色不对

```powershell
scripts\cosyvoice_server.ps1 -Action status
curl.exe -s http://127.0.0.1:50000/health
```

| 现象 | 检查 | 处理 |
|---|---|---|
| 50000 未监听 | `CosyVoice-Runtime\logs\server*.log` | `scripts\cosyvoice_server.ps1 -Action start -Model sft` |
| `status=loading` | 模型加载 9–28 s | 等待；`doctor` 重试 |
| `status=error` | 日志里的 `model load failed` | 模型目录/依赖 |
| 想用中文女但没声 | 当前可能跑的是 0.5B zero-shot | 切 `-Model sft`；见下 |
| zero-shot 参考音失败 | `prompt_text` 与参考音不一致/缺失 | 逐字一致；提供 prompt |
| 两个运行时抢占 | 50000 单实例 | 先 stop 再 start 另一个 |

### 6.1 声音不对：当前是 SFT 还是 zero-shot？

PRD 默认是 **CosyVoice2-0.5B zero-shot**；SFT「中文女」仅显式可选。先看 `audio_manifest.json` 的 `tts_mode`：

| 值 | 含义 |
|---|---|
| `sft` | 预置音色；`speaker_id` 是中文女/中文男 |
| `zero_shot` | 参考音克隆；`speaker_id` 为 null，`prompt` 记录参考音 |

如果 manifest 是 `zero_shot`，说明按 PRD 默认/显式选择了克隆；如果 manifest 是 `sft`，说明任务/CLI 显式选了 SFT，或当前代码默认仍是 SFT。修复：

1. 想用 SFT：启动 `scripts\cosyvoice_server.ps1 -Action start -Model sft`，TTS 加 `--tts-mode sft`；
2. 想用 zero-shot：启动 `-Model cosyvoice2`，加 `--tts-mode zero_shot`；
3. 重新 `tts.synthesize --force`。

如果服务模型与模式不匹配，会直接报“请求 SFT/zero-shot，但 50000 当前加载的是 …”，不会静默切换。

### 6.2 zero-shot 应该用哪个模型

- zero-shot：**CosyVoice2-0.5B**（`-Model cosyvoice2`）。
- SFT：**CosyVoice-300M-SFT**（`-Model sft`）。
- 不要用 300M 做 zero-shot；会丢韵尾/音色漂移（已实测记录）。

---

## 7. 配音文件缺失 / 哈希不一致

```powershell
# 看 manifest
Get-Content <episode>\work\audio_manifest.json
# 逐行核对
.venv\Scripts\python.exe -c "import json,hashlib,pathlib; d=json.load(open(r'<manifest>',encoding='utf-8')); [print(x['index'], pathlib.Path(x['file']).exists(), hashlib.sha256(pathlib.Path(x['file']).read_bytes()).hexdigest()==x['sha256']) for x in d['lines']]"
```

| 现象 | 处理 |
|---|---|
| 文件缺失 | 重跑 `tts.synthesize`（会复用有效行） |
| 哈希不一致 | `--force` 重合成；不要手改 manifest |
| 时长与 manifest 不符 | 重新合成该行；检查采样率 |
| 整行几乎静音 | 看 `broken_silence`；重合成/改文本 |

---

## 8. 字幕异常

| 现象 | 原因 | 处理 |
|---|---|---|
| 字幕字体不对/回退 | fontselect 未命中 | 构建会失败；检查 `config/fonts.yaml` 与 OTF |
| 字幕超出音频尾 | 末行 `pause_after_ms=0` | 恢复 800 ms 尾停顿 |
| 字号过大/过小 | libass 默认 PlayRes | `r3_build` 已显式 1080×1920；不要删 |
| 长句不换行 | `subtitles.max_chars_per_line` 未消费 | 当前需手工断句或改代码 |
| 字幕与语音不同步 | timeline/manifest 不一致 | 重建 timeline；检查 `--leading-ms`/header |
| 繁体字幕但 TTS 简体 | 四层文本设计 | 正常；`display_text` 不变 |

---

## 9. FFmpeg 合成失败

| 现象 | 检查 | 处理 |
|---|---|---|
| 段素材缺失 | task log / `segments.json` | 修路径；不要伪造文件 |
| 音频比视频长 | `r3_build` 报 `total_ms < voice_end` | 延长最后镜头或缩短停顿 |
| 视频比音频短 | 脚本会自动延长最后段 | 看 manifest `total_seconds` |
| 字体检查失败 | `fontselect.log` | 修字体/角色；不要绕过 |
| 覆盖拒绝 | 已有 final | 用新 `--out` 目录；不要删历史 |
| 解码失败 | `decode_returncode`/stderr | 重建；保留失败目录 |
| 声音与历史不同 | `soundscape.enabled=true` | 这是当前音频链路；对比前先确认 |

---

## 10. 任务中断 / 工作台异常

| 现象 | 处理 |
|---|---|
| 任务 `RUNNING` 但服务重启 | `recover_stale_tasks` 会标 `FAILED`（中断） |
| 任务卡住 | 任务中心取消；会 `taskkill /T /F` |
| 日志不更新 | 看 `logs/workspace/tasks/task_*.log`；进程可能已死 |
| 任务 `FAILED` 但产物存在 | 后置校验失败（如 P1 `script.generate` 的 `ModuleNotFoundError`）；以产物+日志为准，重新跑验证 |
| 8765 不通 | `drama serve --port 8765`；端口被占用换端口 |
| DB 异常 | 备份 `projects/workspace.db`；不要随意删除；SQLite WAL |
| 任务重复运行 | 单飞锁只覆盖同 `lock_key`；不同任务仍可并行 |

---

## 11. 风格不生效 / 风格冲突

| 现象 | 原因 | 处理 |
|---|---|---|
| UI 改了风格，运动没变 | DB 风格不含 motion/aesthetic profile | 改 `config/styles.yaml`；或显式 `--style` |
| `motion.plan` 报 style_id 不存在 | `script.style_id` 是 DB 风格 id（如 `style_p1_short`） | 传 `--style ink_wash` 或 `court_green_fine_line` |
| `aesthetic.plan` 同样报错 | 同上 | 同上 |
| 同一作品镜头风格不一致 | 没有强制门；任务可覆盖 | 人工检查；Phase C 加锁 |
| 换风格后旧镜头没变 | 旧镜头的 visual_prompt 已写死 | 新期数/新生产版本，不要原地换 |

---

## 12. 静态质量门 / 运动质量门

| 现象 | 原因 | 处理 |
|---|---|---|
| `motion.plan` 报缺少静态报告 | 默认强制静态门；报告未生成 | 先跑工作台 `static.check`（或 CLI `static_quality.py`）写到 `work/static/<shot_id>/`；确需跳过时显式 `--skip-static-gate` |
| `static_quality` 返回 PENDING | 没有 `--manual` 语义清单 | 补人工 JSON；PENDING 不算通过 |
| 运动质量失败 | 刚体/时序 | 看 `motion_quality_report.json`；修层/区域/转场 |
| UI 不能选 motion manifest | 表单只有 `manifest` | 用 API/CLI |

---

## 13. 历史证据路径缺失

现象：文档引用的 `experiments/r1/...`、`r2/...`、`r3a/...`、`r3b/...`、`s2a/...` 不存在。

处理：

- 不要伪造路径/文件；
- 以仍存在的 `assets/keyframes`、`assets/vertical`、`logs/r0`、`projects/**/build-*`、`docs/R*_TEST_REPORT.md` 为准；
- 需要复跑时重新生成，并在报告中记录新路径；
- 81.373 s 工笔仍可用 `projects/proj_chunjiang_gongbi/.../work` 重建。

---

## 14. 快速恢复清单

```powershell
# 1) 诊断
scripts\doctor.ps1

# 2) 重启服务
scripts\stop.ps1
scripts\start.ps1
scripts\llm_server.ps1 -Action stop
scripts\llm_server.ps1 -Action start
scripts\cosyvoice_server.ps1 -Action stop
scripts\cosyvoice_server.ps1 -Action start -Model sft

# 3) 重跑失败任务
#    工作台任务中心 → 重新执行（新任务）
#    或 CLI 带 --force / 新输出目录

# 4) 重建合成（新目录）
#    期数 → 合成重建（新目录）

# 5) 质量
.venv\Scripts\python.exe -m drama_studio.quality --manifest <build_manifest.json> --root .
```

**不要**：删除历史 `renders/build-*`、删除 `experiments`、清空 `workspace.db`、覆盖 `final_9x16.mp4`、kill 非项目进程。
