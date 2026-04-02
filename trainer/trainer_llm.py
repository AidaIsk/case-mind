# trainer/trainer_llm.py
#
# AI Coach layer для Trainer Mode.
#
# Архитектурный принцип:
#   - deterministic review (trainer.py) работает независимо и не трогается
#   - этот модуль — тонкий слой поверх: получает готовый review и добавляет coach comment
#   - если LLM недоступен или упал — Trainer продолжает работать без изменений
#
# Публичный API:
#   get_coach_comment(case_description, user_output, deterministic_review) -> str | None

import os
import json

_COACH_PROMPT = """Ты — AI Coach внутри Trainer Mode системы CaseMind.
Твоя задача: не оценивать кейс заново и не пересчитывать результат, а помочь пользователю понять качество своего reasoning.

ВАЖНО: не принимай решение заново, не пересчитывай score, не меняй error_type, не спорь с deterministic review, не будь judge. Будь coach layer поверх уже готового review.

Что нужно сделать:
- коротко отметить, что в reasoning было сильным
- назвать одну конкретную слабость, привязанную к данному кейсу — не общую
- дать один главный practical improvement
- если score >= 85 и ошибок нет: сосредоточься на том, что было особенно точным, и дай совет на усложнение
- используй gold_standard_rationale только чтобы понять разрыв между ответом пользователя и эталоном — не цитируй его дословно

Требования к ответу:
- 3–5 предложений
- русский язык
- тон: спокойный, профессиональный, supportive
- без списков, без markdown, без длинной теории AML/KYC
- не переписывай весь ответ пользователя
- не давай новый полный solution
- не повторяй дословно deterministic review
- можно использовать термины CDD, EDD, SoF, UBO

Верни только сам coach comment — без заголовков, без пояснений, без markdown."""


def _build_coach_prompt(
    case_description: str,
    user_output: dict,
    deterministic_review: dict,
) -> str:
    """Собирает финальный промпт с данными кейса и review."""
    user_section = json.dumps({
        "decision":   user_output.get("decision", "—"),
        "risk_level": user_output.get("risk_level", "—"),
        "rationale":  user_output.get("decision_rationale") or user_output.get("decisive_factor", "—"),
    }, ensure_ascii=False, indent=2)

    review_section = json.dumps({
        "score":                 deterministic_review.get("score"),
        "error_type":            deterministic_review.get("error_type"),
        "root_cause":            deterministic_review.get("root_cause"),
        "short_summary":         deterministic_review.get("review_summary"),
        "what_was_good":         deterministic_review.get("what_was_good"),
        "what_was_missed":       deterministic_review.get("what_was_missed"),
        "gold_standard_rationale": (
            deterministic_review.get("note_review", {}) or {}
        ).get("note_summary") or deterministic_review.get("review_summary"),
    }, ensure_ascii=False, indent=2)

    return (
        f"{_COACH_PROMPT}\n\n"
        f"---\n"
        f"ОПИСАНИЕ КЕЙСА:\n{case_description}\n\n"
        f"ОТВЕТ ПОЛЬЗОВАТЕЛЯ:\n{user_section}\n\n"
        f"DETERMINISTIC REVIEW:\n{review_section}\n"
    )


def get_coach_comment(
    case_description: str,
    user_output: dict,
    deterministic_review: dict,
) -> str | None:
    """
    Генерирует AI Coach Comment поверх deterministic review.

    Возвращает строку с комментарием или None при любой ошибке.
    Никогда не бросает исключение наружу — Trainer работает независимо от этой функции.

    Args:
        case_description:     краткое описание кейса из trainer_case["description_user"]
        user_output:          structured output аналитика
        deterministic_review: результат evaluate_trainer_answer()
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception:
        return None

    prompt = _build_coach_prompt(case_description, user_output, deterministic_review)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # быстро и дёшево для coach layer
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,       # немного вариативности, но без галлюцинаций
        )
        comment = response.choices[0].message.content.strip()
        if not comment:
            return None
        return comment

    except Exception:
        # Любая ошибка API — молча возвращаем None, Trainer не падает
        return None
