import os
import sys
import time
from pathlib import Path
import torch
import soundfile as sf
from diffusers import AceStepPipeline

MODEL_DIR = Path("D:/AI/models/audio/acestep-v15-xl-turbo-diffusers")
OUT_DIR = Path("outputs/audio_benchmark")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def test_acestep():
    print("=" * 60)
    print("Testing ACE-Step v1.5 XL Turbo (5B Guidance-Distilled DiT)")
    print("Running on CPU with 64GB DDR5 memory, 8 inference steps")
    print("=" * 60)

    t0 = time.time()
    pipe = AceStepPipeline.from_pretrained(
        str(MODEL_DIR),
        torch_dtype=torch.bfloat16,
    )
    pipe = pipe.to("cpu")
    print(f"Pipeline loaded in {time.time() - t0:.2f}s")

    prompt = (
        "Cinematic dramatic emotional ambient music, solitary cello and soaring string quartet, "
        "atmospheric noir movie soundtrack, elegant, instrumental"
    )

    print("\nGenerating 15.0s audio track...")
    t1 = time.time()
    generator = torch.Generator(device="cpu").manual_seed(202688)

    output = pipe(
        prompt=prompt,
        lyrics="",
        audio_duration=15.0,
        num_inference_steps=8,
        generator=generator,
    )

    elapsed = time.time() - t1
    print(f"Generation completed in {elapsed:.2f}s")

    audio = output.audios[0]
    out_wav = OUT_DIR / "case04_drama_acestep_cinematic_strings.wav"
    sf.write(str(out_wav), audio.T.float().cpu().numpy(), pipe.vae.sampling_rate if hasattr(pipe.vae, 'sampling_rate') else 48000)
    print(f"Saved audio: {out_wav} ({out_wav.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    test_acestep()
