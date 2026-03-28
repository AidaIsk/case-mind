# test_learning.py

from learning import extract_learning_signal, aggregate_errors, detect_weak_zone, summarize


# ---------------------------------------------------------------------------
# Вспомогательные фабрики
# ---------------------------------------------------------------------------

def _make_output(
    error_type="NONE",
    confidence_score=4,
    decision_mode="reject",
    risk_level="Высокий",
) -> dict:
    """Минимальный structured output для тестов learning-модуля."""
    return {
        "error_type":       error_type,
        "confidence_score": confidence_score,
        "decision_mode":    decision_mode,
        "risk_level":       risk_level,
        # остальные поля не нужны learning-модулю
    }


# ---------------------------------------------------------------------------
# extract_learning_signal
# ---------------------------------------------------------------------------

def test_extract_returns_correct_fields():
    output = _make_output(
        error_type="WEAK_RATIONALE",
        confidence_score=3,
        decision_mode="edd",
        risk_level="Средний",
    )
    signal = extract_learning_signal(output)

    assert signal["error_type"]       == "WEAK_RATIONALE"
    assert signal["confidence_score"] == 3
    assert signal["decision_mode"]    == "edd"
    assert signal["risk_level"]       == "Средний"
    print("PASS: test_extract_returns_correct_fields")


def test_extract_defaults_on_missing_fields():
    signal = extract_learning_signal({})
    assert signal["error_type"]       == "NONE"
    assert signal["confidence_score"] == 0
    assert signal["decision_mode"]    == "unknown"
    assert signal["risk_level"]       == "unknown"
    print("PASS: test_extract_defaults_on_missing_fields")


# ---------------------------------------------------------------------------
# aggregate_errors — подсчёт корректен
# ---------------------------------------------------------------------------

def test_aggregate_empty_list():
    stats = aggregate_errors([])
    assert stats["total_cases"]    == 0
    assert stats["error_rate"]     == 0.0
    assert stats["avg_confidence"] == 0.0
    assert stats["by_mode"]        == {}
    print("PASS: test_aggregate_empty_list")


def test_aggregate_total_cases():
    outputs = [_make_output() for _ in range(7)]
    stats = aggregate_errors(outputs)
    assert stats["total_cases"] == 7
    print("PASS: test_aggregate_total_cases")


def test_aggregate_error_distribution():
    outputs = [
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="OVER_REJECT"),
        _make_output(error_type="MISSED_SIGNAL"),
    ]
    stats = aggregate_errors(outputs)

    # _all включает NONE
    assert stats["error_distribution_all"]["NONE"]           == 3
    assert stats["error_distribution_all"]["WEAK_RATIONALE"] == 2
    assert stats["error_distribution_all"]["OVER_REJECT"]    == 1
    assert stats["error_distribution_all"]["MISSED_SIGNAL"]  == 1

    # _errors — только ошибочные, NONE отсутствует
    assert "NONE" not in stats["error_distribution_errors"]
    assert stats["error_distribution_errors"]["WEAK_RATIONALE"] == 2
    assert stats["error_distribution_errors"]["OVER_REJECT"]    == 1
    assert stats["error_distribution_errors"]["MISSED_SIGNAL"]  == 1
    print("PASS: test_aggregate_error_distribution")


def test_aggregate_error_rate():
    outputs = [
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="OVER_REJECT"),
        _make_output(error_type="OVER_REJECT"),
        _make_output(error_type="OVER_REJECT"),
        _make_output(error_type="OVER_REJECT"),
    ]
    stats = aggregate_errors(outputs)
    # 6 ошибочных из 10 = 0.6
    assert stats["error_rate"] == 0.6
    print("PASS: test_aggregate_error_rate")


def test_aggregate_avg_confidence():
    outputs = [
        _make_output(confidence_score=2),
        _make_output(confidence_score=3),
        _make_output(confidence_score=4),
        _make_output(confidence_score=5),
    ]
    stats = aggregate_errors(outputs)
    # (2+3+4+5)/4 = 3.5
    assert stats["avg_confidence"] == 3.5
    print("PASS: test_aggregate_avg_confidence")


def test_aggregate_ignores_invalid_confidence_score():
    """confidence_score=0 (невалидный) не должен попадать в avg_confidence."""
    outputs = [
        _make_output(confidence_score=0),   # невалидный — из fallback/дефолт
        _make_output(confidence_score=4),
        _make_output(confidence_score=4),
    ]
    stats = aggregate_errors(outputs)
    # только 4 и 4 считаются → avg = 4.0, не (0+4+4)/3 = 2.67
    assert stats["avg_confidence"] == 4.0, (
        f"Ожидали 4.0, получили {stats['avg_confidence']} — "
        "confidence_score=0 не должен влиять на среднее"
    )
    print("PASS: test_aggregate_ignores_invalid_confidence_score")


def test_aggregate_by_mode_split():
    outputs = [
        _make_output(decision_mode="reject",  error_type="NONE",           confidence_score=4),
        _make_output(decision_mode="reject",  error_type="WEAK_RATIONALE", confidence_score=3),
        _make_output(decision_mode="reject",  error_type="OVER_REJECT",    confidence_score=2),
        _make_output(decision_mode="edd",     error_type="NONE",           confidence_score=5),
        _make_output(decision_mode="edd",     error_type="NONE",           confidence_score=4),
        _make_output(decision_mode="approve", error_type="NONE",           confidence_score=5),
    ]
    stats = aggregate_errors(outputs)

    assert stats["by_mode"]["reject"]["count"]  == 3
    assert stats["by_mode"]["edd"]["count"]     == 2
    assert stats["by_mode"]["approve"]["count"] == 1

    assert stats["by_mode"]["reject"]["error_distribution_errors"].get("WEAK_RATIONALE") == 1
    assert stats["by_mode"]["reject"]["error_distribution_errors"].get("OVER_REJECT")    == 1
    # avg для reject: (4+3+2)/3 = 3.0
    assert stats["by_mode"]["reject"]["avg_confidence"] == 3.0
    # avg для edd: (5+4)/2 = 4.5
    assert stats["by_mode"]["edd"]["avg_confidence"]    == 4.5
    print("PASS: test_aggregate_by_mode_split")


# ---------------------------------------------------------------------------
# detect_weak_zone — диагноз определяется корректно
# ---------------------------------------------------------------------------

def test_weak_zone_no_errors():
    outputs = [_make_output(error_type="NONE") for _ in range(5)]
    stats   = aggregate_errors(outputs)
    zone    = detect_weak_zone(stats)
    assert "не выявлено" in zone.lower() or "системных" in zone.lower()
    print("PASS: test_weak_zone_no_errors")


def test_weak_zone_dominant_weak_rationale():
    outputs = [
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="OVER_REJECT"),
    ]
    stats = aggregate_errors(outputs)
    zone  = detect_weak_zone(stats)
    # WEAK_RATIONALE = 4/5 ошибочных → доминирует
    assert "WEAK_RATIONALE" in zone or "слабое обоснование" in zone.lower()
    print("PASS: test_weak_zone_dominant_weak_rationale")


def test_weak_zone_dominant_over_reject():
    outputs = [
        _make_output(error_type="OVER_REJECT", decision_mode="reject"),
        _make_output(error_type="OVER_REJECT", decision_mode="reject"),
        _make_output(error_type="OVER_REJECT", decision_mode="reject"),
        _make_output(error_type="OVER_REJECT", decision_mode="reject"),
        _make_output(error_type="NONE"),
        _make_output(error_type="NONE"),
        _make_output(error_type="WEAK_RATIONALE"),
    ]
    stats = aggregate_errors(outputs)
    zone  = detect_weak_zone(stats)
    assert "over" in zone.lower() or "избыточн" in zone.lower()
    print("PASS: test_weak_zone_dominant_over_reject")


def test_weak_zone_low_confidence():
    outputs = [
        _make_output(error_type="NONE", confidence_score=1),
        _make_output(error_type="NONE", confidence_score=2),
        _make_output(error_type="NONE", confidence_score=2),
        _make_output(error_type="NONE", confidence_score=2),
    ]
    stats = aggregate_errors(outputs)
    zone  = detect_weak_zone(stats)
    assert "уверенност" in zone.lower()
    print("PASS: test_weak_zone_low_confidence")


def test_weak_zone_high_error_rate():
    outputs = [
        _make_output(error_type="WEAK_RATIONALE"),
        _make_output(error_type="MISSED_SIGNAL"),
        _make_output(error_type="CDD_LOGIC_GAP"),
        _make_output(error_type="NONE"),
        _make_output(error_type="INCONSISTENT_DECISION"),
    ]
    # ошибок 4 из 5 = 80% — но ни одна не доминирует
    stats = aggregate_errors(outputs)
    zone  = detect_weak_zone(stats)
    # должен сработать либо high error_rate, либо "равномерно"
    assert any(kw in zone.lower() for kw in ["процент", "аудит", "равномерно"])
    print("PASS: test_weak_zone_high_error_rate")


def test_weak_zone_empty():
    zone = detect_weak_zone({"total_cases": 0})
    assert "недостаточно" in zone.lower()
    print("PASS: test_weak_zone_empty")


# ---------------------------------------------------------------------------
# summarize — интеграционный тест: 10 кейсов → полная сводка
# ---------------------------------------------------------------------------

def test_summarize_ten_cases():
    outputs = [
        _make_output(error_type="NONE",           confidence_score=5, decision_mode="approve"),
        _make_output(error_type="NONE",           confidence_score=4, decision_mode="reject"),
        _make_output(error_type="NONE",           confidence_score=4, decision_mode="reject"),
        _make_output(error_type="WEAK_RATIONALE", confidence_score=3, decision_mode="edd"),
        _make_output(error_type="WEAK_RATIONALE", confidence_score=3, decision_mode="edd"),
        _make_output(error_type="WEAK_RATIONALE", confidence_score=2, decision_mode="edd"),
        _make_output(error_type="OVER_REJECT",    confidence_score=2, decision_mode="reject"),
        _make_output(error_type="MISSED_SIGNAL",  confidence_score=3, decision_mode="reject"),
        _make_output(error_type="NONE",           confidence_score=4, decision_mode="edd"),
        _make_output(error_type="WEAK_RATIONALE", confidence_score=2, decision_mode="edd"),
    ]

    summary = summarize(outputs)

    assert summary["total_cases"]        == 10
    assert summary["error_distribution_all"]["WEAK_RATIONALE"] == 4
    assert summary["error_distribution_all"]["NONE"]           == 4
    assert summary["error_distribution_all"]["OVER_REJECT"]    == 1
    assert summary["error_distribution_all"]["MISSED_SIGNAL"]  == 1
    assert "NONE" not in summary["error_distribution_errors"]
    assert summary["error_distribution_errors"]["WEAK_RATIONALE"] == 4
    # 6 ошибочных из 10
    assert summary["error_rate"]         == 0.6
    # avg: (5+4+4+3+3+2+2+3+4+2)/10 = 32/10 = 3.2
    assert summary["avg_confidence"]     == 3.2
    assert "weak_zone"                   in summary
    # WEAK_RATIONALE = 4/6 = 67% → доминирует → должна упоминаться
    assert "WEAK_RATIONALE" in summary["weak_zone"] or "слаб" in summary["weak_zone"].lower()

    print("PASS: test_summarize_ten_cases")
    print("\n--- Summary для 10 кейсов ---")
    print(f"  total_cases:    {summary['total_cases']}")
    print(f"  error_rate:     {summary['error_rate']*100:.0f}%")
    print(f"  avg_confidence: {summary['avg_confidence']}/5")
    print(f"  errors (all):   {summary['error_distribution_all']}")
    print(f"  errors only:    {summary['error_distribution_errors']}")
    print(f"  weak_zone:      {summary['weak_zone']}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== LEARNING MODULE TESTS ===\n")

    print("--- extract_learning_signal ---")
    test_extract_returns_correct_fields()
    test_extract_defaults_on_missing_fields()

    print("\n--- aggregate_errors ---")
    test_aggregate_empty_list()
    test_aggregate_total_cases()
    test_aggregate_error_distribution()
    test_aggregate_error_rate()
    test_aggregate_avg_confidence()
    test_aggregate_ignores_invalid_confidence_score()
    test_aggregate_by_mode_split()

    print("\n--- detect_weak_zone ---")
    test_weak_zone_no_errors()
    test_weak_zone_dominant_weak_rationale()
    test_weak_zone_dominant_over_reject()
    test_weak_zone_low_confidence()
    test_weak_zone_high_error_rate()
    test_weak_zone_empty()

    print("\n--- summarize (10 кейсов) ---")
    test_summarize_ten_cases()

    print("\nВсе тесты пройдены.\n")
