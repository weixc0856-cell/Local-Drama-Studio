"""ASR proxy QA for narration audio (run with the CosyVoice runtime venv).

Run this with the environment that has ``openai-whisper`` installed, e.g.::

    D:\\AI\\CosyVoice-Runtime\\venv\\Scripts\\python.exe scripts\\tts_qa.py ^
        --manifest projects/<project>/episodes/<episode>/audio_manifest.json

Whisper is a proxy, not an ear: classical Chinese homophones are easy for it to
mishear even when the reading is correct. A line with a large character error
rate is strong evidence of a problem; a perfect transcript is not proof of
correct pronunciation.

When the acoustic layer used a curated homophone alias, the ASR text is first
normalized by mapping the alias back to the original word before CER. That is
the character-level equivalent of "the ASR pinyin matches the expected pinyin"
and prevents a correct alias from being counted as a pronunciation error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def norm(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff]", "", text)


def cer(ref: str, hyp: str) -> float:
    ref, hyp = norm(ref), norm(hyp)
    rows = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
    for i in range(len(ref) + 1):
        rows[i][0] = i
    for j in range(len(hyp) + 1):
        rows[0][j] = j
    for i in range(1, len(ref) + 1):
        for j in range(1, len(hyp) + 1):
            rows[i][j] = min(
                rows[i - 1][j] + 1,
                rows[i][j - 1] + 1,
                rows[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]),
            )
    return round(rows[len(ref)][len(hyp)] / max(1, len(ref)), 3)


def levels(path: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", proc.stderr)
    peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", proc.stderr)
    return {
        "mean_db": float(mean.group(1)) if mean else None,
        "max_db": float(peak.group(1)) if peak else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ASR proxy QA for a narration audio_manifest.json")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--model", default="base")
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-cer", type=float, default=0.15)
    args = parser.parse_args()

    try:
        import whisper
    except ImportError:
        print(json.dumps({
            "ok": False,
            "error": "openai-whisper 未安装。请用 CosyVoice 运行时 venv 执行："
                     "D:\\AI\\CosyVoice-Runtime\\venv\\Scripts\\python.exe scripts\\tts_qa.py ...",
        }, ensure_ascii=False))
        return 2

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pronunciation_path = manifest_path.parent / "pronunciation_report.json"
    hits_by_index: dict[int, list[dict]] = {}
    replacements_by_index: dict[int, list[dict]] = {}
    if pronunciation_path.is_file():
        report = json.loads(pronunciation_path.read_text(encoding="utf-8"))
        for line in report.get("lines") or []:
            index = int(line["index"])
            hits_by_index[index] = line.get("hits") or []
            replacements_by_index[index] = line.get("replacements") or []

    def normalize_aliases(text: str, replacements: list[dict]) -> str:
        """Map acoustic homophone aliases back to the original surface."""
        normalized = text
        for item in replacements:
            alias = str(item.get("alias") or "")
            matched = str(item.get("matched") or "")
            if alias and matched:
                normalized = normalized.replace(alias, matched)
        return normalized

    model = whisper.load_model(args.model)
    rows = []
    for line in manifest.get("lines") or []:
        audio = Path(line["file"])
        audio = audio if audio.is_absolute() else (root / audio)
        index = int(line.get("index") or 0)
        tts_text = line.get("tts_text") or line.get("text") or ""
        display_text = line.get("display_text") or line.get("subtitle_text") or tts_text
        acoustic_text = line.get("acoustic_text") or line.get("text") or tts_text
        replacements = replacements_by_index.get(index) or line.get("replacements") or []
        prompted = model.transcribe(
            # Prompt with the original tts_text, not the acoustic alias: this
            # asks whether the audio sounds like the intended words. Raw ASR
            # stays unanchored; pinyin comparison decides the verdict.
            str(audio), language="zh", fp16=False, initial_prompt=tts_text,
            condition_on_previous_text=False,
        )["text"].strip()
        raw = model.transcribe(str(audio), language="zh", fp16=False)["text"].strip()
        prompted_normalized = normalize_aliases(prompted, replacements)
        raw_normalized = normalize_aliases(raw, replacements)
        score = cer(tts_text, raw_normalized)
        prompted_score = cer(tts_text, prompted_normalized)
        alias_seen = [
            item for item in replacements
            if str(item.get("alias") or "") in raw or str(item.get("alias") or "") in prompted
        ]
        row = {
            "index": index,
            "expected": tts_text,
            "display_text": display_text,
            "acoustic_text": acoustic_text,
            "asr_prompted": prompted,
            "asr_raw": raw,
            "asr_prompted_normalized": prompted_normalized,
            "asr_raw_normalized": raw_normalized,
            "cer": score,
            "cer_prompted": prompted_score,
            "ok": score <= args.max_cer,
            "alias_replacements": replacements,
            "alias_seen_in_asr": [item.get("alias") for item in alias_seen],
            "lexicon_hits": hits_by_index.get(index, []),
            "parts": len(line.get("parts") or []),
            **levels(audio),
        }
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("index", "cer", "ok", "mean_db", "max_db")},
                         ensure_ascii=False))

    out = Path(args.out) if args.out else manifest_path.parent / "tts_qa.json"
    payload = {
        "asr": f"openai-whisper {args.model}, language=zh; CER uses raw ASR normalized by tts_alias",
        "manifest": str(manifest_path),
        "threshold_cer": args.max_cer,
        "lines": rows,
        "summary": {
            "lines": len(rows),
            "ok_lines": sum(1 for row in rows if row["ok"]),
            "max_cer": max((row["cer"] for row in rows), default=0.0),
            "hit_lines": sum(1 for row in rows if row["lexicon_hits"]),
            "alias_lines": sum(1 for row in rows if row["alias_replacements"]),
            "alias_seen_lines": sum(1 for row in rows if row["alias_seen_in_asr"]),
            "human_review": "PENDING",
        },
        "note": (
            "ASR 只能辅助发现漏字/错字；CER 先将 tts_alias 归一化回原词，"
            "因此同音替换不会被误计为发音错误。读音正确性仍需人工抽听。"
        ),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Pinyin-level verdict runs in the project venv, where pypinyin is installed;
    # Whisper stays in the CosyVoice runtime venv. Character CER is kept as a
    # secondary signal and must not fail a correct homophone.
    checker = ROOT / "scripts" / "asr_pinyin_check.py"
    project_python = ROOT / ".venv" / "Scripts" / "python.exe"
    pinyin_ok = None
    if checker.is_file() and project_python.is_file():
        # The parent process is the CosyVoice venv (Python 3.10); its
        # PYTHONPATH/PYTHONHOME would poison the 3.12 project venv. -I makes
        # the checker isolated and use only its own site-packages.
        env = {key: value for key, value in os.environ.items()
               if key not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP")}
        proc = subprocess.run(
            [str(project_python), "-I", str(checker), "--qa", str(out),
             "--threshold", str(args.max_cer)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env,
        )
        pinyin_ok = proc.returncode == 0
        print(json.dumps({"pinyin_checker_rc": proc.returncode,
                          "pinyin_checker_stderr": proc.stderr[-400:],
                          "qa": str(out)}, ensure_ascii=False))
        if proc.returncode not in (0, 1):
            payload["pinyin_check_error"] = proc.stderr[-800:]
        payload = json.loads(out.read_text(encoding="utf-8"))
    summary = payload["summary"]
    print(json.dumps({"report": str(out), **summary, "pinyin_pass": pinyin_ok},
                     ensure_ascii=False))
    if pinyin_ok is None:
        return 0 if summary["ok_lines"] == len(rows) else 1
    return 0 if pinyin_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
