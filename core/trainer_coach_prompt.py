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


# ===========================================================================
# AI Mentor Layer
# ===========================================================================
#
# Отличие от AI Coach:
#   Coach  — комментирует что было не так (2-4 предложения)
#   Mentor — объясняет как думать лучше + даёт stronger examples
#
# Возвращает структурированный JSON. UI рендерит каждое поле отдельно.
# Deterministic verdict, score, root_cause — не трогает.

MENTOR_SYSTEM_PROMPT = """
Ты — AI Mentor в системе CaseMind для обучения KYC/AML-аналитиков.

Твоя роль — senior reviewer который объясняет джуну как думать лучше.
НЕ судья. НЕ scoring engine. НЕ rubric dump.

Что ты делаешь:
- интерпретируешь результат как наставник
- объясняешь где логика верная, где слабая и почему это важно
- генерируешь более сильную формулировку decisive factor
- пишешь пример короткой рабочей Decision Note

Жёсткие ограничения:
- НЕ меняешь decision_mode (approve / edd / reject)
- НЕ меняешь cdd_status
- НЕ меняешь reject_reason_type
- НЕ пересчитываешь score
- НЕ выдумываешь факты которых нет в кейсе
- НЕ делаешь из короткой задачи длинное эссе

Тон: уважительный, ясный, не обвинительный, не канцелярский.
Язык: русский. Допустимы compliance-термины: CDD, EDD, UBO, SoF, PEP, decisive factor.

Верни ТОЛЬКО валидный JSON без markdown-обёртки:
{
  "mentor_summary": "2-3 предложения: человеческий разбор — что верно, где пробел",
  "what_you_got_right": ["конкретная сильная сторона 1", "конкретная сильная сторона 2"],
  "main_gap": "один главный gap — максимально конкретно",
  "why_it_matters": "почему именно этот gap важен для compliance reasoning",
  "stronger_decisive_factor": "переформулированный decisive factor — точнее и защищаемее",
  "short_reference_note": "пример короткой рабочей Decision Note (3-5 предложений)",
  "next_step": "одно конкретное действие для следующего кейса"
}

Правила генерации stronger_decisive_factor:
- одна главная мысль, не список
- конкретный факт из кейса, не общий вывод
- согласован с decision_mode из deterministic verdict
- если аналитик был близко к верному — улучши формулировку, не переписывай

Правила генерации short_reference_note:
- 3-5 предложений, не больше
- структура: клиент → что установлено → вывод → решение
- нейтральный тон, без обвинений
- Challenger View одной фразой если уместно
- только факты из кейса, без домыслов
""".strip()


def build_mentor_prompt(
    trainer_case:    dict,
    user_output:     dict,
    expected_output: dict,
    review:          dict,
    decision_note:   str,
) -> str:
    """
    Строит prompt для AI Mentor.

    Использует:
    - trainer_case: описание кейса, typical_mistake, gold_standard
    - user_output: ответ аналитика
    - expected_output: эталонный verdict
    - review: deterministic + semantic + note results
    - decision_note: текст записки аналитика

    Не пересказывает rubric — интерпретирует результат как наставник.
    """
    score      = review.get("score", 0)
    root_cause = review.get("root_cause", "NONE")
    is_correct = review.get("is_correct_decision", False)
    note_score = review.get("note_score")
    df_match   = review.get("decisive_factor_semantic_match", "partial")

    # Compact verdict snapshot
    verdict = {
        "decision_mode":      expected_output.get("decision_mode"),
        "cdd_status":         expected_output.get("cdd_status"),
        "reject_reason_type": expected_output.get("reject_reason_type"),
    }

    # What analyst said
    analyst = {
        "decision_mode":      user_output.get("decision_mode"),
        "cdd_status":         user_output.get("cdd_status"),
        "decisive_factor":    (user_output.get("decisive_factor") or "")[:200],
        "signals_count":      _count_real_signals(user_output.get("signal_trace", [])),
    }

    # Semantic advisory context
    sem = review.get("semantic_review") or {}
    sem_block = ""
    if sem:
        missing = sem.get("mandatory_ideas_missing", [])
        hint    = sem.get("coach_hint", "")
        sem_block = (
            f"\nSEMANTIC ADVISORY (для контекста):\n"
            f"decisive_factor_match: {df_match}\n"
            + (f"Пропущенные идеи: {'; '.join(missing)}\n" if missing else "")
            + (f"Hint: {hint}\n" if hint else "")
        )

    # Note advisory context
    note_criteria = (review.get("note_review") or {}).get("note_criteria", {})
    note_block = ""
    if note_criteria:
        weak = [k for k, v in note_criteria.items() if not v]
        note_block = (
            f"\nNOTE REVIEW (для контекста):\n"
            f"note_score: {note_score}\n"
            + (f"Слабые критерии: {', '.join(weak)}\n" if weak else "Все критерии OK\n")
        )

    # Decision note preview
    note_preview = ""
    if decision_note and decision_note.strip():
        preview = decision_note.strip()[:400]
        if len(decision_note.strip()) > 400:
            preview += "…"
        note_preview = f"\nАНАЛИТИЧЕСКАЯ ЗАПИСКА АНАЛИТИКА:\n{preview}"
    else:
        note_preview = "\nАНАЛИТИЧЕСКАЯ ЗАПИСКА: не заполнена."

    # Case context
    case_desc       = trainer_case.get("description_user", "")[:300]
    typical_mistake = trainer_case.get("typical_mistake") or trainer_case.get("common_mistake", "—")
    gold_standard   = trainer_case.get("gold_standard") or trainer_case.get("rationale_gold_standard", "—")
    expected_df     = (expected_output.get("decisive_factor") or "")[:200]

    lines = [
        "КОНТЕКСТ КЕЙСА:",
        f"Описание: {case_desc}",
        f"Типичная ошибка: {typical_mistake}",
        f"Эталонный decisive factor: {expected_df}",
        "",
        "DETERMINISTIC VERDICT (ground truth — не меняй):",
        json.dumps(verdict, ensure_ascii=False),
        "",
        f"ОТВЕТ АНАЛИТИКА:",
        json.dumps(analyst, ensure_ascii=False),
        "",
        f"SCORE: {score}/100  |  ROOT_CAUSE: {root_cause}  |  CORRECT: {is_correct}",
        f"DF_SEMANTIC_MATCH: {df_match}",
        sem_block,
        note_block,
        note_preview,
        "",
        f"GOLD STANDARD RATIONALE (ориентир для shorter_reference_note):",
        gold_standard[:400],
        "",
        "Сгенерируй mentor response в JSON формате согласно system prompt.",
        "stronger_decisive_factor должен быть согласован с verdict['decision_mode'].",
        "short_reference_note пиши только на основе фактов из описания кейса.",
    ]

    return "\n".join(lines)
