# core/trainer_coach_prompt.py
#
# AI Coach prompt для Trainer Mode.
# Соответствует Рубрике оценки Trainer Mode v2.0 (ru_05_rubric.docx).
#
# Использование в services.py:
#
#   from core.trainer_coach_prompt import COACH_SYSTEM_PROMPT, build_coach_user_prompt
#
#   response = client.chat.completions.create(
#       model=...,
#       messages=[
#           {"role": "system", "content": COACH_SYSTEM_PROMPT},
#           {"role": "user",   "content": build_coach_user_prompt(
#               trainer_case, user_output, expected_output, review, decision_note
#           )},
#       ],
#       max_tokens=300,
#   )
#   ai_comment = response.choices[0].message.content.strip()

import json

# ── System prompt ────────────────────────────────────────────────────────

COACH_SYSTEM_PROMPT = """
Ты — AI Coach в системе CaseMind. Твоя роль: наставник для KYC/AML-аналитика,
а не судья и не повторный оценщик. Детерминированный балл уже выставлен системой.
Твоя задача — дать один короткий coaching-комментарий (2–4 предложения) по качеству
аналитического рассуждения.

ЯЗЫК: пиши по-русски. Допустимы английские compliance-термины внутри русских предложений:
CDD, EDD, UBO, SoF, Decisive Factor, Signal Trace, Challenger View, Decision Note.

═══════════════════════════════════════════════
ПРАВИЛА ФРЕЙМИНГА (обязательны, приоритет высокий)
═══════════════════════════════════════════════

SCORE >= 80 — фрейм «точка роста», не «исправление ошибки»:
  • Начни с признания сильной стороны ответа.
  • Предлагай ОДНО конкретное улучшение, не список.
  • НЕ используй слова «ошибка», «неверно», «пропущено», «недостаток».
  • Допустимые формулировки: «чтобы сделать позицию ещё более защищаемой»,
    «следующий шаг», «для полной аудиторской готовности».

SCORE 60–79 — фрейм «конкретный gap»:
  • Укажи ОДНУ точку улучшения — самую значимую.
  • Фокус: статус CDD или Decisive Factor (это highest-weight измерения по рубрике).
  • Тон конструктивный, не карательный.

SCORE < 60 — фрейм «прямая обратная связь»:
  • Будь конкретен: где именно произошло расхождение с ожидаемой логикой.
  • Укажи, что именно нужно пересмотреть.
  • Сохраняй профессиональный тон.

═══════════════════════════════════════════════
ПРАВИЛА ПО CHALLENGER VIEW (обязательны)
═══════════════════════════════════════════════

Challenger View — это признак зрелости рассуждения, НЕ базовое требование к правильности.
Его отсутствие не является «ошибкой» в логике решения.

• Если Challenger View ПРИСУТСТВУЕТ в записке — это ВСЕГДА позитивный сигнал.
  Отметь явно, особенно при score >= 80.

• Если Challenger View ОТСУТСТВУЕТ при score >= 80:
  Используй точно эту формулировку (или близкую к ней):
  «Решение верное. Чтобы записка стала полностью готова к аудиторской проверке,
   добавь одно предложение о том, почему ближайшая альтернатива была отклонена.»

• Если Challenger View ОТСУТСТВУЕТ при score < 80:
  Упомяни кратко как второстепенное наблюдение — после основного gap в логике.
  НЕ делай Challenger View главным фокусом при наличии более серьёзных проблем.

• НИКОГДА не называй отсутствие Challenger View «ошибкой» или «критическим пробелом».

═══════════════════════════════════════════════
ЧЕГО НЕЛЬЗЯ ДЕЛАТЬ
═══════════════════════════════════════════════

• Пересчитывать или оспаривать детерминированный балл.
• Говорить «ты неправ» / «это неверно» при score >= 80.
• Перечислять все проблемы подряд — выбери ОДНУ самую важную.
• Хвалить за стиль, словарный запас или использование терминологии.
• Использовать «молодец», «отлично» — это педагогически слабые маркеры.
  Вместо этого: «Сильный ответ. [конкретная точка роста].»
• Писать более 4 предложений.
""".strip()


# ── User prompt builder ───────────────────────────────────────────────────

def build_coach_user_prompt(
    trainer_case: dict,
    user_output: dict,
    expected_output: dict,
    review: dict,
    decision_note: str,
) -> str:
    """
    Строит user-сообщение для AI Coach.

    trainer_case    — полная запись кейса из trainer_cases.json
    user_output     — ответ аналитика (decision_mode, cdd_status, decisive_factor, signal_trace, …)
    expected_output — эталонный ответ кейса (decision_mode, cdd_status, decisive_factor, …)
    review          — результат детерминированной оценки (score, root_cause, is_correct_decision, …)
    decision_note   — текст аналитической записки (может быть пустым)
    """

    score      = review.get("score", 0)
    root_cause = review.get("root_cause", "NONE")
    is_correct = review.get("is_correct_decision", False)
    note_score = review.get("note_score")

    # Detect Challenger View presence
    challenger_present = _has_challenger_view(decision_note)

    # Compact user answer snapshot (не весь dict, только значимые поля)
    user_snap = {
        "decision_mode":        user_output.get("decision_mode"),
        "cdd_status":           user_output.get("cdd_status"),
        "reject_reason_type":   user_output.get("reject_reason_type"),
        "decisive_factor":      (user_output.get("decisive_factor") or "")[:200],
        "signal_count":         _count_real_signals(user_output.get("signal_trace", [])),
    }

    # Compact expected snapshot
    exp_snap = {
        "decision_mode":        expected_output.get("decision_mode"),
        "cdd_status":           expected_output.get("cdd_status"),
        "reject_reason_type":   expected_output.get("reject_reason_type"),
        "decisive_factor":      (expected_output.get("decisive_factor") or "")[:200],
    }

    lines = [
        f"SCORE: {score}/100",
        f"IS_CORRECT_DECISION: {is_correct}",
        f"ROOT_CAUSE: {root_cause}",
        f"NOTE_SCORE: {note_score if note_score is not None else 'нет'}",
        f"CHALLENGER_VIEW_IN_NOTE: {challenger_present}",
        "",
        "ОТВЕТ АНАЛИТИКА:",
        json.dumps(user_snap, ensure_ascii=False),
        "",
        "ЭТАЛОННЫЙ ОТВЕТ:",
        json.dumps(exp_snap, ensure_ascii=False),
        "",
        f"ТИПИЧНАЯ ОШИБКА ДЛЯ ЭТОГО КЕЙСА: {trainer_case.get('typical_mistake', '—')}",
        f"ЗОЛОТОЙ СТАНДАРТ: {trainer_case.get('gold_standard', '—')}",
    ]

    if decision_note and decision_note.strip():
        preview = decision_note.strip()[:500]
        if len(decision_note.strip()) > 500:
            preview += "…"
        lines += ["", "АНАЛИТИЧЕСКАЯ ЗАПИСКА (фрагмент):", preview]
    else:
        lines += ["", "АНАЛИТИЧЕСКАЯ ЗАПИСКА: не заполнена."]

    # ── Advisory context: semantic_hints + semantic_review ──────────────
    # Оба источника — advisory only. Coach читает их для framing,
    # но НЕ пересчитывает score, root_cause, is_correct.

    # 1. semantic_hints из кейса (pilot: только TR-KZ-003)
    semantic_hints = trainer_case.get("semantic_hints")
    if semantic_hints:
        lines += [
            "",
            "ADVISORY CONTEXT — SEMANTIC HINTS (для framing, не для пересчёта score):",
            "Эти подсказки — только контекст для наставника. Deterministic verdict остаётся главным.",
        ]
        for sig in semantic_hints.get("focus_signals", []):
            lines.append(f"  • {sig}")
        warning = semantic_hints.get("coach_warning", "")
        if warning:
            lines.append(f"Типичная ошибка: {warning}")
        wrong_path = semantic_hints.get("closest_wrong_path", "")
        if wrong_path:
            lines.append(f"Ближайший неверный путь: {wrong_path}")

    # 2. semantic_review result (если запускался для этого кейса)
    semantic_review = review.get("semantic_review")
    if semantic_review:
        df_match  = semantic_review.get("decisive_factor_semantic_match", "—")
        missing   = semantic_review.get("mandatory_ideas_missing", [])
        tone      = semantic_review.get("note_tone", "acceptable")
        fairness  = semantic_review.get("fairness_note", "")
        hint      = semantic_review.get("coach_hint", "")

        lines += [
            "",
            "ADVISORY CONTEXT — SEMANTIC REVIEW v1 (advisory only, не меняет score):",
        ]
        if df_match == "match":
            lines.append(
                "✓ Смысл decisive factor верный — аналитик уловил суть своими словами. "
                "Не акцентируй на decisive factor как на ошибке."
            )
        elif df_match == "partial":
            lines.append("~ Decisive factor частично верный — есть правильная идея, но не полностью.")
        elif df_match == "miss":
            lines.append("✗ Decisive factor не попадает в суть кейса.")

        if missing:
            lines.append(f"Пропущенные ключевые идеи: {'; '.join(missing)}")
        if tone == "accusatory":
            lines.append("⚠ В Decision Note выявлен обвинительный тон.")
        if fairness:
            lines.append(f"Fairness note: {fairness}")
        if hint:
            lines.append(f"Coaching hint: {hint}")

    lines += [
        "",
        "Дай coaching-комментарий (2–4 предложения) согласно правилам из system prompt.",
    ]

    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────

def _has_challenger_view(note: str) -> bool:
    """Эвристика: содержит ли записка Challenger View."""
    if not note:
        return False
    keywords = [
        "challenger view", "challenger",
        "альтернативн", "почему не",
        "однако ", "тем не менее",
        "можно было бы",
    ]
    note_lower = note.lower()
    return any(kw in note_lower for kw in keywords)


def _count_real_signals(signal_trace: list) -> int:
    """Считает сигналы, которые аналитик действительно заполнил."""
    return sum(
        1 for s in signal_trace
        if s.get("signal", "").strip()
        and "не указан" not in s.get("signal", "").lower()
        and "автоматически добавлен" not in s.get("comment", "").lower()
    )
