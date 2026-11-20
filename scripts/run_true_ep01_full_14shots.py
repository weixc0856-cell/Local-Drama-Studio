"""
Full 14-Shot Production for "Luo Shen Fu" Episode 1: "Luo Shui Jing Hong" (洛水惊鸿·真实序章全本)
Style: Traditional Chinese Gongbi Wash (工笔设色·宣纸墨韵)
Total Duration: ~55s
Hardware: FLUX.3 Klein + Intel Arc A750 8GB
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
EP1_DIR = ROOT / "experiments" / "luoshenfu_true_ep01"
SCENES_DIR = EP1_DIR / "scenes"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

VOICE_AUDIO = EP1_DIR / "tts" / "true_ep01_narration_yunxi.mp3"
BGM = ROOT / "assets" / "audio" / "bgm" / "commons" / "serenity_guitar.wav"
WATER = ROOT / "assets" / "audio" / "sfx" / "sfx_water_flow_20s.wav"
WIND = ROOT / "assets" / "audio" / "sfx" / "sfx_wind_soft_30s.wav"
CHIME = ROOT / "assets" / "audio" / "sfx" / "sfx_chime_single_6s.wav"

OUT_MP4 = EP1_DIR / "luoshenfu_ep01_full_master_55s.mp4"
ART_MP4 = ARTIFACTS_DIR / "luoshenfu_ep01_full_master_55s.mp4"

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

# 14 Full Detailed Storyboard Shots
SCENES = [
    {
        "id": "Shot_01_dusk_vast",
        "title": "01【洛水暮色】黄昏将及，残阳如血",
        "pre_existing": ROOT / "experiments" / "luoshenfu_style_1_gongbi" / "scenes" / "S01_gongbi_dusk.png",
        "params": None
    },
    {
        "id": "Shot_02_carriage_horses",
        "title": "02【秣马草蓐】车马卸驾，仆夫草蓐",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.45,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "ancient Chinese royal carriage unhitched on the grassy riverbank at twilight (秣马草蓐、税驾兰渚、工笔长卷). "
                "Carriage driver feeding grass to weary horses resting by the clear Luo riverbank, "
                "curling evening smoke, reeds swaying in gentle wind, soft mineral pigments, masterpiece, best quality"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261202,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s02_horses"
        }
    },
    {
        "id": "Shot_03_scholar_stroll",
        "title": "03【漫步水湄】容与阳林，流眄洛川",
        "pre_existing": ROOT / "experiments" / "luoshenfu_style_1_gongbi" / "scenes" / "S02_gongbi_scholar.png",
        "params": None
    },
    {
        "id": "Shot_04_scholar_shocked",
        "title": "04【精移神骇】心神忽动，蓦然回顾",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.50,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "medium close-up of noble young ancient Chinese poet-prince Cao Zhi (曹植神色动容、精移神骇、蓦然回顾). "
                "Wearing black Wei-Jin scholar cap and dark navy robe, turning head suddenly with wide astonished eyes, "
                "gazing into the mist, breathless expression of awe, fine lineart, subtle ink wash, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261204,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s04_shocked"
        }
    },
    {
        "id": "Shot_05_goddess_distant",
        "title": "05【睹一丽人】岩之水畔，仙影依稀",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.70,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "long wide shot of an ethereal ancient Chinese goddess standing solitary beside mossy riverside rocks (岩之水畔、睹一丽人、隔岸初见). "
                "Surrounded by nocturnal river mist, wearing flowing pale celadon and white Wei-Jin silk hanfu, "
                "translucent ribbons drifting in cold breeze, soft diffused moonlight on rippling water, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261205,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s05_distant"
        }
    },
    {
        "id": "Shot_06_ask_driver",
        "title": "06【援御急问】尔觌彼乎？彼何人斯！",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.45,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "poet-prince Cao Zhi gripping the carriage driver's sleeve with one hand, pointing urgently toward the distant river (乃援御者而急问、手指仙踪、神情震动). "
                "Two figures by the royal carriage, scholar in dark robes, driver looking astonished, dynamic classical composition, fine lineart, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261206,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s06_ask"
        }
    },
    {
        "id": "Shot_07_driver_reply",
        "title": "07【御者回禀】名曰宓妃，臣愿闻之",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.45,
            "positive_prompt": (
                "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "ancient Chinese carriage driver bowing respectfully beside resting horse, hand over heart, gazing toward the river (御者躬身回禀、名曰宓妃、愿闻其状). "
                "Riverbank reeds, soft twilight gradient in background, delicate brushwork, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261207,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s07_reply"
        }
    },
    {
        "id": "Shot_08_goddess_full",
        "title": "08【翩若惊鸿】翩若惊鸿，婉若游龙",
        "pre_existing": ROOT / "experiments" / "luoshenfu_style_1_gongbi" / "scenes" / "S03_gongbi_arrival.png",
        "params": None
    },
    {
        "id": "Shot_09_autumn_chrysanthemum",
        "title": "09【秋菊春松】荣曜秋菊，华茂春松",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "ethereal ancient Chinese goddess standing poised among celestial autumn chrysanthemum blossoms and evergreen pine branches (荣曜秋菊、华茂春松、高贵端穆). "
                "Medium full shot, refined oval face, high cloud bun with gold and pearl hairpins, "
                "pale celadon and ivory silk robes draped gracefully, serene divine radiance, mineral pigments, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261209,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s09_chrysanthemum"
        }
    },
    {
        "id": "Shot_10_clouds_moon",
        "title": "10【轻云蔽月】髣髴轻云，飘飖回雪",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.70,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "ethereal Chinese goddess enveloped in swirling moonlit clouds and falling snow particles (髣髴轻云蔽月、飘飖流风回雪). "
                "Three-quarter view, translucent silk veils fluttering in circular motion, soft pale cyan and silver glow, poetic dreamlike atmosphere, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261210,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s10_clouds"
        }
    },
    {
        "id": "Shot_11_lotus_portrait",
        "title": "11【灼若芙蕖】迫而察之，灼若芙蕖",
        "pre_existing": ROOT / "experiments" / "luoshenfu_style_1_gongbi" / "scenes" / "S04_gongbi_portrait.png",
        "params": None
    },
    {
        "id": "Shot_12_slender_waist",
        "title": "12【肩削腰约】肩若削成，腰如约素",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.70,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "cinematic medium shot emphasizing graceful posture and authentic Wei-Jin silhouette (肩若削成、腰如约素、罗衣垂曳). "
                "Slender elegant neck and delicate shoulders, narrow fitted waist bound by pale jade sash, "
                "translucent layered sleeves cascading like water, side profile with gentle smile, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261212,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s12_waist"
        }
    },
    {
        "id": "Shot_13_orchid_fragrance",
        "title": "13【气若幽兰】微幽兰芳，步踟蹰隅",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "goddess pacing hesitatingly at the rocky mountain corner by the riverbank (微幽兰之芳蔼、步踟蹰于山隅、欲往又止). "
                "Blooming wild fragrant orchids growing on rocks, goddess pausing mid-stride, turning back with soulful eyes toward the observer, mineral wash, masterpiece"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261213,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s13_orchid"
        }
    },
    {
        "id": "Shot_14_ready_to_dance",
        "title": "14【展袂欲遨】忽焉纵体，正欲凌波 (悬念留白)",
        "pre_existing": None,
        "params": {
            "lora_name": "characters\\immortal_lady_v1.safetensors",
            "lora_strength": 0.72,
            "positive_prompt": (
                "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
                "breathtaking shot of the goddess stepping delicately onto the glowing water surface, raising both long silk sleeves into the wind (忽焉纵体、以遨以嬉、神妃展袂、悬念定格). "
                "Water ripples expanding into golden circles, ribbons sweeping into calligraphy curves, distant shore shows poet watching in awe, masterpiece 8k artwork"
            ),
            "width": 576,
            "height": 1024,
            "seed": 20261214,
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": "ep1_s14_dance"
        }
    }
]

def main():
    os.makedirs(SCENES_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_SINGLE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated_paths = []
    
    # 1. Generate or link 14 shots
    for idx, scene in enumerate(SCENES):
        dst_path = SCENES_DIR / f"{scene['id']}.png"
        art_path = ARTIFACTS_DIR / f"{scene['id']}.png"

        print(f"\n=======================================================")
        print(f"[{idx+1}/14] Processing: {scene['title']}")
        print(f"=======================================================")

        # Check existing asset
        if scene["pre_existing"] and scene["pre_existing"].exists():
            print(f"Reusing verified approved master asset: {scene['pre_existing']}")
            shutil.copyfile(scene["pre_existing"], dst_path)
            shutil.copyfile(scene["pre_existing"], art_path)
            generated_paths.append(dst_path)
            continue

        if dst_path.exists() and dst_path.stat().st_size > 100000:
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

    # 2. Stitch 14-shot panoramic strip (2 rows of 7)
    print("\nStitching 14-shot Gongbi storyboard grid (2x7)...")
    images = [Image.open(p) for p in generated_paths]
    w, h = images[0].size
    grid_img = Image.new("RGB", (w * 7 + 60, h * 2 + 30), color=(240, 236, 226))
    for i, img in enumerate(images):
        col = i % 7
        row = i // 7
        grid_img.paste(img, (col * (w + 10), row * (h + 20)))
    
    grid_path = SCENES_DIR / "luoshenfu_ep01_14shot_storyboard_grid.png"
    grid_art = ARTIFACTS_DIR / "luoshenfu_ep01_14shot_storyboard_grid.png"
    grid_img.save(grid_path, quality=95)
    grid_img.save(grid_art, quality=95)
    print(f"[DONE] Storyboard grid saved to:\n{grid_art}")

    # 3. Build Subtitle SRT for 14 shots
    srt_path = SCENES_DIR / "true_ep01_subtitles.srt"
    srt_content = """1
00:00:00,500 --> 00:00:03,800
黄昏将及，秣马草蓐。

2
00:00:03,900 --> 00:00:07,500
余乃税驾乎蘅皋，税驾兰渚，

3
00:00:07,600 --> 00:00:10,800
容与阳林，流眄乎洛川。

4
00:00:11,000 --> 00:00:14,200
于是精移神骇，忽焉思散。

5
00:00:14,300 --> 00:00:18,500
顾眄瞻视，睹一丽人，于岩之畔。

6
00:00:18,800 --> 00:00:22,800
乃援御者而急问曰：尔有觌于彼者乎？

7
00:00:22,900 --> 00:00:25,800
彼何人斯，若此之艳也！

8
00:00:26,000 --> 00:00:29,800
御者对曰：臣闻河洛之神，名曰宓妃。

9
00:00:29,900 --> 00:00:33,800
君王所见，无乃是乎？其状若何，臣愿闻之。

10
00:00:34,000 --> 00:00:37,800
余告之曰：其形也，翩若惊鸿，婉若游龙。

11
00:00:37,900 --> 00:00:41,200
荣曜秋菊，华茂春松。

12
00:00:41,400 --> 00:00:44,800
髣髴兮若轻云之蔽月，飘飖兮若流风之回雪。

13
00:00:44,900 --> 00:00:48,800
迫而察之，灼若芙蕖出渌波。

14
00:00:49,000 --> 00:00:54,500
微幽兰之芳蔼兮，步踟蹰于山隅。神妃展步，方欲凌波而遨。
"""
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # 4. FFmpeg Video Synthesis (14 Shots, ~54.5s)
    print("\nSynthesizing full 55s Episode 1 Movie with FFmpeg...")
    FPS = 24
    W_OUT, H_OUT = 1080, 1920
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # Each shot duration ~4.2s (100 frames), xfade 0.5s (12 frames)
    # Total duration = 14 * 4.2 - 13 * 0.5 = 58.8 - 6.5 = 52.3s ~ 54.5s
    # Let's customize per shot duration:
    durations = [4.2, 4.0, 4.0, 3.8, 4.4, 4.2, 4.2, 4.5, 4.2, 4.2, 4.8, 4.0, 4.2, 5.5]
    # Sum of durations = 60.2s, 13 transitions of 0.5s = -6.5s -> net = 53.7s (perfect for 52.7s audio + 1s tail)

    video_filters = []
    for i in range(14):
        dur_f = int(durations[i] * FPS)
        if i in [0, 1, 4, 13]: # Wide shots
            z_expr = f"1.0+0.05*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*(0.3+0.3*(on/{dur_f}))"
        elif i in [3, 10]: # Close-up facial shock / beauty
            z_expr = f"1.0+0.065*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*0.28"
        elif i in [2, 5, 6]: # Scholar / Driver dialogue
            z_expr = f"1.0+0.055*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*0.35"
        else:
            z_expr = f"1.0+0.05*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*0.4"
        
        vf = (
            f"[{i}:v]scale=2160:3840:flags=lanczos,"
            f"zoompan=z='{z_expr}':x='(iw-iw/zoom)*0.5':y='{y_expr}':d={dur_f}:s={W_OUT}x{H_OUT}:fps={FPS}[v{i}];"
        )
        video_filters.append(vf)

    # Build chain of 13 xfades
    xfades = []
    cur_offset = durations[0] - 0.5
    last_node = "v0"
    for i in range(1, 14):
        out_node = f"xf{i-1}" if i < 13 else "xf_last"
        xf = f"[{last_node}][v{i}]xfade=transition=fade:duration=0.5:offset={cur_offset:.2f}[{out_node}];"
        xfades.append(xf)
        last_node = out_node
        cur_offset += durations[i] - 0.5

    sub_filter = f"[xf_last]subtitles='{srt_escaped}':force_style='FontName=SimSun,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BackColour=&H40000000,Outline=1.5,Shadow=1,MarginV=65'[vout]"

    full_video_filter = "".join(video_filters) + "".join(xfades) + sub_filter

    # Audio Mix (5 inputs: Voice, BGM, Water, Wind, Chime)
    total_dur = cur_offset + 0.5
    audio_filter = (
        f"[14:a]atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS,volume=1.15[voice];"
        f"[15:a]aloop=loop=-1:size=2e+09,atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS,volume=0.32,afade=t=in:st=0:d=2.0,afade=t=out:st={total_dur-2.0:.1f}:d=2.0[bgm];"
        f"[16:a]aloop=loop=-1:size=2e+09,atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS,volume=0.22,afade=t=in:st=0:d=1.5,afade=t=out:st={total_dur-1.5:.1f}:d=1.5[water];"
        f"[17:a]atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS,volume=0.18,afade=t=out:st={total_dur-2.0:.1f}:d=2.0[wind];"
        f"[18:a]adelay=33000|33000,atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS,volume=0.35[chime];"
        f"[voice][bgm][water][wind][chime]amix=inputs=5:duration=first:dropout_transition=2[aout]"
    )

    cmd = ["ffmpeg", "-y"]
    for i in range(14):
        cmd.extend(["-loop", "1", "-t", f"{durations[i]:.1f}", "-i", str(generated_paths[i])])
    cmd.extend([
        "-i", str(VOICE_AUDIO),
        "-i", str(BGM),
        "-i", str(WATER),
        "-i", str(WIND),
        "-i", str(CHIME),
        "-filter_complex", f"{full_video_filter};{audio_filter}",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{total_dur:.1f}",
        "-movflags", "+faststart",
        str(OUT_MP4)
    ])

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr[-3000:])
        raise SystemExit(1)

    shutil.copyfile(OUT_MP4, ART_MP4)
    print(f"\n[ALL DONE] Full 14-Shot Episode 1 Masterpiece generated:\n{OUT_MP4}\n{ART_MP4}")

if __name__ == "__main__":
    main()
