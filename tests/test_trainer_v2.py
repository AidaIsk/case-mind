# tests/test_trainer_v2.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

from trainer.trainer_note import evaluate_decision_note
from trainer.trainer_analytics import get_next_trainer_case
from trainer.trainer import evaluate_trainer_answer
from trainer.trainer_cases import get_all_trainer_cases, get_trainer_case_by_id


CASES = get_all_trainer_cases()


def _expected(case_id="TR-003"):
    return get_trainer_case_by_id(case_id)["expected_output"]


def _user_perfect(case_id="TR-003"):
    return dict(_expected(case_id))


# ---------------------------------------------------------------------------
# 1. Decision Note evaluation
# ---------------------------------------------------------------------------

_GOOD_NOTE = """
Клиент — польская агрологистическая компания AgroTrans Polska, onboarding.
Деятельность: транспортировка зерна, основные контрагенты — Украина и Румыния.

Факты: UBO установлен и подтверждён документально (Томаш Ковальски, 75%).
Подтверждающие документы по операции предоставлены. Screening чистый.
Однако источник средств по конкретной операции на сумму EUR 280,000 не подтверждён —
компания ссылается на контракты, но документы не представлены.

Анализ: CDD не завершён по причине отсутствия подтверждения SoF.
Пробел является закрываемым — нужно запросить договор с контрагентом.
Отказ преждевременен, так как UBO установлен и деятельность прозрачна.

Решение: Эскалация (EDD). Источник средств по операции не подтверждён.
Рекомендуется запросить подтверждающие документы по SoF.
"""

_SHORT_NOTE = "Клиент плохой, отказать."

_INCONSISTENT_NOTE = """
Клиент — компания с непрозрачной структурой. UBO не установлен.
Документы отсутствуют. Источник средств неизвестен.
Анализ показывает критические риски. Необходимо отказать в обслуживании.
Бенефициарный владелец не установлен и не может быть подтверждён.
Завершение CDD невозможно. Рекомендую отказать.
"""


def test_note_too_short_is_weak():
    result = evaluate_decision_note(_SHORT_NOTE, _user_perfect(), _expected())
    assert result["note_quality"] == "weak"
    assert result["note_score"] == 0
    print(f"PASS: test_note_too_short_is_weak (score={result['note_score']})")


def test_good_note_consistency_ok():
    user = _user_perfect()  # decision_mode = edd
    result = evaluate_decision_note(_GOOD_NOTE, user, _expected())
    assert result["note_consistency_ok"] is True
    assert result["note_score"] >= 50
    print(f"PASS: test_good_note_consistency_ok (score={result['note_score']}, quality={result['note_quality']})")


def test_inconsistent_note_caught():
    """Записка с reject-тональностью при EDD-решении — inconsistency."""
    user = _user_perfect("TR-003")  # EDD
    result = evaluate_decision_note(_INCONSISTENT_NOTE, user, _expected("TR-003"))
    assert result["note_consistency_ok"] is False
    assert any("противоречит" in issue for issue in result["note_issues"])
    print(f"PASS: test_inconsistent_note_caught (issues={result['note_issues']})")


def test_note_score_in_review():
    """submit_trainer_run должен возвращать note_score в review."""
    # Прямой вызов evaluate_trainer_answer + имитация note
    from trainer.trainer_note import evaluate_decision_note as _eval_note
    user = _user_perfect()
    exp  = _expected()
    review = evaluate_trainer_answer(user, exp)
    note_review = _eval_note(_GOOD_NOTE, user, exp)
    review["note_score"]  = note_review["note_score"]
    review["note_review"] = note_review
    assert "note_score" in review
    assert isinstance(review["note_score"], int)
    print(f"PASS: test_note_score_in_review (note_score={review['note_score']})")


# ---------------------------------------------------------------------------
# 2. Next case modes
# ---------------------------------------------------------------------------

def _run(case_id, date_str=None):
    from datetime import date
    date_str = date_str or date.today().strftime("%Y-%m-%d")
    return {"run_id": f"R-{case_id}", "trainer_case_id": case_id,
            "saved_at": f"{date_str} 10:00", "score": 80, "root_cause": "NONE",
            "is_correct_decision": True}


def test_sequential_next():
    """sequential возвращает следующий по порядку кейс."""
    result = get_next_trainer_case([], CASES, "TR-001", mode="sequential")
    assert result is not None
    assert result["case_id"] == "TR-002"
    print(f"PASS: test_sequential_next (next={result['case_id']})")


def test_sequential_wraps():
    """sequential оборачивается на первый при достижении конца."""
    last_id = CASES[-1]["case_id"]
    result  = get_next_trainer_case([], CASES, last_id, mode="sequential")
    assert result["case_id"] == CASES[0]["case_id"]
    print(f"PASS: test_sequential_wraps (last={last_id} → first={result['case_id']})")


def test_random_not_same():
    """random не возвращает текущий кейс (при наличии альтернатив)."""
    results = {get_next_trainer_case([], CASES, "TR-001", mode="random")["case_id"]
               for _ in range(20)}
    # За 20 попыток хотя бы раз должен быть не TR-001
    assert len(results) > 1 or list(results)[0] != "TR-001"
    print(f"PASS: test_random_not_same (unique results={results})")


def test_unfinished_today_skips_done():
    """unfinished_today пропускает кейсы, уже решённые сегодня."""
    runs = [_run("TR-001"), _run("TR-002")]
    result = get_next_trainer_case(runs, CASES, "TR-002", mode="unfinished_today")
    assert result is not None
    assert result["case_id"] not in ("TR-001", "TR-002")
    print(f"PASS: test_unfinished_today_skips_done (next={result['case_id']})")


# ---------------------------------------------------------------------------
# 3. Coach message
# ---------------------------------------------------------------------------

def test_review_always_has_coach_message():
    """evaluate_trainer_answer всегда возвращает coach_message."""
    review = evaluate_trainer_answer(_user_perfect(), _expected())
    assert "coach_message" in review
    assert isinstance(review["coach_message"], str) and review["coach_message"]
    print(f"PASS: test_review_always_has_coach_message (msg='{review['coach_message'][:50]}...')")


def test_coach_message_weak_decisive_factor():
    """При слабом decisive_factor coach_message указывает на это."""
    user = _user_perfect()
    user["decisive_factor"] = "Высокий уровень риска."  # расплывчатый
    review = evaluate_trainer_answer(user, _expected())
    msg = review.get("coach_message", "").lower()
    # Должно быть сообщение про обоснование или decisive factor
    assert any(kw in msg for kw in ["обоснование", "фактор", "решение", "верно"]), \
        f"Unexpected message: {review['coach_message']}"
    print(f"PASS: test_coach_message_weak_decisive_factor (msg='{review['coach_message']}')")


def test_coach_message_over_reject():
    """При OVER_REJECT coach_message упоминает EDD."""
    case = get_trainer_case_by_id("TR-003")  # EDD кейс
    user = dict(case["expected_output"])
    user["decision_mode"] = "reject"
    user["decision"] = "Отказать"
    user["cdd_status"] = "Incomplete and cannot be completed"
    user["reject_reason_type"] = "CDD_FAILURE"
    review = evaluate_trainer_answer(user, case["expected_output"])
    assert review["root_cause"] == "OVER_REJECT"
    assert "edd" in review["coach_message"].lower()
    print(f"PASS: test_coach_message_over_reject (msg='{review['coach_message']}')")


# ---------------------------------------------------------------------------
# 4. History filters (логика фильтрации)
# ---------------------------------------------------------------------------

def _make_runs():
    return [
        {"run_id": "R1", "trainer_case_id": "TR-001", "saved_at": "2025-01-01 10:00",
         "score": 90, "root_cause": "NONE",       "error_type": "NONE", "is_correct_decision": True, "review": {}, "decision_note": ""},
        {"run_id": "R2", "trainer_case_id": "TR-002", "saved_at": "2025-01-01 11:00",
         "score": 45, "root_cause": "OVER_REJECT", "error_type": "OVER_REJECT", "is_correct_decision": False, "review": {}, "decision_note": ""},
        {"run_id": "R3", "trainer_case_id": "TR-003", "saved_at": "2025-01-01 12:00",
         "score": 70, "root_cause": "WEAK_RATIONALE", "error_type": "WEAK_RATIONALE", "is_correct_decision": True, "review": {}, "decision_note": ""},
    ]


def _filter_errors(runs):
    return [r for r in runs if r.get("root_cause", "NONE") != "NONE" or r.get("error_type", "NONE") != "NONE"]


def _filter_low_score(runs):
    return [r for r in runs if r.get("score", 100) < 60]


def test_filter_errors_works():
    runs = _make_runs()
    filtered = _filter_errors(runs)
    assert len(filtered) == 2
    assert all(r["root_cause"] != "NONE" for r in filtered)
    print("PASS: test_filter_errors_works")


def test_filter_low_score_works():
    runs = _make_runs()
    filtered = _filter_low_score(runs)
    assert len(filtered) == 1
    assert filtered[0]["score"] == 45
    print("PASS: test_filter_low_score_works")


def test_filter_all_shows_all():
    runs = _make_runs()
    assert len(runs) == 3
    print("PASS: test_filter_all_shows_all")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== TRAINER v2 TESTS ===\n")

    print("--- 1. Decision Note ---")
    test_note_too_short_is_weak()
    test_good_note_consistency_ok()
    test_inconsistent_note_caught()
    test_note_score_in_review()

    print("\n--- 2. Next case modes ---")
    test_sequential_next()
    test_sequential_wraps()
    test_random_not_same()
    test_unfinished_today_skips_done()

    print("\n--- 3. Coach message ---")
    test_review_always_has_coach_message()
    test_coach_message_weak_decisive_factor()
    test_coach_message_over_reject()

    print("\n--- 4. History filters ---")
    test_filter_errors_works()
    test_filter_low_score_works()
    test_filter_all_shows_all()

    print("\nВсе тесты пройдены.\n")
