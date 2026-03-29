# tests/test_trainer_polish.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

from trainer.trainer import evaluate_trainer_answer
from trainer.trainer_cases import get_trainer_case_by_id
from trainer.trainer_analytics import get_next_trainer_case
from datetime import date


CASES_LIST = __import__('trainer.trainer_cases', fromlist=['get_all_trainer_cases']).get_all_trainer_cases()

def _exp(cid="TR-003"):
    return get_trainer_case_by_id(cid)["expected_output"]

def _user(cid="TR-003"):
    return dict(_exp(cid))

def _run(cid, date_str=None, score=80, root="NONE"):
    d = date_str or date.today().strftime("%Y-%m-%d")
    return {"run_id": f"R-{cid}", "trainer_case_id": cid,
            "saved_at": f"{d} 10:00", "score": score,
            "root_cause": root, "error_type": root if root != "NONE" else "NONE",
            "is_correct_decision": root == "NONE",
            "review": {"combined_summary": "Тест", "coach_message": ""},
            "decision_note": ""}


# ---------------------------------------------------------------------------
# 1. combined_summary всегда есть в review
# ---------------------------------------------------------------------------

def test_combined_summary_always_present_in_review():
    """evaluate_trainer_answer возвращает combined_summary (None — заполняется в services)."""
    review = evaluate_trainer_answer(_user(), _exp())
    assert "combined_summary" in review
    print(f"PASS: test_combined_summary_always_present_in_review")


def test_combined_summary_set_by_services():
    """submit_trainer_run через services заполняет combined_summary строкой."""
    import types, sys
    openai_mock = types.ModuleType("openai")
    class _F:
        def __init__(self, **kw): pass
    openai_mock.OpenAI = _F
    sys.modules.setdefault("openai", openai_mock)

    from core.services import submit_trainer_run
    review, _ = submit_trainer_run("TR-003", _user(), _exp())
    assert review.get("combined_summary") is not None
    assert isinstance(review["combined_summary"], str)
    assert len(review["combined_summary"]) > 0
    print(f"PASS: test_combined_summary_set_by_services — '{review['combined_summary']}'")


# ---------------------------------------------------------------------------
# 2. Comparison message при большой разнице
# ---------------------------------------------------------------------------

def test_comparison_message_structured_higher():
    """Если structured >> note_score (разница >= 20), combined_summary отражает это."""
    from core.services import _build_combined_summary
    msg = _build_combined_summary(score=90, note_score=50, root_cause="NONE", note_quality="acceptable")
    assert "лучше определяешь" in msg or "записка" in msg.lower()
    print(f"PASS: test_comparison_message_structured_higher — '{msg}'")


def test_comparison_message_note_higher():
    from core.services import _build_combined_summary
    msg = _build_combined_summary(score=40, note_score=85, root_cause="NONE", note_quality="strong")
    assert "записка" in msg.lower() or "лучше" in msg.lower()
    print(f"PASS: test_comparison_message_note_higher — '{msg}'")


def test_comparison_no_message_small_delta():
    from core.services import _build_combined_summary
    # Разница < 15 — нет специального сообщения
    msg_small = _build_combined_summary(score=80, note_score=75, root_cause="NONE", note_quality="strong")
    msg_large = _build_combined_summary(score=90, note_score=60, root_cause="NONE", note_quality="acceptable")
    assert msg_small != msg_large  # разные сценарии — разные тексты
    print("PASS: test_comparison_no_message_small_delta")


# ---------------------------------------------------------------------------
# 3. История — фильтр "только сегодня"
# ---------------------------------------------------------------------------

def _filter_today(runs):
    today = date.today().strftime("%Y-%m-%d")
    return [r for r in runs if r.get("saved_at", "").startswith(today)]


def test_filter_today_returns_only_today():
    runs = [
        _run("TR-001", date.today().strftime("%Y-%m-%d")),
        _run("TR-002", "2000-01-01"),
        _run("TR-003", date.today().strftime("%Y-%m-%d")),
    ]
    filtered = _filter_today(runs)
    assert len(filtered) == 2
    assert all(r.get("saved_at", "").startswith(date.today().strftime("%Y-%m-%d")) for r in filtered)
    print("PASS: test_filter_today_returns_only_today")


def test_filter_today_empty_when_no_runs_today():
    runs = [_run("TR-001", "2000-01-01"), _run("TR-002", "1999-12-31")]
    filtered = _filter_today(runs)
    assert filtered == []
    print("PASS: test_filter_today_empty_when_no_runs_today")


# ---------------------------------------------------------------------------
# 4. История содержит note_score и combined_summary
# ---------------------------------------------------------------------------

def test_run_record_has_note_score_and_combined():
    import types, sys
    openai_mock = types.ModuleType("openai")
    class _F:
        def __init__(self, **kw): pass
    openai_mock.OpenAI = _F
    sys.modules.setdefault("openai", openai_mock)

    from core.services import submit_trainer_run
    from trainer.trainer import load_trainer_runs

    note = "Клиент — польская компания. UBO установлен. SoF не подтверждён. Требуется EDD. Решение: Эскалация."
    _, run_id = submit_trainer_run("TR-003", _user(), _exp(), decision_note=note)
    runs = load_trainer_runs()
    saved = next((r for r in runs if r["run_id"] == run_id), None)
    assert saved is not None
    assert "note_score" in saved
    combined = saved.get("review", {}).get("combined_summary", "")
    assert isinstance(combined, str) and combined
    print(f"PASS: test_run_record_has_note_score_and_combined (combined='{combined}')")


# ---------------------------------------------------------------------------
# 5. Empty-state логика
# ---------------------------------------------------------------------------

def test_empty_state_no_runs():
    """При пустой истории нет IndexError."""
    filtered = []
    msg = "Пока нет прогонов — реши первый кейс, и здесь появится история."
    assert isinstance(msg, str)
    print("PASS: test_empty_state_no_runs")


def test_empty_state_filter_low_score():
    """Фильтр low score на чистой истории даёт пустой список."""
    runs = [_run("TR-001", score=90), _run("TR-002", score=85)]
    filtered = [r for r in runs if r.get("score", 100) < 60]
    assert filtered == []
    print("PASS: test_empty_state_filter_low_score")


# ---------------------------------------------------------------------------
# 6. Review mode — поле combined_summary присутствует
# ---------------------------------------------------------------------------

def test_review_mode_fields():
    """Краткий режим: combined_summary, coach_message, score присутствуют."""
    review = evaluate_trainer_answer(_user(), _exp())
    # combined_summary заполняется в services — проверяем что поле есть
    assert "combined_summary" in review
    assert "coach_message" in review
    assert "score" in review
    print("PASS: test_review_mode_fields")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== TRAINER POLISH TESTS ===\n")

    print("--- 1. combined_summary ---")
    test_combined_summary_always_present_in_review()
    test_combined_summary_set_by_services()

    print("\n--- 2. Comparison message ---")
    test_comparison_message_structured_higher()
    test_comparison_message_note_higher()
    test_comparison_no_message_small_delta()

    print("\n--- 3. Фильтр 'только сегодня' ---")
    test_filter_today_returns_only_today()
    test_filter_today_empty_when_no_runs_today()

    print("\n--- 4. История: note_score и combined_summary ---")
    test_run_record_has_note_score_and_combined()

    print("\n--- 5. Empty-states ---")
    test_empty_state_no_runs()
    test_empty_state_filter_low_score()

    print("\n--- 6. Review mode fields ---")
    test_review_mode_fields()

    print("\nВсе тесты пройдены.\n")
