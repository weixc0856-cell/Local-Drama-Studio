"""
Synthesize full cinematic short drama: "Luo Shen Fu - Prologue" (洛神赋·序章)
Visual Style: Route B (Guofeng Manhua CG / Semi-Realistic Anime)
Narration: Microsoft Edge-TTS (zh-CN-YunxiNeural)
Music & SFX: Multi-track ambient landscape mix
Output: 1080x1920 vertical MP4, 24 fps, H.264 / AAC
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(r"d:\Local-Drama-Studio")
SCENES_DIR = ROOT / "experiments" / "luoshenfu_style_comparison" / "scenes"
TTS_DIR = ROOT / "experiments" / "luoshenfu_style_comparison" / "tts"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

S01_IMG = SCENES_DIR / "S01_luo_river_dusk.png"
S02_IMG = SCENES_DIR / "S02_scholar_rocks.png"
S03_IMG = SCENES_DIR / "S03_goddess_arrival.png"
S04_IMG = SCENES_DIR / "S04_goddess_portrait.png"
S05_IMG = SCENES_DIR / "S05_parting_sorrow.png"

VOICE_AUDIO = TTS_DIR / "audition_yunxi.mp3"
BGM = ROOT / "assets" / "audio" / "bgm" / "commons" / "serenity_guitar.wav"
WATER = ROOT / "assets" / "audio" / "sfx" / "sfx_water_flow_20s.wav"
WIND = ROOT / "assets" / "audio" / "sfx" / "sfx_wind_soft_30s.wav"
CHIME = ROOT / "assets" / "audio" / "sfx" / "sfx_chime_single_6s.wav"

OUT_MP4 = ROOT / "experiments" / "luoshenfu_style_comparison" / "luoshenfu_prologue_23s.mp4"
ART_MP4 = ARTIFACTS_DIR / "luoshenfu_prologue_23s.mp4"

FPS = 24
W, H = 1080, 1920

# Durations:
# S01: 4.8s (115 frames)
# S02: 4.6s (110 frames)
# S03: 4.8s (115 frames)
# S04: 5.6s (134 frames)
# S05: 5.2s (125 frames)
# Transition: 0.6s (14 frames)
# Total duration = 4.8 + 4.6 + 4.8 + 5.6 + 5.2 - 4 * 0.6 = 22.6s

def build_srt():
    srt_path = SCENES_DIR / "subtitles.srt"
    content = """1
00:00:00,500 --> 00:00:04,200
黄昏日暮，洛水苍茫。

2
00:00:04,500 --> 00:00:08,200
其形也，翩若惊鸿，婉若游龙。

3
00:00:08,300 --> 00:00:10,200
荣曜秋菊，华茂春松。

4
00:00:10,300 --> 00:00:13,600
髣髴兮若轻云之蔽月，

5
00:00:13,700 --> 00:00:16,500
飘飖兮若流风之回雪。

6
00:00:16,600 --> 00:00:19,200
恨人神之殊途，怅神光之渐隐。

7
00:00:19,300 --> 00:00:22,400
洛水汤汤，空留千古相思。
"""
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(content)
    return srt_path

def main():
    srt_path = build_srt()
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # Zoompan camera motions:
    # S01: slow pan down & push in on landscape
    s01_filter = (
        f"[0:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.055*(on/115)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*(0.3+0.3*(on/115))':d=115:s={W}x{H}:fps={FPS}[v0];"
    )
    # S02: push in over shoulder toward the misty water
    s02_filter = (
        f"[1:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.06*(on/110)':x='(iw-iw/zoom)*0.55':y='(ih-ih/zoom)*0.35':d=110:s={W}x{H}:fps={FPS}[v1];"
    )
    # S03: pan up along flowing silk ribbons toward the goddess
    s03_filter = (
        f"[2:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.06*(on/115)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*(0.6-0.3*(on/115))':d=115:s={W}x{H}:fps={FPS}[v2];"
    )
    # S04: hero portrait close-up push in to the soulful eyes
    s04_filter = (
        f"[3:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.07*(on/134)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.28':d=134:s={W}x{H}:fps={FPS}[v3];"
    )
    # S05: gentle zoom out into the vast night water
    s05_filter = (
        f"[4:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.06-0.05*(on/125)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.45':d=125:s={W}x{H}:fps={FPS}[v4];"
    )

    # Cross-fades (0.6s = 14 frames)
    # cut 1: 4.8 - 0.6 = 4.2s
    # cut 2: 4.2 + 4.6 - 0.6 = 8.2s
    # cut 3: 8.2 + 4.8 - 0.6 = 12.4s
    # cut 4: 12.4 + 5.6 - 0.6 = 17.4s
    xfades = (
        "[v0][v1]xfade=transition=fade:duration=0.6:offset=4.2[xf0];"
        "[xf0][v2]xfade=transition=fade:duration=0.6:offset=8.2[xf1];"
        "[xf1][v3]xfade=transition=fade:duration=0.6:offset=12.4[xf2];"
        "[xf2][v4]xfade=transition=fade:duration=0.6:offset=17.4[xf3];"
        f"[xf3]subtitles='{srt_escaped}':force_style='FontName=SimSun,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BackColour=&H40000000,Outline=1.5,Shadow=1,MarginV=65'[vout]"
    )

    video_filter = s01_filter + s02_filter + s03_filter + s04_filter + s05_filter + xfades

    # Audio Mix (5 inputs: Voice, BGM, Water, Wind, Chime)
    # Total duration = 22.6s
    audio_filter = (
        f"[5:a]atrim=0:22.6,asetpts=PTS-STARTPTS,volume=1.1[voice];"
        f"[6:a]aloop=loop=-1:size=2e+09,atrim=0:22.6,asetpts=PTS-STARTPTS,volume=0.35,afade=t=in:st=0:d=1.5,afade=t=out:st=21.0:d=1.6[bgm];"
        f"[7:a]aloop=loop=-1:size=2e+09,atrim=0:22.6,asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:st=0:d=1.0,afade=t=out:st=21.2:d=1.4[water];"
        f"[8:a]atrim=0:22.6,asetpts=PTS-STARTPTS,volume=0.18,afade=t=out:st=21.0:d=1.6[wind];"
        f"[9:a]adelay=8200|8200,atrim=0:22.6,asetpts=PTS-STARTPTS,volume=0.35[chime];"
        f"[voice][bgm][water][wind][chime]amix=inputs=5:duration=first:dropout_transition=2[aout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", "4.8", "-i", str(S01_IMG),
        "-loop", "1", "-t", "4.6", "-i", str(S02_IMG),
        "-loop", "1", "-t", "4.8", "-i", str(S03_IMG),
        "-loop", "1", "-t", "5.6", "-i", str(S04_IMG),
        "-loop", "1", "-t", "5.2", "-i", str(S05_IMG),
        "-i", str(VOICE_AUDIO),
        "-i", str(BGM),
        "-i", str(WATER),
        "-i", str(WIND),
        "-i", str(CHIME),
        "-filter_complex", f"{video_filter};{audio_filter}",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", "22.6",
        "-movflags", "+faststart",
        str(OUT_MP4)
    ]

    print("Synthesizing multi-shot cinematic film...")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-2500:])
        raise SystemExit(1)
    
    import shutil
    shutil.copyfile(OUT_MP4, ART_MP4)
    print(f"\n[DONE] High-definition film generated:\n{OUT_MP4}\n{ART_MP4}")

if __name__ == "__main__":
    main()
