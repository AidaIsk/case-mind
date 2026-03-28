# test_self_review.py

from output_schema import validate_output_structure, build_fallback_output
from renderers import render_decision_note


# ---------------------------------------------------------------------------
# Базовый валидный output — основа для всех тестов
# ---------------------------------------------------------------------------

def _base_output(**overrides) -> dict:
    base = {
        "decision_mode": "reject",
        "decision": "Отказать",
        "edd_required": "Нет",
        "cdd_status": "Incomplete and cannot be completed",
        "risk_level": "Высокий",
        "reject_reason_type": "CDD_FAILURE",
        "decision_summary": "Тестовый кейс. Отказ по причине невозможности завершить CDD.",
        "case_overview": "Клиент: Test Corp. Тип кейса: Onboarding.",
        "key_risk_factors": ["UBO не установлен", "Документы отсутствуют"],
        "cdd_assessment": {
            "confirmed": ["Идентификация юридического лица"],
            "not_confirmed": ["UBO", "SoF"],
            "conclusion": "CDD не завершён и не может быть завершён.",
        },
        "analysis": "Отсутствие UBO делает завершение CDD невозможным.",
        "decisive_factor": "Бенефициарный владелец не установлен и не может быть подтверждён.",
        "decision_rationale": "Клиент не может быть принят.",
        "required_actions": [],
        "error_type": "NONE",
        "confidence_score": 4,
        "self_review": {
            "summary": "Решение логически согласовано и защищаемо.",
            "main_gap": "Существенных аналитических gaps не выявлено.",
            "what_to_recheck": ["UBO", "SoF"],
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# a) Schema — форма: обязательные поля
# ---------------------------------------------------------------------------

def test_schema_rejects_missing_error_type():
    output = _base_output()
    del output["error_type"]
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("error_type" in e for e in errors)
    print("PASS: test_schema_rejects_missing_error_type")


def test_schema_rejects_missing_confidence_score():
    output = _base_output()
    del output["confidence_score"]
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("confidence_score" in e for e in errors)
    print("PASS: test_schema_rejects_missing_confidence_score")


def test_schema_rejects_missing_self_review():
    output = _base_output()
    del output["self_review"]
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("self_review" in e for e in errors)
    print("PASS: test_schema_rejects_missing_self_review")


def test_schema_rejects_confidence_score_zero():
    output = _base_output(confidence_score=0)
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("confidence_score" in e for e in errors)
    print("PASS: test_schema_rejects_confidence_score_zero")


def test_schema_rejects_confidence_score_six():
    output = _base_output(confidence_score=6)
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("confidence_score" in e for e in errors)
    print("PASS: test_schema_rejects_confidence_score_six")


def test_schema_rejects_invalid_error_type():
    output = _base_output(error_type="BAD_VALUE")
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("error_type" in e for e in errors)
    print("PASS: test_schema_rejects_invalid_error_type")


def test_schema_rejects_what_to_recheck_over_limit():
    output = _base_output()
    output["self_review"]["what_to_recheck"] = ["a", "b", "c", "d"]
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("what_to_recheck" in e for e in errors)
    print("PASS: test_schema_rejects_what_to_recheck_over_limit")


# ---------------------------------------------------------------------------
# b) Logic — смысловые проверки
# ---------------------------------------------------------------------------

def test_logic_rejects_confidence5_with_error_type():
    """error_type != NONE + confidence_score = 5 → fail."""
    output = _base_output(error_type="WEAK_RATIONALE", confidence_score=5)
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("confidence_score" in e for e in errors)
    print("PASS: test_logic_rejects_confidence5_with_error_type")


def test_logic_rejects_confidence5_with_incomplete_cdd():
    """cdd_status = Incomplete + confidence_score = 5 → fail."""
    output = _base_output(
        decision_mode="edd",
        decision="Эскалация",
        edd_required="Да",
        cdd_status="Incomplete",
        reject_reason_type="NONE",
        decisive_factor="Источник средств не подтверждён.",
        confidence_score=5,
        error_type="NONE",
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("confidence_score" in e for e in errors)
    print("PASS: test_logic_rejects_confidence5_with_incomplete_cdd")


def test_logic_rejects_over_reject_non_reject_mode():
    """OVER_REJECT при decision_mode != reject → fail."""
    output = _base_output(
        decision_mode="edd",
        decision="Эскалация",
        edd_required="Да",
        cdd_status="Incomplete",
        reject_reason_type="NONE",
        decisive_factor="SoF не подтверждён.",
        error_type="OVER_REJECT",
        confidence_score=3,
        self_review={
            "summary": "Решение возможно избыточно жёсткое.",
            "main_gap": "Нет явных признаков того, что reject неизбежен.",
            "what_to_recheck": ["SoF", "UBO"],
        },
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("OVER_REJECT" in e for e in errors)
    print("PASS: test_logic_rejects_over_reject_non_reject_mode")


def test_logic_rejects_under_reject_on_reject_mode():
    """UNDER_REJECT при decision_mode = reject → fail."""
    output = _base_output(
        error_type="UNDER_REJECT",
        confidence_score=3,
        self_review={
            "summary": "Решение чрезмерно мягкое.",
            "main_gap": "Риск недооценён аналитиком.",
            "what_to_recheck": ["risk_level"],
        },
    )
    ok, errors = validate_output_structure(output)
    assert not ok
    assert any("UNDER_REJECT" in e for e in errors)
    print("PASS: test_logic_rejects_under_reject_on_reject_mode")


def test_logic_valid_edd_weak_rationale():
    """Валидный EDD-кейс с WEAK_RATIONALE и confidence_score = 3 → pass."""
    output = _base_output(
        decision_mode="edd",
        decision="Эскалация",
        edd_required="Да",
        cdd_status="Incomplete",
        reject_reason_type="NONE",
        decisive_factor="Источник средств по операции не подтверждён.",
        error_type="WEAK_RATIONALE",
        confidence_score=3,
        self_review={
            "summary": "Решение рабочее, но rationale требует большей точности.",
            "main_gap": "Decision rationale недостаточно чётко связывает finding с выводом.",
            "what_to_recheck": ["SoF", "decision_rationale"],
        },
    )
    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали pass для валидного EDD/WEAK_RATIONALE, получили: {errors}"
    print("PASS: test_logic_valid_edd_weak_rationale")


def test_logic_valid_reject_none_confidence4():
    """Валидный reject-кейс с error_type = NONE и confidence_score = 4 → pass."""
    output = _base_output(error_type="NONE", confidence_score=4)
    ok, errors = validate_output_structure(output)
    assert ok, f"Ожидали pass для валидного reject/NONE, получили: {errors}"
    print("PASS: test_logic_valid_reject_none_confidence4")


# ---------------------------------------------------------------------------
# c) Render — блок Self-Review отображается в ноте
# ---------------------------------------------------------------------------

def test_renderer_includes_self_review_section():
    """Все три режима должны содержать ## Self-Review с нужными полями."""
    modes = [
        _base_output(
            decision_mode="reject",
            error_type="NONE",
            confidence_score=4,
        ),
        _base_output(
            decision_mode="edd",
            decision="Эскалация",
            edd_required="Да",
            cdd_status="Incomplete",
            reject_reason_type="NONE",
            decisive_factor="SoF не подтверждён.",
            error_type="WEAK_RATIONALE",
            confidence_score=3,
            self_review={
                "summary": "Решение допустимо, но слабо обосновано.",
                "main_gap": "Rationale не связывает finding с выводом.",
                "what_to_recheck": ["SoF"],
            },
        ),
        _base_output(
            decision_mode="approve",
            decision="Одобрить",
            edd_required="Нет",
            cdd_status="Complete",
            reject_reason_type="NONE",
            decisive_factor="Ключевые элементы CDD подтверждены.",
            error_type="NONE",
            confidence_score=5,
            self_review={
                "summary": "Решение логически обосновано и защищаемо.",
                "main_gap": "Существенных аналитических gaps не выявлено.",
                "what_to_recheck": ["screening findings"],
            },
        ),
    ]

    for output in modes:
        note = render_decision_note(output)
        mode = output["decision_mode"]
        assert "## Self-Review" in note, f"Нет ## Self-Review для {mode}"
        assert output["error_type"] in note, f"error_type не отображается для {mode}"
        assert str(output["confidence_score"]) in note, f"confidence_score не отображается для {mode}"
        assert output["self_review"]["summary"] in note, f"summary не отображается для {mode}"
        assert output["self_review"]["main_gap"] in note, f"main_gap не отображается для {mode}"

    print("PASS: test_renderer_includes_self_review_section")


# ---------------------------------------------------------------------------
# d) Fallback — новые поля всегда присутствуют и валидны
# ---------------------------------------------------------------------------

def test_fallback_contains_all_new_fields():
    """build_fallback_output() должен содержать error_type, confidence_score, self_review."""
    for recommendation in ["Отказать", "Одобрить", "Эскалация"]:
        case_data = {
            "recommendation": recommendation,
            "selected_risk_level": "Средний",
            "client_name": "Test",
            "case_type": "Onboarding",
        }
        result = build_fallback_output(case_data, "test error")

        assert "error_type" in result, f"error_type отсутствует в fallback ({recommendation})"
        assert "confidence_score" in result, f"confidence_score отсутствует в fallback ({recommendation})"
        assert "self_review" in result, f"self_review отсутствует в fallback ({recommendation})"

        sr = result["self_review"]
        assert "summary" in sr
        assert "main_gap" in sr
        assert "what_to_recheck" in sr

    print("PASS: test_fallback_contains_all_new_fields")


def test_fallback_passes_schema_validation():
    """Fallback output должен проходить базовую schema validation."""
    case_data = {
        "recommendation": "Эскалация",
        "selected_risk_level": "Средний",
        "client_name": "Test Corp",
        "case_type": "Review",
    }
    result = build_fallback_output(case_data, "LLM timeout")

    ok, errors = validate_output_structure(result)
    assert ok, f"Fallback не прошёл валидацию: {errors}"
    print("PASS: test_fallback_passes_schema_validation")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== SELF-REVIEW TESTS ===\n")

    print("--- Schema ---")
    test_schema_rejects_missing_error_type()
    test_schema_rejects_missing_confidence_score()
    test_schema_rejects_missing_self_review()
    test_schema_rejects_confidence_score_zero()
    test_schema_rejects_confidence_score_six()
    test_schema_rejects_invalid_error_type()
    test_schema_rejects_what_to_recheck_over_limit()

    print("\n--- Logic ---")
    test_logic_rejects_confidence5_with_error_type()
    test_logic_rejects_confidence5_with_incomplete_cdd()
    test_logic_rejects_over_reject_non_reject_mode()
    test_logic_rejects_under_reject_on_reject_mode()
    test_logic_valid_edd_weak_rationale()
    test_logic_valid_reject_none_confidence4()

    print("\n--- Render ---")
    test_renderer_includes_self_review_section()

    print("\n--- Fallback ---")
    test_fallback_contains_all_new_fields()
    test_fallback_passes_schema_validation()

    print("\nВсе тесты пройдены.\n")
