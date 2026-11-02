# 《春江花月夜》视觉圣经（R1）

完整规范见 `docs/R1_VISUAL_DESIGN.md`。本文件是提示词与验收时使用的速查版。

## 色板

| 名称 | 色值 | 用途 |
|---|---|---|
| 墨黑 | `#10161C` | 阴影、远山剪影 |
| 靛青 | `#1E3247` | 夜空、江水暗部 |
| 月白 | `#DCE6EA` | 月光、水面高光、雾 |
| 青绿 | `#4F6F63` | 近岸植物 |
| 雾灰 | `#8A9499` | 中景雾气 |
| 淡金 | `#C9A76A` | 晨曦、月光边缘 |
| 胭脂淡 | `#8E5B5B` | 花瓣点缀（≤5%） |

## 统一提示词后缀

```text
classical Tang-dynasty China, spring river landscape, ink-wash atmosphere blended with photoreal natural texture,
muted indigo-jade and moon-white palette, soft volumetric light, fine 35mm grain, cinematic 16:9 composition,
no modern buildings, no text, no watermark
```

## 统一负向约束

```text
modern architecture, power lines, neon, western fantasy, castle, oversaturated game CG, plastic look,
extra moon, distorted geometry, text, watermark, modern clothing, face close-up
```

## 时间与月亮

- 摄影机位于南岸，面向下游；东在左，西在右。
- KF1 初月：左侧低空；冷蓝 + 暮色淡金；薄雾。
- KF2 花林月照：左上方；冷银蓝；林间薄雾。
- KF3 孤舟远行：上方偏左；冷蓝低对比；江面平雾。
- KF4 落月晨曦：右侧低空；淡金 + 冷蓝阴影；厚晨雾。

## 空间锚点

- 近岸在画面下方，远山在上方偏右，花林在近岸左侧。
- 孤舟从中左向右远方移动，不换岸。
- 四个关键帧共享同一组远山轮廓与河湾结构。

## 禁止

- 现代建筑/电线/路灯/玻璃幕墙/水泥堤坝
- 西方城堡/哥特/日式鸟居
- 现代服饰、塑料与金属护栏
- 高饱和游戏 CG、纯橙青调色、霓虹
- 双月、文字、水印、正脸特写
