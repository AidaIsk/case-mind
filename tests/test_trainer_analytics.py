# tests/test_trainer_analytics.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

from trainer.trainer_analytics import (
    summarize_trainer_runs,
    detect_score_trend,
    detect_trainer_weak_zone,
)
from trainer.trainer_cases import get_all_trainer_cases


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _run(case_id="TR-003", score=80, root_cause="NONE", correct=True):
    return {
        "run_id":              f"RUN-{score}",
        "trainer_case_id":    case_id,
        "saved_at":           "2025-01-01 10:00",
        "score":              score,
        "root_cause":         root_cause,
        "is_correct_decision": correct,
        "error_type":         "NONE" if root_cause == "NONE" else "WEAK_RATIONALE",
        "review":             {},
    }


CASES = get_all_trainer_cases()


# ---------------------------------------------------------------------------
# summarize_trainer_runs
# ---------------------------------------------------------------------------

def test_summary_total_runs():
    runs = [_run(score=70), _run(score=80), _run(score=90)]
    s = summarize_trainer_runs(runs, CASES)
    assert s["total_runs"] == 3
    print("PASS: test_summary_total_runs")


def test_summary_avg_score():
    runs = [_run(score=60), _run(score=80), _run(score=100)]
    s = summarize_trainer_runs(runs, CASES)
    assert s["avg_score"] == 80.0
    print("PASS: test_summary_avg_score")


def test_summary_correct_decision_rate():
    runs = [
        _run(correct=True),
        _run(correct=True),
        _run(correct=False),
        _run(correct=False),
    ]
    s = summarize_trainer_runs(runs, CASES)
    assert s["correct_decision_rate"] == 50.0
    print("PASS: test_summary_correct_decision_rate")


def test_summary_root_cause_distribution():
    runs = [
        _run(root_cause="NONE"),
        _run(root_cause="OVER_REJECT"),
        _run(root_cause="OVER_REJECT"),
        _run(root_cause="WEAK_DECISIVE_FACTOR"),
    ]
    s = summarize_trainer_runs(runs, CASES)
    dist = s["root_cause_distribution"]
    assert dist["OVER_REJECT"] == 2
    assert dist["NONE"] == 1
    assert dist["WEAK_DECISIVE_FACTOR"] == 1
    print("PASS: test_summary_root_cause_distribution")


def test_summary_theme_distribution():
    """Темы должны подтягиваться из trainer_cases."""
    runs = [
        _run(case_id="TR-003"),  # SoF
        _run(case_id="TR-003"),  # SoF
        _run(case_id="TR-007"),  # Adverse Media
    ]
    s = summarize_trainer_runs(runs, CASES)
    dist = s["theme_distribution"]
    assert dist.get("SoF", 0) == 2
    assert dist.get("Adverse Media", 0) == 1
    print("PASS: test_summary_theme_distribution")


def test_summary_empty_runs():
    """Пустая история не должна ломать функцию."""
    s = summarize_trainer_runs([], CASES)
    assert s["total_runs"] == 0
    assert s["avg_score"] == 0.0
    assert "weak_zone" in s
    print("PASS: test_summary_empty_runs")


# ---------------------------------------------------------------------------
# detect_score_trend
# ---------------------------------------------------------------------------

def test_trend_improving():
    runs = (
        [_run(score=50)] * 5 +
        [_run(score=80)] * 5
    )
    assert detect_score_trend(runs) == "improving"
    print("PASS: test_trend_improving")


def test_trend_declining():
    runs = (
        [_run(score=80)] * 5 +
        [_run(score=50)] * 5
    )
    assert detect_score_trend(runs) == "declining"
    print("PASS: test_trend_declining")


def test_trend_stable():
    runs = [_run(score=70)] * 10
    assert detect_score_trend(runs) == "stable"
    print("PASS: test_trend_stable")


def test_trend_not_enough_data():
    runs = [_run(score=70)] * 7  # меньше двух окон по 5
    assert detect_score_trend(runs) == "not_enough_data"
    print("PASS: test_trend_not_enough_data")


# ---------------------------------------------------------------------------
# detect_trainer_weak_zone
# ---------------------------------------------------------------------------

def test_weak_zone_identifies_dominant_root_cause():
    """Самая частая ошибка должна попасть в диагноз."""
    runs = [
        _run(root_cause="WEAK_DECISIVE_FACTOR", correct=False),
        _run(root_cause="WEAK_DECISIVE_FACTOR", correct=False),
        _run(root_cause="WEAK_DECISIVE_FACTOR", correct=False),
        _run(root_cause="OVER_REJECT",           correct=False),
        _run(root_cause="NONE",                  correct=True),
    ]
    result = detect_trainer_weak_zone(runs, CASES)
    assert "decisive factor" in result.lower() or "weak_decisive_factor" in result.lower()
    print(f"PASS: test_weak_zone_identifies_dominant_root_cause — '{result}'")


def test_weak_zone_links_to_theme():
    """Диагноз должен содержать тему кейса при достаточном количестве данных."""
    # TR-003 имеет theme="SoF"
    runs = [
        _run(case_id="TR-003", root_cause="MISSED_SOF_GAP", correct=False),
        _run(case_id="TR-003", root_cause="MISSED_SOF_GAP", correct=False),
        _run(case_id="TR-003", root_cause="MISSED_SOF_GAP", correct=False),
    ]
    result = detect_trainer_weak_zone(runs, CASES)
    assert "SoF" in result or "sof" in result.lower()
    print(f"PASS: test_weak_zone_links_to_theme — '{result}'")


def test_weak_zone_empty_runs():
    """Пустая история возвращает строку, не падает."""
    result = detect_trainer_weak_zone([], CASES)
    assert isinstance(result, str) and len(result) > 0
    print(f"PASS: test_weak_zone_empty_runs — '{result}'")


def test_weak_zone_all_correct():
    """Если все прогоны без ошибок — сообщение об отсутствии слабых зон."""
    runs = [_run(root_cause="NONE", correct=True) for _ in range(5)]
    result = detect_trainer_weak_zone(runs, CASES)
    assert "не выявлено" in result.lower() or "без ошибок" in result.lower()
    print(f"PASS: test_weak_zone_all_correct — '{result}'")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== TRAINER ANALYTICS TESTS (Stage 3B) ===\n")

    print("--- summarize_trainer_runs ---")
    test_summary_total_runs()
    test_summary_avg_score()
    test_summary_correct_decision_rate()
    test_summary_root_cause_distribution()
    test_summary_theme_distribution()
    test_summary_empty_runs()

    print("\n--- detect_score_trend ---")
    test_trend_improving()
    test_trend_declining()
    test_trend_stable()
    test_trend_not_enough_data()

    print("\n--- detect_trainer_weak_zone ---")
    test_weak_zone_identifies_dominant_root_cause()
    test_weak_zone_links_to_theme()
    test_weak_zone_empty_runs()
    test_weak_zone_all_correct()

    print("\nВсе тесты пройдены.\n")
