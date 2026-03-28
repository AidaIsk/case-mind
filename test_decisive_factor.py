# test_decisive_factor.py

from output_schema import validate_output_structure, build_fallback_output
from renderers import render_decision_note


# ---------------------------------------------------------------------------
# Базовый валидный output — используется как основа для всех тестов
# ---------------------------------------------------------------------------

def _base_output(**overrides) -> dict:
    base = {
        "decision_mode": "reject",
        "decision": "Отказать",
        "edd_required": "Нет",
        "cdd_status": "Incomplete and cannot be completed",
        "risk_level": "Высокий",
        "reject_reason_type": "CDD_FAILURE",
        "decision_summary": "Тестовый кейс.",
        "case_overview": "Клиент: Test Corp.",
        "key_risk_factors": ["Фактор 1", "Фактор 2"],
        "cdd_assessment": {
            "confirmed": ["Идентификация"],
            "not_confirmed": ["UBO"],
            "conclusion": "CDD не завершён.",
        },
        "analysis": "Совокупность факторов формирует неуправляемый риск.",
        "decisive_factor": "Бенефициарный владелец не установлен и не может быть подтверждён.",
        "decision_rationale": "Клиент не может быть принят.",
        "required_actions": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# a) Schema validation
# ---------------------------------------------------------------------------

def test_schema_rejects_missing_decisive_factor():
    """Output без decisive_factor не должен проходить validate_output_structure."""
    output = _base_output()
    del output["decisive_factor"]

    ok, errors = validate_output_structure(output)

    assert not ok, "Ожидали ошибку валидации при отсутствии decisive_factor"
    assert any("decisive_factor" in e for e in errors), (
        f"Ожидали ошибку про decisive_factor, получили: {errors}"
    )
    print("PASS: test_schema_rejects_missing_decisive_factor")


def test_schema_rejects_empty_decisive_factor():
    """Output с пустым decisive_factor (только пробелы) не должен проходить валидацию."""
    output = _base_output(decisive_factor="   ")

    ok, errors = validate_output_structure(output)

    assert not ok, "Ожидали ошибку валидации при пустом decisive_factor"
    assert any("decisive_factor" in e for e in errors), (
        f"Ожидали ошибку про decisive_factor, получили: {errors}"
    )
    print("PASS: test_schema_rejects_empty_decisive_factor")


def test_schema_accepts_valid_decisive_factor():
    """Полный валидный output с заполненным decisive_factor должен проходить валидацию."""
    output = _base_output()

    ok, errors = validate_output_structure(output)

    assert ok, f"Ожидали успешную валидацию, получили ошибки: {errors}"
    print("PASS: test_schema_accepts_valid_decisive_factor")


# ---------------------------------------------------------------------------
# b) Fallback
# ---------------------------------------------------------------------------

def test_fallback_always_contains_decisive_factor():
    """build_fallback_output() всегда должен возвращать decisive_factor."""
    for recommendation in ["Отказать", "Одобрить", "Эскалация"]:
        case_data = {
            "recommendation": recommendation,
            "selected_risk_level": "Средний",
            "client_name": "Test",
            "case_type": "Onboarding",
        }
        result = build_fallback_output(case_data, "test error")

        assert "decisive_factor" in result, (
            f"decisive_factor отсутствует в fallback для recommendation={recommendation}"
        )
        assert result["decisive_factor"].strip(), (
            f"decisive_factor пустой в fallback для recommendation={recommendation}"
        )
    print("PASS: test_fallback_always_contains_decisive_factor")


# ---------------------------------------------------------------------------
# c) Renderer
# ---------------------------------------------------------------------------

def test_renderer_includes_decisive_factor_section():
    """Итоговый note должен содержать секцию ## Decisive Factor для всех трёх режимов."""
    modes = [
        _base_output(
            decision_mode="reject",
            decisive_factor="Бенефициарный владелец не установлен.",
        ),
        _base_output(
            decision_mode="edd",
            decision="Эскалация",
            edd_required="Да",
            cdd_status="Incomplete",
            reject_reason_type="NONE",
            decisive_factor="Источник средств по операции не подтверждён.",
        ),
        _base_output(
            decision_mode="approve",
            decision="Одобрить",
            edd_required="Нет",
            cdd_status="Complete",
            reject_reason_type="NONE",
            decisive_factor="Ключевые элементы CDD подтверждены, существенные blockers не выявлены.",
        ),
    ]

    for output in modes:
        note = render_decision_note(output)
        assert "## Decisive Factor" in note, (
            f"Секция '## Decisive Factor' не найдена в note для режима {output['decision_mode']}"
        )
        assert output["decisive_factor"] in note, (
            f"Текст decisive_factor не отображается в note для режима {output['decision_mode']}"
        )
    print("PASS: test_renderer_includes_decisive_factor_section")


# ---------------------------------------------------------------------------
# d) Логическая валидация decisive_factor (смысловое соответствие режиму)
# ---------------------------------------------------------------------------

def test_decisive_factor_logic_edd_forbidden_phrase():
    """EDD-кейс с формулировкой 'CDD не может быть завершён' должен не пройти валидацию."""
    output = _base_output(
        decision_mode="edd",
        decision="Эскалация",
        edd_required="Да",
        cdd_status="Incomplete",
        reject_reason_type="NONE",
        decisive_factor="CDD не может быть завершён ввиду отсутствия документов.",
    )

    ok, errors = validate_output_structure(output)

    assert not ok, "Ожидали ошибку: EDD с forbidden-фразой о невозможности CDD"
    assert any("decisive_factor" in e for e in errors), (
        f"Ожидали ошибку про decisive_factor, получили: {errors}"
    )
    print("PASS: test_decisive_factor_logic_edd_forbidden_phrase")


def test_decisive_factor_logic_cdd_failure_no_blocker():
    """CDD_FAILURE без упоминания конкретного blocker'а должен не пройти валидацию."""
    output = _base_output(
        decisive_factor="Высокий риск клиента.",  # общий вывод, не CDD-blocker
    )

    ok, errors = validate_output_structure(output)

    assert not ok, "Ожидали ошибку: CDD_FAILURE без указания конкретного CDD-блокера"
    assert any("decisive_factor" in e for e in errors), (
        f"Ожидали ошибку про decisive_factor, получили: {errors}"
    )
    print("PASS: test_decisive_factor_logic_cdd_failure_no_blocker")


def test_decisive_factor_logic_risk_unacceptable_no_finding():
    """RISK_UNACCEPTABLE без risk finding в decisive_factor должен не пройти валидацию."""
    output = _base_output(
        cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Клиент не соответствует требованиям.",  # нет risk finding
    )

    ok, errors = validate_output_structure(output)

    assert not ok, "Ожидали ошибку: RISK_UNACCEPTABLE без risk finding"
    assert any("decisive_factor" in e for e in errors), (
        f"Ожидали ошибку про decisive_factor, получили: {errors}"
    )
    print("PASS: test_decisive_factor_logic_risk_unacceptable_no_finding")


def test_decisive_factor_logic_valid_edd():
    """Корректный EDD decisive_factor (незакрытый gap) должен проходить валидацию."""
    output = _base_output(
        decision_mode="edd",
        decision="Эскалация",
        edd_required="Да",
        cdd_status="Incomplete",
        reject_reason_type="NONE",
        decisive_factor="Источник средств по операции не подтверждён.",
    )

    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали успех для корректного EDD decisive_factor, получили: {errors}"
    print("PASS: test_decisive_factor_logic_valid_edd")


def test_decisive_factor_logic_valid_risk_unacceptable():
    """Корректный RISK_UNACCEPTABLE decisive_factor должен проходить валидацию."""
    output = _base_output(
        cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Негативные публикации о возможной вовлечённости в сомнительные схемы не были сняты.",
    )

    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали успех для корректного RISK_UNACCEPTABLE decisive_factor, получили: {errors}"
    print("PASS: test_decisive_factor_logic_valid_risk_unacceptable")


def test_fallback_decisive_factor_by_mode():
    """build_fallback_output() возвращает осмысленный decisive_factor для каждого режима."""
    cases = [
        ("Эскалация", "edd", "CDD"),
        ("Отказать", "reject", "риск"),
        ("Одобрить", "approve", "CDD"),
    ]
    for recommendation, expected_mode, expected_signal in cases:
        case_data = {
            "recommendation": recommendation,
            "selected_risk_level": "Средний",
            "client_name": "Test",
            "case_type": "Onboarding",
        }
        result = build_fallback_output(case_data, "test error")
        df = result["decisive_factor"].lower()

        assert expected_signal.lower() in df, (
            f"Ожидали '{expected_signal}' в decisive_factor для {expected_mode}, получили: '{result['decisive_factor']}'"
        )
    print("PASS: test_fallback_decisive_factor_by_mode")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== DECISIVE FACTOR TESTS ===\n")

    # Форма
    test_schema_rejects_missing_decisive_factor()
    test_schema_rejects_empty_decisive_factor()
    test_schema_accepts_valid_decisive_factor()
    test_fallback_always_contains_decisive_factor()
    test_renderer_includes_decisive_factor_section()

    # Смысл
    test_decisive_factor_logic_edd_forbidden_phrase()
    test_decisive_factor_logic_cdd_failure_no_blocker()
    test_decisive_factor_logic_risk_unacceptable_no_finding()
    test_decisive_factor_logic_valid_edd()
    test_decisive_factor_logic_valid_risk_unacceptable()
    test_fallback_decisive_factor_by_mode()

    print("\nВсе тесты пройдены.\n")
