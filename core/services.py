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


def _build_user_note(user_output: dict) -> str:
    """
    Детерминированно собирает короткую записку из beta reasoning fields.
    Без LLM. Работает всегда, даже без API.
    """
    dm      = user_output.get("decision_mode", "")
    cdd     = user_output.get("cdd_status", "")
    df      = (user_output.get("decisive_factor") or "").strip()
    facts   = (user_output.get("_beta_key_facts") or "").strip()
    risk    = (user_output.get("_beta_main_risk") or "").strip()
    why     = (user_output.get("_beta_risk_reasoning") or "").strip()
    actions = (user_output.get("_beta_actions") or "").strip()
    ch      = (user_output.get("_beta_challenger") or "").strip()

    _DM = {"approve": "Одобрить", "edd": "Эскалация (EDD)", "reject": "Отказать"}
    outcome = _DM.get(dm, dm)

    parts = []
    if facts:
        parts.append(f"Установлено: {facts}.")
    if risk and why:
        parts.append(f"{risk} — {why}.")
    elif risk:
        parts.append(f"Основной риск: {risk}.")
    if df:
        parts.append(f"Ключевой фактор: {df}.")
    if actions:
        parts.append(f"Действия: {actions}.")
    parts.append(f"Решение: {outcome}.")
    if ch:
        parts.append(f"{ch}.")

    return " ".join(parts) if parts else ""


def _build_reference_note(
    trainer_case: dict,
    expected_output: dict,
    mentor_short_ref: str,
) -> str:
    """
    Детерминированно строит референсную записку.
    Приоритет: mentor short_reference (LLM) → gold_standard → компиляция из expected_output.
    """
    # Приоритет 1: если Mentor уже сгенерировал short_reference — используем
    if mentor_short_ref and len(mentor_short_ref) > 30:
        return mentor_short_ref

    # Приоритет 2: gold_standard из кейса
    gold = (
        trainer_case.get("gold_standard") or
        trainer_case.get("rationale_gold_standard") or ""
    ).strip()
    if gold and len(gold) > 30:
        # Обрезаем если слишком длинный
        return gold[:600] + ("…" if len(gold) > 600 else "")

    # Приоритет 3: компиляция из expected_output
    dm  = expected_output.get("decision_mode", "")
    df  = (expected_output.get("decisive_factor") or "").strip()
    cdd = expected_output.get("cdd_status", "")
    _DM = {"approve": "Одобрить", "edd": "Эскалация (EDD)", "reject": "Отказать"}
    outcome = _DM.get(dm, dm)

    parts = []
    decisive_signals = [
        s["signal"] for s in expected_output.get("signal_trace", [])
        if s.get("impact") == "DECISIVE"
    ]
    if decisive_signals:
        parts.append(f"Установлено: {decisive_signals[0]}.")
    if df:
        parts.append(f"Ключевой фактор: {df}.")
    parts.append(f"Статус CDD: {cdd}.")
    parts.append(f"Решение: {outcome}.")

    return " ".join(parts) if parts else ""


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

    # ── Semantic review v1 — advisory only ─────────────────────────────
    # Не меняет score, root_cause, is_correct_*.
    # Возвращает None если кейс без semantic_hints или оба флага True.
    trainer_case = get_trainer_case_by_id(trainer_case_id) or {}
    review["semantic_review"] = run_semantic_review(
        user_output               = user_output,
        expected_output           = expected_output,
        trainer_case              = trainer_case,
        decision_note             = decision_note,
        deterministic_decisive_ok = review["is_correct_decisive_factor"],
        deterministic_trace_ok    = review["is_correct_signal_trace"],
    )

    # ── Apply semantic score ──────────────────────────────────────────
    # Deterministic base (max 70) + semantic (max 30) = итоговый score.
    # Делается ДО combined_summary — чтобы summary видел финальный score.
    from trainer.trainer import _apply_semantic_score, _score_decisive_factor
    review["score"] = _apply_semantic_score(
        review["score"],
        review.get("semantic_review"),
    )

    # ── decisive_factor_semantic_match — явный semantic result ────────
    # Приоритет 1: LLM semantic review (если запускался для этого кейса)
    # Приоритет 2: deterministic sanity-check как fallback
    # is_correct_decisive_factor остаётся булевым — backward compat.
    _sr = review.get("semantic_review")
    if _sr and "decisive_factor_semantic_match" in _sr:
        review["decisive_factor_semantic_match"] = _sr["decisive_factor_semantic_match"]
    else:
        review["decisive_factor_semantic_match"] = _score_decisive_factor(
            user_output, expected_output,
        )

    # ── Combined summary — строится по финальному score ───────────────
    review["combined_summary"] = _build_combined_summary(
        score        = review["score"],
        note_score   = review["note_score"],
        root_cause   = review["root_cause"],
        note_quality = (review["note_review"] or {}).get("note_quality"),
    )

    # ── AI Coach Comment — core/trainer_coach_prompt ──────────────────
    # Использует COACH_SYSTEM_PROMPT + build_coach_user_prompt()
    # с Challenger View rules, rubric v2.0, semantic advisory context.
    # Optional: если API недоступен или упал — None, система не ломается.
    coach_comment = None
    try:
        import os as _os
        from openai import OpenAI as _OpenAI
        from core.trainer_coach_prompt import COACH_SYSTEM_PROMPT, build_coach_user_prompt

        _api_key = _os.getenv("OPENAI_API_KEY")
        if _api_key:
            _oa = _OpenAI(api_key=_api_key)
            _resp = _oa.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": COACH_SYSTEM_PROMPT},
                    {"role": "user",   "content": build_coach_user_prompt(
                        trainer_case    = trainer_case,
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

    # ── AI Mentor Layer ───────────────────────────────────────────────
    # Возвращает structured JSON для conversational teaching feedback.
    # Не меняет verdict, score, root_cause. Optional — None если нет API.
    # Сохраняет ai_mentor_status для debug visibility.
    mentor_output = None
    mentor_status = "not_available"
    mentor_error  = None
    try:
        import os as _os2, json as _json
        from openai import OpenAI as _OpenAI2
        from core.trainer_coach_prompt import MENTOR_SYSTEM_PROMPT, build_mentor_prompt

        _api_key2 = _os2.getenv("OPENAI_API_KEY")
        if not _api_key2:
            mentor_status = "not_available"
        else:
            _oa2 = _OpenAI2(api_key=_api_key2)
            _resp2 = _oa2.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": MENTOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": build_mentor_prompt(
                        trainer_case    = trainer_case,
                        user_output     = user_output,
                        expected_output = expected_output,
                        review          = review,
                        decision_note   = decision_note,
                    )},
                ],
                max_tokens=800,
                temperature=0.35,
            )
            raw = _resp2.choices[0].message.content.strip()
            # Убираем markdown-обёртку если модель её добавила
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            mentor_output = _json.loads(raw.strip())
            # Проверяем что хотя бы одно ключевое поле есть
            if not any(k in mentor_output for k in ("opening", "mentor_summary", "main_focus")):
                mentor_status = "missing_key"
                mentor_error  = "Response parsed but missing expected fields"
                mentor_output = None
            else:
                mentor_status = "ok"
    except _json.JSONDecodeError as _e:
        mentor_status = "parse_error"
        mentor_error  = f"JSON parse failed: {str(_e)[:120]}"
    except Exception as _e:
        mentor_status = "api_error"
        mentor_error  = str(_e)[:120]
    review["ai_mentor"]        = mentor_output
    review["ai_mentor_status"] = mentor_status
    review["ai_mentor_error"]  = mentor_error

    # ── Field Review Layer ────────────────────────────────────────────
    # Разбирает каждое beta-поле отдельно как teaching layer.
    # Не меняет verdict, score, root_cause. Optional — None если нет API.
    field_review = None
    try:
        import os as _os3, json as _json3
        from openai import OpenAI as _OA3
        from core.trainer_coach_prompt import (
            FIELD_REVIEW_SYSTEM_PROMPT, build_field_review_prompt
        )
        _key3 = _os3.getenv("OPENAI_API_KEY")
        # Запускаем только если хотя бы одно beta-поле заполнено
        _has_beta = any(
            (user_output.get(k) or "").strip()
            for k in ("_beta_main_risk", "_beta_risk_reasoning",
                      "_beta_actions", "_beta_challenger")
        )
        if _key3 and _has_beta:
            _oa3 = _OA3(api_key=_key3)
            _r3 = _oa3.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": FIELD_REVIEW_SYSTEM_PROMPT},
                    {"role": "user",   "content": build_field_review_prompt(
                        trainer_case    = trainer_case,
                        user_output     = user_output,
                        expected_output = expected_output,
                    )},
                ],
                max_tokens=600,
                temperature=0.2,
            )
            _raw3 = _r3.choices[0].message.content.strip()
            if _raw3.startswith("```"):
                _raw3 = _raw3.split("```")[1]
                if _raw3.startswith("json"):
                    _raw3 = _raw3[4:]
            field_review = _json3.loads(_raw3.strip())
    except Exception:
        pass
    review["field_review"] = field_review

    # ── Note compare layer (teaching, no LLM) ────────────────────────────
    # user_note: детерминированная сборка из beta reasoning fields
    # reference_note: mentor short_reference → gold_standard → compiled
    mentor_short_ref = ""
    if mentor_output and isinstance(mentor_output, dict):
        nb = mentor_output.get("note_block", {}) or {}
        mentor_short_ref = nb.get("short_reference", "") or ""

    user_note_text = _build_user_note(user_output)
    ref_note_text  = _build_reference_note(trainer_case, expected_output, mentor_short_ref)

    review["user_note"]      = user_note_text if user_note_text else None
    review["reference_note"] = ref_note_text  if ref_note_text  else None

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

