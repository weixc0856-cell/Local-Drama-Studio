# 宋氏美学与「宋韵新中式」风格依据（2026-11-06）

> 用途：为 `oriental.modern_chinese` 风格包提供可引用的美学依据。本文只做研究记录，不复制任何具体作品。
> 结论先行：宋画的关键不是「山水 + 月亮」的符号拼贴，而是 **平淡天真的气质、留白构成的虚实、边角/平远的取景、墨线主导的淡彩**。
> 2026-11-06 后续：生成媒介已改为当代建筑/景观写实，不再做水墨拟古；宋画只保留空间观与克制原则，见 `NEO_CHINESE_DIRECTION.md`。

## 1. 总纲：平淡天真

- 苏轼：「笔势峥嵘，文采绚烂，渐老渐熟，乃造平淡。实非平淡，绚烂之极也。」平淡是绚烂之后的克制，不是简陋。（[佩文斋书画谱·卷十六](https://ctext.org/wiki.pl?chapter=120573&if=gb)）
- 米芾评董源：「平淡天真多，唐无此品……峰峦出没，云雾显晦，不装巧趣，皆得天真。」（转引自 [林海钟《以画体道》](http://www.bookschina.com/5709876.htm)、[新民晚报](https://paper.xinmin.cn/html/xmzk/2023-04-10/31/31648.html)）
- 落到生成提示词：少即是多，不要装饰性边框、金色、满构图和「精巧」的小趣味。

## 2. 取景：平远为主，边角为辅

- 郭熙《林泉高致·山水训》三远：「自山下而仰山巅，谓之高远；自山前而窥山后，谓之深远；自近山而望远山，谓之平远。高远之色清明，深远之色重晦，平远之色有明有晦。」（[中国艺术报·「远法」漫谈](https://o.cflac.org.cn/whsy/mx/202112/t20211203_573750.html)）
- 同书「四可」：「可行、可望、可游、可居」，山水应让人愿意栖居其中，而不是被观看的舞台。
- 南宋马远、夏圭把全景裁成「边角之景」：山取一角、水取一涯，其余留白。《格古要论》：「或峭壁直上而不见其顶，或绝壁直下而不见其脚……此边角之景也。」（[故宫名画记·释「空白」](https://minghuaji.dpm.org.cn/pdf/web/viewer.html?file=https%3A%2F%2Fminghuaji-1259446244.cos.ap-beijing.myqcloud.com%2Farticle%2F2020%2F12%2F03%2Fb9bb472e398a46e7b3a5f3cd21840814.pdf)）
- 马远《水图》十二段专画水，绢本淡设色，以中锋勾水纹、淡墨渲染，说明「水」本身可以成为主体，不必每张都塞满山。（[故宫名画记·水图卷](https://minghuaji.dpm.org.cn/paint/detail?id=df3320e6acc646118a50505d5562a132&topicType=15)、[澎湃新闻](https://www.thepaper.cn/newsDetail_forward_10069985)）

## 3. 留白：无画处皆成妙境

- 空白同时承担天空、水面、云雾三种功能，是构图的一半，不是「没画完」。
- 小景山水（惠崇、赵令穰）「以小见大，笔简意长」，截取一角一段，四周留余纸与画外相连；折枝花鸟同样「剪头去尾，巧取一边一角」。（[故宫名画记·宋代折枝花鸟画的构图程式](https://minghuaji.dpm.org.cn/pdf/web/viewer.html?file=https%3A%2F%2Fminghuaji-1259446244.cos.ap-beijing.myqcloud.com%2Farticle%2F2020%2F12%2F03%2Faf513b9fa26a402d9d4ff19eb4cae6b3.pdf)）
- 提示词层面：留白要写成主体（"a large unpainted void reads as mist, water or sky"），否则模型会用云纹、山石把画面填满。

## 4. 笔墨与设色：墨线立形，淡彩为辅

- 宋画由唐代的重彩转向水墨与淡彩，「以素为绚」；浅绛以水墨勾皴为骨，淡赭石染山石树木，花青渲染，讲究「色不碍墨，墨不碍色」「薄中见厚」。（[西南大学《中国山水画》课程](https://courseware.eduwest.com/courseware/0616/content/0201/060001.htm)、[三联生活周刊](https://www.lifeweek.com.cn/article/32634)）
- 注意史实：成熟的「浅绛」体多见于元代（黄公望、王蒙）；宋代是淡彩倾向，不是元人浅绛。因此风格包用「pale ochre and indigo washes」而不是标榜「浅绛」。
- 材质：绢本、纸本册页，底色微暖偏灰，不能有塑料高光。

## 5. 色彩：宋瓷色系

- 汝窑天青「雨过天青云破处」：蓝而不艳、青而不翠、灰而不暗；粉青如青玉；月白介于青白之间。宋瓷整体审美是「简约」「素雅」「外枯而中膏，似淡而实美」。（[艺术与设计·藏在宋瓷中的绝美中国色](http://www.artdesign.org.cn/article/view/id/71694)、[中新网·汝瓷](https://www.chinanews.com.cn/hb/2013/05-21/4841209.shtml)）
- 抽取为验证色板（只用于客观检查，不进入提示词）：天青 `#8FA9A4`、粉青 `#A9C0B4`、月白 `#E4E8E4`、赭石 `#A9714F`、墨 `#3B3B38`、绢底 `#E6DCC6`。

## 6. 格物与四时

- 北宋理学「格物」让院体画重观察：树种、石理、水纹要可辨，不能是泛泛的「山」。
- 郭熙写四时：「春山淡冶而如笑，夏山苍翠而如滴，秋山明净而如妆，冬山惨淡而如睡。」生成时用季节语气约束整体色调，而不是只写「beautiful mountains」。

## 7. 反例（明确禁止）

金碧重彩、装饰边框与角花、对称舞台式构图、满画面细节、摄影镜头光斑、3D 渲染光泽、日式浮世绘/禅意标签、现代楼阁与游船、写实月亮环形山。宋韵靠克制，不靠符号堆叠。

## 8. 落地映射

| 美学原则 | 风格包字段 |
|---|---|
| 平淡天真 | `identity`、`positive_anchors` 第一条 |
| 平远 / 边角 | `composition`、`camera.allowed_moves`（static/tilt/dolly_in/tracking/crane） |
| 留白 | `composition` 的 void 条目、验证用 `edge_density` 上限 |
| 墨主色辅 | `medium`、`material_profile`、`positive_anchors` 的 line-first |
| 宋瓷色 | `color_profile`（仅验证用） |
| 四时 | `lighting_profile` 与分镜 `lighting` 字段 |
| 小点景 | `positive_anchors` 的 tiny architecture/figure |
