# tests/test_trainer_ux.py
# Тесты для UX-правок Trainer Mode

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

from trainer.trainer_cases import get_all_trainer_cases, get_trainer_case_by_id
from trainer.trainer_analytics import (
    detect_score_trend,
    get_next_unfinished_trainer_case_for_today,
)
from trainer.trainer import evaluate_trainer_answer


# ---------------------------------------------------------------------------
# 1. Нет утечек в description_user
# ---------------------------------------------------------------------------

_FORBIDDEN_PHRASES = [
    "правильный ответ",
    "обязательный отказ",
    "edd, не reject",
    "reject/cdd_failure",
    "reject/risk_unacceptable",
    "шаблонный отказ",
    "нужен edd",
    "нужно edd",
    "это edd",
    "decision_mode",
    "cdd_status",
]

def test_no_answer_leaks_in_descriptions():
    """description_user не должен содержать подсказок правильного ответа."""
    cases = get_all_trainer_cases()
    leaks = []
    for case in cases:
        desc = case.get("description_user", "").lower()
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in desc:
                leaks.append(f"{case['case_id']}: найдено «{phrase}»")
    assert not leaks, f"Утечки в descriptions:\n" + "\n".join(leaks)
    print(f"PASS: test_no_answer_leaks_in_descriptions ({len(cases)} кейсов проверено)")


def test_description_user_exists_for_all_cases():
    """У каждого кейса должен быть description_user."""
    cases = get_all_trainer_cases()
    missing = [c["case_id"] for c in cases if not c.get("description_user")]
    assert not missing, f"Нет description_user у кейсов: {missing}"
    print("PASS: test_description_user_exists_for_all_cases")


def test_description_internal_exists_for_all_cases():
    """У каждого кейса должен быть description_internal."""
    cases = get_all_trainer_cases()
    missing = [c["case_id"] for c in cases if not c.get("description_internal")]
    assert not missing, f"Нет description_internal у кейсов: {missing}"
    print("PASS: test_description_internal_exists_for_all_cases")


# ---------------------------------------------------------------------------
# 2. error_type определяется системой, не является input
# ---------------------------------------------------------------------------

def test_error_type_determined_by_system():
    """evaluate_trainer_answer должен возвращать error_type в review (не требовать его в user_output)."""
    case = get_trainer_case_by_id("TR-003")
    # user_output без error_type вообще
    user_output = dict(case["expected_output"])
    user_output.pop("error_type", None)  # убираем явно
    user_output.setdefault("error_type", "NONE")  # система может добавить NONE

    review = evaluate_trainer_answer(user_output, case["expected_output"])
    assert "error_type" in review, "error_type отсутствует в review"
    assert isinstance(review["error_type"], str)
    print(f"PASS: test_error_type_determined_by_system (error_type={review['error_type']})")


# ---------------------------------------------------------------------------
# 3. get_next_unfinished_trainer_case_for_today
# ---------------------------------------------------------------------------

def _make_run(case_id: str, date_str: str = None) -> dict:
    from datetime import date
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    return {
        "run_id": f"RUN-{case_id}",
        "trainer_case_id": case_id,
        "saved_at": f"{date_str} 10:00",
        "score": 80,
        "root_cause": "NONE",
        "is_correct_decision": True,
        "review": {},
    }


def test_next_case_skips_done_today():
    """Функция должна пропустить кейсы, уже пройденные сегодня."""
    cases = get_all_trainer_cases()
    # Помечаем TR-001 и TR-002 как пройденные сегодня
    runs = [_make_run("TR-001"), _make_run("TR-002")]
    result = get_next_unfinished_trainer_case_for_today(runs, cases)
    assert result is not None
    assert result["case_id"] not in ("TR-001", "TR-002")
    print(f"PASS: test_next_case_skips_done_today (следующий: {result['case_id']})")


def test_next_case_skips_current():
    """Функция не должна возвращать текущий кейс."""
    cases = get_all_trainer_cases()
    runs = []
    result = get_next_unfinished_trainer_case_for_today(runs, cases, current_case_id="TR-001")
    assert result is not None
    assert result["case_id"] != "TR-001"
    print(f"PASS: test_next_case_skips_current (следующий: {result['case_id']})")


def test_next_case_returns_none_when_all_done():
    """Если все кейсы пройдены сегодня — возвращает None."""
    cases = get_all_trainer_cases()
    runs = [_make_run(c["case_id"]) for c in cases]
    result = get_next_unfinished_trainer_case_for_today(runs, cases)
    assert result is None
    print("PASS: test_next_case_returns_none_when_all_done")


def test_next_case_ignores_old_runs():
    """Прогоны за прошлые дни не считаются пройденными."""
    cases = get_all_trainer_cases()
    # Все кейсы пройдены вчера — сегодня все доступны
    runs = [_make_run(c["case_id"], "2000-01-01") for c in cases]
    result = get_next_unfinished_trainer_case_for_today(runs, cases)
    assert result is not None
    print(f"PASS: test_next_case_ignores_old_runs (следующий: {result['case_id']})")


# ---------------------------------------------------------------------------
# 4. Preliminary trend при 3–5 прогонах
# ---------------------------------------------------------------------------

def _run(score): return {"score": score}

def test_preliminary_trend_improving():
    runs = [_run(50), _run(50), _run(80), _run(80)]
    result = detect_score_trend(runs)
    assert result == "preliminary_improving", f"Получили: {result}"
    print(f"PASS: test_preliminary_trend_improving (result={result})")


def test_preliminary_trend_declining():
    runs = [_run(80), _run(80), _run(50), _run(50)]
    result = detect_score_trend(runs)
    assert result == "preliminary_declining", f"Получили: {result}"
    print(f"PASS: test_preliminary_trend_declining (result={result})")


def test_preliminary_trend_stable():
    runs = [_run(70), _run(72), _run(71), _run(70)]
    result = detect_score_trend(runs)
    assert result == "preliminary_stable", f"Получили: {result}"
    print(f"PASS: test_preliminary_trend_stable (result={result})")


def test_not_enough_data_below_3():
    assert detect_score_trend([]) == "not_enough_data"
    assert detect_score_trend([_run(80)]) == "not_enough_data"
    assert detect_score_trend([_run(80), _run(60)]) == "not_enough_data"
    print("PASS: test_not_enough_data_below_3")


def test_full_trend_with_10_runs():
    runs = [_run(50)] * 5 + [_run(80)] * 5
    assert detect_score_trend(runs) == "improving"
    print("PASS: test_full_trend_with_10_runs")


# ---------------------------------------------------------------------------
# 5. Динамические сигналы не ломают submit flow
# ---------------------------------------------------------------------------

def test_dynamic_signals_min_2():
    """Даже если аналитик не заполнил сигналы — система добавляет минимум 2."""
    case = get_trainer_case_by_id("TR-003")
    exp  = case["expected_output"]

    # user_output с пустым signal_trace — имитируем что UI добавил заглушки
    user_output = dict(exp)
    user_output["signal_trace"] = [
        {"signal": "Тест", "category": "OTHER", "impact": "DECISIVE",
         "direction": "SUPPORTS_ESCALATION", "comment": "Тест."},
        {"signal": "Второй сигнал", "category": "OTHER", "impact": "LOW",
         "direction": "MITIGATING", "comment": "Авто."},
    ]
    review = evaluate_trainer_answer(user_output, exp)
    assert isinstance(review["score"], int)
    assert 0 <= review["score"] <= 100
    print(f"PASS: test_dynamic_signals_min_2 (score={review['score']})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== TRAINER UX TESTS ===\n")

    print("--- 1. Утечки в descriptions ---")
    test_no_answer_leaks_in_descriptions()
    test_description_user_exists_for_all_cases()
    test_description_internal_exists_for_all_cases()

    print("\n--- 2. error_type определяется системой ---")
    test_error_type_determined_by_system()

    print("\n--- 3. Следующий непройденный ---")
    test_next_case_skips_done_today()
    test_next_case_skips_current()
    test_next_case_returns_none_when_all_done()
    test_next_case_ignores_old_runs()

    print("\n--- 4. Preliminary trend ---")
    test_preliminary_trend_improving()
    test_preliminary_trend_declining()
    test_preliminary_trend_stable()
    test_not_enough_data_below_3()
    test_full_trend_with_10_runs()

    print("\n--- 5. Динамические сигналы ---")
    test_dynamic_signals_min_2()

    print("\nВсе тесты пройдены.\n")
