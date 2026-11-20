"""Tests for the Z-Image style vocabulary, mix experiments and the benchmark testbench CLI."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from drama_studio.domain.style.z_image_atlas import (
    DIMENSION_FIELDS,
    ZImagePromptCompiler,
    ZImageStyleAtlas,
    ZImageVocabulary,
    compile_style_mix,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "scripts" / "run_z_image_style_atlas.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("atlas_runner", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------- vocabulary
def test_vocabulary_covers_all_seven_dimensions():
    vocab = ZImageVocabulary()
    assert set(vocab.dimensions()) == set(DIMENSION_FIELDS)
    assert vocab.count() > 50
    for dim in vocab.dimensions():
        for entry_id, entry in vocab.entries(dim).items():
            assert entry.get("en"), f"{dim}:{entry_id} missing English phrase"
            assert entry.get("cn"), f"{dim}:{entry_id} missing Chinese gloss"


def test_vocabulary_resolve_and_errors():
    vocab = ZImageVocabulary()
    resolved = vocab.resolve("lighting:low_key_neon,composition:intimate_close_up")
    assert set(resolved) == {"lighting", "composition"}
    assert "neon" in resolved["lighting"]
    with pytest.raises(ValueError):
        vocab.resolve("lighting-low_key_neon")
    with pytest.raises(KeyError):
        vocab.resolve("lighting:does_not_exist")
    with pytest.raises(KeyError):
        vocab.get("not_a_dimension", "x")


def test_vocabulary_phrases_carry_no_tag_spam():
    vocab = ZImageVocabulary()
    for dim in vocab.dimensions():
        for entry_id, entry in vocab.entries(dim).items():
            low = entry["en"].lower()
            for tag in ZImagePromptCompiler.BANNED_TAGS:
                assert tag not in low, f"{dim}:{entry_id} contains banned tag '{tag}'"


# --------------------------------------------------------------------- compiler
def test_compiler_does_not_double_preposition():
    atlas = ZImageStyleAtlas()
    compiler = ZImagePromptCompiler()
    style = atlas.get_style("editorial_fashion")  # scene already starts with "beside"
    prompt = compiler.compile(style=style)
    assert "in beside" not in prompt
    assert "set in" not in prompt


def test_compiler_adds_preposition_when_missing():
    atlas = ZImageStyleAtlas()
    compiler = ZImagePromptCompiler()
    prompt = compiler.compile(style=atlas.get_style("editorial_fashion"),
                              scene="a quiet scholar's studio")
    assert ", in a quiet scholar's studio." in prompt


def test_compiler_keeps_terminal_period_and_quotes():
    compiler = ZImagePromptCompiler()
    style = ZImageStyleAtlas().get_style("swiss_style")
    prompt = compiler.compile(style=style, text_quote="STUDIO")
    assert prompt.endswith(".")
    assert '"STUDIO"' in prompt


def test_compiler_article_agreement():
    compiler = ZImagePromptCompiler()
    style = ZImageStyleAtlas().get_style("editorial_fashion")
    prompt = compiler.compile(style=style, medium_style="anamorphic cinema film still")
    assert prompt.startswith("An anamorphic")


# --------------------------------------------------------------------- mix
def test_mix_borrows_only_requested_dimensions():
    atlas = ZImageStyleAtlas()
    base = atlas.get_style("song_aesthetics")
    borrow = atlas.get_style("luxury_product")
    result = compile_style_mix(atlas, "song_aesthetics", "luxury_product",
                               ["lighting", "color_texture"])
    assert result["dimensions"]["lighting"] == borrow.dimensions.lighting
    assert result["dimensions"]["color_texture"] == borrow.dimensions.color_texture
    assert result["dimensions"]["medium_style"] == base.dimensions.medium_style
    assert result["dimensions"]["composition"] == base.dimensions.composition
    assert result["medium_conflict_warning"] is None
    assert borrow.dimensions.lighting.split(",")[0].lower() in result["prompt"].lower()


def test_mix_warns_when_medium_is_borrowed():
    atlas = ZImageStyleAtlas()
    result = compile_style_mix(atlas, "song_aesthetics", "stylized_3d_animation", ["medium_style"])
    assert result["medium_conflict_warning"]


def test_mix_rejects_unknown_dimension_and_style():
    atlas = ZImageStyleAtlas()
    with pytest.raises(ValueError):
        compile_style_mix(atlas, "song_aesthetics", "luxury_product", ["vibe"])
    with pytest.raises(KeyError):
        compile_style_mix(atlas, "no_such_style", "luxury_product", ["lighting"])


def test_mix_subject_override_and_text_quote():
    atlas = ZImageStyleAtlas()
    result = compile_style_mix(atlas, "song_aesthetics", "luxury_product", ["lighting"],
                               subject="a celadon tea bowl", text_quote="SONG")
    assert "a celadon tea bowl" in result["prompt"]
    assert '"SONG"' in result["prompt"]


# --------------------------------------------------------------------- testbench
def test_plan_recipe_mode_uses_native_prompt():
    runner = load_runner()
    atlas = ZImageStyleAtlas()

    class Args:
        styles = "editorial_fashion,chinese_ink_wash"
        mode = "recipe"
        all = False
        seeds = "42,2026"
        subject_key = "portrait"
        size = "square"
        limit = None

    plan = runner.build_plan(atlas, runner.ZImageBenchmarkSuite(atlas), Args)
    assert len(plan) == 4  # 2 styles x 2 seeds
    for job in plan:
        assert job["prompt"] == atlas.get_style(job["style_id"]).positive_prompt
        assert job["prompt_source"] == "recipe.positive_prompt"
        assert job["subject_key"] is None
        assert (job["width"], job["height"]) == (1024, 1024)
        assert job["steps"] == 8 and job["cfg"] == 1.0
        assert all(v is None for v in job["scores"].values()), "scores must never be pre-filled"
    assert len({runner.job_key(j) for j in plan}) == 4


def test_plan_controlled_mode_shares_one_subject():
    runner = load_runner()
    atlas = ZImageStyleAtlas()
    suite = runner.ZImageBenchmarkSuite(atlas)

    class Args:
        styles = "editorial_fashion,chinese_ink_wash,watercolor"
        mode = "controlled"
        all = False
        seeds = "42"
        subject_key = "portrait"
        size = "portrait"
        limit = None

    plan = runner.build_plan(atlas, suite, Args)
    canonical = suite.CANONICAL_SUBJECTS["portrait"]
    assert len(plan) == 3
    for job in plan:
        assert canonical in job["prompt"]
        assert job["subject_key"] == "portrait"
        assert (job["width"], job["height"]) == (768, 1360)


def test_plan_all_sweeps_every_registered_style():
    runner = load_runner()
    atlas = ZImageStyleAtlas()

    class Args:
        styles = None
        mode = "recipe"
        all = True
        seeds = "42"
        subject_key = "portrait"
        size = "square"
        limit = None

    plan = runner.build_plan(atlas, runner.ZImageBenchmarkSuite(atlas), Args)
    assert len(plan) == atlas.count()


def test_plan_rejects_unknown_style_id():
    runner = load_runner()
    atlas = ZImageStyleAtlas()

    class Args:
        styles = "definitely_not_a_style"
        mode = "recipe"
        all = False
        seeds = "42"
        subject_key = "portrait"
        size = "square"
        limit = None

    with pytest.raises(KeyError):
        runner.build_plan(atlas, runner.ZImageBenchmarkSuite(atlas), Args)


def test_connection_error_detection():
    runner = load_runner()
    assert runner.looks_like_connection_error(ConnectionRefusedError("[WinError 10061] refused"))
    assert runner.looks_like_connection_error(TimeoutError("timed out"))
    assert not runner.looks_like_connection_error(ValueError("bad prompt"))


def test_dry_run_cli_writes_manifest_report_and_unfilled_scores(tmp_path):
    run_dir = tmp_path / "dryrun"
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion,chinese_ink_wash", "--seeds", "42",
         "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((run_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["runs"]) == 2
    for r in manifest["runs"]:
        assert r["status"] == "DRY_RUN_VERIFIED"
        assert all(v is None for v in r["scores"].values())
    assert (run_dir / "Z_IMAGE_STYLE_BENCHMARK_REPORT.md").exists()
    csv_text = (run_dir / "scores.csv").read_text(encoding="utf-8-sig")
    assert "5/5" not in csv_text  # no fabricated rubric scores


def test_score_command_updates_manifest_and_report(tmp_path):
    run_dir = tmp_path / "scoring"
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "score", "--run-dir", str(run_dir),
         "--style", "editorial_fashion", "--mode", "recipe", "--seed", "42",
         "--distinctiveness", "5", "--purity", "4", "--detail", "4",
         "--composition", "5", "--usability", "5", "--notes", "clean editorial light"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    manifest = json.loads((run_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))
    entry = manifest["runs"][0]
    assert entry["scores"] == {"distinctiveness": 5, "purity": 4, "detail_quality": 4,
                              "composition": 5, "usability": 5}
    assert entry["notes"] == "clean editorial light"
    report = (run_dir / "Z_IMAGE_STYLE_BENCHMARK_REPORT.md").read_text(encoding="utf-8")
    assert "clean editorial light" in report
    assert "4.6" in report  # mean of 5,4,4,5,5


def test_score_command_rejects_unmatched_entry(tmp_path):
    run_dir = tmp_path / "nomatch"
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "score", "--run-dir", str(run_dir),
         "--style", "watercolor", "--purity", "3"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0


def _seed_scored_run(run_dir: Path):
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    subprocess.run(
        [sys.executable, str(RUNNER), "score", "--run-dir", str(run_dir),
         "--style", "editorial_fashion", "--purity", "3", "--notes", "keep me"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )


def test_rerun_without_resume_preserves_human_scores(tmp_path):
    run_dir = tmp_path / "preserve"
    _seed_scored_run(run_dir)
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    entry = json.loads((run_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))["runs"][0]
    assert entry["scores"]["purity"] == 3
    assert entry["notes"] == "keep me"


def test_fresh_flag_discards_previous_manifest(tmp_path):
    run_dir = tmp_path / "fresh"
    _seed_scored_run(run_dir)
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "chinese_ink_wash", "--dry-run", "--fresh", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    runs = json.loads((run_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))["runs"]
    assert [r["style_id"] for r in runs] == ["chinese_ink_wash"]
    assert all(v is None for v in runs[0]["scores"].values())


def test_score_import_roundtrip_and_validation(tmp_path):
    run_dir = tmp_path / "import"
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "editorial_fashion,chinese_ink_wash", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    csv_path = tmp_path / "review.csv"
    csv_path.write_text(
        "style_id,mode,seed,distinctiveness,purity,detail_quality,composition,usability,notes\n"
        "editorial_fashion,recipe,42,5,5,4,5,5,clean window light\n"
        "chinese_ink_wash,recipe,42,5,9,4,5,4,out of range purity is skipped\n"
        "not_a_style,recipe,42,5,5,5,5,5,no matching entry\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "score-import", "--run-dir", str(run_dir),
         "--csv", str(csv_path), "--reviewer", "tester"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert "no matching entry" in proc.stdout or "no matching" in proc.stdout
    runs = {r["style_id"]: r for r in
            json.loads((run_dir / "benchmark_manifest.json").read_text(encoding="utf-8"))["runs"]}
    assert runs["editorial_fashion"]["scores"]["detail_quality"] == 4
    assert runs["editorial_fashion"]["reviewer"] == "tester"
    # invalid 9 must be rejected, valid cells on the same row still applied
    assert runs["chinese_ink_wash"]["scores"]["purity"] is None
    assert runs["chinese_ink_wash"]["scores"]["distinctiveness"] == 5


def test_ink_wash_declares_grayscale_postprocess():
    """The blue-green prior on mountain subjects is chroma-only; delivery must include a pure-ink variant."""
    style = ZImageStyleAtlas().get_style("chinese_ink_wash")
    assert style.postprocess == "grayscale"


def test_grayscale_variant_removes_chroma(tmp_path):
    from PIL import Image
    runner = load_runner()
    src = tmp_path / "ink.png"
    im = Image.new("RGB", (32, 32))
    im.paste((90, 130, 160), (0, 0, 16, 32))   # blue-green leak
    im.paste((40, 40, 40), (16, 0, 32, 32))    # ink
    im.save(src)
    out = runner.save_grayscale_variant(src)
    assert out.exists() and out.name == "ink_MONO.png"
    mono = Image.open(out).convert("HSV")
    assert max(mono.getchannel("S").get_flattened_data()) == 0
    # luminance structure survives
    assert Image.open(out).convert("L").getpixel((4, 4)) != Image.open(out).convert("L").getpixel((24, 4))


def test_plan_carries_postprocess(tmp_path):
    runner = load_runner()
    atlas = ZImageStyleAtlas()

    class Args:
        styles = "chinese_ink_wash,editorial_fashion"
        mode = "recipe"
        all = False
        seeds = "42"
        subject_key = "portrait"
        size = "square"
        limit = None

    plan = {j["style_id"]: j for j in runner.build_plan(atlas, runner.ZImageBenchmarkSuite(atlas), Args)}
    assert plan["chinese_ink_wash"]["postprocess"] == "grayscale"
    assert plan["editorial_fashion"]["postprocess"] == ""


def test_report_flags_low_scoring_styles(tmp_path):
    run_dir = tmp_path / "flagged"
    subprocess.run(
        [sys.executable, str(RUNNER), "benchmark", "--mode", "recipe",
         "--styles", "swiss_style", "--dry-run", "--run-dir", str(run_dir)],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    subprocess.run(
        [sys.executable, str(RUNNER), "score", "--run-dir", str(run_dir),
         "--style", "swiss_style", "--usability", "2", "--notes", "garbled typography"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO_ROOT), check=True,
    )
    report = (run_dir / "Z_IMAGE_STYLE_BENCHMARK_REPORT.md").read_text(encoding="utf-8")
    assert "需要修订后才可用" in report
    assert "usability=2" in report
    assert "garbled typography" in report