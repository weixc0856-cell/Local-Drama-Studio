"""
Generate sample voice auditions for "Luo Shen Fu" narration using Microsoft Edge-TTS:
1. zh-CN-YunxiNeural: Emotional, immersive, cultural documentary tone (云希)
2. zh-CN-YunjianNeural: Authoritative, grand CCTV-style historical documentary tone (云健)
3. zh-CN-YunyangNeural: Formal, broadcast narration tone (云扬)
"""
import os
import asyncio
import edge_tts

OUTPUT_DIR = r"d:\Local-Drama-Studio\experiments\luoshenfu_style_comparison\tts"
ARTIFACTS_DIR = r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3"

SAMPLE_TEXT = (
    "黄昏日暮，洛水苍茫。"
    "其形也，翩若惊鸿，婉若游龙。荣曜秋菊，华茂春松。"
    "髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。"
    "恨人神之殊途，怅神光之渐隐。洛水汤汤，空留千古相思。"
)

VOICES = [
    {
        "id": "yunxi",
        "name": "zh-CN-YunxiNeural",
        "title": "云希（深情沉浸·国风解说腔）",
        "rate": "-4%",
        "pitch": "-2Hz"
    },
    {
        "id": "yunjian",
        "name": "zh-CN-YunjianNeural",
        "title": "云健（庄重浑厚·央视纪录片大片腔）",
        "rate": "-2%",
        "pitch": "-1Hz"
    },
    {
        "id": "yunyang",
        "name": "zh-CN-YunyangNeural",
        "title": "云扬（正气凛然·专业典雅播音腔）",
        "rate": "-3%",
        "pitch": "+0Hz"
    }
]

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    print("Generating Luo Shen Fu TTS audition samples...")
    for v in VOICES:
        dst_path = os.path.join(OUTPUT_DIR, f"audition_{v['id']}.mp3")
        art_path = os.path.join(ARTIFACTS_DIR, f"audition_{v['id']}.mp3")
        
        communicate = edge_tts.Communicate(SAMPLE_TEXT, v["name"], rate=v["rate"], pitch=v["pitch"])
        await communicate.save(dst_path)
        
        import shutil
        shutil.copyfile(dst_path, art_path)
        print(f"[OK] {v['title']} -> {dst_path}")

if __name__ == "__main__":
    asyncio.run(main())
