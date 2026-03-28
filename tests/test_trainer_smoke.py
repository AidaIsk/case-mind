# tests/test_trainer_smoke.py
# Smoke test для полного цикла Stage 3A:
# загрузка кейса → review → save → история

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core"))

import types
openai_mock = types.ModuleType("openai")
class _FakeClient:
    def __init__(self, **kw): pass
openai_mock.OpenAI = _FakeClient
sys.modules.setdefault("openai", openai_mock)

from core.services import (
    get_trainer_cases,
    get_trainer_case,
    submit_trainer_run,
    get_trainer_runs,
)
from trainer.trainer import load_trainer_runs


def test_full_trainer_cycle():
    print("\n=== TRAINER SMOKE TEST ===\n")

    # 1. Загрузка кейса
    cases = get_trainer_cases()
    assert len(cases) >= 8, f"Ожидали >= 8 кейсов, получили {len(cases)}"
    print(f"[1] Кейсов загружено: {len(cases)} — OK")

    case = get_trainer_case("TR-003")
    assert case is not None
    assert case["case_id"] == "TR-003"
    print(f"[2] Кейс TR-003 загружен: {case['description'][:50]}... — OK")

    # 2. Review — идеальный ответ
    expected = case["expected_output"]
    user_perfect = dict(expected)
    review, run_id = submit_trainer_run("TR-003", user_perfect, expected)

    assert review["score"] >= 85
    assert review["root_cause"] == "NONE"
    assert review["is_correct_decision"] is True
    assert run_id.startswith("RUN-")
    print(f"[3] Review (идеальный): score={review['score']}, root_cause={review['root_cause']} — OK")

    # 3. Review — неверный режим
    user_bad = dict(expected)
    user_bad["decision_mode"] = "edd"
    user_bad["decision"] = "Эскалация"
    user_bad["cdd_status"] = "Incomplete"
    user_bad["reject_reason_type"] = "NONE"
    review_bad, run_id_bad = submit_trainer_run("TR-005", user_bad, get_trainer_case("TR-005")["expected_output"])

    assert review_bad["score"] < 85
    assert not review_bad["is_correct_decision"]
    assert review_bad["root_cause"] in ("UNDER_REJECT", "MISREAD_CDD_STATUS")
    print(f"[4] Review (неверный режим): score={review_bad['score']}, root_cause={review_bad['root_cause']} — OK")

    # 4. История прогонов
    runs = get_trainer_runs()
    assert len(runs) >= 2
    run_ids = [r["run_id"] for r in runs]
    assert run_id in run_ids
    assert run_id_bad in run_ids
    print(f"[5] История: {len(runs)} прогонов, оба run_id найдены — OK")

    # 5. Записи не попали в cases.json
    cases_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "cases.json"
    )
    if os.path.exists(cases_file):
        import json
        with open(cases_file) as f:
            cases_data = json.load(f)
        case_ids = [c.get("case_id", "") for c in cases_data]
        assert run_id not in case_ids, "trainer run_id попал в cases.json!"
        print("[6] Trainer runs не смешаны с cases.json — OK")
    else:
        print("[6] cases.json не существует — OK (чистый стенд)")

    # 6. Структура записи
    last_run = next(r for r in runs if r["run_id"] == run_id)
    for field in ["run_id", "trainer_case_id", "saved_at", "score",
                  "error_type", "root_cause", "is_correct_decision", "review"]:
        assert field in last_run, f"Поле {field} отсутствует в записи"
    print("[7] Структура записи корректна — OK")

    print("\n=== SMOKE TEST PASSED ===\n")


if __name__ == "__main__":
    test_full_trainer_cycle()
