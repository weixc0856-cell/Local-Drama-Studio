from __future__ import annotations

import argparse
import atexit
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drama_studio.config import load_settings
from literary_intelligence.harness.claims import load_claims
from literary_intelligence.harness.evidence_validator import validate_claim
from literary_intelligence.harness.llm_client import OpenAICompatibleLLMClient
from literary_intelligence.harness.pipeline import PASS_ORDER, RoleContractError, build_context, check_role_contracts
from literary_intelligence.harness.source_registry import load_source_registry


SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "llm_server.ps1"


def _server_root(base_url: str) -> str:
    return base_url.rstrip("/").removesuffix("/v1")


def _is_local(base_url: str) -> bool:
    host = (urlparse(base_url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _llm_healthy(base_url: str) -> bool:
    import httpx

    try:
        r = httpx.get(f"{_server_root(base_url)}/health", timeout=2.0, trust_env=False)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def _server_script(action: str) -> int:
    """Start/stop the project-owned llama-server; never touches a foreign process."""
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(SERVER_SCRIPT), "-Action", action],
        check=False,
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True, help="corpus directory containing source_registry.json")
    parser.add_argument("--out", default="literary_intelligence/runs/li15")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--no-manage-server", action="store_true",
                        help="do not start/stop the project llama-server around this run")
    args = parser.parse_args()

    settings = load_settings()
    base_url = args.base_url or settings.llm.base_url
    model = args.model or settings.llm.model

    # Start the local server only when it is down; stop it afterwards only when this run
    # started it. A foreign instance (another project / the daily task) is left alone.
    manage_server = not args.no_manage_server and _is_local(base_url)
    if manage_server and not _llm_healthy(base_url):
        if _server_script("start") == 0:
            atexit.register(_server_script, "stop")
    corpus = Path(args.corpus)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    registry = load_source_registry(corpus / "source_registry.json")
    claims = load_claims(corpus / "claims.json")
    client = OpenAICompatibleLLMClient(
        base_url=base_url,
        model=model,
        api_key=settings.llm.api_key,
        timeout_s=args.timeout,
        max_tokens=args.max_tokens,
    )
    context = build_context(registry, claims)
    started = datetime.now(timezone.utc).isoformat()
    passes = []
    all_valid = True
    current_candidates = []
    for pass_name in PASS_ORDER:
        t0 = time.perf_counter()
        record = {"pass_name": pass_name, "status": "NOT_RUN", "elapsed_s": None}
        try:
            output = client.complete(pass_name, context)
            elapsed = round(time.perf_counter() - t0, 1)
            validations = {}
            for claim in output.claims:
                validation = validate_claim(claim, registry)
                validations[claim.claim_id] = {
                    "ok": validation.ok,
                    "codes": validation.codes,
                }
                all_valid = all_valid and validation.ok
            check_role_contracts(
                pass_name, output, context["target"], claims,
                {c.claim_id for c in current_candidates},
            )
            if pass_name in {"text_analyst", "literary_analyst"}:
                current_candidates.extend(
                    c for c in output.claims if validations[c.claim_id]["ok"]
                )
                context["current_claims"] = [c.model_dump() for c in current_candidates]
                context["current_claim_ids"] = [c.claim_id for c in current_candidates]
            record.update({
                "status": "PASS_VERIFIED",
                "elapsed_s": elapsed,
                "is_mock": output.is_mock,
                "notes": output.notes,
                "draft_text": output.draft_text,
                "coverage": output.coverage,
                "coverage_reason": output.coverage_reason,
                "research_status": output.research_status,
                "skeptic_verdict": output.skeptic_verdict,
                "reviewed_claim_ids": output.reviewed_claim_ids,
                "reviewed_dimensions": output.reviewed_dimensions,
                "skeptic_findings": [f.model_dump() for f in output.skeptic_findings],
                "claims": [c.model_dump() for c in output.claims],
                "validations": validations,
                "raw_response": output.raw_response,
            })
            record["fatal_role_error"] = False
        except RoleContractError as exc:
            record.update({
                "status": "FAILED",
                "elapsed_s": round(time.perf_counter() - t0, 1),
                "error_type": type(exc).__name__,
                "error_code": exc.code,
                "error": str(exc),
                "fatal_role_error": True,
            })
            all_valid = False
        except Exception as exc:  # preserve a failure record instead of losing the run
            record.update({
                "status": "FAILED",
                "elapsed_s": round(time.perf_counter() - t0, 1),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            all_valid = False
        passes.append(record)
        (out / f"{pass_name}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(pass_name, record["status"], record.get("elapsed_s"), flush=True)
        if record.get("fatal_role_error"):
            break

    manifest = {
        "run_type": "LI-1.6-D real local LLM",
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "model": model,
        "model_path": getattr(settings.llm, "model_path", None),
        "context_size": getattr(settings.llm, "context_size", None),
        "server": {"host": "127.0.0.1", "port": (urlparse(base_url).port or 8080), "ngl": 0, "reasoning": "off"},
        "max_tokens": args.max_tokens,
        "timeout_s": args.timeout,
        "source_ids": sorted(registry.sources),
        "registered_claim_ids": [c.claim_id for c in claims],
        "passes": passes,
        "all_evidence_valid": all_valid,
        "human_review": "NOT_RUN",
        "note": "Raw model output; not approved. Failures are preserved.",
    }
    (out / "real_pipeline.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", out / "real_pipeline.json")
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
