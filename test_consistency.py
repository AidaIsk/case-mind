# test_consistency.py
#
# Тесты для validate_decision_consistency,
# validate_signal_strength_alignment,
# validate_decisive_factor_alignment
# и validation_report в fallback/output.

from output_schema import (
    validate_output_structure,
    validate_decision_consistency,
    validate_signal_strength_alignment,
    validate_decisive_factor_alignment,
    build_fallback_output,
)


# ---------------------------------------------------------------------------
# Базовый валидный output
# ---------------------------------------------------------------------------

def _sig(signal, category="SOF", impact="DECISIVE",
         direction="SUPPORTS_ESCALATION", comment="Тест."):
    return {"signal": signal, "category": category,
            "impact": impact, "direction": direction, "comment": comment}


def _base(**overrides):
    base = {
        "decision_mode":      "edd",
        "decision":           "Эскалация",
        "edd_required":       "Да",
        "cdd_status":         "Incomplete",
        "risk_level":         "Средний",
        "reject_reason_type": "NONE",
        "decision_summary":   "CDD не завершён.",
        "case_overview":      "Test Corp.",
        "key_risk_factors":   ["SoF не подтверждён"],
        "cdd_assessment": {
            "confirmed": ["UBO"], "not_confirmed": ["SoF"], "conclusion": "CDD не завершён.",
        },
        "analysis":           "SoF закрываем через EDD.",
        "decisive_factor":    "Источник средств по операции не подтверждён.",
        "decision_rationale": "Требуется EDD.",
        "required_actions":   ["Запросить SoF"],
        "error_type":         "NONE",
        "confidence_score":   4,
        "self_review": {
            "summary": "Решение защищаемо.", "main_gap": "Существенных аналитических пробелов не выявлено.",
            "what_to_recheck": ["SoF"],
        },
        "signal_trace": [
            _sig("Источник средств по операции не подтверждён.", "SOF", "DECISIVE", "SUPPORTS_ESCALATION"),
            _sig("Документы предоставлены частично.", "CDD", "MEDIUM", "SUPPORTS_ESCALATION"),
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Задача 1 — validate_decision_consistency
# ---------------------------------------------------------------------------

def test_consistency_reject_complete_cdd_without_risk_unacceptable():
    """Reject + cdd_status=Complete + CDD_FAILURE → нарушение."""
    output = _base(
        decision_mode="reject", decision="Отказать", edd_required="Нет",
        cdd_status="Complete", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен.",
        signal_trace=[_sig("UBO не установлен.", "CDD", "DECISIVE", "SUPPORTS_REJECT")],
    )
    issues = validate_decision_consistency(output)
    assert any("RISK_UNACCEPTABLE" in i for i in issues), f"Ожидали ошибку, получили: {issues}"
    print("PASS: test_consistency_reject_complete_cdd_without_risk_unacceptable")


def test_consistency_reject_complete_cdd_with_risk_unacceptable_ok():
    """Reject + cdd_status=Complete + RISK_UNACCEPTABLE → корректно."""
    output = _base(
        decision_mode="reject", decision="Отказать", edd_required="Нет",
        cdd_status="Complete but risk not acceptable", reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Негативные публикации не сняты.",
        signal_trace=[_sig("Негативные публикации не сняты.", "SCREENING", "DECISIVE", "SUPPORTS_REJECT")],
        error_type="NONE", confidence_score=4,
    )
    issues = validate_decision_consistency(output)
    assert not issues, f"Ожидали пустой список, получили: {issues}"
    print("PASS: test_consistency_reject_complete_cdd_with_risk_unacceptable_ok")


def test_consistency_edd_with_impossible_cdd_in_decisive():
    """EDD + 'невозможно завершить' в decisive_factor → нарушение."""
    output = _base(decisive_factor="CDD невозможно завершить ввиду структуры.")
    issues = validate_decision_consistency(output)
    assert any("EDD" in i for i in issues), f"Ожидали ошибку, получили: {issues}"
    print("PASS: test_consistency_edd_with_impossible_cdd_in_decisive")


def test_consistency_approve_with_high_reject_signal():
    """Approve + HIGH сигнал SUPPORTS_REJECT → нарушение."""
    output = _base(
        decision_mode="approve", decision="Одобрить", edd_required="Нет",
        cdd_status="Complete", reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены.",
        signal_trace=[
            _sig("CDD завершён.", "CDD", "DECISIVE", "SUPPORTS_DECISION"),
            _sig("Выявлена высокорисковая география.", "GEOGRAPHY", "HIGH", "SUPPORTS_REJECT"),
        ],
        error_type="NONE", confidence_score=4,
    )
    issues = validate_decision_consistency(output)
    assert any("SUPPORTS_REJECT" in i for i in issues), f"Ожидали ошибку, получили: {issues}"
    print("PASS: test_consistency_approve_with_high_reject_signal")


# ---------------------------------------------------------------------------
# Задача 2 — validate_signal_strength_alignment
# ---------------------------------------------------------------------------

def test_strength_decisive_reject_signal_in_approve():
    """DECISIVE + SUPPORTS_REJECT при Approve → нарушение."""
    output = _base(
        decision_mode="approve", decision="Одобрить", edd_required="Нет",
        cdd_status="Complete", reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены.",
        signal_trace=[
            _sig("CDD завершён.", "CDD", "DECISIVE", "SUPPORTS_DECISION"),
            _sig("Неснятые негативные публикации.", "SCREENING", "DECISIVE", "SUPPORTS_REJECT"),
        ],
        error_type="NONE", confidence_score=4,
    )
    issues = validate_signal_strength_alignment(output)
    assert any("DECISIVE" in i for i in issues), f"Ожидали ошибку, получили: {issues}"
    print("PASS: test_strength_decisive_reject_signal_in_approve")


def test_strength_all_low_medium_signals_but_reject():
    """Все сигналы LOW/MEDIUM при Reject → нарушение."""
    output = _base(
        decision_mode="reject", decision="Отказать", edd_required="Нет",
        cdd_status="Incomplete and cannot be completed", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен.",
        signal_trace=[
            _sig("Минорный риск географии.", "GEOGRAPHY", "LOW", "SUPPORTS_REJECT"),
            _sig("Документы частично.", "CDD", "MEDIUM", "SUPPORTS_ESCALATION"),
        ],
    )
    issues = validate_signal_strength_alignment(output)
    assert any("LOW/MEDIUM" in i or "all_low" in i.lower() or "все сигналы" in i.lower() for i in issues), \
        f"Ожидали ошибку про слабые сигналы, получили: {issues}"
    print("PASS: test_strength_all_low_medium_signals_but_reject")


def test_strength_valid_edd_signals():
    """Валидный EDD с корректными сигналами → pass."""
    output = _base()
    issues = validate_signal_strength_alignment(output)
    assert not issues, f"Ожидали пустой список, получили: {issues}"
    print("PASS: test_strength_valid_edd_signals")


# ---------------------------------------------------------------------------
# Задача 3 — validate_decisive_factor_alignment
# ---------------------------------------------------------------------------

def test_alignment_decisive_factor_matches_signal():
    """decisive_factor совпадает по смыслу с DECISIVE сигналом → pass."""
    output = _base()
    issues = validate_decisive_factor_alignment(output)
    assert not issues, f"Ожидали пустой список, получили: {issues}"
    print("PASS: test_alignment_decisive_factor_matches_signal")


def test_alignment_decisive_factor_no_match():
    """decisive_factor не совпадает ни с одним DECISIVE сигналом → warning."""
    output = _base(
        decisive_factor="Высокий уровень риска клиента.",  # нет совпадения с trace
        signal_trace=[
            _sig("Источник средств по операции не подтверждён.", "SOF", "DECISIVE", "SUPPORTS_ESCALATION"),
        ],
    )
    issues = validate_decisive_factor_alignment(output)
    assert issues, f"Ожидали предупреждение, получили пустой список"
    assert any("подтверждён" in i or "alignment" in i.lower() for i in issues)
    print("PASS: test_alignment_decisive_factor_no_match")


# ---------------------------------------------------------------------------
# Задача 4 — validation_report в output и fallback
# ---------------------------------------------------------------------------

def test_validation_report_present_in_valid_output():
    """После validate_output_structure в output появляется validation_report."""
    output = _base()
    ok, errors = validate_output_structure(output)
    assert "validation_report" in output, "validation_report отсутствует в output"
    vr = output["validation_report"]
    assert "passed" in vr
    assert "consistency_issues" in vr
    assert "strength_issues" in vr
    assert "alignment_issues" in vr
    assert "all_issues" in vr
    print("PASS: test_validation_report_present_in_valid_output")


def test_validation_report_passed_true_for_valid():
    """Валидный output → validation_report.passed = True."""
    output = _base()
    ok, _ = validate_output_structure(output)
    assert ok
    assert output["validation_report"]["passed"] is True
    print("PASS: test_validation_report_passed_true_for_valid")


def test_validation_report_in_fallback():
    """build_fallback_output всегда содержит validation_report."""
    for rec in ["Отказать", "Одобрить", "Эскалация"]:
        result = build_fallback_output(
            {"recommendation": rec, "selected_risk_level": "Средний",
             "client_name": "Test", "case_type": "Onboarding"},
            "test error",
        )
        assert "validation_report" in result, f"validation_report отсутствует в fallback для {rec}"
        vr = result["validation_report"]
        assert vr["passed"] is False
        assert vr["all_issues"]
    print("PASS: test_validation_report_in_fallback")


def test_validation_report_captures_consistency_issue():
    """Если consistency нарушена — validation_report фиксирует это в all_issues."""
    output = _base(decisive_factor="CDD невозможно завершить ввиду структуры.")
    validate_output_structure(output)
    vr = output["validation_report"]
    assert any("EDD" in i or "невозможно" in i for i in vr["all_issues"]), \
        f"Ожидали consistency issue в validation_report, получили: {vr}"
    print("PASS: test_validation_report_captures_consistency_issue")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== CONSISTENCY & VALIDATION REPORT TESTS ===\n")

    print("--- Задача 1: Decision Consistency ---")
    test_consistency_reject_complete_cdd_without_risk_unacceptable()
    test_consistency_reject_complete_cdd_with_risk_unacceptable_ok()
    test_consistency_edd_with_impossible_cdd_in_decisive()
    test_consistency_approve_with_high_reject_signal()

    print("\n--- Задача 2: Signal Strength Alignment ---")
    test_strength_decisive_reject_signal_in_approve()
    test_strength_all_low_medium_signals_but_reject()
    test_strength_valid_edd_signals()

    print("\n--- Задача 3: Decisive Factor Alignment ---")
    test_alignment_decisive_factor_matches_signal()
    test_alignment_decisive_factor_no_match()

    print("\n--- Задача 4: Validation Report ---")
    test_validation_report_present_in_valid_output()
    test_validation_report_passed_true_for_valid()
    test_validation_report_in_fallback()
    test_validation_report_captures_consistency_issue()

    print("\nВсе тесты пройдены.\n")