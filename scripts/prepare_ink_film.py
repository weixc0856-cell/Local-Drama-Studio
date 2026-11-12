"""Prepare the Wan I2V batch and build inputs for the 24-shot ink film.

Run after the FLUX keyframes exist. It copies each keyframe into ComfyUI's
input directory, writes per-shot Wan params and jobs, and writes
segments_24.json + audio_timeline_24.json for the final r3_build.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = output_path("experiments/ink_dream")
INPUT = ROOT / "runtime" / "ComfyUI" / "input"
MOVES = [
    "mist drifts slowly, ink diffuses at the edges, composition preserved",
    "water ripples gently, mist moves, composition preserved",
    "extremely slow push-in, ink wash texture stays stable, composition preserved",
    "slow lateral drift, mist and water move, architecture stays rigid",
]
NEG = ("camera shake, flicker, strobing, morphing, warping, melting, extra objects, "
       "new buildings, text, watermark, low quality, colour shift")


def main() -> int:
    images = sorted(BASE.glob("images/shot_*"))
    if len(images) != 24:
        raise SystemExit(f"expected 24 keyframes, found {len(images)}")
    INPUT.mkdir(parents=True, exist_ok=True)
    params_dir = BASE / "wan_params"
    params_dir.mkdir(exist_ok=True)
    jobs = []
    segments = []
    for index, folder in enumerate(images, 1):
        shot = folder.name
        frames = sorted(folder.glob("*.png"))
        if not frames:
            raise SystemExit(f"{shot}: no keyframe png")
        source = frames[0]
        from PIL import Image, ImageStat
        with Image.open(source) as img:
            if img.size != (576, 1024):
                raise SystemExit(f"{shot}: unexpected size {img.size}")
            spread = sum(ImageStat.Stat(img.convert("L")).stddev)
            if spread < 8:
                raise SystemExit(f"{shot}: looks blank (stddev {spread:.1f})")
        sid = f"ink{index:02d}"
        input_name = f"ink_{shot}.png"
        shutil.copyfile(source, INPUT / input_name)
        params = {
            "positive_prompt": f"Traditional Chinese ink wash scene; {MOVES[(index - 1) % len(MOVES)]}; "
                               "no subject displacement, no new objects, no text.",
            "negative_prompt": NEG,
            "input_image": input_name,
            "seed": 20261105 + index,
            "width": 576,
            "height": 1024,
            "frames": 73,
            "steps": 20,
            "cfg": 5.0,
            "shift": 8.0,
            "filename_prefix": f"ink_dream/wan24/{sid}",
        }
        pp = params_dir / f"{sid}.json"
        pp.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jobs.append({
            "id": sid,
            "workflow": "workflows/r0_wan_i2v_api.json",
            "params": pp.relative_to(ROOT).as_posix(),
            "out": f"experiments/ink_dream/wan24/{sid}",
            "reference": {"source": source.relative_to(ROOT).as_posix(), "input_name": input_name},
        })
        segments.append({
            "id": sid,
            "type": "image",
            "source": source.as_posix(),
            "duration": 5.0,
            "shot": shot,
        })
    (BASE / "wan24_jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (BASE / "segments_24.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    timeline = {
        "schema_version": "1.0",
        "sample_rate": 48000,
        "duration_ms": 121300,
        "tracks": [
            {"track_id": "bgm_main", "type": "bgm", "asset_id": "bgm_schubert_d664_piano",
             "duration_ms": 121300, "gain_db": -15.0, "loop": True,
             "fade_in_ms": 2500, "fade_out_ms": 5000, "ducking": None},
            {"track_id": "sfx_main", "type": "sfx", "duration_ms": 121300, "gain_db": 0.0,
             "events": [
                 {"event_id": "water_1", "asset_id": "sfx_water_flow_20s", "start_ms": 0,
                  "duration_ms": 20000, "gain_db": -20},
                 {"event_id": "wind_1", "asset_id": "sfx_wind_soft_30s", "start_ms": 20000,
                  "duration_ms": 30000, "gain_db": -22},
                 {"event_id": "water_2", "asset_id": "sfx_water_flow_20s", "start_ms": 55000,
                  "duration_ms": 30000, "gain_db": -20},
                 {"event_id": "wind_2", "asset_id": "sfx_wind_soft_30s", "start_ms": 85000,
                  "duration_ms": 30000, "gain_db": -22},
                 {"event_id": "whoosh_1", "asset_id": "sfx_whoosh_2s", "start_ms": 20000,
                  "duration_ms": 2000, "gain_db": -20},
                 {"event_id": "whoosh_2", "asset_id": "sfx_whoosh_2s", "start_ms": 45000,
                  "duration_ms": 2000, "gain_db": -20},
                 {"event_id": "whoosh_3", "asset_id": "sfx_whoosh_2s", "start_ms": 70000,
                  "duration_ms": 2000, "gain_db": -20},
                 {"event_id": "whoosh_4", "asset_id": "sfx_whoosh_2s", "start_ms": 95000,
                  "duration_ms": 2000, "gain_db": -20},
             ]},
        ],
    }
    (BASE / "audio_timeline_24.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audio = {
        "content_type": "narration",
        "sample_rate": 48000,
        "lines": [{
            "index": 1, "text": "", "subtitle_text": "",
            "file": (output_path("experiments/shinkai_scene") / "silence_120s.wav").as_posix(),
            "duration_seconds": 120.0,
            "sha256": "c779c14bb0cbf9e62bc480f33ca3233283dd45b48bc416df46beda10ce5133ae",
            "pause_after_ms": 0,
        }],
    }
    (BASE / "audio_24.json").write_text(json.dumps(audio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "segments": len(segments)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
