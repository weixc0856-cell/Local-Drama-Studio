"""
Complete Production Pipeline for "Luo Shen Fu" - Route 1: Traditional Chinese Gongbi Style (工笔淡彩水墨画卷版)
1. Batch render 5 Gongbi storyboard keyframes on Intel Arc A750
2. Stitch 5-shot storyboard strip
3. Synthesize full 1080x1920 MP4 with camera motion, Yunxi narration, multi-track audio, and subtitles
"""
import os
import sys
import json
import time
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image

BASE_URL = "http://127.0.0.1:8188"
WF_SINGLE = r"d:\Local-Drama-Studio\workflows\flux3_lora_t2i_api.json"

ROOT = Path(r"d:\Local-Drama-Studio")
OUTPUT_DIR = ROOT / "experiments" / "luoshenfu_style_1_gongbi"
SCENES_DIR = OUTPUT_DIR / "scenes"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

VOICE_AUDIO = ROOT / "experiments" / "luoshenfu_style_comparison" / "tts" / "audition_yunxi.mp3"
BGM = ROOT / "assets" / "audio" / "bgm" / "commons" / "serenity_guitar.wav"
WATER = ROOT / "assets" / "audio" / "sfx" / "sfx_water_flow_20s.wav"
WIND = ROOT / "assets" / "audio" / "sfx" / "sfx_wind_soft_30s.wav"
CHIME = ROOT / "assets" / "audio" / "sfx" / "sfx_chime_single_6s.wav"
SUBTITLES_SRT = ROOT / "experiments" / "luoshenfu_style_comparison" / "scenes" / "subtitles.srt"

OUT_MP4 = OUTPUT_DIR / "luoshenfu_gongbi_23s.mp4"
ART_MP4 = ARTIFACTS_DIR / "luoshenfu_gongbi_23s.mp4"

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

def _render(value, params: dict):
    if isinstance(value, dict):
        return {k: _render(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, params) for v in value]
    if isinstance(value, str):
        match = PLACEHOLDER.match(value)
        if match:
            key = match.group(1)
            if key not in params:
                raise KeyError(f"missing workflow parameter: {key}")
            return params[key]
    return value

def queue_prompt(prompt_workflow):
    data = json.dumps({"prompt": prompt_workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/prompt", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_history(prompt_id):
    req = urllib.request.Request(f"{BASE_URL}/history/{prompt_id}")
    for _ in range(10):
        try:
            with OPENER.open(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            time.sleep(3)
    return {}

SCENES = [
    {
        "id": "S01_gongbi_dusk",
        "title": "S01【洛水暮色】工笔设色，黄昏草蓐",
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.50,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "breathtaking wide scenic Chinese ink painting, vast Luo river at twilight dusk (工笔重彩、宣纸墨韵、天地一色、空灵留白). "
                "Pale indigo and amber mineral wash, distant misty mountains in light ink, ancient Chinese royal carriage "
                "and resting horses on the grassy riverbank, fine lineart, poetic negative space, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261111,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "gongbi_s01_dusk"
        }
    },
    {
        "id": "S02_gongbi_scholar",
        "title": "S02【岸畔伫立】白描博带，凭石眺望",
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.50,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "young noble ancient Chinese scholar-poet standing by riverbank rocks (工笔白描、玄衣博带、凭虚远眺). "
                "Three-quarter back view over shoulder, wearing elegant deep navy-black Wei-Jin scholar robe with wide draped sleeves, "
                "gazing into the vast misty nocturnal river, wind blowing long hair ribbons, subtle mineral wash, poetic negative space, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261112,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "gongbi_s02_scholar"
        }
    },
    {
        "id": "S03_gongbi_arrival",
        "title": "S03【凌波初现】高古游丝，吴带当风",
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "full-body shot of ethereal ancient Chinese goddess floating gracefully above the misty Luo river (凌波微步、吴带当风、高古游丝、工笔设色). "
                "Wei-Jin dynasty classical beauty, high classical cloud bun hairstyle with subtle jade hairpin, "
                "wearing layered pale celadon and ivory silk Wei-Jin hanfu with wide draped sleeves, "
                "flowing translucent silk ribbons swirling in elegant calligraphy curves, delicate water wave lines beneath her feet, "
                "soft moonlit mist, subtle mineral pigments, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261113,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "gongbi_s03_arrival"
        }
    },
    {
        "id": "S04_gongbi_portrait",
        "title": "S04【神妃仙颜】轻云蔽月，流风回雪",
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "medium close-up cinematic portrait of the ethereal ancient Chinese goddess turning back with a serene and melancholic gaze (工笔绝色、回眸神凝、轻云蔽月、流风回雪). "
                "Refined oval face, delicate willow-leaf eyebrows, serene melancholic almond eyes with soft catchlights, "
                "tender relaxed lips with sheer mineral peach hydration. "
                "High classical cloud bun with delicate freshwater pearls and jade hairpins, "
                "fine wisps of hair framing forehead, pale celadon and ivory silk collar with flowing ribbons, "
                "soft diffused moonlight, poetic negative space, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261114,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "gongbi_s04_portrait"
        }
    },
    {
        "id": "S05_gongbi_sorrow",
        "title": "S05【怅然归隐】空灵留白，洛水汤汤",
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.50,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "wide atmospheric Chinese painting of the vast Luo river under gentle moonlight (空灵留白、神光敛去、洛水汤汤、千古余恨). "
                "Ethereal silhouette of the goddess dissolving into soft river mist and lotus leaves, "
                "gentle rippling ink lines expanding on water surface, vast poetic negative space, "
                "subtle pale celadon and indigo mineral wash, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261115,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "gongbi_s05_sorrow"
        }
    }
]

def main():
    os.makedirs(SCENES_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_SINGLE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated_paths = []
    
    # Step 1: Render 5 scenes
    for idx, scene in enumerate(SCENES):
        dst_path = SCENES_DIR / f"{scene['id']}.png"
        art_path = ARTIFACTS_DIR / f"{scene['id']}.png"

        print(f"\n=======================================================")
        print(f"[{idx+1}/5] Generating: {scene['title']}")
        print(f"=======================================================")

        if os.path.exists(dst_path) and os.path.getsize(dst_path) > 100000:
            print(f"File exists, using: {dst_path}")
            shutil.copyfile(dst_path, art_path)
            generated_paths.append(dst_path)
            continue

        wf = _render(template, scene["params"])
        res = queue_prompt(wf)
        pid = res["prompt_id"]
        print(f"Queued prompt_id: {pid} on Intel Arc A750...")

        start_time = time.time()
        while True:
            time.sleep(3)
            h = get_history(pid)
            if pid in h:
                outputs = h[pid]["outputs"]
                for node_id, node_out in outputs.items():
                    if "images" in node_out:
                        for img_meta in node_out["images"]:
                            fn = img_meta["filename"]
                            sub = img_meta.get("subfolder", "")
                            src_path = os.path.join(r"d:\Local-Drama-Studio\runtime\ComfyUI\output", sub, fn)
                            shutil.copyfile(src_path, dst_path)
                            shutil.copyfile(src_path, art_path)
                            elapsed = time.time() - start_time
                            print(f"[SUCCESS] {scene['id']} finished in {elapsed:.1f}s -> {dst_path}")
                            generated_paths.append(dst_path)
                break

    # Step 2: Stitch storyboard strip
    print("\nStitching 5-shot Gongbi storyboard strip...")
    images = [Image.open(p) for p in generated_paths]
    w, h = images[0].size
    strip = Image.new("RGB", (w * 5 + 40, h), color=(240, 236, 226))  # Xuan paper warm beige
    for i, img in enumerate(images):
        strip.paste(img, (i * (w + 10), 0))
    
    strip_path = SCENES_DIR / "luoshenfu_gongbi_5shot_storyboard_strip.png"
    strip_art = ARTIFACTS_DIR / "luoshenfu_gongbi_5shot_storyboard_strip.png"
    strip.save(strip_path, quality=95)
    strip.save(strip_art, quality=95)
    print(f"[DONE] Storyboard strip saved to:\n{strip_art}")

    # Step 3: Synthesize Video with FFmpeg
    print("\nSynthesizing full Gongbi film with FFmpeg...")
    FPS = 24
    W_OUT, H_OUT = 1080, 1920
    srt_escaped = str(SUBTITLES_SRT).replace("\\", "/").replace(":", "\\:")

    s01_filter = (
        f"[0:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.055*(on/115)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*(0.3+0.3*(on/115))':d=115:s={W_OUT}x{H_OUT}:fps={FPS}[v0];"
    )
    s02_filter = (
        f"[1:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.06*(on/110)':x='(iw-iw/zoom)*0.55':y='(ih-ih/zoom)*0.35':d=110:s={W_OUT}x{H_OUT}:fps={FPS}[v1];"
    )
    s03_filter = (
        f"[2:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.06*(on/115)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*(0.6-0.3*(on/115))':d=115:s={W_OUT}x{H_OUT}:fps={FPS}[v2];"
    )
    s04_filter = (
        f"[3:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.0+0.07*(on/134)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.28':d=134:s={W_OUT}x{H_OUT}:fps={FPS}[v3];"
    )
    s05_filter = (
        f"[4:v]scale=2160:3840:flags=lanczos,"
        f"zoompan=z='1.06-0.05*(on/125)':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.45':d=125:s={W_OUT}x{H_OUT}:fps={FPS}[v4];"
    )

    xfades = (
        "[v0][v1]xfade=transition=fade:duration=0.6:offset=4.2[xf0];"
        "[xf0][v2]xfade=transition=fade:duration=0.6:offset=8.2[xf1];"
        "[xf1][v3]xfade=transition=fade:duration=0.6:offset=12.4[xf2];"
        "[xf2][v4]xfade=transition=fade:duration=0.6:offset=17.4[xf3];"
        f"[xf3]subtitles='{srt_escaped}':force_style='FontName=SimSun,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BackColour=&H40000000,Outline=1.5,Shadow=1,MarginV=65'[vout]"
    )

    video_filter = s01_filter + s02_filter + s03_filter + s04_filter + s05_filter + xfades

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
        "-loop", "1", "-t", "4.8", "-i", str(generated_paths[0]),
        "-loop", "1", "-t", "4.6", "-i", str(generated_paths[1]),
        "-loop", "1", "-t", "4.8", "-i", str(generated_paths[2]),
        "-loop", "1", "-t", "5.6", "-i", str(generated_paths[3]),
        "-loop", "1", "-t", "5.2", "-i", str(generated_paths[4]),
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

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-2500:])
        raise SystemExit(1)
    
    shutil.copyfile(OUT_MP4, ART_MP4)
    print(f"\n[ALL DONE] Gongbi Version Movie generated:\n{OUT_MP4}\n{ART_MP4}")

if __name__ == "__main__":
    main()
