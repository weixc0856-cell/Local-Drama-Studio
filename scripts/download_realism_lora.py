import urllib.request
from pathlib import Path

url = "https://huggingface.co/XLabs-AI/flux-RealismLora/resolve/main/lora.safetensors"
dst = Path(r"d:\Local-Drama-Studio\runtime\ComfyUI\models\loras\flux_realism_xlabs.safetensors")

print(f"Downloading {url} to {dst}...", flush=True)

def reporthook(blocknum, blocksize, totalsize):
    read = blocknum * blocksize
    if totalsize > 0:
        pct = min(100.0, read * 100.0 / totalsize)
        if blocknum % 50 == 0:
            print(f"  Downloaded: {read/1024/1024:.1f} MB / {totalsize/1024/1024:.1f} MB ({pct:.1f}%)", flush=True)

urllib.request.urlretrieve(url, dst, reporthook=reporthook)
print(f"Downloaded successfully: {dst} ({dst.stat().st_size / 1024 / 1024:.1f} MB)")
