# Z-Image Turbo 视觉风格图谱与 Prompt 写法体系 (Visual Style Atlas)

> 面向生产的本地 6B 单流 DiT 风格实验库与提示词体系。本文件由 `scripts/run_z_image_style_atlas.py export-atlas` 从 `config/z_image_styles.yaml` 自动生成，请勿手工编辑。

> 实测结论（评分、失败模式、已验证修法、吞吐基线）见 [Z_IMAGE_STYLE_FINDINGS.md](Z_IMAGE_STYLE_FINDINGS.md)。

## 一、Z-Image Turbo 官方提示词工程规范

1. **自然语言长句描述**：细节充实的完整段落，禁止 `masterpiece, 8k, best quality` 标签堆叠。
2. **零负面提示词 (Zero Negative Prompt)**：少步蒸馏 DiT（8 次前向），不依赖传统 CFG；否定约束一律转成正向语言（如 `a clean empty background without graphic overlays`）。
3. **画面文字精准控制**：需要出现的文字必须用英文双引号标明（如 `"STATION"`）。
4. **7 维度结构**：Subject / Scene / Composition / Lighting / Medium & Style / Color & Texture / Constraints。
5. **一次只给一个主风格**：不要把水墨 + 3D 卡通 + 写实摄影 + 赛博朋克堆在同一 Prompt。

## 二、38 套视觉风格完整配方库

### A. 写实摄影与人物肖像 (Portrait & Photography) · 优先级 HIGHEST

#### 01｜高级时尚人像 (Editorial Fashion) · `editorial_fashion`

- **适用场景**: 社交媒体、人物封面、高端时尚广告、品牌写真
- **7 维度特征表**:
  - **Subject**: a young East Asian woman with natural facial features and relaxed confident expression, wearing a minimalist black tailored outfit
  - **Scene**: beside a large floor-to-ceiling window in a contemporary minimalist architectural interior
  - **Composition**: medium close-up composition, elegant spatial balance
  - **Lighting**: soft directional daylight illuminating the face, creating gentle natural shadows
  - **Medium & Style**: medium-format fashion photography, refined magazine editorial aesthetic
  - **Color & Texture**: elegant neutral color palette, realistic skin texture, subtle makeup
  - **Constraints**: authentic unretouched skin pores, no oversaturation, clean uncluttered frame

```text
A sophisticated editorial fashion portrait of a young East Asian woman with natural facial features, wearing a minimalist black tailored outfit. She stands beside a large window in a contemporary architectural interior. Soft directional daylight illuminates her face, creating gentle shadows. Medium close-up composition, relaxed confident expression, subtle makeup, realistic skin texture, elegant neutral color palette, medium-format fashion photography, refined magazine editorial aesthetic.
```

#### 02｜街头纪实摄影 (Street Documentary) · `street_documentary`

- **适用场景**: 纪实短片、人文摄影、真实生活感视觉素材
- **7 维度特征表**:
  - **Subject**: a young Asian woman in everyday casual clothes carrying a canvas bag, candid unposed expression
  - **Scene**: crowded urban pedestrian street after rainfall, shop lights reflecting on wet asphalt
  - **Composition**: slightly imperfect candid street framing, dynamic depth of field with walking pedestrians
  - **Lighting**: direct ambient street light, natural daylight with warm store illumination
  - **Medium & Style**: unposed street documentary photography, authentic photojournalism
  - **Color & Texture**: subtle 35mm film grain, authentic street color rendition, realistic wet pavement texture
  - **Constraints**: authentic motion blur in background pedestrians, unposed natural posture, no synthetic plastic look

```text
A candid documentary photograph of a young Asian woman walking through a crowded urban street after rainfall. She wears ordinary everyday clothes and carries a canvas bag. Reflections of shop lights appear on the wet pavement, pedestrians move naturally in the background. Slightly imperfect framing, direct available light, authentic facial expressions, subtle 35mm film grain, natural colors, unposed street photography.
```

#### 03｜黑白电影人像 (Black and White Noir) · `black_white_noir`

- **适用场景**: 悬疑影视、戏剧人物特写、艺术黑白画册
- **7 维度特征表**:
  - **Subject**: a middle-aged man with weathered facial features, restrained reflective expression
  - **Scene**: dimly lit atmospheric interior, subtle background shadows
  - **Composition**: intimate close-up framing, classic chiaroscuro portrait composition
  - **Lighting**: strong directional side lighting carving facial contours, other side falling into deep shadow
  - **Medium & Style**: classic black and white cinema portrait, timeless fine-art portrait photography
  - **Color & Texture**: monochromatic silver gelatin print tones, rich grayscale gradation, subtle organic silver grain
  - **Constraints**: deep rich blacks without clipping, high tonal contrast, authentic skin texture

```text
A dramatic black and white portrait of a middle-aged man standing in a dimly lit interior. Strong side lighting reveals the texture of his face while the other side falls into deep shadow. Classic chiaroscuro, subtle silver grain, rich tonal gradation, intimate close-up framing, restrained expression, timeless fine-art portrait photography.
```

#### 04｜复古胶片 (Vintage Film) · `vintage_film`

- **适用场景**: 怀旧短片、日常写真、温暖生活感视觉
- **7 维度特征表**:
  - **Subject**: a relaxed young woman with subtle natural smile sitting comfortably
  - **Scene**: beside a sunlit cafe window with wooden frame and rustic elements
  - **Composition**: relaxed eye-level medium shot, authentic everyday framing
  - **Lighting**: warm natural sunlight pouring through glass, gentle highlight halation
  - **Medium & Style**: Kodak Portra 400 inspired analog 35mm film photography
  - **Color & Texture**: muted greens and warm beige tones, slightly faded pastel palette, visible fine film grain
  - **Constraints**: natural chromatic halation on bright highlights, organic analog depth, authentic paper print texture

```text
A relaxed portrait of a young woman sitting beside a sunlit cafe window. Warm natural sunlight, slightly faded colors, gentle highlight halation, soft shadows, visible fine film grain, muted greens and warm beige tones, Kodak Portra 400 inspired analog film aesthetic, authentic everyday moment, 35mm film photography.
```

### B. 影视与电影概念艺术 (Cinematic & Film Aesthetics) · 优先级 HIGHEST

#### 05｜科幻电影剧照 (Sci-Fi Cinematic Still) · `scifi_cinematic`

- **适用场景**: 科幻影视、太空探索概念、未来主题短剧
- **7 维度特征表**:
  - **Subject**: a lone astronaut in detailed functional spacesuit standing resolutely
  - **Scene**: inside a vast abandoned orbital space station with massive observation windows revealing a distant blue planet
  - **Composition**: wide anamorphic cinematic establishing shot, strong foreground middle-ground separation
  - **Lighting**: narrow beams of cold volumetric light piercing through dust particles in microgravity
  - **Medium & Style**: atmospheric science fiction cinematography, 2.39:1 widescreen movie still
  - **Color & Texture**: restrained blue-gray color grading with subtle warm amber indicator accents, realistic industrial metal finishes
  - **Constraints**: realistic physical production design, volumetric atmospheric haze, no cartoon elements

```text
A cinematic film still showing a lone astronaut standing inside a vast abandoned orbital station. Large observation windows reveal a distant blue planet. Dust particles float through narrow beams of cold light. Strong foreground, middle-ground and background separation, wide anamorphic composition, restrained blue-gray color grading, realistic production design, atmospheric science fiction cinematography.
```

#### 06｜东方武侠电影 (Wuxia Cinema) · `wuxia_cinema`

- **适用场景**: 武侠古装短剧、历史动作影视、国风分镜
- **7 维度特征表**:
  - **Subject**: a lone swordswoman wearing flowing ivory traditional robes, wind moving her loose hair
  - **Scene**: on an ancient weathered wooden bridge suspended above a mist-covered mountain canyon, distant peaks shrouded in fog
  - **Composition**: wide cinematic establishing shot, sweeping atmospheric landscape composition
  - **Lighting**: diffused natural overcast mountain daylight, soft shadows filtered through dense mist
  - **Medium & Style**: cinematic historical wuxia film still, classic martial arts cinema aesthetic
  - **Color & Texture**: restrained earthy color palette, ivory, charcoal, muted forest green, cinematic 35mm film grain
  - **Constraints**: authentic historical garment layers and fabric weave, realistic atmospheric fog, no neon fantasy glow

```text
A cinematic historical wuxia film still. A lone swordswoman wearing flowing ivory robes stands on a wooden bridge above a mist-covered mountain valley. Ancient Chinese architecture is barely visible through the fog. Wind moves the fabric and loose hair. Wide establishing shot, atmospheric natural light, restrained earthy colors, elegant composition, realistic historical costume design, cinematic film grain.
```

#### 07｜黑色电影 (Neo-Noir) · `neo_noir`

- **适用场景**: 悬疑犯罪短片、城市夜景、戏剧性冲突场景
- **7 维度特征表**:
  - **Subject**: a solitary trench-coated figure walking with purposeful steps
  - **Scene**: narrow wet city alleyway at midnight, distant silhouettes disappearing into ambient fog
  - **Composition**: low-angle perspective, dynamic depth with deep shadows and reflective puddles
  - **Lighting**: low-key chiaroscuro lighting, vibrant red and cyan neon signs casting sharp reflections on wet asphalt
  - **Medium & Style**: neo-noir cinematic still, 35mm anamorphic lens with subtle horizontal streak character
  - **Color & Texture**: high contrast deep velvety blacks, saturated neon magenta and cyan highlights, wet asphalt sheen
  - **Constraints**: moody atmospheric mist, controlled highlight spill, cinematic urban thriller production quality

```text
A neo-noir cinematic still of a solitary figure walking through a narrow city alley at midnight. Rain falls under red and blue neon signs. Wet asphalt reflects the lights, distant silhouettes disappear into fog. Low-key lighting, deep shadows, strong color contrast, 35mm anamorphic lens character, carefully controlled highlights, atmospheric urban thriller cinematography.
```

#### 08｜史诗奇幻 (Epic Fantasy) · `epic_fantasy`

- **适用场景**: 奇幻世界观、史诗级故事场景、大场景概念设定
- **7 维度特征表**:
  - **Subject**: a small cloaked traveler standing on a rugged cliff ledge overlooking a monumental realm
  - **Scene**: an enormous ancient stone fortress city carved into precipitous cliffs with snow-capped peaks in the background
  - **Composition**: epic wide-angle panoramic vista emphasizing monumental architectural scale
  - **Lighting**: volumetric golden hour sunlight streaming across mountain ridges, thousands of warm glowing windows
  - **Medium & Style**: epic high-fantasy production cinematic still, matte painting realism
  - **Color & Texture**: warm sunset gold, deep slate stone, pure mountain snow, atmospheric aerial haze
  - **Constraints**: intricate stonework and bridges, layered atmospheric perspective, monumental scale contrast

```text
An epic fantasy film still showing an enormous ancient stone city built along the edge of a mountain. Thousands of warm lights illuminate the buildings as the sun sets behind distant snow-covered peaks. A small traveler stands in the foreground, emphasizing the monumental scale. Atmospheric perspective, volumetric golden light, detailed architectural design, cinematic wide shot, realistic fantasy production art.
```

### C. 中国传统美学与国风 (Traditional Chinese & Oriental Aesthetics) · 优先级 HIGHEST

#### 09｜水墨山水 (Ink Wash Painting) · `chinese_ink_wash`

- **适用场景**: 国风纪录片、文化典籍分镜、高雅艺术视觉
- **7 维度特征表**:
  - **Subject**: towering craggy mountains emerging through layers of swirling mist, a tiny wooden fishing boat on calm waters
  - **Scene**: vast river canyon surrounded by precipitous peaks and distant pines
  - **Composition**: classical Chinese landscape composition, dramatic balance of dense brushwork and expansive negative space
  - **Lighting**: diffused ethereal light natural to traditional ink wash art
  - **Medium & Style**: traditional Chinese ink wash painting, expressive sumi-e brushwork, wet ink diffusion and dry brush dry-rub texture
  - **Color & Texture**: monochromatic black and charcoal tones, handmade raw xuan paper texture with organic fiber flecks
  - **Constraints**: strict traditional brush aesthetics, authentic ink bleed, no synthetic Western shading, no modern photographic elements

```text
A traditional Chinese ink wash landscape painting of towering mountains emerging through layers of mist. A small wooden boat travels along a quiet river, with a tiny fisherman beneath distant cliffs. Expressive brushwork, varying ink density, wet ink diffusion, dry brush textures, delicate mountain contours, extensive negative space, handmade xuan paper texture, monochromatic black and gray palette.
```

#### 10｜工笔花鸟 (Gongbi Painting) · `gongbi_flower_bird`

- **适用场景**: 传统文化插画、东方美学包装、精品国风道具视觉
- **7 维度特征表**:
  - **Subject**: two delicate songbirds perched gracefully among blooming peony branches and budding flowers
  - **Scene**: peaceful garden setting captured in meticulous classical stillness
  - **Composition**: elegant asymmetrical botanical composition, balanced empty space
  - **Lighting**: uniform soft diffused daylight illuminating every contour without harsh shadows
  - **Medium & Style**: meticulous traditional Chinese gongbi painting, delicate iron-wire and gossamer brush contours
  - **Color & Texture**: layered natural mineral pigments, cinnabar, malachite green, azurite, fine antique silk canvas grain
  - **Constraints**: precision linework outlining every petal and feather, translucent mineral pigment washes, no rough ink splashes

```text
A meticulous traditional Chinese gongbi painting of two small birds perched among blooming peony branches. Every feather, leaf vein and flower petal is carefully outlined with delicate fine brushwork. Layered mineral pigments, subtle color transitions, elegant botanical composition, fine silk texture, precise decorative details, restrained traditional Chinese painting aesthetics.
```

#### 11｜宋代青绿山水 (Song Dynasty Landscape) · `song_landscape`

- **适用场景**: 院体山水、文化巨制视觉、高规格历史背景
- **7 维度特征表**:
  - **Subject**: majestic layered mountain ranges, winding rivers, ancient pavilions, and winding pine bridges
  - **Scene**: monumental panorama inspired by Northern and Southern Song court landscape masters
  - **Composition**: traditional court three-level perspective, deep atmospheric space, balanced empty river waters
  - **Lighting**: clear morning mountain light, gentle luminous clarity
  - **Medium & Style**: Song dynasty blue-green landscape painting, court academy style
  - **Color & Texture**: rich mineral azurite blue and malachite green pigments accented with gold dust, delicate contour lines on aged silk
  - **Constraints**: exquisite architectural precision in pavilions and brackets, harmonious mineral tones, antique silk substrate

```text
A refined Chinese Song dynasty inspired landscape painting. Majestic layered mountains rise above winding rivers and quiet valleys. Tiny traditional pavilions and pine trees are carefully placed within the vast landscape. Mineral blue and green pigments, delicate contour lines, intricate architectural details, balanced empty space, elegant classical composition, silk painting texture.
```

#### 12｜宋式美学 (Song-inspired Aesthetics) · `song_aesthetics`

- **适用场景**: 东方极简生活方式、茶道香道视觉、高定国风器物展示
- **7 维度特征表**:
  - **Subject**: a simple white Ru-ware style porcelain vase, a single plum blossom branch, an antique silk-bound book, celadon teacup
  - **Scene**: serene scholarly study with dark weathered timber table and clean paper screen
  - **Composition**: minimalist still-life composition, generous negative space, geometric tranquility
  - **Lighting**: gentle directional morning window light casting soft elongated shadows
  - **Medium & Style**: Song dynasty minimalist aesthetic still life, restrained classical styling
  - **Color & Texture**: celadon glaze, eggshell white, matte dark wood grain, restrained muted earth tones
  - **Constraints**: profound restraint, unpretentious elegance, tactile porcelain crazing, no modern clutter

```text
An elegant still life inspired by the aesthetics of the Chinese Song dynasty. A simple white porcelain vase, a single flowering branch, an antique book and a small celadon ceramic bowl rest on a dark wooden table. Soft natural window light, restrained neutral colors, balanced negative space, subtle material textures, quiet scholarly atmosphere, minimalist classical Chinese interior styling.
```

#### 13｜敦煌壁画 (Dunhuang Mural) · `dunhuang_mural`

- **适用场景**: 丝路历史短剧、华丽神话场景、壁画艺术复现
- **7 维度特征表**:
  - **Subject**: a celestial flying apsara (feitian) gliding gracefully among undulating ribbons, lotus blossoms, and stylized clouds
  - **Scene**: celestial grotto vault with ornamental geometric borders
  - **Composition**: rhythmic flowing spiral composition, dynamic classical dance posture
  - **Lighting**: warm ambient subterranean cave lighting illuminating ancient pigment surfaces
  - **Medium & Style**: ancient Dunhuang Mogao Grottoes fresco mural painting, historical silk road sacred art
  - **Color & Texture**: weathered mineral pigments, rich vermilion, copper green, malachite, gold leaf foil, textured weathered plaster cracks
  - **Constraints**: authentic plaster grain and craquelure, historical Buddhist art proportions, aged mineral oxidation

```text
A decorative illustration inspired by ancient Dunhuang mural painting. A celestial apsara floats gracefully among flowing ribbons and stylized clouds. Rich mineral pigments, muted vermilion, turquoise, ochre and golden accents, rhythmic flowing lines, intricate ornamental patterns, aged plaster texture, historical mural composition.
```

#### 14｜中国传统木版年画 (Traditional Chinese Woodblock Print) · `woodblock_new_year`

- **适用场景**: 节庆民俗短剧、民间传奇故事、传统版画风格化展示
- **7 维度特征表**:
  - **Subject**: joyous folk celebration in a festive courtyard, playful children, symbolic carp, and hanging decorative lanterns
  - **Scene**: vibrant traditional northern Chinese courtyard under auspicious skies
  - **Composition**: bold planar composition, iconic folk heraldic layout
  - **Lighting**: flat graphic illumination characteristic of relief printing
  - **Medium & Style**: traditional Chinese folk woodblock relief print (nianhua), hand-carved woodcut aesthetic
  - **Color & Texture**: vivid festive scarlet red, golden ochre, jade green, deep soot black ink, handmade mulberry paper grain
  - **Constraints**: bold chiselled contour outlines, intentional minor block alignment shifts, unadorned folk graphic vitality

```text
A traditional Chinese folk woodblock print depicting a lively festive courtyard with children, flowers and decorative lanterns. Bold carved outlines, simplified symbolic forms, vivid red, warm yellow, dark green and black ink, flat color areas, visible handmade paper fibers, traditional folk printmaking texture.
```

### D. 动漫与动画电影 (Anime & Animation Art) · 优先级 HIGHEST

#### 15｜日系动画电影背景美术 (Luminous Anime Scenery) · `shinkai_scenery`

- **适用场景**: 青春动画、治愈系风景短视频、唯美壁纸级画面
- **7 维度特征表**:
  - **Subject**: a quiet coastal town stretching along sea shoreline, telephone wires crisscrossing foreground
  - **Scene**: seaside railway crossing and lush hillside houses under towering volumetric summer cumulonimbus clouds
  - **Composition**: wide cinematic landscape panorama, pristine environmental perspective
  - **Lighting**: dazzling natural summer sunlight, glistening water reflections, cinematic chromatic lens bloom
  - **Medium & Style**: hand-painted Japanese animated film background art, Makoto Shinkai inspired scenery
  - **Color & Texture**: luminous cerulean sky, emerald ocean, crisp clean gouache washes, vibrant hyper-clear palette
  - **Constraints**: crystalline environmental clarity, detailed painted cloud volumes, no murky flat colors

```text
A beautifully hand-painted Japanese animated film background. A quiet coastal town stretches along the shoreline beneath enormous summer clouds. Sunlight reflects on the blue ocean, telephone wires cross the foreground, and distant houses are surrounded by lush trees. Rich atmospheric perspective, expressive painted clouds, luminous natural colors, delicate environmental details, cinematic wide composition.
```

#### 16｜手绘奇幻动画 (Fantasy Hand-painted Animation) · `ghibli_fantasy`

- **适用场景**: 奇幻童话短片、温暖森林探索、生态人文动画
- **7 维度特征表**:
  - **Subject**: a young traveler walking through an enchanted primeval woodland with mossy stone path
  - **Scene**: ancient towering trees with colossal roots, tiny gentle glowing forest spirits floating in air
  - **Composition**: organic eye-level tracking composition, rich layered foreground leaves and deep foliage
  - **Lighting**: dappled golden sunlight filtering through leafy canopy (komorebi)
  - **Medium & Style**: traditional cel animation hand-painted background, Studio Ghibli inspired visual aesthetic
  - **Color & Texture**: lush watercolor and gouache texture, olive green, warm amber, moss teal, organic paper tooth
  - **Constraints**: warm nostalgic emotional tone, organic hand-drawn linework, peaceful natural vitality

```text
A hand-painted fantasy animation scene showing a young traveler walking through an ancient forest filled with enormous trees. Tiny glowing spirits float among moss-covered roots, soft sunlight filters through the dense canopy, and a narrow stone path leads into the distance. Delicate watercolor-like background textures, organic character design, warm natural colors, expressive environmental storytelling, traditional animation aesthetic.
```

#### 17｜现代日系动画电影 (Modern Anime) · `modern_anime`

- **适用场景**: 剧情向动漫短片、角色情感镜头、日系叙事分镜
- **7 维度特征表**:
  - **Subject**: a high school student with windblown hair standing contemplatively on a train station platform
  - **Scene**: suburban railway platform at dusk, distant commuter train approaching on glistening steel rails
  - **Composition**: cinematic rule-of-thirds character framing, dramatic twilight sky in backdrop
  - **Lighting**: warm golden hour backlighting creating soft rim light along character profile
  - **Medium & Style**: modern theatrical Japanese anime feature still, clean vector lines and painterly scenery
  - **Color & Texture**: crisp cel shading, gradient sunset orange and violet sky, fine line art contours
  - **Constraints**: expressive emotional character posture, sharp precise lines, detailed painted scenery without 3D stiffness

```text
A cinematic Japanese anime scene featuring a high school student standing on a railway platform at sunset. Her hair moves gently in the evening breeze. A distant train approaches through warm atmospheric light. Precise clean line art, carefully layered cel shading, detailed painted background, expressive character acting, dramatic sky, rich yet natural color palette, cinematic framing.
```

#### 18｜3D 家庭动画 (Stylized 3D Animation) · `stylized_3d_animation`

- **适用场景**: 3D 动画电影、儿童家庭向短片、IP 角色概念
- **7 维度特征表**:
  - **Subject**: a charming stylized little fox character wearing a hand-knitted blue wool scarf, curious large eyes
  - **Scene**: sun-dappled colorful forest clearing with oversized mushrooms and wildflowers
  - **Composition**: appealing character portrait with soft shallow depth of field
  - **Lighting**: warm cinematic global illumination, soft bounce lighting, subsurface scattering on ears and fur
  - **Medium & Style**: polished 3D feature animation rendering, Pixar/Disney inspired character appeal
  - **Color & Texture**: tactile knitted yarn texture, individual soft fur grooming, vibrant saturated whimsical palette
  - **Constraints**: rounded expressive proportions, family-friendly aesthetic, physically plausible material shaders

```text
A charming stylized 3D animated character, a curious little fox wearing a blue knitted scarf, standing in a colorful forest clearing. Expressive large eyes, appealing rounded proportions, soft sculpted shapes, detailed fur, warm global illumination, carefully designed materials, polished feature animation rendering, vibrant cinematic color palette, family-friendly character design.
```

### E. 商业广告与产品摄影 (Commercial Advertising & Product Photography) · 优先级 HIGH

#### 19｜奢侈品广告 (Luxury Product Advertising) · `luxury_product`

- **适用场景**: 高端香水、珠宝首饰、顶级奢侈品牌商业海报
- **7 维度特征表**:
  - **Subject**: a premium luxury perfume bottle made of heavy transparent smoked glass with geometric gold cap
  - **Scene**: polished obsidian stone pedestal inside an acoustic studio setting
  - **Composition**: centered hero product shot, pristine architectural symmetry
  - **Lighting**: narrow golden overhead spotlight sculpting glass facets and amber internal liquid
  - **Medium & Style**: high-end commercial studio still-life photography
  - **Color & Texture**: deep velvety black backdrop, refractive amber glow, polished gold mirror reflections
  - **Constraints**: clean dust-free glass surfaces, precise caustic refractions, restrained luxury elegance

```text
A premium luxury perfume bottle made of transparent smoked glass, standing on a polished dark stone pedestal. A narrow golden spotlight illuminates the bottle and reveals the liquid inside. Deep black background, controlled reflections, elegant shadow gradients, sophisticated product styling, high-end commercial studio photography, restrained luxury aesthetic.
```

#### 20｜汽车商业广告 (Automotive Advertising) · `automotive_ad`

- **适用场景**: 新能源汽车、豪华轿跑、工业工业设计品宣
- **7 维度特征表**:
  - **Subject**: a premium liquid silver performance sedan with aerodynamic body contours and illuminated LED headlights
  - **Scene**: monumental minimalist brutalist concrete pavilion with expansive floor
  - **Composition**: dynamic front three-quarter hero angle, grounded stable stance
  - **Lighting**: giant overhead diffuser softbox reflecting smooth continuous light bars across car panels
  - **Medium & Style**: high-end automotive campaign studio photography
  - **Color & Texture**: multi-layer liquid metallic silver paint, carbon fiber trim, polished industrial concrete floor
  - **Constraints**: accurate body proportions, realistic panel gaps, controlled pristine reflections, no distortion

```text
A premium silver performance sedan photographed inside a monumental minimalist architectural space. The vehicle is shown in a front three-quarter view, with realistic body proportions, precise panel gaps, detailed headlights and metallic paint reflections. Large softbox lighting, polished concrete floor, controlled highlights, sophisticated neutral color palette, luxury automotive campaign photography.
```

#### 21｜护肤品广告 (Beauty Campaign) · `beauty_skincare`

- **适用场景**: 美妆护肤、有机精油、生物科技品牌宣发
- **7 维度特征表**:
  - **Subject**: an elegant frosted glass skincare serum bottle with minimalist dropper
  - **Scene**: smooth wet ivory river stone surface surrounded by delicate dewy monstera leaf shadows
  - **Composition**: clean organic tabletop composition with gentle diagonal balance
  - **Lighting**: soft diffused morning daylight passing through leaves, dappled botanic shadows
  - **Medium & Style**: clean commercial beauty cosmetic campaign photography
  - **Color & Texture**: frosted translucent glass, micro condensation droplets, pale beige and eucalyptus green tones
  - **Constraints**: pure sterile aesthetic, natural fresh hydration feel, crystal-clear liquid dropper

```text
A premium skincare serum bottle placed on a smooth ivory stone surface. Translucent glass, delicate condensation droplets, soft botanical shadows, pale beige and muted green color palette, diffused natural daylight, refined minimalist composition, elegant cosmetic campaign photography.
```

#### 22｜美食广告 (Food Photography) · `food_photography`

- **适用场景**: 餐饮品牌、精品甜点、食谱杂志封面与分镜
- **7 维度特征表**:
  - **Subject**: an exquisite multi-layered matcha opera dessert dusted with fine ceremonial green tea powder
  - **Scene**: rustic artisanal ceramic plate set upon a dark tactile slate tabletop
  - **Composition**: intimate 45-degree angled macro close-up with shallow depth of field
  - **Lighting**: directional soft window daylight from side, gentle organic rim lighting
  - **Medium & Style**: premium editorial food photography, culinary magazine aesthetic
  - **Color & Texture**: vibrant jade matcha green, rich dark chocolate ganache layers, tactile powder dusting
  - **Constraints**: mouth-watering freshness, sharp focus on front crumb texture, natural appetizing styling

```text
An elegant matcha dessert served on a handmade ceramic plate. Fine green tea powder rests on the surface, revealing delicate textures and layers. Soft directional window light, natural shadows, carefully arranged ingredients, shallow depth of field, premium editorial food photography, fresh restrained color palette.
```

### F. 平面设计与编辑插画 (Graphic Design & Editorial Illustration) · 优先级 HIGH

#### 23｜瑞士国际主义平面设计 (Swiss Style) · `swiss_style`

- **适用场景**: 现代展览海报、设计杂志、前沿品牌视觉系统
- **7 维度特征表**:
  - **Subject**: minimalist typographic poster featuring bold geometric shapes and structured abstract forms
  - **Scene**: clean white studio presentation backdrop
  - **Composition**: strict modular grid alignment, generous intentional white space, strong visual hierarchy
  - **Lighting**: uniform flat graphic lighting
  - **Medium & Style**: Swiss international typographic style poster, modernist graphic design
  - **Color & Texture**: stark black, vivid international safety orange, crisp alpine white, clean screen-printed ink finish
  - **Constraints**: rigid alignment discipline, no superfluous ornamentation, pure modernist clarity

```text
A minimalist Swiss international typographic style poster. A strict modular grid, strong geometric alignment, generous white space, bold sans-serif typography, black and warm orange graphic elements, a single abstract geometric focal point, clean editorial hierarchy, precise modernist graphic design.
```

#### 24｜杂志编辑插画 (Editorial Illustration) · `editorial_illustration`

- **适用场景**: 深度文章配图、科技哲学专栏、观念视觉概念
- **7 维度特征表**:
  - **Subject**: a stylized human hand assembling vibrant geometric paper fragments into a glowing conceptual brain
  - **Scene**: minimalist conceptual studio space
  - **Composition**: thoughtful centered metaphorical composition with strong silhouette
  - **Lighting**: gentle dimensional studio lighting casting soft shadows behind paper layers
  - **Medium & Style**: contemporary conceptual editorial illustration, layered paper cutout collage aesthetic
  - **Color & Texture**: tactile rag paper textures, curated palette of warm ochre, ivory, charcoal, and cornflower blue
  - **Constraints**: intelligent visual metaphor, tactile cut-paper edges, sophisticated intellectual narrative

```text
A conceptual editorial illustration about artificial intelligence and human creativity. A human hand carefully assembles colorful geometric paper fragments into a luminous mechanical brain. Sophisticated visual metaphor, layered paper collage, tactile textures, limited palette of orange, cream, charcoal and muted blue, clean composition, contemporary magazine illustration.
```

#### 25｜波普艺术 (Pop Art) · `pop_art`

- **适用场景**: 潮流短视频封面、年轻潮牌视觉、波普复古插画
- **7 维度特征表**:
  - **Subject**: an iconic glamorous woman wearing oversized geometric sunglasses with vibrant reflections
  - **Scene**: dynamic two-tone pop pattern backdrop
  - **Composition**: high-impact graphic portrait filling the frame
  - **Lighting**: flat graphic comic book illumination with intense graphic contrast
  - **Medium & Style**: 1960s pop art screenprint illustration, Roy Lichtenstein and Andy Warhol aesthetic
  - **Color & Texture**: primary color palette of cadmium red, sunny yellow, cobalt blue, coarse Ben-Day halftone dot texture
  - **Constraints**: bold heavy black inked outlines, screen-printing ink registration offset, vintage comic book vitality

```text
A bold pop art illustration of a woman wearing oversized sunglasses. Strong black outlines, flat primary colors, exaggerated graphic shapes, coarse halftone dot patterns, screen printing texture, high contrast composition, vintage comic book visual language.
```

### G. 奇幻、超现实与实验艺术 (Fantasy, Surreal & Experimental Art) · 优先级 MEDIUM_HIGH

#### 26｜超现实主义 (Surrealism) · `surrealism`

- **适用场景**: 哲学概念片、视觉实验短剧、梦境隐喻场景
- **7 维度特征表**:
  - **Subject**: a monumental classical stone staircase rising directly out of a perfectly mirror-flat calm ocean into pastel sky
  - **Scene**: boundless dreamscape with levitating stone architectural fragments and distant quiet clouds
  - **Composition**: enigmatic centered composition exploring infinite metaphysical space
  - **Lighting**: serene timeless atmospheric light with gentle diffused shadows
  - **Medium & Style**: contemporary fine-art surrealism, Rene Magritte and Salvador Dali inspired dream architecture
  - **Color & Texture**: soft muted pastel tones, pale cerulean ocean, warm sandstone, mother-of-pearl clouds
  - **Constraints**: hyper-realistic textures combined with impossible physics, quiet contemplation, no chaotic horror

```text
A surreal landscape where a monumental staircase rises from a calm ocean and disappears into a cloudy sky. Small floating architectural fragments surround the structure. Precise realistic surfaces combined with impossible spatial relationships, quiet atmospheric light, restrained pastel colors, dreamlike composition, contemporary surrealist fine art.
```

#### 27｜赛博朋克 (Cyberpunk) · `cyberpunk`

- **适用场景**: 近未来科幻短剧、霓虹反乌托邦都市、赛博机能视觉
- **7 维度特征表**:
  - **Subject**: futuristic pedestrians navigating crowded multi-level street markets under towering holographic ads
  - **Scene**: dense vertical Asian megalopolis at night, rain-slicked pavement and elevated skyway monorails
  - **Composition**: low-angle street-level perspective capturing monumental architectural density
  - **Lighting**: intense saturated neon glow in electric cyan, hot magenta, and amber piercing through urban rain haze
  - **Medium & Style**: cinematic cyberpunk concept art, high-tech dystopian worldbuilding
  - **Color & Texture**: glossy wet reflections, weathered metallic cables, dense particulate atmospheric haze
  - **Constraints**: rich ambient street details, realistic damp surfaces, authentic futuristic industrial grit

```text
A dense futuristic Asian metropolis at night, viewed from street level. Towering buildings covered in illuminated signs, elevated transport lines, rain-soaked streets and distant flying vehicles. Rich environmental detail, layered atmospheric haze, cyan and magenta lighting, cinematic science fiction concept art.
```

#### 28｜太阳朋克 (Solarpunk) · `solarpunk`

- **适用场景**: 绿色未来愿景、可持续发展生态城、乐观科幻故事
- **7 维度特征表**:
  - **Subject**: diverse citizens strolling through shaded open-air sky bridges surrounded by flourishing gardens
  - **Scene**: a harmonious future eco-city where curved white organic architecture merges with vertical forests and crystalline waterways
  - **Composition**: expansive wide-angle architectural visualization capturing community and nature
  - **Lighting**: brilliant natural sunbeams illuminating solar glass panels and lush hanging foliage
  - **Medium & Style**: optimistic solarpunk environmental concept art, bio-futurist architectural illustration
  - **Color & Texture**: warm sunlit greens, sandstone cream, sky cyan, sparkling clean water reflections
  - **Constraints**: positive utopian mood, plausible eco-technologies, vibrant biological integration, zero dystopian grime

```text
A sustainable future city where elegant architecture is integrated with lush vegetation, rooftop gardens, solar panels and clean waterways. People walk through shaded public spaces surrounded by trees. Bright natural daylight, warm green and cream palette, optimistic environmental concept art, detailed architectural visualization.
```

### H. 手工媒介与复古风格 (Traditional Mediums & Vintage Art) · 优先级 MEDIUM_HIGH

#### 29｜水彩 (Watercolor) · `watercolor`

- **适用场景**: 植物绘本、自然纪录片包装、温暖抒情插画
- **7 维度特征表**:
  - **Subject**: delicate meadow wildflowers, wild lavender, and grasses swaying gently
  - **Scene**: sun-warmed open countryside meadow
  - **Composition**: airy loose composition with natural breathing room
  - **Lighting**: soft diffused ambient morning daylight
  - **Medium & Style**: traditional botanical watercolor painting, wet-on-wet washes and spontaneous bleeding
  - **Color & Texture**: translucent mineral pigment washes, natural bloom cauliflower edges, heavy textured cold-press cotton paper grain
  - **Constraints**: organic imperfect fluid marks, visible paper tooth, clean luminous transparency

```text
A delicate watercolor illustration of wildflowers growing in a meadow. Transparent pigment washes, soft bleeding edges, visible paper texture, layered translucent colors, gentle brush marks, organic imperfections, airy composition, traditional botanical watercolor painting.
```

#### 30｜古典油画 (Classical Oil Painting) · `classical_oil`

- **适用场景**: 欧洲历史剧集、古典名画质感人像、戏剧油画分镜
- **7 维度特征表**:
  - **Subject**: a dignified elderly woman with wise expressive eyes and gently weathered hands resting on lap
  - **Scene**: seated beside an antique dark wooden window in a stone room
  - **Composition**: intimate half-length classical portrait, Rembrandt-inspired lighting triangle on cheek
  - **Lighting**: single-source warm directional window light sculpting skin volumes, deep rich umber shadows
  - **Medium & Style**: European Old Masters classical oil painting on linen canvas
  - **Color & Texture**: rich impasto texture on highlights, luminous oil glazes, warm sienna and burnt ochre tones
  - **Constraints**: expressive masterly brushstrokes, authentic aged craquelure, deep emotional humanity

```text
A classical oil painting portrait of an elderly woman seated beside a wooden window. Warm directional light illuminates her face and hands. Rich layered pigments, visible expressive brush strokes, subtle impasto texture, deep warm shadows, natural skin tones, traditional European fine art painting.
```

#### 31｜孔版印刷 (Risograph) · `risograph`

- **适用场景**: 独立出版物插图、复古音乐海报、小众文艺短剧片头
- **7 维度特征表**:
  - **Subject**: a charming small urban rooftop garden with potted cacti and a curious sleeping cat
  - **Scene**: sunlit rooftop overlooking city rooftops
  - **Composition**: stylized flat graphic composition with playful overlapping silhouettes
  - **Lighting**: flat graphic stencil lighting
  - **Medium & Style**: two-color risograph stencil print, contemporary indie zine aesthetic
  - **Color & Texture**: fluorescent orange and deep teal riso inks, coarse halftone dot grain, slight mechanical registration misalignment
  - **Constraints**: handmade screenprinting imperfections, visible uncoated paper fibers, authentic print shop charm

```text
A playful two-color risograph print depicting a small urban garden. Bold simplified shapes, slightly misregistered ink layers, visible paper fibers, coarse halftone texture, limited orange and dark teal inks, handmade printmaking imperfections, contemporary independent publishing aesthetic.
```

#### 32｜彩铅绘本 (Colored Pencil Illustration) · `colored_pencil`

- **适用场景**: 儿童绘本、温暖温情短剧片头、童年回忆故事
- **7 维度特征表**:
  - **Subject**: a curious little brown rabbit carrying a woven wicker basket filled with forest berries
  - **Scene**: winding dirt footpath through sunlit woodland with wild clover
  - **Composition**: intimate eye-level storybook narrative framing
  - **Lighting**: warm gentle morning light filtering through tree leaves
  - **Medium & Style**: traditional children's book colored pencil illustration, Beatrix Potter inspired charm
  - **Color & Texture**: delicate layered pencil hatch marks, warm earthy palette of cedar, moss, and warm cream, visible paper tooth
  - **Constraints**: soft gentle outlines, tender tactile craftsmanship, nostalgic heartwarming atmosphere

```text
A charming storybook illustration of a small rabbit carrying a basket through a woodland path. Delicate colored pencil strokes, visible paper grain, layered hand-colored shading, gentle imperfect outlines, warm earthy colors, intimate children's book illustration.
```

### T. 2026 前瞻视觉趋势 (2026 Visual Design Trends) · 优先级 HIGH

#### 33｜直闪抓拍摄影 (Direct Flash Photography) · `trend_direct_flash`

- **适用场景**: 2026 趋势街头、青年亚文化、派对日常纪实
- **7 维度特征表**:
  - **Subject**: stylish young friends laughing spontaneously during a late-night street gathering
  - **Scene**: dark urban street corner outside a vintage diner
  - **Composition**: dynamic candid snapshot, close-range framing with raw unposed energy
  - **Lighting**: harsh on-camera direct xenon flash casting hard sharp cast shadows immediately behind subjects
  - **Medium & Style**: raw direct flash snapshot photography, 1990s disposable camera aesthetics
  - **Color & Texture**: intense color pop, rich dark backgrounds, authentic color film grain and mild lens flare
  - **Constraints**: unpolished genuine spontaneity, sharp immediate shadows, anti-AI plastic perfection

```text
A raw direct flash candid photograph of young people enjoying an evening in an urban street. Harsh direct camera flash casts crisp dark shadows against the wall behind them. Authentic spontaneous expressions, unposed natural body language, deep saturated colors, authentic 35mm disposable camera grain, anti-polished snapshot aesthetic.
```

#### 34｜触感综合媒介拼贴 (Tactile Mixed Media) · `trend_tactile_mixed`

- **适用场景**: 艺术展览视觉、实验音乐海报、情绪化艺术概念
- **7 维度特征表**:
  - **Subject**: an abstract portrait blended with torn botanical engravings and textured archival papers
  - **Scene**: artist's craft cutting mat workshop
  - **Composition**: layered physical collage composition with intentional raw edges
  - **Lighting**: raking natural studio light revealing physical paper elevation and drop shadows
  - **Medium & Style**: tactile mixed-media paper collage, physical analog assemblage art
  - **Color & Texture**: torn cardboard fibers, yellowed newsprint, transparent vellum overlays, real scotch tape sheen
  - **Constraints**: genuine physical depth between layers, visible paper tears and distress, tangible handmade texture

```text
A tactile mixed-media collage blending an expressive portrait with torn vintage botanical prints, corrugated cardboard, and faded paper fragments. Raking side light casts tiny realistic shadows along torn edges. Visible adhesive textures, deckled paper borders, subdued earthy pigments, authentic physical assemblage art.
```

#### 35｜戏剧化舞台布光 (Dramatic Editorial) · `trend_dramatic_editorial`

- **适用场景**: 戏剧先锋电影海报、时尚艺术短剧、强情绪特写
- **7 维度特征表**:
  - **Subject**: an avant-garde performer in sculptural structured garments with sharp angular shoulders
  - **Scene**: minimalist dark theatrical stage with subtle atmospheric haze
  - **Composition**: high-drama heroic portrait framing, stark architectural figure presence
  - **Lighting**: sharp single spotlight beam cutting through darkness, high-contrast theatrical chiaroscuro
  - **Medium & Style**: dramatic theatrical editorial photography, high-fashion stage portraiture
  - **Color & Texture**: deep pitch black surroundings, ivory garment glow, bold crimson accent lighting
  - **Constraints**: powerful sculptural silhouette, absolute lighting control, evocative emotional tension

```text
A dramatic high-fashion editorial portrait on a minimalist stage. A sharp theatrical spotlight cuts through atmospheric haze, illuminating a striking figure in architectural garments while plunging the surroundings into deep shadow. Extreme tonal contrast, sculptured silhouettes, intense emotional presence, refined theatrical production aesthetics.
```

#### 36｜怀旧胶片漏光 (Analog Nostalgia) · `trend_analog_nostalgia`

- **适用场景**: 复古青春故事、夏日公路片、暖调回忆滤镜
- **7 维度特征表**:
  - **Subject**: a vintage convertible automobile parked on a coastal cliffside road overlooking the sea
  - **Scene**: golden sun setting over the Pacific coastline
  - **Composition**: wide cinematic nostalgic road-trip framing
  - **Lighting**: warm golden sunset rays with warm organic red-orange light leaks across the film frame edge
  - **Medium & Style**: vintage 1970s Kodachrome slide photography, authentic analog film camera
  - **Color & Texture**: warm honey amber, faded turquoise sea, chemical film dye fading, soft highlight halation
  - **Constraints**: authentic light leak streaks, subtle dust specks, nostalgic warmth without digital filters

```text
A nostalgic 1970s analog photograph of a vintage automobile parked beside a golden coastal cliff at dusk. Warm natural sunlight produces soft chemical halation and an organic red-orange light leak along the edge of the frame. Warm faded color tones, authentic film grain, gentle dust specks, emotional nostalgic atmosphere.
```

#### 37｜有机侘寂极简 (Organic Minimalism) · `trend_organic_minimalism`

- **适用场景**: 极简空间生活方式、自然侘寂美学、禅宗短剧
- **7 维度特征表**:
  - **Subject**: a single handmade raw unglazed ceramic tea bowl with subtle organic asymmetry
  - **Scene**: smooth lime-washed plaster niche overlooking a bamboo courtyard
  - **Composition**: quiet balanced wabi-sabi composition, generous breathing empty space
  - **Lighting**: soft diffused daylight entering through a linen curtain, delicate continuous tonal gradients
  - **Medium & Style**: organic minimalist architectural photography, wabi-sabi still life
  - **Color & Texture**: warm oat beige, tactile lime plaster texture, coarse terracotta clay, unvarnished natural wood
  - **Constraints**: profound tranquility, appreciation of natural imperfections, tactile material authenticity

```text
An organic minimalist wabi-sabi still life. A handcrafted unglazed ceramic vessel rests on a textured lime-plaster surface near a softly lit window. Subtle natural daylight, warm oat and limestone tones, generous negative space, imperfect organic curves, tactile physical textures, quiet contemplative atmosphere.
```

#### 38｜超现实商业视觉隐喻 (Surreal Visual Metaphor) · `trend_surreal_metaphor`

- **适用场景**: 创意广告大奖视觉、科技概念片、概念营销视觉
- **7 维度特征表**:
  - **Subject**: a sleek glass hourglass wherein golden sand cascades downward, transforming into a blooming miniature pine forest
  - **Scene**: pristine reflective horizon under infinite gradient twilight
  - **Composition**: centered high-impact conceptual product visual
  - **Lighting**: pristine studio lighting with luminous internal refraction inside the glass
  - **Medium & Style**: high-end conceptual advertising CGI still, thought-provoking commercial art
  - **Color & Texture**: crystal clear optical glass, rich evergreen needles, warm golden sand particles, cool twilight blue
  - **Constraints**: poetic visual transformation, razor-sharp optical refractions, elegant conceptual wonder

```text
A conceptual advertising visual showing an elegant glass hourglass where falling golden sand seamlessly transforms into a flourishing miniature pine forest inside the lower chamber. Pristine optical glass, illuminated refraction, clean horizon background, clever visual metaphor about time and growth, high-end commercial art.
```

## 三、七维度视觉词典与组合实验

配方库是成品菜，词典是调料架。当 38 套配方都不合适时，用 `config/z_image_style_vocabulary.yaml` 里的客观视觉词条按 7 维度组装新风格，而不是继续堆标签。

| 维度 | 词条数 | 示例 entry_id |
| :-- | --: | :-- |
| `subject` | 8 | `east_asian_woman_natural`, `middle_aged_man_weathered`, `hanfu_woman_round_fan` |
| `scene` | 9 | `minimal_interior_window`, `wet_street_after_rain`, `misty_mountain_valley` |
| `composition` | 10 | `medium_close_up_waist`, `intimate_close_up`, `full_body_environmental` |
| `lighting` | 10 | `soft_window_north`, `hard_side_chiaroscuro`, `low_key_neon` |
| `medium_style` | 15 | `medium_format_editorial`, `documentary_35mm_film`, `anamorphic_cinema_still` |
| `color_texture` | 13 | `neutral_low_saturation`, `monochrome_silver_gelatin`, `portra_faded_warm` |
| `constraints` | 10 | `candid_realism_zero_lora`, `clean_frame_no_overlay`, `widescreen_guard_16x9` |

```powershell
# 查词典
python src/produce.py atlas vocab --dimension lighting

# 用词典词条覆盖某几个维度
python src/produce.py atlas compile -s song_aesthetics --vocab "lighting:narrow_golden_spotlight,color_texture:celadon_mineral"

# 跨风格组合实验：宋式美学 + 奢侈品广告布光（只借光线与色彩，保留主媒介）
python src/produce.py atlas mix --base song_aesthetics --borrow luxury_product --dims lighting,color_texture --subject "a celadon tea bowl on a dark wooden table" --live
```

> **组合纪律**：一次只保留一个主媒介（`medium_style`）。借用 `medium_style` 时 CLI 会给出冲突告警——水墨 + 3D 卡通 + 写实摄影堆在一起只会得到风格糊。

## 四、实测工作台 (Benchmark Testbench)

```powershell
# 全量原生配方实拍（38 风格 x 1 seed）
python src/produce.py atlas benchmark --mode recipe --all --seeds 42 --size square --live --resume

# 同主体跨媒介对照（分离风格能力与主体难易）
python src/produce.py atlas benchmark --mode controlled --seeds 42,2026 --size square --live --resume

# 人工五维评分（脚本绝不自造分数）
python src/produce.py atlas score --run-dir "<run>" --style chinese_ink_wash --mode recipe --seed 42 --distinctiveness 5 --purity 3 --detail 4 --composition 5 --usability 4 --notes "水墨成立但混入青绿色块"

# 重建拼版与报告
python src/produce.py atlas board --run-dir "<run>"
python src/produce.py atlas report --run-dir "<run>"
```

运行目录结构（位于输出根 `experiments/z_image_styles/<run-name>/`）：

- `images/` 实拍原图，文件名含编号、风格 ID、模式与 seed
- `boards/` 分类拼版 + 全量总览拼版（CJK 标注）
- `benchmark_manifest.json` 逐图增量落盘，含完整 Prompt、耗时、状态、评分位
- `Z_IMAGE_STYLE_BENCHMARK_REPORT.md` / `scores.csv` 实测报告与评分表

工程约束：

- `--live` 且 ComfyUI 离线时**直接报错退出**，不会伪装成干跑成功。
- 单图失败不中断整轮；连接类错误等待服务器恢复后自动重试一次。
- `--resume` 按 `风格|模式|主体|seed|分辨率` 去重，可随时中断续跑。
- 五维评分初始为 `null`，只能由人工 `score` 写入。

## 五、生产调用方式

```powershell
# 单图生产（自动路由 Z-Image Turbo）
python src/produce.py image --project <id> --type portrait --style song_aesthetics --subject "a celadon tea bowl on a dark wooden table"

# 图谱批量实测
python scripts/run_z_image_style_atlas.py benchmark --mode recipe --all --seeds 42 --size square --live --resume
```
