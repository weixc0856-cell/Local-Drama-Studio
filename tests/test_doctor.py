from drama_studio.doctor import FAIL, NOT_RUN, PASS_LIMITED, PASS_VERIFIED, Check, summarize


def test_summarize_counts_and_required_failure() -> None:
    checks = [
        Check("a", "A", PASS_VERIFIED, "", required=True),
        Check("b", "B", PASS_LIMITED, "", required=False),
        Check("c", "C", NOT_RUN, "", required=False),
        Check("d", "D", FAIL, "", required=True),
    ]
    summary = summarize(checks)
    assert summary["counts"] == {PASS_VERIFIED: 1, PASS_LIMITED: 1, FAIL: 1, NOT_RUN: 1}
    assert summary["required_failed"] == ["d"]
    assert summary["ok"] is False


def test_optional_failure_does_not_fail_summary() -> None:
    summary = summarize([Check("x", "X", FAIL, "", required=False)])
    assert summary["ok"] is True
