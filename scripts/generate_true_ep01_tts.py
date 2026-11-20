"""
Generate Narration Audio for True Episode 1: "Luo Shui Jing Hong" (洛水惊鸿·真实序章)
Speaker: Microsoft Edge-TTS (zh-CN-YunxiNeural)
Strictly adheres to Cao Zhi's original text and dialogue.
"""
import os
import asyncio
import edge_tts
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EP1_DIR = ROOT / "experiments" / "luoshenfu_true_ep01"
TTS_DIR = EP1_DIR / "tts"
ARTIFACTS_DIR = Path(os.environ.get("DRAMA_ARTIFACTS_DIR", "./studio_data/artifacts"))

os.makedirs(TTS_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

TRUE_EP1_TEXT = (
    "黄昏将及，秣马草蓐。余乃税驾乎蘅皋，税驾兰渚，流眄乎洛川。"
    "于是精移神骇，顾眄瞻视，睹一丽人，于岩之畔。"
    "乃援御者而急问曰：尔有觌于彼者乎？彼何人斯，若此之艳也！"
    "御者对曰：臣闻河洛之神，名曰宓妃。君王所见，无乃是乎？其状若何，臣愿闻之。"
    "余告之曰：其形也，翩若惊鸿，婉若游龙。荣曜秋菊，华茂春松。"
    "髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。迫而察之，灼若芙蕖出渌波。"
    "微幽兰之芳蔼兮，步踟蹰于山隅。神妃展步，方欲凌波而遨。"
)

async def main():
    voice = "zh-CN-YunxiNeural"
    rate = "-3%"
    pitch = "-2Hz"
    
    dst_mp3 = TTS_DIR / "true_ep01_narration_yunxi.mp3"
    art_mp3 = ARTIFACTS_DIR / "true_ep01_narration_yunxi.mp3"
    
    print(f"Generating True Episode 1 TTS with {voice}...")
    communicate = edge_tts.Communicate(TRUE_EP1_TEXT, voice, rate=rate, pitch=pitch)
    await communicate.save(dst_mp3)
    
    import shutil
    shutil.copyfile(dst_mp3, art_mp3)
    print(f"[OK] True Episode 1 Narration generated successfully:\n{dst_mp3}")

if __name__ == "__main__":
    asyncio.run(main())
