"""Minimal-pair probe for the -n / -ng confusion (前后鼻音).

Synthesises a short list of minimal pairs with every available voice, transcribes
each clip with Whisper and compares the finals. The question it answers is not
"is the ASR right" but "does the error follow the voice", which separates a
prompt problem from a model problem.

    .venv\\Scripts\\python.exe scripts\\ng_probe.py --out experiments/audio_probe/ng
"""

from __future__ import annotations

import argparse
import os
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drama_studio.paths import output_root, output_path
from drama_studio.voice.zeroshot import DEFAULT_BASE, synthesize  # noqa: E402

# Disyllabic words, not isolated syllables: on a bare syllable Whisper normalises
# to the commonest character (森 -> 生), which measures its prior rather than the
# voice. A word's meaning pins the final.
PAIRS = [
    ("生活", "sheng", "ng"), ("森林", "sen", "n"),
    ("平安", "ping", "ng"), ("贫穷", "pin", "n"),
    ("明天", "ming", "ng"), ("民族", "min", "n"),
]
TEXT = "，".join(word for word, _, _ in PAIRS) + "。"
_AI_HOME = os.environ.get("DRAMA_AI_HOME")
_RUNTIME = os.environ.get("VOXCPM_RUNTIME") or (
    str(Path(_AI_HOME) / "VoxCPM-Runtime") if _AI_HOME else str(Path("VoxCPM-Runtime"))
)
WHISPER = Path(_RUNTIME) / "venv" / "Scripts" / "python.exe"
PROMPT_TEXT = "希望你以后能够做的比我还好呦。"


def whisper(path: Path, out_dir: Path) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(WHISPER), "-X", "utf8", "-m", "whisper", str(path), "--model", "small",
                    "--language", "zh", "--output_format", "txt",
                    "--output_dir", str(out_dir), "--fp16", "False"],
                   check=True, capture_output=True)
    return (out_dir / (path.stem + ".txt")).read_text(encoding="utf-8").strip()


def final_of(syllable: str) -> str | None:
    """ng / n / None for one transcribed syllable."""
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError:
        return None
    pieces = lazy_pinyin(syllable, style=Style.NORMAL)
    if not pieces:
        return None
    value = pieces[0]
    if value.endswith("ng"):
        return "ng"
    if value.endswith("n"):
        return "n"
    return None


class MissingDependencyError(RuntimeError):
    """Raised when the ASR toolchain is not installed; never fail silently."""


def require_whisper() -> None:
    if not WHISPER.is_file():
        raise MissingDependencyError(
            f"Whisper 解释器不存在：{WHISPER}\n"
            "请确认 VoxCPM 运行时已安装：VoxCPM-Runtime")
    probe = subprocess.run([str(WHISPER), "-c", "import whisper"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise MissingDependencyError(
            "VoxCPM 运行时未安装 openai-whisper。\n"
            f"请执行：{WHISPER} -m pip install openai-whisper")


def main(argv: list[str] | None = None) -> int:
    require_whisper()
    parser = argparse.ArgumentParser(description="probe -n / -ng by voice")
    parser.add_argument("--out", default="experiments/audio_probe/ng")
    parser.add_argument("--prompt", default="assets/audio/prompts/my_voice_clean_v1.wav")
    parser.add_argument("--prompt-original", default=None,
                        help="second prompt to test (e.g. the uncleaned recording)")
    parser.add_argument("--speed", type=float, default=0.82)
    args = parser.parse_args(argv)

    out = output_path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    voices: dict[str, Path] = {}

    prompt = ROOT / args.prompt
    result = synthesize(TEXT, prompt_wav=prompt, prompt_text=PROMPT_TEXT,
                        out_wav=out / "clone_clean.wav", speed=args.speed,
                        base=DEFAULT_BASE)
    voices["clone_clean"] = result.path

    if args.prompt_original:
        original = ROOT / args.prompt_original
        result = synthesize(TEXT, prompt_wav=original, prompt_text=PROMPT_TEXT,
                            out_wav=out / "clone_original.wav", speed=args.speed,
                            base=DEFAULT_BASE)
        voices["clone_original"] = result.path

    # SFT 预置音色已退休（2026-11-06）：VoxCPM2 只有参考音克隆，不再有 sft_male 这一路。

    report = {"text": TEXT, "pairs": [{"word": w, "final": f} for w, _, f in PAIRS],
              "speed": args.speed, "voices": {}}
    for name, path in voices.items():
        text = whisper(path, out / "asr")
        hits = []
        for word, _, expected in PAIRS:
            position = text.find(word)
            healed = position >= 0
            hits.append({"word": word, "expected": expected, "transcribed": healed})
        report["voices"][name] = {
            "audio": str(path.relative_to(ROOT)),
            "transcript": text,
            "kept": sum(1 for item in hits if item["transcribed"]),
            "of": len(PAIRS),
            "detail": hits,
        }

    (out / "ng_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
