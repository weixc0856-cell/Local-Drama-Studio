"""
Strict Character Consistency Pipeline for "Luo Shen Fu" Episode 1:
Triple Lock-in:
1. Mifei (Goddess): strictly locked facial bone structure, high cloud bun with single jade hairpin, celadon & ivory wide-sleeve Wei-Jin robe.
2. Cao Zhi (Scholar): strictly locked 28yo scholar face, black Jinxiang cap with ribbons, deep navy-indigo wide-sleeve scholar robe.
3. Driver (Peasant): strictly locked weathered face, brown hemp tunic with rolled sleeves, brown linen head wrap.
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
EP1_DIR = ROOT / "experiments" / "luoshenfu_consistent_ep01"
SCENES_DIR = EP1_DIR / "scenes"
ARTIFACTS_DIR = Path(r"C:\Users\99236\.gemini\antigravity\brain\d1169d61-a3c4-438c-b9fb-7026d0aa29b3")

VOICE_AUDIO = ROOT / "experiments" / "luoshenfu_true_ep01" / "tts" / "true_ep01_narration_yunxi.mp3"
BGM = ROOT / "assets" / "audio" / "bgm" / "commons" / "serenity_guitar.wav"
WATER = ROOT / "assets" / "audio" / "sfx" / "sfx_water_flow_20s.wav"
WIND = ROOT / "assets" / "audio" / "sfx" / "sfx_wind_soft_30s.wav"
CHIME = ROOT / "assets" / "audio" / "sfx" / "sfx_chime_single_6s.wav"
SRT_PATH = ROOT / "experiments" / "luoshenfu_true_ep01" / "scenes" / "true_ep01_subtitles.srt"

OUT_MP4 = EP1_DIR / "luoshenfu_ep01_consistent_master.mp4"
ART_MP4 = ARTIFACTS_DIR / "luoshenfu_ep01_consistent_master.mp4"

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

# 1. Triple Character Anchors (Word for word identical across shots)
LADY_ANCHOR = (
    "girlslikeflux_lyf5, traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
    "Wei-Jin ancient goddess Mifei (洛水神女宓妃). Pure East Asian delicate facial features, refined oval face with dainty chin, "
    "serene melancholic almond eyes with dark pupils, natural sheer peach parted lips. "
    "High classical Wei-Jin cloud bun hairstyle strictly adorned with a single pale jade hairpin, soft wispy air bangs casually draping forehead. "
    "Wearing layered pale celadon cyan silk (#A0D8D0) and pure ivory white silk (#FFFFF0) Wei-Jin hanfu with wide draped sleeves, "
    "bound with pale jade belt sash, translucent cyan silk ribbons floating around her. "
)

SCHOLAR_ANCHOR = (
    "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
    "noble young Chinese scholar-poet Cao Zhi, aged 28, slender handsome scholar face, fair skin, high brow, melancholy contemplative eyes. "
    "Wearing black Wei-Jin scholar cap (魏晋进贤冠) with black tied ribbons, "
    "wearing deep navy-indigo Wei-Jin dynasty scholar robe with wide draped sleeves (深青玄衣博带), dark charcoal silk collar. "
)

DRIVER_ANCHOR = (
    "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
    "ancient Chinese carriage driver, middle-aged weathered face, wearing brown coarse hemp peasant tunic with rolled sleeves and brown linen head wrap. "
)

SCENES = [
    {
        "id": "Shot_01_dusk_landscape",
        "title": "01【洛水暮色】黄昏将及，残阳如血",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.35,
        "seed": 20261111,
        "prompt": (
            "traditional Chinese gongbi painting style, delicate ink wash texture, Xuan paper texture, "
            "breathtaking wide scenic Chinese ink painting, vast Luo river at twilight dusk (日暮黄昏、洛水苍茫、大景空灵). "
            "Pale amber and soft indigo mineral wash, distant misty mountains in light ink, ancient Chinese royal carriage and resting horses on the grassy riverbank, "
            "reeds swaying in cold evening breeze, poetic negative space, masterpiece, best quality"
        )
    },
    {
        "id": "Shot_02_carriage_horses",
        "title": "02【秣马草蓐】车马卸驾，仆夫草蓐",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.45,
        "seed": 20261302,
        "prompt": (
            DRIVER_ANCHOR +
            "feeding dried grass to royal horses beside unhitched wooden carriage on the riverbank (车马卸驾、秣马草蓐). "
            "Horses drinking from clear shallow water, curling evening campfire smoke rising into dusk, fine lineart, masterpiece"
        )
    },
    {
        "id": "Shot_03_scholar_stroll",
        "title": "03【漫步水湄】容与阳林，流眄洛川",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.50,
        "seed": 20261303,
        "prompt": (
            SCHOLAR_ANCHOR +
            "strolling pensively along the grassy riverbank, three-quarter back view looking out toward the vast misty river (容与阳林、流眄洛川、负手独立). "
            "Wind blowing wide draped sleeves and black ribbons, solitary dignified posture, evening mist drifting over water, masterpiece"
        )
    },
    {
        "id": "Shot_04_scholar_shocked",
        "title": "04【精移神骇】心神忽动，蓦然回顾",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.50,
        "seed": 20261304,
        "prompt": (
            SCHOLAR_ANCHOR +
            "medium close-up, poet-prince Cao Zhi turning his head suddenly toward the river with startled wide eyes (精移神骇、心神大动、蓦然回首). "
            "Breathless astonishment, gazing across the water into the mist, hair ribbons fluttering in cold wind, fine lineart, masterpiece"
        )
    },
    {
        "id": "Shot_05_goddess_distant",
        "title": "05【睹一丽人】岩之水畔，仙影依稀",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261305,
        "prompt": (
            LADY_ANCHOR +
            "long wide environmental shot, standing solitary beside riverside rocks across the misty river (睹一丽人、于岩之畔、隔水相望). "
            "Surrounded by nocturnal water vapor, flowing pale celadon and ivory robes draped to the ground, translucent ribbons caught in the breeze, masterpiece"
        )
    },
    {
        "id": "Shot_06_ask_driver",
        "title": "06【援御急问】尔觌彼乎？彼何人斯！",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.45,
        "seed": 20261306,
        "prompt": (
            SCHOLAR_ANCHOR +
            "urgently gripping the carriage driver's shoulder with one hand, pointing with other hand toward the misty river (乃援御者而急问、手指仙踪). "
            "Beside him, the carriage driver in brown hemp tunic looks with astonishment in the same direction, dynamic narrative composition, masterpiece"
        )
    },
    {
        "id": "Shot_07_driver_reply",
        "title": "07【御者回禀】名曰宓妃，臣愿闻之",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.45,
        "seed": 20261307,
        "prompt": (
            DRIVER_ANCHOR +
            "bowing respectfully with hands cupped toward the poet-prince, looking toward the river (御者躬身回禀、名曰宓妃、愿闻其状). "
            "Ancient carriage wheel in foreground, twilight riverbank reeds in background, delicate classical ink wash, masterpiece"
        )
    },
    {
        "id": "Shot_08_goddess_full",
        "title": "08【翩若惊鸿】翩若惊鸿，婉若游龙",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261308,
        "prompt": (
            LADY_ANCHOR +
            "full body shot, floating gracefully above misty water ripples (翩若惊鸿、婉若游龙、吴带当风). "
            "Wide draped ivory sleeves and layered pale celadon robes sweeping gracefully like a flying swan, swirling translucent ribbons, glowing river mist, masterpiece"
        )
    },
    {
        "id": "Shot_09_autumn_chrysanthemum",
        "title": "09【秋菊春松】荣曜秋菊，华茂春松",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261309,
        "prompt": (
            LADY_ANCHOR +
            "medium full shot, standing with dignified serene grace beside celestial autumn chrysanthemums and pine branches (荣曜秋菊、华茂春松、高贵端穆). "
            "Layered celadon and ivory silk robes draped immaculately, single jade hairpin in high cloud bun, pure divine radiance, mineral wash, masterpiece"
        )
    },
    {
        "id": "Shot_10_clouds_moon",
        "title": "10【轻云蔽月】髣髴轻云，飘飖回雪",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261310,
        "prompt": (
            LADY_ANCHOR +
            "three-quarter view enveloped in gentle swirling moonlit mist and drifting snow particles (髣髴轻云蔽月、飘飖流风回雪). "
            "Translucent silk veils fluttering in circular motion around her celadon collar, soft moonlight illuminating her pure oval face and high bun, masterpiece"
        )
    },
    {
        "id": "Shot_11_lotus_portrait",
        "title": "11【灼若芙蕖】迫而察之，灼若芙蕖",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.75,
        "seed": 20261114,
        "prompt": (
            LADY_ANCHOR +
            "medium close-up cinematic portrait, looking back over shoulder with serene melancholic dark almond eyes (迫而察之、灼若芙蕖、绝代神颜). "
            "Pure oval face, delicate willow-leaf eyebrows, tender relaxed lips with sheer peach tint, single white jade hairpin in high cloud bun, air bangs, celadon collar, masterpiece"
        )
    },
    {
        "id": "Shot_12_slender_waist",
        "title": "12【肩削腰约】肩若削成，腰如约素",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261312,
        "prompt": (
            LADY_ANCHOR +
            "medium shot from side-back profile, emphasizing slender graceful shoulders and narrow waist (肩若削成、腰如约素、身段合度). "
            "Fitted pale jade sash around waist, cascading layered ivory and celadon sleeves, high cloud bun with single jade pin visible from profile, masterpiece"
        )
    },
    {
        "id": "Shot_13_orchid_fragrance",
        "title": "13【气若幽兰】微幽兰芳，步踟蹰隅",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261313,
        "prompt": (
            LADY_ANCHOR +
            "standing beside riverbank mossy rock where wild orchids bloom, hesitating mid-step and turning head back toward the observer (微幽兰芳、步踟蹰隅、欲往又止). "
            "Soulful eyes, single white jade pin in cloud bun, layered celadon and ivory robe hem touching water ripples, masterpiece"
        )
    },
    {
        "id": "Shot_14_ready_to_dance",
        "title": "14【展袂欲遨】忽焉纵体，正欲凌波 (悬念留白)",
        "lora": "characters\\immortal_lady_v1.safetensors",
        "strength": 0.72,
        "seed": 20261314,
        "prompt": (
            LADY_ANCHOR +
            "stepping delicately onto water surface, raising wide draped ivory sleeves into the night breeze (忽焉纵体、以遨以嬉、神女展袂、定格悬念). "
            "Expanding water ripples under delicate silk socks, translucent ribbons sweeping into wind, distant riverbank shows poet in navy robe watching in awe, masterpiece 8k"
        )
    }
]

def main():
    os.makedirs(SCENES_DIR, exist_ok=True)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    with open(WF_SINGLE, "r", encoding="utf-8") as f:
        template = json.load(f)

    generated_paths = []
    
    for idx, scene in enumerate(SCENES):
        dst_path = SCENES_DIR / f"{scene['id']}.png"
        art_path = ARTIFACTS_DIR / f"{scene['id']}.png"

        print(f"\n=======================================================")
        print(f"[{idx+1}/14] Generating Consistent Shot: {scene['title']}")
        print(f"=======================================================")

        params = {
            "lora_name": scene["lora"],
            "lora_strength": scene["strength"],
            "positive_prompt": scene["prompt"],
            "width": 576,
            "height": 1024,
            "seed": scene["seed"],
            "steps": 18,
            "cfg": 1.0,
            "filename_prefix": f"consist_{scene['id']}"
        }

        wf = _render(template, params)
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

    # Stitch 2x7 Storyboard Grid
    print("\nStitching 14-shot Consistent Storyboard Grid...")
    images = [Image.open(p) for p in generated_paths]
    w, h = images[0].size
    grid_img = Image.new("RGB", (w * 7 + 60, h * 2 + 30), color=(240, 236, 226))
    for i, img in enumerate(images):
        col = i % 7
        row = i // 7
        grid_img.paste(img, (col * (w + 10), row * (h + 20)))
    
    grid_path = SCENES_DIR / "luoshenfu_consistent_14shot_grid.png"
    grid_art = ARTIFACTS_DIR / "luoshenfu_consistent_14shot_grid.png"
    grid_img.save(grid_path, quality=95)
    grid_img.save(grid_art, quality=95)
    print(f"[DONE] Consistent Storyboard Grid saved to:\n{grid_art}")

    # FFmpeg Video Synthesis (54.5s)
    print("\nSynthesizing Consistent Episode 1 Master Movie...")
    FPS = 24
    W_OUT, H_OUT = 1080, 1920
    srt_escaped = str(SRT_PATH).replace("\\", "/").replace(":", "\\:")
    durations = [4.2, 4.0, 4.0, 3.8, 4.4, 4.2, 4.2, 4.5, 4.2, 4.2, 4.8, 4.0, 4.2, 5.5]

    video_filters = []
    for i in range(14):
        dur_f = int(durations[i] * FPS)
        if i in [0, 1, 4, 13]:
            z_expr = f"1.0+0.05*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*(0.3+0.3*(on/{dur_f}))"
        elif i in [3, 10]:
            z_expr = f"1.0+0.065*(on/{dur_f})"
            y_expr = f"(ih-ih/zoom)*0.28"
        elif i in [2, 5, 6]:
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
    print(f"\n[MASTER GENERATED] Consistent Episode 1 Movie:\n{OUT_MP4}\n{ART_MP4}")

if __name__ == "__main__":
    main()
