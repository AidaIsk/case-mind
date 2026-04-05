# core/semantic_review.py  —  Semantic Review Layer v1 (advisory only)
#
# Принцип: этот модуль только читает и анализирует — он ничего не меняет.
# Детерминированный score, root_cause, is_correct_* остаются нетронутыми.
#
# Что делает:
#   - оценивает смысл decisive_factor аналитика vs эталон
#   - проверяет покрытие mandatory_ideas
#   - оценивает тон Decision Note
#   - возвращает контекст для AI Coach и wording diagnosis
#
# Что НЕ делает:
#   - не меняет score
#   - не меняет is_correct_decisive_factor
#   - не меняет root_cause
#   - не применяет upgrade / downgrade
#
# Вызывается только если:
#   - кейс имеет поле semantic_hints
#   - хотя бы один из deterministic флагов (decisive / trace) = False
#
# При любой ошибке или отсутствии API — возвращает None, система работает как раньше.

import json
import os
from typing import Optional


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
Ты — semantic advisor внутри KYC/AML Trainer Mode системы CaseMind.
Твоя роль: помочь AI Coach понять, верно ли аналитик уловил суть кейса,
даже если формулировка отличается от эталона.

Ты НЕ переоцениваешь финальное решение — оно уже проверено детерминированно.
Ты оцениваешь только смысловое качество аргументации.

Правила оценки:
- Аналитик мог выразить правильную идею другими словами — это не ошибка, это стиль.
- mandatory_ideas — обязательные концепции. Если их нет — это реальный пробел в понимании.
- supporting_ideas — дополнительный контекст, их отсутствие не является ошибкой.
- note_tone = "accusatory" только при явных обвинениях без доказательств:
  "клиент явно отмывает", "очевидный преступник" и т.п.
- Будь конкретным: если mandatory idea присутствует своими словами — засчитывай её.

Верни ТОЛЬКО валидный JSON без markdown, без пояснений.
""".strip()


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(
    user_decisive:     str,
    user_signals:      list[str],
    user_note:         str,
    expected_decisive: str,
    semantic_hints:    dict,
    decision_mode:     str,
) -> str:
    mandatory  = semantic_hints.get("mandatory_ideas", [])
    supporting = semantic_hints.get("supporting_ideas", [])

    clean_signals = [
        s for s in user_signals
        if s
        and "не указан" not in s.lower()
        and "автоматически" not in s.lower()
    ]

    return f"""
КОНТЕКСТ КЕЙСА:
- Режим решения (уже проверен): {decision_mode}
- Эталонный decisive factor: {expected_decisive}
- Обязательные идеи (mandatory_ideas): {json.dumps(mandatory, ensure_ascii=False)}
- Поддерживающие идеи (supporting_ideas): {json.dumps(supporting, ensure_ascii=False)}

ОТВЕТ АНАЛИТИКА:
- Decisive factor: {user_decisive or "(не заполнен)"}
- Сигналы: {json.dumps(clean_signals, ensure_ascii=False)}
- Decision Note (первые 400 символов): {(user_note or "")[:400] or "(не заполнена)"}

Верни JSON строго в таком формате — без markdown, без текста до/после:
{{
  "decisive_factor_semantic_match": "match" | "partial" | "miss",
  "mandatory_ideas_found": ["идеи из mandatory_ideas, которые есть в ответе аналитика"],
  "mandatory_ideas_missing": ["идеи из mandatory_ideas, которых нет"],
  "signal_trace_semantic_coverage": "covered" | "partial" | "missed_key",
  "note_tone": "professional" | "acceptable" | "accusatory",
  "fairness_note": "одно предложение для Coach: верно ли аналитик понял суть, независимо от формулировки",
  "coach_hint": "одно предложение с конкретной подсказкой — что улучшить в аргументации"
}}

Логика decisive_factor_semantic_match:
- "match"   — аналитик уловил ту же ключевую идею, пусть другими словами
- "partial" — часть идеи есть, но не вся
- "miss"    — формулировка далека от сути кейса
""".strip()


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(system: str, user: str) -> Optional[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=350,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        # Убираем markdown-обёртку если модель её добавила
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

_VALID = {
    "decisive_factor_semantic_match": {"match", "partial", "miss"},
    "signal_trace_semantic_coverage": {"covered", "partial", "missed_key"},
    "note_tone":                      {"professional", "acceptable", "accusatory"},
}


def _normalize(raw: dict, mandatory: list[str]) -> dict:
    """Нормализует выход LLM, заполняет безопасные дефолты."""
    df_match  = raw.get("decisive_factor_semantic_match", "partial")
    trace_cov = raw.get("signal_trace_semantic_coverage", "partial")
    tone      = raw.get("note_tone", "acceptable")

    if df_match  not in _VALID["decisive_factor_semantic_match"]: df_match  = "partial"
    if trace_cov not in _VALID["signal_trace_semantic_coverage"]: trace_cov = "partial"
    if tone      not in _VALID["note_tone"]:                      tone      = "acceptable"

    found   = raw.get("mandatory_ideas_found", [])
    missing = raw.get("mandatory_ideas_missing", mandatory)

    if not isinstance(found,   list): found   = []
    if not isinstance(missing, list): missing = mandatory

    # Согласованность: если все mandatory найдены — coverage не может быть missed_key
    if not missing and trace_cov == "missed_key":
        trace_cov = "partial"

    return {
        "decisive_factor_semantic_match":  df_match,
        "mandatory_ideas_found":           found,
        "mandatory_ideas_missing":         missing,
        "signal_trace_semantic_coverage":  trace_cov,
        "note_tone":                       tone,
        "fairness_note":                   (raw.get("fairness_note") or "").strip(),
        "coach_hint":                      (raw.get("coach_hint") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_semantic_review(
    user_output:     dict,
    expected_output: dict,
    trainer_case:    dict,
    decision_note:   str = "",
    *,
    deterministic_decisive_ok: bool = True,
    deterministic_trace_ok:    bool = True,
) -> Optional[dict]:
    """
    Запускает semantic review и возвращает advisory dict.

    Возвращает None если:
      - оба детерминированных флага True (semantic не нужен)
      - кейс не имеет semantic_hints
      - mandatory_ideas пуст
      - LLM недоступен или вернул невалидный ответ

    Никогда не бросает исключение наружу.
    Не изменяет score, root_cause, is_correct_* — только возвращает контекст.
    """
    # Guard 1: если deterministic доволен обоими — не тратим API
    if deterministic_decisive_ok and deterministic_trace_ok:
        return None

    # Guard 2: кейс должен иметь semantic_hints с непустыми mandatory_ideas
    semantic_hints = trainer_case.get("semantic_hints")
    if not semantic_hints:
        return None

    mandatory = semantic_hints.get("mandatory_ideas", [])
    if not mandatory:
        return None

    user_signals = [
        s.get("signal", "")
        for s in user_output.get("signal_trace", [])
    ]

    try:
        prompt = _build_prompt(
            user_decisive     = user_output.get("decisive_factor", ""),
            user_signals      = user_signals,
            user_note         = decision_note,
            expected_decisive = expected_output.get("decisive_factor", ""),
            semantic_hints    = semantic_hints,
            decision_mode     = expected_output.get("decision_mode", ""),
        )
        raw = _call_llm(_SYSTEM_PROMPT, prompt)
        if raw is None:
            return None
        return _normalize(raw, mandatory)
    except Exception:
        return None
