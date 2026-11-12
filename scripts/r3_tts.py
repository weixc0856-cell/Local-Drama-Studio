"""Parameterized narration TTS entry point.

All paths, speaker and speed are explicit; no episode directory is assumed.
The implementation lives in ``drama_studio.application.voice.tts`` so the workspace task
and this CLI share one code path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from drama_studio.domain.voice.recitation import RecitationError
from drama_studio.application.voice.tts import TTSError, synthesize_narration

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--narration", required=True, help="narration.json (lines + optional speaker/speed)")
    parser.add_argument("--out", required=True, help="directory for line_XX.wav files")
    parser.add_argument("--manifest", default=None, help="audio_manifest.json path (default: <out>/../audio_manifest.json)")
    parser.add_argument("--speaker", default=None, help="override CosyVoice preset speaker (SFT only)")
    parser.add_argument("--speed", type=float, default=None, help="override narration speed")
    parser.add_argument("--mode", default=None, help="narration / recitation / classical_recitation")
    parser.add_argument("--tts-mode", choices=("sft", "zero_shot"), default=None,
                        help="synthesis backend (default: config/audio.yaml tts.mode; default sft)")
    parser.add_argument("--voice-profile", default=None,
                        help="voice profile id (config/voices.yaml); per-line profiles still override")
    parser.add_argument("--voices", default=None, help="voice library path (default: config/voices.yaml)")
    parser.add_argument("--voice-cast", default=None, help="voice cast sidecar (YAML) mapping lines to profiles")
    parser.add_argument("--allow-unapproved-voices", action="store_true",
                        help="allow non-APPROVED profiles for auditions; never for production")
    parser.add_argument("--base-url", default=None, help="CosyVoice base URL (default: config/settings.yaml)")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--force", action="store_true", help="re-synthesize even when the manifest is valid")
    args = parser.parse_args()

    narration = Path(args.narration)
    out_dir = Path(args.out)
    manifest = Path(args.manifest) if args.manifest else out_dir.parent / "audio_manifest.json"
    try:
        result = synthesize_narration(
            narration,
            out_dir,
            manifest,
            root=ROOT,
            speaker=args.speaker,
            speed=args.speed,
            mode=args.mode,
            tts_mode=args.tts_mode,
            voice_profile=args.voice_profile,
            voices_path=Path(args.voices) if args.voices else None,
            voice_cast_path=Path(args.voice_cast) if args.voice_cast else None,
            require_approved_voices=not args.allow_unapproved_voices,
            base_url=args.base_url,
            force=args.force,
            timeout=args.timeout,
        )
    except RecitationError as exc:
        print(json.dumps({"ok": False, "capability": "unsupported_chant", "error": str(exc)},
                         ensure_ascii=False))
        return 3
    except TTSError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "manifest": str(result.manifest),
                "speaker": result.speaker,
                "speaker_id": result.speaker_id,
                "voice_profiles": list(result.voice_profiles),
                "voice_cast_sha256": result.voice_cast_sha256,
                "tts_mode": result.tts_mode,
                "model_class": result.model_class,
                "model_dir": result.model_dir,
                "speed": result.speed,
                "mode": result.mode,
                "pronunciation_report": str(result.pronunciation_report) if result.pronunciation_report else None,
                "lines": result.line_count,
                "total_seconds": result.total_seconds,
                "reused": result.reused,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
