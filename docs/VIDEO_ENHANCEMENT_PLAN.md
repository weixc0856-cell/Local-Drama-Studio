# 视频画质增强层（Enhancement Layer）方案

> 状态：`DECISION` / 2026-11-07
> 最高原则：**连续性优先**。任何增强都不得为了单帧锐度牺牲整段视频的时序稳定、结构真实与艺术笔触。
> 适用范围：`projects/<id>/shots/<shot>/` 下的 Wan 帧序列与镜头 MP4；不改变 `r3_build` 的成片职责。

## 1. 结论

1. **生产默认保持 Lanczos。** 当前 8 GB A750 的已验证路径是：Wan 448×768 / 576×1024 生成运动 → `film clips` 统一时长 → `r3_build` Lanczos 放大到 1080×1920。它不增加细节，但零闪烁、零幻觉、零额外模型。
2. **学习型超分是可选增强，不是默认生产链。** 先安装外部 `realesrgan-ncnn-vulkan`，用 S01 的 6 s 干净片段做 Lanczos / Real-ESRNet / Real-ESRGAN 三组 A/B，人工看片通过后才允许进入生产。
3. **时序超分只做研究。** BasicVSR++ 等模型需要缓存全序列特征，显存与框架兼容性都不适合当前 A750 8 GB；不部署、不设为依赖。
4. **不追求 4K。** 发布目标是 1080×1920 竖屏；4× 模型输出再缩小会增加计算与中间文件，收益需实测。
5. **源素材永不覆盖。** 增强写到独立版本（`_sr.mp4` / `enhancement/<backend>/`），原始 Wan 帧和源剪辑保留。

## 2. 五段式架构

```text
01 Motion Generation   Wan I2V 448×768 / 576×1024 / 24 fps，分段生成
02 Source QC           黑帧、尾帧伪影、亮度/结构突变、段落接缝；不合格先截断或重跑
03 Video Enhancement   spatial SR（可选）→ temporal（可选）→ denoise（可选）→ resize
04 Enhanced QC         分辨率/帧数/黑帧/时序闪烁/结构一致性/人工看片
05 Final Assembly      r3_build：转场、字幕、字体、旁白、BGM/SFX、编码
```

边界：`film clips` 只做帧序列编码与时长统一；`r3_build` 只做最终合成；增强层独立、可替换、可回退。

## 3. 默认配置

```json
{
  "production": {
    "enhancement": {
      "enabled": false,
      "profile": "conservative_1080p",
      "spatial_backend": "lanczos",
      "model": "realesrnet-x4plus",
      "scale": 4,
      "tile_size": 128,
      "temporal_backend": "none",
      "denoise": false,
      "output_width": 1080,
      "output_height": 1920,
      "fallback": "explicit_manual_approval"
    }
  }
}
```

- `enabled=false`：生产保持 Lanczos。
- 学习型后端必须显式开启；缺可执行文件/权重时失败，不静默回退。
- `denoise=false`、`temporal=none` 起步：先知道模型改变了什么，再决定补偿。

## 4. 模型分级与内容策略

| 后端 | 定位 | 风险 | 当前状态 |
|---|---|---|---|
| Lanczos | 生产默认、保守缩放 | 不增加细节 | 已验证 |
| Real-ESRNet (ncnn) | 保守增强首选 | 可能过平滑/过度锐化背景 | 适配器已写，权重未安装 |
| Real-ESRGAN (ncnn) | 纹理增强 | 幻觉纹理、逐帧闪烁 | 适配器已写，权重未安装 |
| BasicVSR++ / RVRT | 时序超分研究 | 显存大、框架复杂 | 不部署 |

内容策略（后续按镜头配置，不写代码分支）：

| 内容 | 主要风险 | 优先策略 |
|---|---|---|
| 水墨山水 | 笔触被锐化破坏 | Lanczos / Real-ESRNet |
| 岩石山体 | 纹理不足 | Real-ESRNet → Real-ESRGAN A/B |
| 建筑亭台 | 轮廓变化 | 保守 SR，检查边缘 |
| 水面流水 | 帧间纹理跳变 | 时序 QC 优先，必要时不增强 |
| 云雾烟尘 | 噪声被放大 | 轻降噪 + 保守 SR |
| 人物服饰 | 面部/衣纹形变 | 人工重点审核 |

## 5. 时序闪烁：三层处理

1. **源 QC**：`wan_qc.py` 已实现尾帧伪影检测（黑像素、亮度突降、边缘突增），只保留干净前缀；`wan_chain` 记录段落接缝亮度差。
2. **轻量时域稳定**：`hqdn3d` 只作为可选滤镜，参数分 A/B/C 三组测试，不设固定全局值。
3. **时序超分**：BasicVSR++/RVRT 仅研究；需要真实样片、显存、时序质量证据后才考虑。

注意：时域降噪平滑相邻帧，不等于时域超分；前者不能替代后者。

## 6. 增强 QC 报告

每份增强产物写 `enhancement_qc.json`：

```json
{
  "shot_id": "S01",
  "backend": "realesrnet-ncnn",
  "model": "realesrnet-x4plus",
  "source": {"width": 448, "height": 768, "frames": 160, "fps": 24},
  "output": {"width": 1080, "height": 1920, "frames": 160, "fps": 24},
  "checks": {
    "frame_integrity": "PASS",
    "black_frames": "PASS",
    "temporal_flicker": "REVIEW",
    "structural_consistency": "REVIEW",
    "perceptual_quality": "PENDING_HUMAN"
  },
  "human_review": "PENDING"
}
```

自动指标只做异常筛查；最终判断必须人工在 1080×1920 实际播放尺寸看片。

## 7. GPU 调度

| 队列 | 任务 | 规则 |
|---|---|---|
| GPU-Heavy | Wan、FLUX | 一次一个，`gpu:comfy` 单飞锁 |
| GPU-Light | ncnn 超分 | 不与 Wan/FLUX 并发；也走 `gpu:comfy` 锁 |
| CPU/Media | FFmpeg、字幕、音频、QC | 可并行，按内存限制 |

顺序：Wan 全部完成 → 源 QC → 释放 GPU → ncnn 超分 → 增强 QC → 最终 r3_build。

## 8. A/B 实验协议（R1）

1. 选 S01 的干净片段（当前 4 段续接约 6.6 s，尾帧已截断）。
2. 三个版本，输入完全相同：
   - A：Lanczos（当前生产）。
   - B：Real-ESRNet x4plus（保守）。
   - C：Real-ESRGAN x4plus（纹理）。
3. 全部输出 1080×1920 / 24 fps / 同 CRF；不覆盖源素材。
4. 记录：推理耗时、峰值显存（若可读）、文件大小、细节增益、结构差异、时序闪烁代理指标。
5. 动态验收：实际尺寸播放，检查纹理闪烁、边缘跳动、镜头运动是否自然、段落接缝。
6. 通过条件：至少一个学习型后端在**整段播放**中优于 Lanczos，且无明显时序问题；否则保持 Lanczos。

## 9. 实施路线

| 轮次 | 内容 | 状态 |
|---|---|---|
| R1 | 基准与 A/B（Lanczos / Real-ESRNet / Real-ESRGAN） | A 组 Lanczos 完成（2.12 s，1080×1920/6.0 s）；B/C `NOT_RUN`（未安装 ncnn exe/权重） |
| R2 | 统一 Enhancement Backend、权重注册、Manifest、失败隔离、GPU 锁 | 配置与 `film.enhance` 任务已落地；权重注册/断点恢复待做 |
| R3 | 按镜头内容自适应策略 | 规划 |
| R4 | BasicVSR++/RVRT 研究 | 不在当前生产链 |

## 10. 参考资料

- Real-ESRGAN 是逐帧图像超分，没有时序建模；逐帧应用会产生 flicker/crawl。GAN 对抗损失会放大闪烁。
- BasicVSR++ 用时序传播与光流对齐提升一致性，但需要缓存全序列特征，显存开销大。
- Real-ESRNet 为非对抗 L1 训练，幻觉更少但偏平滑；它同样不具时序一致性。
- 2026 OTT 工程文章明确建议：单帧超分用于静帧，视频应使用时序 VSR，并增加光流残差 QC。

Sources:
- [BasicVSR++ (CVPR 2022)](https://openaccess.thecvf.com/content/CVPR2022/papers/Chan_BasicVSR_Improving_Video_Super-Resolution_With_Enhanced_Propagation_and_Alignment_CVPR_2022_paper.pdf)
- [Real-ESRGAN / BasicVSR++ OTT upscaling playbook (2026)](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/real-esrgan-basicvsr-ott-archive-upscaling)
- [Real-ESRNet model card summary](https://crafiq.ai/models/image-upscale/nightmareai-real-esrgan)
- [Investigating Tradeoffs in Real-World Video Super-Resolution (CVPR 2022)](https://openaccess.thecvf.com/content/CVPR2022/supplemental/Chan_Investigating_Tradeoffs_in_CVPR_2022_supplemental.pdf)
