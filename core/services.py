# core/services.py

from llm import generate_structured_decision_output, is_llm_available
from core.renderers import render_decision_note
from validators import validate_case
from helpers import get_rejection_reasons, get_required_actions, build_case_timeline
from schemas import build_case_data
from storage import save_case_record, load_cases, get_case
from logic import get_cdd_status_and_system_decision

from core.semantic_review import run_semantic_review


def process_case(case_data: dict) -> dict:
    """
    Единый сервисный поток обработки кейса:
    case_data -> validation -> structured_output -> note -> derived artifacts
    """
    validation = validate_case(case_data)

    if validation["blocking_errors"]:
        return {
            "ok": False,
            "validation": validation,
            "structured_output": None,
            "note": None,
            "rejection_reasons": [],
            "required_actions": [],
            "timeline": [],
        }

    structured_output = generate_structured_decision_output(case_data)
    note = render_decision_note(structured_output)
    rejection_reasons = get_rejection_reasons(case_data)
    required_actions = get_required_actions(case_data)
    timeline = build_case_timeline(case_data)

    return {
        "ok": True,
        "validation": validation,
        "structured_output": structured_output,
        "note": note,
        "rejection_reasons": rejection_reasons,
        "required_actions": required_actions,
        "timeline": timeline,
    }


def save_result(case_data: dict, result: dict) -> None:
    """Сохраняет результат process_case() в storage. UI вызывает только эту функцию."""
    save_case_record(
        case_data=case_data,
        structured_output=result["structured_output"],
        note=result["note"],
        rejection_reasons=result["rejection_reasons"],
        required_actions=result["required_actions"],
        timeline=result["timeline"],
    )


def get_all_cases() -> list:
    """Возвращает все сохранённые кейсы. UI-точка входа для списка."""
    return load_cases()


def get_case_by_id(case_id: str) -> dict | None:
    """Возвращает кейс по ID. UI-точка входа для просмотра."""
    return get_case(case_id)


def build_case_input(*args, **kwargs) -> dict:
    """Обёртка над schemas.build_case_data. UI не импортирует schemas напрямую."""
    return build_case_data(*args, **kwargs)


def get_case_decision_meta(case_data: dict) -> tuple:
    """Обёртка над logic. UI не импортирует logic напрямую."""
    return get_cdd_status_and_system_decision(case_data)


def check_llm() -> bool:
    """Проверяет доступность LLM. UI не импортирует llm напрямую."""
    return is_llm_available()


# ---------------------------------------------------------------------------
# Trainer Mode API
# ---------------------------------------------------------------------------

from trainer.trainer_cases import get_all_trainer_cases, get_trainer_case_by_id
from trainer.trainer import evaluate_trainer_answer, save_trainer_run, load_trainer_runs
from trainer.trainer_analytics import (
    summarize_trainer_runs,
    get_next_unfinished_trainer_case_for_today,
    get_next_trainer_case,
)
from trainer.trainer_note import evaluate_decision_note


def get_trainer_cases() -> list:
    """Возвращает библиотеку тренировочных кейсов."""
    return get_all_trainer_cases()


def get_trainer_case(case_id: str) -> dict | None:
    """Возвращает тренировочный кейс по ID."""
    return get_trainer_case_by_id(case_id)


def _build_combined_summary(score: int, note_score: int | None, root_cause: str, note_quality: str | None) -> str:
    """
    Одна строка, объединяющая качество structured decision и decision note.
    Вызывается после того как известны оба score.
    """
    has_note = note_score is not None

    if score >= 85 and (not has_note or note_score >= 75):
        return "Структурная логика и аналитическая записка в целом согласованы."

    if score >= 85 and has_note and note_score <= 65:
        return "Ты лучше определяешь решение, чем формулируешь аналитическую записку."

    if has_note and note_score >= 75 and score <= 55:
        return "Записка звучит лучше, чем структурная логика решения — проработай основы CDD/EDD."

    if root_cause in ("OVER_REJECT", "UNDER_REJECT"):
        base = "Основная проблема — неверный режим решения"
        if has_note and note_quality == "weak":
            return f"{base} и слабая аргументация в записке."
        return f"{base}."

    if root_cause in ("WEAK_DECISIVE_FACTOR", "WEAK_SIGNAL_TRACE", "WEAK_RATIONALE"):
        if has_note and note_score and note_score >= 70:
            return "Решение выбрано верно, но структурное обоснование пока слабее записки."
        return "Решение выбрано верно, но аналитическая записка и обоснование требуют доработки."

    if score >= 60:
        if has_note and note_score and note_score < 50:
            return "Решение выбрано верно, но аналитическая записка пока слабее structured-части."
        return "Частичное совпадение с эталоном — есть над чем поработать."

    return "Существенное расхождение с эталоном. Рекомендуется повторить теорию по теме кейса."


def review_trainer_case(user_output: dict, expected_output: dict) -> dict:
    """Сравнивает ответ аналитика с эталоном и возвращает review."""
    return evaluate_trainer_answer(user_output, expected_output)


def submit_trainer_run(
    trainer_case_id: str,
    user_output: dict,
    expected_output: dict,
    decision_note: str = "",
) -> tuple[dict, str]:
    """
    Оркестрирует полный цикл тренировки:
    evaluate → evaluate_note → build_combined_summary → save.
    """
    review = evaluate_trainer_answer(user_output, expected_output)

    if decision_note.strip():
        note_review = evaluate_decision_note(decision_note, user_output, expected_output)
        review["note_score"]  = note_review["note_score"]
        review["note_review"] = note_review
    else:
        review["note_score"]  = None
        review["note_review"] = None

    # Строим combined_summary после получения обоих score
    review["combined_summary"] = _build_combined_summary(
        score      = review["score"],
        note_score = review["note_score"],
        root_cause = review["root_cause"],
        note_quality = (review["note_review"] or {}).get("note_quality"),
    )

    # ── AI Coach Comment — core/trainer_coach_prompt ────────────────────
    # Заменяет trainer/trainer_llm.py → get_coach_comment().
    # Использует COACH_SYSTEM_PROMPT + build_coach_user_prompt():
    #   - trainer_case (typical_mistake, gold_standard, expected_output)
    #   - Challenger View detection и framing rules (rubric v2.0)
    # Optional: если API недоступен или упал — None, система не ломается.
    coach_comment = None
    try:
        import os as _os
        from openai import OpenAI as _OpenAI
        from core.trainer_coach_prompt import COACH_SYSTEM_PROMPT, build_coach_user_prompt

        _api_key = _os.getenv("OPENAI_API_KEY")
        if _api_key:
            _trainer_case = get_trainer_case_by_id(trainer_case_id) or {}
            _oa = _OpenAI(api_key=_api_key)
            _resp = _oa.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": COACH_SYSTEM_PROMPT},
                    {"role": "user",   "content": build_coach_user_prompt(
                        trainer_case    = _trainer_case,
                        user_output     = user_output,
                        expected_output = expected_output,
                        review          = review,
                        decision_note   = decision_note,
                    )},
                ],
                max_tokens=300,
                temperature=0.4,
            )
            coach_comment = _resp.choices[0].message.content.strip() or None
    except Exception:
        pass
    review["ai_coach_comment"] = coach_comment

    run_id = save_trainer_run(
        trainer_case_id, user_output, expected_output, review, decision_note
    )
    return review, run_id


def get_trainer_runs() -> list:
    """Возвращает историю тренировочных прогонов."""
    return load_trainer_runs()


def get_trainer_progress_summary() -> dict:
    """Агрегирует прогресс аналитика по всей истории trainer runs."""
    runs  = load_trainer_runs()
    cases = get_all_trainer_cases()
    return summarize_trainer_runs(runs, cases)


def get_next_unfinished_trainer_case(current_case_id: str | None = None) -> dict | None:
    """Возвращает следующий кейс, не пройденный сегодня."""
    runs  = load_trainer_runs()
    cases = get_all_trainer_cases()
    return get_next_unfinished_trainer_case_for_today(runs, cases, current_case_id)


def get_next_trainer_case_by_mode(
    current_case_id: str | None = None,
    mode: str = "unfinished_today",
) -> dict | None:
    """
    Возвращает следующий кейс по выбранному режиму.
    Режимы: sequential / random / unfinished_today.
    """
    runs  = load_trainer_runs()
    cases = get_all_trainer_cases()
    return get_next_trainer_case(runs, cases, current_case_id, mode)

