# 超现实主义 · 视觉要点（2026-11-06）

> 用途：`artistic.surrealism` 参考板的生成依据。只做风格研究，不复刻具体作品。
> 采用分支：**veristic / naturalistic surrealism（写实梦境派，达利、马格利特）**；自动主义（米罗式自由涂绘）不在本包范围。

## 1. 核心公式

用**高度写实、古典严谨的技法**描绘**逻辑崩塌的世界**。冲击力来自「细节真实 + 关系荒谬」的落差，而不是抽象乱画。

## 2. 六种可执行手法

| 手法 | 说明 | 提示词落点 |
|---|---|---|
| 异质并置 | 无关物体同处一室（雨伞与缝纫机在解剖台上） | absurd juxtaposition of unrelated objects |
| 软化/材质变换 | 坚硬物体像奶酪一样下垂，金属与玻璃仍真实 | objects melt while keeping realistic materials |
| 尺度错位 | 物体被异常放大或缩小 | drastic scale shift |
| 悬浮/反重力 | 物体无支撑地漂浮 | objects float without support |
| 变形/重复 | 形体被拉长、折叠、复制 | deform or repeat |
| 冷静写实 | 平滑笔触、精确边缘、长投影、空旷地平线 | smooth classical brushwork, long shadows |

## 3. 两个代表方向（只取方法）

- **达利**：偏执批判法，细密写实 + 软化/抽屉/拐杖等符号；亮色、强光、戏剧性透视。
- **马格利特**：冷静错位，日常物被移出语境；硬边、平光、哲学式冷幽默，几乎不解释。

本包偏 **马格利特的冷静 + 达利的材质精确**：一件不可能的事，平静地画出来。

## 4. 风格包映射

| 要素 | 字段 |
|---|---|
| 写实梦境 | `identity` / `medium` |
| 并置、软化、悬浮、尺度 | `composition` 与 `positive_anchors` |
| 长投影、空旷地平线 | `lighting` + 构图 |
| 平滑笔触、精确边缘 | `preserve` |
| 禁魔法光效、禁卡通 | `negative_constraints` |

## 5. 排除

抽象表现式自动涂绘、发光魔法、恐怖血腥、3D 渲染、拼贴式符号堆砌、可读文字/画框、人物特写。

## 6. 来源

- [Ketterer Kunst：Veristic Surrealism](https://www.kettererkunst.com/dict/veristischer-surrealismus.php)
- [Watson Institute：Surrealism Worksheet（并置/尺度/重复/变形/不可能动作）](https://www.thewatsoninstitute.org/wp-content/uploads/2020/05/Surrealism-Worksheet.pdf)
- [IPL：Elements of Surrealism](https://www.ipl.org/essay/Surrealism-The-Creation-Of-The-Surrealism-Movement-PJSCJ7HWSQG)
- [台师大论文：达利与马格利特的图像研究](https://etds.lib.ntnu.edu.tw/thesis/detail/428fd03f24a866d9c257f80e9e8c977d/)
- [百度百科：超现实主义绘画](https://baike.baidu.com/item/%E8%B6%85%E7%8E%B0%E5%AE%9E%E4%B8%BB%E4%B9%89%E7%BB%98%E7%94%BB/2340158)
