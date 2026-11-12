"""Pinyin-level ASR verification for homophone-substituted narration.

Run with the project ``.venv`` (it has ``pypinyin``); Whisper itself runs in the
CosyVoice runtime venv. ``tts_qa.py`` calls this script after writing its raw
ASR report.

Character CER punishes a correct homophone: Whisper may write 结石 when the
audio says 碣石. This script compares pinyin syllables with tones instead, so
jié shí == jié shí passes while the old jiē shí reading fails.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_CJK = re.compile(r"[㐀-鿿]")


class MissingDependencyError(RuntimeError):
    """Raised when the ASR post-processing toolchain is missing."""


def require_pypinyin() -> None:
    try:
        import pypinyin  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment guard
        raise MissingDependencyError(
            "缺少 pypinyin：请用项目 venv 执行 `uv sync`（或 `pip install pypinyin`）后再运行本脚本"
        ) from exc


def pinyin_cer(reference: str, hypothesis: str) -> tuple[float, list[str], list[str]]:
    from pypinyin import Style, lazy_pinyin

    # Pinyin comparison ignores punctuation and ASR symbols; only CJK matters.
    reference = "".join(_CJK.findall(reference))
    hypothesis = "".join(_CJK.findall(hypothesis))
    ref = [item for item in lazy_pinyin(reference, style=Style.TONE3,
                                        neutral_tone_with_five=True)]
    hyp = [item for item in lazy_pinyin(hypothesis, style=Style.TONE3,
                                        neutral_tone_with_five=True)]
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
    return round(rows[len(ref)][len(hyp)] / max(1, len(ref)), 3), ref, hyp


def main() -> int:
    require_pypinyin()
    parser = argparse.ArgumentParser(description="Pinyin-level ASR check")
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=0.15)
    args = parser.parse_args()

    data = json.loads(args.qa.read_text(encoding="utf-8"))
    rows = data.get("lines") or []
    if not rows:
        raise SystemExit("QA 输入没有行数据；请先运行 scripts/tts_qa.py 生成。")
    if not any((row.get("asr_raw") or row.get("asr_prompted")) for row in rows):
        raise SystemExit(
            "QA 输入缺少 ASR 文本（asr_raw / asr_prompted 全为空）；"
            "请先运行 scripts/tts_qa.py 生成 ASR 结果。")
    ok_lines = 0
    max_cer = 0.0
    for row in rows:
        reference = row.get("expected") or ""
        prompted = row.get("asr_prompted") or ""
        raw = row.get("asr_raw") or ""
        prompted_cer, ref_syllables, prompted_syllables = pinyin_cer(reference, prompted)
        raw_cer, _, raw_syllables = pinyin_cer(reference, raw)
        # Two independent decodes: a prompted pass can hallucinate on a long
        # whole-line clip, while the raw pass can be noisy. Either matching the
        # expected pinyin is evidence the audio is phonetically correct.
        if prompted_cer <= raw_cer:
            verdict, basis = prompted_cer, "prompted"
        else:
            verdict, basis = raw_cer, "raw"
        ok = verdict <= args.threshold
        row["pinyin_expected"] = ref_syllables
        row["pinyin_prompted"] = prompted_syllables
        row["pinyin_raw"] = raw_syllables
        row["pinyin_cer_prompted"] = prompted_cer
        row["pinyin_cer"] = verdict
        row["pinyin_verdict_basis"] = basis
        row["pinyin_cer_raw"] = raw_cer
        row["pinyin_ok"] = ok
        row["character_ok"] = bool(row.get("ok"))
        row["ok"] = ok
        ok_lines += 1 if ok else 0
        max_cer = max(max_cer, verdict)
        print(json.dumps({"index": row.get("index"), "pinyin_cer": prompted_cer,
                          "pinyin_cer_raw": raw_cer, "pinyin_ok": ok},
                         ensure_ascii=False))
    summary = data.setdefault("summary", {})
    summary["character_ok_lines"] = summary.get("ok_lines")
    summary["ok_lines"] = ok_lines
    summary["ok_basis"] = "pinyin"
    summary["pinyin_ok_lines"] = ok_lines
    summary["max_pinyin_cer"] = round(max_cer, 3)
    summary["pinyin_threshold"] = args.threshold
    summary["pinyin_human_review"] = "PENDING"
    data["pinyin_check"] = (
        "pypinyin TONE3 syllable edit distance; prompted ASR is anchored on the "
        "original tts_text, raw ASR is unanchored. Homophones with the same tone "
        "pass; a wrong tone/initial/final fails."
    )
    args.qa.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(json.dumps({"ok_lines": ok_lines, "lines": len(rows),
                      "max_pinyin_cer": round(max_cer, 3)}, ensure_ascii=False))
    return 0 if ok_lines == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
