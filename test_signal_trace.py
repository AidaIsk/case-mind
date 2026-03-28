# test_signal_trace.py

from output_schema import validate_output_structure, build_fallback_output
from renderers import render_decision_note


# ---------------------------------------------------------------------------
# Базовый валидный output
# ---------------------------------------------------------------------------

def _valid_signal(
    signal="Источник средств по операции не подтверждён.",
    category="SOF",
    impact="DECISIVE",
    direction="SUPPORTS_ESCALATION",
    comment="SoF является обязательным элементом CDD.",
) -> dict:
    return {
        "signal": signal,
        "category": category,
        "impact": impact,
        "direction": direction,
        "comment": comment,
    }


def _base_output(**overrides) -> dict:
    base = {
        "decision_mode":      "edd",
        "decision":           "Эскалация",
        "edd_required":       "Да",
        "cdd_status":         "Incomplete",
        "risk_level":         "Средний",
        "reject_reason_type": "NONE",
        "decision_summary":   "CDD не завершён. Запрошен EDD.",
        "case_overview":      "Клиент: Test Corp.",
        "key_risk_factors":   ["SoF не подтверждён"],
        "cdd_assessment": {
            "confirmed":     ["Идентификация и UBO"],
            "not_confirmed": ["SoF"],
            "conclusion":    "CDD не завершён.",
        },
        "analysis":           "Пробел по SoF закрываем через EDD.",
        "decisive_factor":    "Источник средств по операции не подтверждён.",
        "decision_rationale": "На текущем этапе кейс не может быть одобрен. Требуется EDD.",
        "required_actions":   ["Запросить подтверждение SoF"],
        "error_type":         "NONE",
        "confidence_score":   4,
        "self_review": {
            "summary":        "Решение защищаемо.",
            "main_gap":       "Существенных аналитических пробелов не выявлено.",
            "what_to_recheck": ["SoF"],
        },
        "signal_trace": [
            _valid_signal(),
            _valid_signal(
                signal="Подтверждающие документы предоставлены частично.",
                category="CDD",
                impact="MEDIUM",
                direction="SUPPORTS_ESCALATION",
                comment="Документация закрываема через EDD.",
            ),
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# a) Schema — форма
# ---------------------------------------------------------------------------

def test_schema_rejects_missing_signal_trace():
    output = _base_output()
    del output["signal_trace"]
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("signal_trace" in e for e in errors)
    print("PASS: test_schema_rejects_missing_signal_trace")


def test_schema_rejects_empty_signal_trace():
    output = _base_output(signal_trace=[])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("signal_trace" in e for e in errors)
    print("PASS: test_schema_rejects_empty_signal_trace")


def test_schema_rejects_signal_trace_over_limit():
    output = _base_output(signal_trace=[_valid_signal() for _ in range(7)])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("signal_trace" in e and "6" in e for e in errors)
    print("PASS: test_schema_rejects_signal_trace_over_limit")


def test_schema_rejects_invalid_category():
    sig = _valid_signal(category="INVALID_CAT")
    output = _base_output(signal_trace=[sig, _valid_signal(impact="HIGH", direction="SUPPORTS_ESCALATION")])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("category" in e for e in errors)
    print("PASS: test_schema_rejects_invalid_category")


def test_schema_rejects_invalid_impact():
    sig = _valid_signal(impact="CRITICAL")
    output = _base_output(signal_trace=[sig, _valid_signal()])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("impact" in e for e in errors)
    print("PASS: test_schema_rejects_invalid_impact")


def test_schema_rejects_invalid_direction():
    sig = _valid_signal(direction="BLOCKS")
    output = _base_output(signal_trace=[sig, _valid_signal(impact="HIGH", direction="SUPPORTS_ESCALATION")])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("direction" in e for e in errors)
    print("PASS: test_schema_rejects_invalid_direction")


def test_schema_rejects_missing_field_in_signal():
    sig = {"signal": "Тест", "category": "CDD", "impact": "DECISIVE"}  # нет direction и comment
    sig2 = {"signal": "Второй.", "category": "SOF", "impact": "HIGH",
            "direction": "SUPPORTS_ESCALATION", "comment": "OK"}
    output = _base_output(signal_trace=[sig, sig2])
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("direction" in e or "comment" in e for e in errors)
    print("PASS: test_schema_rejects_missing_field_in_signal")


# ---------------------------------------------------------------------------
# b) Logic — смысловые проверки
# ---------------------------------------------------------------------------

def test_logic_rejects_no_decisive_signal():
    """Нет ни одного DECISIVE сигнала → fail."""
    trace = [
        _valid_signal(impact="HIGH", direction="SUPPORTS_ESCALATION"),
        _valid_signal(signal="Документы частично предоставлены.", impact="MEDIUM",
                      direction="SUPPORTS_ESCALATION", category="CDD"),
    ]
    output = _base_output(signal_trace=trace)
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("DECISIVE" in e for e in errors)
    print("PASS: test_logic_rejects_no_decisive_signal")


def test_logic_rejects_decisive_factor_mismatch():
    """decisive_factor не совпадает по смыслу с DECISIVE сигналом → fail."""
    trace = [
        _valid_signal(
            signal="UBO не установлен и не может быть подтверждён.",
            category="CDD", impact="DECISIVE", direction="SUPPORTS_REJECT",
            comment="Завершение CDD невозможно.",
        ),
    ]
    output = _base_output(
        decision_mode="reject",
        decision="Отказать",
        edd_required="Нет",
        cdd_status="Incomplete and cannot be completed",
        reject_reason_type="CDD_FAILURE",
        decisive_factor="Негативные публикации не сняты.",  # не совпадает
        signal_trace=trace,
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("decisive_factor" in e.lower() or "decisive" in e.lower() for e in errors)
    print("PASS: test_logic_rejects_decisive_factor_mismatch")


def test_logic_rejects_approve_with_supports_reject_signal():
    """Approve + SUPPORTS_REJECT сигнал → fail."""
    trace = [
        _valid_signal(
            signal="Ключевые элементы CDD подтверждены.",
            category="CDD", impact="DECISIVE", direction="SUPPORTS_DECISION",
            comment="CDD завершён.",
        ),
        _valid_signal(
            signal="Выявлена высокорисковая география.",
            category="GEOGRAPHY", impact="HIGH", direction="SUPPORTS_REJECT",
            comment="Требует внимания.",
        ),
    ]
    output = _base_output(
        decision_mode="approve",
        decision="Одобрить",
        edd_required="Нет",
        cdd_status="Complete",
        reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены.",
        signal_trace=trace,
        error_type="NONE",
        confidence_score=4,
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("SUPPORTS_REJECT" in e for e in errors)
    print("PASS: test_logic_rejects_approve_with_supports_reject_signal")


def test_logic_rejects_edd_with_impossible_cdd_signal():
    """EDD + сигнал 'невозможно завершить' → fail."""
    trace = [
        _valid_signal(
            signal="SoF не подтверждён.",
            category="SOF", impact="HIGH", direction="SUPPORTS_ESCALATION",
            comment="Пробел закрываем.",
        ),
        _valid_signal(
            signal="CDD невозможно завершить ввиду структуры владения.",
            category="CDD", impact="DECISIVE", direction="SUPPORTS_ESCALATION",
            comment="Завершение невозможно.",
        ),
    ]
    output = _base_output(
        decisive_factor="SoF не подтверждён.",
        signal_trace=trace,
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("невозможн" in e.lower() or "EDD" in e for e in errors)
    print("PASS: test_logic_rejects_edd_with_impossible_cdd_signal")


def test_logic_valid_edd_signal_trace():
    """Корректный EDD signal_trace → pass."""
    trace = [
        _valid_signal(
            signal="Источник средств по операции не подтверждён.",
            category="SOF", impact="DECISIVE", direction="SUPPORTS_ESCALATION",
            comment="SoF закрываем через EDD.",
        ),
        _valid_signal(
            signal="Документы предоставлены частично.",
            category="CDD", impact="MEDIUM", direction="SUPPORTS_ESCALATION",
            comment="Закрываемый пробел.",
        ),
    ]
    output = _base_output(
        decisive_factor="Источник средств по операции не подтверждён.",
        signal_trace=trace,
    )
    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали pass для валидного EDD, получили: {errors}"
    print("PASS: test_logic_valid_edd_signal_trace")


def test_logic_valid_reject_risk_unacceptable_signal_trace():
    """Корректный Reject/RISK_UNACCEPTABLE signal_trace → pass."""
    trace = [
        _valid_signal(
            signal="Негативные публикации о возможной вовлечённости не сняты.",
            category="SCREENING", impact="DECISIVE", direction="SUPPORTS_REJECT",
            comment="Риск-сигнал не устранён.",
        ),
        _valid_signal(
            signal="Репутационные риски не снижены до приемлемого уровня.",
            category="SCREENING", impact="HIGH", direction="SUPPORTS_REJECT",
            comment="Совокупность публикаций формирует неприемлемый риск.",
        ),
    ]
    output = _base_output(
        decision_mode="reject",
        decision="Отказать",
        edd_required="Нет",
        cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Негативные публикации о возможной вовлечённости не сняты.",
        signal_trace=trace,
        error_type="NONE",
        confidence_score=4,
    )
    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали pass для валидного RISK_UNACCEPTABLE, получили: {errors}"
    print("PASS: test_logic_valid_reject_risk_unacceptable_signal_trace")


# ---------------------------------------------------------------------------
# c) Render — ## Signal Trace в ноте
# ---------------------------------------------------------------------------

def test_renderer_includes_signal_trace_section():
    """Все три режима должны содержать ## Signal Trace."""
    modes = [
        _base_output(),  # EDD
        _base_output(
            decision_mode="reject", decision="Отказать",
            edd_required="Нет", cdd_status="Incomplete and cannot be completed",
            reject_reason_type="CDD_FAILURE",
            decisive_factor="Источник средств по операции не подтверждён.",
            signal_trace=[_valid_signal(direction="SUPPORTS_REJECT")],
            confidence_score=4,
        ),
        _base_output(
            decision_mode="approve", decision="Одобрить",
            edd_required="Нет", cdd_status="Complete",
            reject_reason_type="NONE",
            decisive_factor="Ключевые элементы CDD подтверждены.",
            signal_trace=[
                _valid_signal(
                    signal="Ключевые элементы CDD подтверждены.",
                    category="CDD", impact="DECISIVE", direction="SUPPORTS_DECISION",
                    comment="CDD завершён.",
                )
            ],
            confidence_score=5,
        ),
    ]
    for output in modes:
        note = render_decision_note(output)
        mode = output["decision_mode"]
        assert "## Signal Trace" in note, f"Нет ## Signal Trace для {mode}"
        # Проверяем что хотя бы один сигнал отображается
        first_signal = output["signal_trace"][0]["signal"]
        assert first_signal in note, f"Текст сигнала не отображается для {mode}"
    print("PASS: test_renderer_includes_signal_trace_section")


def test_renderer_shows_impact_labels():
    """Рендерер должен показывать метки DECISIVE/HIGH/MEDIUM/LOW."""
    output = _base_output()
    note = render_decision_note(output)
    assert "[DECISIVE]" in note
    assert "[MEDIUM]" in note
    print("PASS: test_renderer_shows_impact_labels")


# ---------------------------------------------------------------------------
# d) Fallback
# ---------------------------------------------------------------------------

def test_fallback_always_contains_signal_trace():
    """build_fallback_output() всегда должен содержать signal_trace."""
    for recommendation in ["Отказать", "Одобрить", "Эскалация"]:
        case_data = {
            "recommendation":      recommendation,
            "selected_risk_level": "Средний",
            "client_name":         "Test",
            "case_type":           "Onboarding",
        }
        result = build_fallback_output(case_data, "test error")

        assert "signal_trace" in result, (
            f"signal_trace отсутствует в fallback для {recommendation}"
        )
        st = result["signal_trace"]
        assert isinstance(st, list) and len(st) > 0, (
            f"signal_trace пустой в fallback для {recommendation}"
        )
        # Должен быть DECISIVE сигнал
        decisive = [s for s in st if s.get("impact") == "DECISIVE"]
        assert decisive, f"Нет DECISIVE сигнала в fallback для {recommendation}"
    print("PASS: test_fallback_always_contains_signal_trace")


def test_fallback_passes_schema_validation():
    """Fallback output должен проходить schema validation."""
    case_data = {
        "recommendation":      "Эскалация",
        "selected_risk_level": "Средний",
        "client_name":         "Test Corp",
        "case_type":           "Review",
    }
    result = build_fallback_output(case_data, "LLM timeout")
    ok, errors = validate_output_structure(result)
    assert ok, f"Fallback не прошёл валидацию: {errors}"
    print("PASS: test_fallback_passes_schema_validation")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== SIGNAL TRACE TESTS ===\n")

    print("--- Schema ---")
    test_schema_rejects_missing_signal_trace()
    test_schema_rejects_empty_signal_trace()
    test_schema_rejects_signal_trace_over_limit()
    test_schema_rejects_invalid_category()
    test_schema_rejects_invalid_impact()
    test_schema_rejects_invalid_direction()
    test_schema_rejects_missing_field_in_signal()

    print("\n--- Logic ---")
    test_logic_rejects_no_decisive_signal()
    test_logic_rejects_decisive_factor_mismatch()
    test_logic_rejects_approve_with_supports_reject_signal()
    test_logic_rejects_edd_with_impossible_cdd_signal()
    test_logic_valid_edd_signal_trace()
    test_logic_valid_reject_risk_unacceptable_signal_trace()

    print("\n--- Render ---")
    test_renderer_includes_signal_trace_section()
    test_renderer_shows_impact_labels()

    print("\n--- Fallback ---")
    test_fallback_always_contains_signal_trace()
    test_fallback_passes_schema_validation()

    print("\nВсе тесты пройдены.\n")