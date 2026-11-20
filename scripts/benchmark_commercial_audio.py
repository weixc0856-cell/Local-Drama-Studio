#!/usr/bin/env python3
"""
scripts/benchmark_commercial_audio.py
Commercial Audio Generation Benchmark & Audiovisual Muxing Suite:
Evaluates vetted commercial-permissive models for two core production lines:
1. Local-Drama-Studio: Tokyo Rain Night Cinematic Ambient Score + Rain SFX
2. CourseWorkspace: Minimalist Contemporary Classical Piano Explainer BGM

Target Audio Directory: D:/AI/models/audio/
Outputs: outputs/audio_benchmark/
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO_MODEL_DIR = Path("D:/AI/models/audio")
OUTPUT_DIR = ROOT / "outputs" / "audio_benchmark"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_CASES = [
    {
        "id": "case01_drama_tokyo_rain_ambient",
        "title": "Local-Drama-Studio · Tokyo Rain Night Cinematic Ambient",
        "target_line": "AI Cinematic Short Film (Emotion & Atmosphere)",
        "prompt": (
            "Cinematic melancholic ambient music, deep solo cello melody and delicate solitary piano notes, "
            "nocturnal rainy mood, Wong Kar-wai atmospheric movie soundtrack, 48kHz high fidelity stereo, instrumental"
        ),
        "duration": 10.0,
        "model_type": "stable_audio"
    },
    {
        "id": "case02_drama_tokyo_rain_foley",
        "title": "Local-Drama-Studio · Tokyo Rain Pattering & Traffic Foley SFX",
        "target_line": "Sound Design & Atmospheric Foley",
        "prompt": (
            "Gentle raindrops falling on a clear umbrella, soft rhythmic rain tapping, "
            "distant city street night traffic hum, delicate water splash, crisp natural acoustic field recording"
        ),
        "duration": 10.0,
        "model_type": "stable_audio"
    },
    {
        "id": "case03_course_minimalist_piano",
        "title": "CourseWorkspace · Minimalist Contemporary Classical Piano BGM",
        "target_line": "Technical Course & Documentary Explainer Background Score",
        "prompt": (
            "Minimalist contemporary classical piano, serene, continuous gentle flowing acoustic piano notes, "
            "soft atmospheric synth pads, calm thoughtful focus, no drums, no beat, no percussion, no sudden dynamic changes, "
            "pure documentary background score, Max Richter style, instrumental"
        ),
        "duration": 15.0,
        "model_type": "stable_audio"
    }
]


def run_stable_audio_generation(case: dict, device: str = "cpu") -> Path:
    """Generate audio using Stable Audio Open 1.0 pipeline."""
    import torch
    import soundfile as sf
    from diffusers import StableAudioPipeline

    model_path = AUDIO_MODEL_DIR / "stable-audio-open-1.0"
    if not model_path.exists():
        raise FileNotFoundError(f"Model path {model_path} does not exist. Please run download script first.")

    out_wav = OUTPUT_DIR / f"{case['id']}.wav"
    print(f"\n[*] Generating: {case['title']} ({case['duration']}s)...")
    t0 = time.time()

    torch_dtype = torch.float32 if device == "cpu" else torch.float16
    pipe = StableAudioPipeline.from_pretrained(str(model_path), torch_dtype=torch_dtype)
    pipe = pipe.to(device)

    generator = torch.Generator(device=device).manual_seed(20268801)
    output = pipe(
        prompt=case["prompt"],
        negative_prompt="low quality, noisy, distorted, crackling, loud drums, sudden screaming",
        num_inference_steps=25,
        audio_end_in_s=case["duration"],
        num_waveforms_per_prompt=1,
        generator=generator,
    )

    audio = output.audios[0] # [channels, samples]
    audio_data = audio.T.float().cpu().numpy()
    sf.write(str(out_wav), audio_data, pipe.vae.sampling_rate)

    elapsed = time.time() - t0
    print(f"[+] Audio generated in {elapsed:.1f}s -> {out_wav.name} ({out_wav.stat().st_size / 1024:.1f} KB)")
    return out_wav


def mux_audiovisual(video_path: Path, bgm_path: Path, sfx_path: Path | None, output_video: Path):
    """Mux video with background music and optional sound effects using FFmpeg."""
    if not video_path.exists():
        print(f"[Mux] Video path {video_path} not found. Skipping mux.")
        return False
    if not bgm_path.exists():
        print(f"[Mux] BGM path {bgm_path} not found. Skipping mux.")
        return False

    print(f"[Mux] Combining {video_path.name} + {bgm_path.name} -> {output_video.name}...")
    if sfx_path and sfx_path.exists():
        # Dual-track audio mix: BGM at -16dB, SFX at -10dB
        filter_complex = "[1:a]volume=0.5[a1];[2:a]volume=0.8[a2];[a1][a2]amix=inputs=2:duration=first[aout]"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(bgm_path),
            "-i", str(sfx_path),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_video)
        ]
    else:
        # Single track BGM
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(bgm_path),
            "-filter_complex", "[1:a]volume=0.7[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_video)
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[Mux] Master Audiovisual MP4 created: {output_video.name} ({output_video.stat().st_size / 1024 / 1024:.2f} MB)")
    return True


def run_benchmark():
    print("=" * 75)
    print(" Local Drama Studio · Commercial Audio Benchmark Suite")
    print(" Permissive Commercial Licenses (Apache 2.0 / MIT / Community <$1M)")
    print("=" * 75)

    generated_wavs = {}
    results = []

    for case in AUDIO_CASES:
        cid = case["id"]
        try:
            wav_path = run_stable_audio_generation(case, device="cpu")
            generated_wavs[cid] = wav_path
            results.append({
                "id": cid,
                "title": case["title"],
                "target_line": case["target_line"],
                "duration": case["duration"],
                "status": "SUCCESS",
                "wav_file": str(wav_path),
                "prompt": case["prompt"]
            })
        except Exception as e:
            print(f"[!] Error generating {cid}: {e}")
            results.append({
                "id": cid,
                "title": case["title"],
                "target_line": case["target_line"],
                "duration": case["duration"],
                "status": "FAILED",
                "error": str(e)
            })

    # Mux Audiovisual Master Video for Drama Studio
    video_9x16 = ROOT / "experiments" / "wan22_14b_test" / "case01_tokyo_rain_9x16_32fps_upscaled.mp4"
    bgm_wav = generated_wavs.get("case01_drama_tokyo_rain_ambient")
    sfx_wav = generated_wavs.get("case02_drama_tokyo_rain_foley")
    master_mp4 = ROOT / "experiments" / "wan22_14b_test" / "tokyo_rain_complete_audiovisual_master.mp4"

    if video_9x16.exists() and bgm_wav:
        mux_audiovisual(video_9x16, bgm_wav, sfx_wav, master_mp4)

    manifest = OUTPUT_DIR / "audio_benchmark_manifest.json"
    manifest.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Manifest] Audio benchmark configuration saved -> {manifest}")


if __name__ == "__main__":
    run_benchmark()
