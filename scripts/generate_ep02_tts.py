"""
Generate Narration Audio for Episode 2: "Ling Bo Wei Bu" (凌波微步)
Speaker: Microsoft Edge-TTS (zh-CN-YunxiNeural)
"""
import os
import asyncio
import edge_tts
from pathlib import Path

ROOT = Path(r"d:\Local-Drama-Studio")
EP2_DIR = ROOT / "experiments" / "luoshenfu_ep02_lingbo"
TTS_DIR = EP2_DIR / "tts"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

os.makedirs(TTS_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

EP2_TEXT = (
    "体迅飞凫，飘忽若神。"
    "凌波微步，罗袜生尘。"
    "动无常则，若危若安。进止难期，若往若还。"
    "转眄流精，光润玉颜。"
    "含辞未吐，气若幽兰。华容婀娜，令我忘餐。"
    "余情悦其淑美兮，心振荡而不怡。"
)

async def main():
    voice = "zh-CN-YunxiNeural"
    rate = "-3%"
    pitch = "-2Hz"
    
    dst_mp3 = TTS_DIR / "ep02_narration_yunxi.mp3"
    art_mp3 = ARTIFACTS_DIR / "ep02_narration_yunxi.mp3"
    
    print(f"Generating Episode 2 TTS with {voice}...")
    communicate = edge_tts.Communicate(EP2_TEXT, voice, rate=rate, pitch=pitch)
    await communicate.save(dst_mp3)
    
    import shutil
    shutil.copyfile(dst_mp3, art_mp3)
    print(f"[OK] Episode 2 Narration generated:\n{dst_mp3}")

if __name__ == "__main__":
    asyncio.run(main())
