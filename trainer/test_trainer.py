# test_trainer.py

from trainer import (
    evaluate_trainer_answer,
    save_trainer_run,
    load_trainer_runs,
    ROOT_CAUSE_LABELS,
)
from trainer_cases import get_all_trainer_cases, get_trainer_case_by_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expected(case_id="TR-003"):
    case = get_trainer_case_by_id(case_id)
    return case["expected_output"]


def _user_perfect(case_id="TR-003"):
    """Идеальный ответ = копия эталона."""
    return dict(get_trainer_case_by_id(case_id)["expected_output"])


def _user_wrong_mode(case_id="TR-003"):
    """Аналитик выбрал Reject вместо EDD."""
    u = _user_perfect(case_id)
    u["decision_mode"] = "reject"
    u["decision"] = "Отказать"
    u["cdd_status"] = "Incomplete and cannot be completed"
    u["reject_reason_type"] = "CDD_FAILURE"
    return u


def _user_wrong_cdd(case_id="TR-003"):
    """Правильный режим, но неверный cdd_status."""
    u = _user_perfect(case_id)
    u["cdd_status"] = "Incomplete and cannot be completed"
    return u


def _user_weak_decisive(case_id="TR-003"):
    """Режим верен, но decisive_factor расплывчатый."""
    u = _user_perfect(case_id)
    u["decisive_factor"] = "Высокий уровень риска."
    return u


# ---------------------------------------------------------------------------
# Trainer Cases Library
# ---------------------------------------------------------------------------

def test_trainer_cases_count():
    """Должно быть не менее 8 кейсов."""
    cases = get_all_trainer_cases()
    assert len(cases) >= 8, f"Ожидали >= 8, получили {len(cases)}"
    print(f"PASS: test_trainer_cases_count ({len(cases)} кейсов)")


def test_trainer_cases_coverage():
    """Покрытие: approve, edd, reject/CDD_FAILURE, reject/RISK_UNACCEPTABLE."""
    cases = get_all_trainer_cases()
    modes = {c["expected_output"]["decision_mode"] for c in cases}
    reasons = {c["expected_output"]["reject_reason_type"] for c in cases}
    assert "approve" in modes
    assert "edd" in modes
    assert "reject" in modes
    assert "CDD_FAILURE" in reasons
    assert "RISK_UNACCEPTABLE" in reasons
    print("PASS: test_trainer_cases_coverage")


def test_get_trainer_case_by_id():
    case = get_trainer_case_by_id("TR-001")
    assert case is not None
    assert case["case_id"] == "TR-001"
    print("PASS: test_get_trainer_case_by_id")


def test_get_trainer_case_unknown():
    assert get_trainer_case_by_id("UNKNOWN") is None
    print("PASS: test_get_trainer_case_unknown")


# ---------------------------------------------------------------------------
# evaluate_trainer_answer
# ---------------------------------------------------------------------------

def test_perfect_answer_gives_high_score():
    """Идеальный ответ → score >= 85."""
    review = evaluate_trainer_answer(_user_perfect(), _expected())
    assert review["score"] >= 85, f"Ожидали >= 85, получили {review['score']}"
    assert review["is_correct_decision"]
    assert review["root_cause"] == "NONE"
    print(f"PASS: test_perfect_answer_gives_high_score (score={review['score']})")


def test_wrong_decision_mode_gives_error():
    """Неверный decision_mode → is_correct_decision = False."""
    review = evaluate_trainer_answer(_user_wrong_mode(), _expected())
    assert not review["is_correct_decision"]
    assert review["root_cause"] != "NONE"
    print(f"PASS: test_wrong_decision_mode_gives_error (root_cause={review['root_cause']})")


def test_wrong_cdd_status_is_detected():
    """Неверный cdd_status → is_correct_cdd_logic = False."""
    review = evaluate_trainer_answer(_user_wrong_cdd(), _expected())
    assert not review["is_correct_cdd_logic"]
    print(f"PASS: test_wrong_cdd_status_is_detected (root_cause={review['root_cause']})")


def test_weak_decisive_factor_lowers_score():
    """Слабый decisive_factor → score < perfect."""
    perfect_score = evaluate_trainer_answer(_user_perfect(), _expected())["score"]
    weak_score    = evaluate_trainer_answer(_user_weak_decisive(), _expected())["score"]
    assert weak_score < perfect_score, f"Ожидали {weak_score} < {perfect_score}"
    print(f"PASS: test_weak_decisive_factor_lowers_score ({perfect_score} → {weak_score})")


def test_over_reject_root_cause():
    """EDD-кейс решён как Reject → root_cause = OVER_REJECT (слишком жёсткое решение)."""
    review = evaluate_trainer_answer(_user_wrong_mode("TR-003"), _expected("TR-003"))
    assert review["root_cause"] == "OVER_REJECT", f"Получили: {review['root_cause']}"
    print("PASS: test_over_reject_root_cause")


def test_under_reject_root_cause():
    """Reject-кейс (TR-005) решён как EDD → root_cause = UNDER_REJECT."""
    u = _user_perfect("TR-005")
    u["decision_mode"] = "edd"
    u["decision"] = "Эскалация"
    u["cdd_status"] = "Incomplete"
    u["reject_reason_type"] = "NONE"
    review = evaluate_trainer_answer(u, _expected("TR-005"))
    assert review["root_cause"] == "UNDER_REJECT", f"Получили: {review['root_cause']}"
    print("PASS: test_under_reject_root_cause")


def test_root_cause_labels_complete():
    """Все root_cause имеют человекочитаемый label."""
    for key in ["OVER_REJECT", "UNDER_REJECT", "MISSED_SOF_GAP",
                "MISSED_UBO_BLOCKER", "MISSED_ADVERSE_MEDIA",
                "MISREAD_CDD_STATUS", "WEAK_DECISIVE_FACTOR",
                "WEAK_SIGNAL_TRACE", "WEAK_RATIONALE", "NONE"]:
        assert key in ROOT_CAUSE_LABELS, f"Нет label для {key}"
    print("PASS: test_root_cause_labels_complete")


def test_review_structure():
    """review содержит все обязательные поля."""
    review = evaluate_trainer_answer(_user_perfect(), _expected())
    required = [
        "is_correct_decision", "is_correct_cdd_logic",
        "is_correct_decisive_factor", "error_type", "root_cause",
        "root_cause_label", "review_summary",
        "what_was_good", "what_was_missed", "what_to_recheck", "score",
    ]
    for field in required:
        assert field in review, f"Поле '{field}' отсутствует в review"
    print("PASS: test_review_structure")


def test_score_range():
    """score всегда в диапазоне 0–100."""
    for case in get_all_trainer_cases():
        exp = case["expected_output"]
        # идеальный ответ
        r1 = evaluate_trainer_answer(dict(exp), exp)
        assert 0 <= r1["score"] <= 100, f"score={r1['score']} вне диапазона"
    print("PASS: test_score_range")


# ---------------------------------------------------------------------------
# save / load trainer runs
# ---------------------------------------------------------------------------

def test_trainer_run_saved_separately():
    """Trainer runs сохраняются в trainer_runs.json, не в cases.json."""
    import os
    review  = evaluate_trainer_answer(_user_perfect(), _expected())
    run_id  = save_trainer_run("TR-003", _user_perfect(), _expected(), review)

    assert run_id.startswith("RUN-")

    runs = load_trainer_runs()
    saved = next((r for r in runs if r["run_id"] == run_id), None)
    assert saved is not None, "Прогон не найден в trainer_runs.json"
    assert saved["trainer_case_id"] == "TR-003"
    assert saved["score"] == review["score"]

    # Проверяем, что trainer_runs.json отдельный файл
    assert not os.path.exists("data/cases.json") or run_id not in open("data/cases.json").read()
    print(f"PASS: test_trainer_run_saved_separately (run_id={run_id})")


def test_trainer_run_contains_required_fields():
    """Каждая запись в trainer_runs.json содержит обязательные поля."""
    review = evaluate_trainer_answer(_user_perfect(), _expected())
    run_id = save_trainer_run("TR-003", _user_perfect(), _expected(), review)

    runs   = load_trainer_runs()
    saved  = next(r for r in runs if r["run_id"] == run_id)

    for field in ["run_id", "trainer_case_id", "saved_at", "score",
                  "error_type", "root_cause", "is_correct_decision",
                  "review", "user_output", "expected_output"]:
        assert field in saved, f"Поле '{field}' отсутствует в записи"
    print("PASS: test_trainer_run_contains_required_fields")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== TRAINER TESTS (Stage 3A) ===\n")

    print("--- Library ---")
    test_trainer_cases_count()
    test_trainer_cases_coverage()
    test_get_trainer_case_by_id()
    test_get_trainer_case_unknown()

    print("\n--- Evaluate ---")
    test_perfect_answer_gives_high_score()
    test_wrong_decision_mode_gives_error()
    test_wrong_cdd_status_is_detected()
    test_weak_decisive_factor_lowers_score()
    test_under_reject_root_cause()
    test_over_reject_root_cause()
    test_root_cause_labels_complete()
    test_review_structure()
    test_score_range()

    print("\n--- Save / Load ---")
    test_trainer_run_saved_separately()
    test_trainer_run_contains_required_fields()

    print("\nВсе тесты пройдены.\n")
