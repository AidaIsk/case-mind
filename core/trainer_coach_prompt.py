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
Ты — AI Mentor в системе CaseMind. Умный, спокойный senior reviewer.
Учишь аналитика думать и упаковывать reasoning лучше.

ГЛАВНЫЙ ПРИНЦИП:
Если decision_mode в VERDICT = decision_mode аналитика — логика ВЕРНАЯ.
Тогда ты НЕ correction engine. Говоришь: "логика есть — усилим упаковку."
Если логика неверная — прямо, спокойно, один главный разрыв.

ЖЁСТКИЕ ОГРАНИЧЕНИЯ:
- НЕ меняй decision_mode, cdd_status, reject_reason_type из VERDICT
- НЕ пересчитывай score
- НЕ выдумывай факты которых нет в кейсе
- НЕ пиши длинные объяснения

СТИЛЬ: разговорный, живой. НЕ язык чек-листа ("не указано / отсутствует").
Язык: русский. OK: CDD, EDD, UBO, SoF, PEP, decisive factor.

Верни ТОЛЬКО валидный JSON без markdown:
{
  "opening": "1-2 предложения: человеческий открывающий тезис — верна ли логика и где точка роста",

  "verdict_block": {
    "decision_ok": true,
    "cdd_ok": true,
    "summary": "1 предложение: что верно в логике решения, или где главный разрыв"
  },

  "logic_block": {
    "decisive_factor_verdict": "strong | acceptable | weak",
    "decisive_factor_comment": "1 предложение: конкретно что сильно или что слишком общо",
    "stronger_decisive_factor": "[конкретный факт из кейса] → [что это означает для решения]",
    "signals_strong": ["сигнал который был точным"],
    "signals_weak": ["сигнал который слишком общий или пропущен"]
  },

  "note_block": {
    "note_verdict": "strong | acceptable | weak | not_written | generated",
    "what_works": "1 предложение: что в записке уже хорошо (или null если не написана)",
    "what_to_tighten": "1 предложение: одна конкретная вещь которую усилить",
    "short_reference": "1-2 предложения: очень короткий рабочий вариант записки",
    "full_reference_note": "4-6 предложений: короткая связная analyst note в рабочем профессиональном тоне"
  },

  "score_explanation": "1-2 предложения: почему score именно такой — без rubric, по-человечески",

  "drill_next": "одна фраза: что потренировать в следующем кейсе"
}

ПРАВИЛА opening:
- логика верная → начни с "Решение верное, ..."
- логика неверная → "Вижу логику, но вот где разрыв: ..."
- НЕ начинай с "Ты сделала"

ПРАВИЛА logic_block.stronger_decisive_factor:
- структура: [конкретный факт] → [что означает для решения]
- согласован с decision_mode из VERDICT
- если аналитик был близко — улучши, не переписывай полностью

ПРАВИЛА note_block:
- если записка не заполнена И reasoning blocks пусты:
    note_verdict = "not_written"
    what_works = null
    what_to_tighten = null
    short_reference = null
    full_reference_note = null

- если записка не заполнена НО reasoning blocks есть:
    note_verdict = "generated"
    what_works = null
    what_to_tighten = null
    short_reference = ОБЯЗАТЕЛЕН: 1-2 предложения рабочего варианта
    full_reference_note = ОБЯЗАТЕЛЕН: 4-6 предложений, короткий связный абзац рабочей analyst note

- если записка заполнена:
    оцени как обычно (strong / acceptable / weak)
    short_reference = короткий улучшенный вариант
    full_reference_note = более полный сильный вариант той же записки

- short_reference:
    только факты из кейса
    нейтральный тон
    без обвинений
    очень короткий формат

- full_reference_note:
    только факты из кейса
    4-6 предложений
    один короткий связный абзац
    tone: professional analyst note
    не bullet list
    не markdown report
    не пафосный compliance language
    должно звучать как то, как strong analyst кратко оформил бы кейс в реальной работе
    
ПРАВИЛА score_explanation:
- объясни score разговорно: "Score X потому что..."
- НЕ перечисляй веса rubric
- если логика верная но формулировка слабая — скажи это прямо
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
        note_preview = "\nАНАЛИТИЧЕСКАЯ ЗАПИСКА: не заполнена — сгенерируй в note_block.short_reference."

    # Beta v1: reasoning blocks
    beta_facts   = user_output.get("_beta_key_facts", "")
    beta_risk    = user_output.get("_beta_main_risk", "")
    beta_why     = user_output.get("_beta_risk_reasoning", "")
    beta_actions = user_output.get("_beta_actions", "")
    beta_ch      = user_output.get("_beta_challenger", "")
    beta_block = ""
    if any([beta_facts, beta_risk, beta_why, beta_actions, beta_ch]):
        beta_block = (
            "\nREASONING BLOCKS (beta input — используй для note_block.short_reference):\n"
            + (f"Факты: {beta_facts}\n"        if beta_facts   else "")
            + (f"Риск: {beta_risk}\n"          if beta_risk    else "")
            + (f"Почему риск: {beta_why}\n"    if beta_why     else "")
            + (f"Действия: {beta_actions}\n"   if beta_actions else "")
            + (f"Challenger: {beta_ch}\n"      if beta_ch      else "")
        )

    # Case context
    case_desc       = trainer_case.get("description_user", "")[:300]
    typical_mistake = trainer_case.get("typical_mistake") or trainer_case.get("common_mistake", "—")
    gold_standard   = trainer_case.get("gold_standard") or trainer_case.get("rationale_gold_standard", "—")
    expected_df     = (expected_output.get("decisive_factor") or "")[:200]

    # Framing для LLM: правильная ли логика — ключевой контекст для тона
    logic_correct = (
        user_output.get("decision_mode") == expected_output.get("decision_mode")
    )
    framing = (
        "ЛОГИКА ВЕРНАЯ — аналитик выбрал правильное решение. "
        "Фокус на упаковке: formulation, decisive factor, note."
        if logic_correct else
        "ЛОГИКА ТРЕБУЕТ КОРРЕКЦИИ — decision_mode не совпадает с verdict."
    )

    lines = [
        f"FRAMING: {framing}",
        "",
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
        f"GOLD STANDARD RATIONALE (ориентир для note_block.short_reference):",
        gold_standard[:400],
        beta_block,
        "",
                "Сгенерируй mentor response в JSON формате согласно system prompt.",
        "Если REASONING BLOCKS заполнены И записка не написана: note_verdict = generated, short_reference ОБЯЗАТЕЛЕН.",
        "short_reference строй только на фактах из кейса, нейтральный тон.",
        "full_reference_note тоже строй только на фактах из кейса.",
        "full_reference_note должен быть 4-6 предложений и звучать как короткая рабочая analyst note, а не как one-liner.",
    ]

    return "\n".join(lines)


# ===========================================================================
# Field Review Layer
# ===========================================================================
#
# Разбирает каждую ключевую ячейку Beta v1 отдельно.
# Teaching layer — не меняет verdict, score, root_cause.
# Вызывается в services.py после AI Mentor.

FIELD_REVIEW_SYSTEM_PROMPT = """
Ты — teaching reviewer в системе CaseMind для KYC/AML-аналитиков.

Твоя задача: разобрать каждое поле beta-формы отдельно.
Помочь junior-аналитику понять, чем поля отличаются друг от друга и где он их смешивает.

ЖЁСТКИЕ ОГРАНИЧЕНИЯ:
- НЕ меняй decision_mode, cdd_status, reject_reason_type
- НЕ пересчитывай score
- НЕ противоречь основному mentor review
- НЕ выдумывай факты которых нет в кейсе
- Это teaching layer, а не evaluator

СТИЛЬ:
- коротко — 1-2 предложения на что хорошо, 1-2 на что смешано
- concrete: называй конкретную проблему, не общий вывод
- stronger_version: конкретная формулировка, не совет "будь конкретнее"
- если поле хорошее — скажи честно, не придумывай проблему
- если поле пустое — верни null для этого поля

Язык: русский. OK: CDD, EDD, UBO, SoF, decisive factor.

РАЗНИЦА МЕЖДУ ПОЛЯМИ (важно для teaching):
- main_risk: один вопрос-риск кейса. НЕ итоговое решение, НЕ список сигналов.
- risk_reasoning: ПОЧЕМУ это создаёт риск — связка факт→риск. НЕ повтор main_risk.
- actions: конкретные шаги — что запросить/проверить. НЕ просто "EDD" или "отказать".
- decisive_factor: одна причина РЕШЕНИЯ — [факт]→[что означает для outcome]. НЕ список, НЕ пересказ всего.
- challenger: почему именно этот outcome, а не ближайшая альтернатива. НЕ повтор decisive_factor.

Верни ТОЛЬКО валидный JSON без markdown:
{
  "main_risk": {
    "user_text": "точный текст аналитика из поля main_risk — скопируй как есть",
    "what_is_good": "что точно верно — конкретно",
    "what_is_mixed": "что смешано или слабее — конкретно (или null если всё OK)",
    "stronger_version": "как звучало бы точнее"
  },
  "risk_reasoning": {
    "user_text": "точный текст аналитика из поля risk_reasoning",
    "what_is_good": "...",
    "what_is_mixed": "...",
    "stronger_version": "..."
  },
  "actions": {
    "user_text": "точный текст аналитика из поля actions",
    "what_is_good": "...",
    "what_is_mixed": "...",
    "stronger_version": "..."
  },
  "decisive_factor": {
    "user_text": "точный текст аналитика из поля decisive_factor",
    "what_is_good": "...",
    "what_is_mixed": "...",
    "stronger_version": "..."
  },
  "challenger": {
    "user_text": "точный текст аналитика из поля challenger",
    "what_is_good": "...",
    "what_is_mixed": "...",
    "stronger_version": "..."
  }
}

Правило user_text: скопируй текст аналитика дословно, без изменений.
Если поле пустое или "—" — верни null для этого ключа целиком.
""".strip()


def build_field_review_prompt(
    trainer_case:    dict,
    user_output:     dict,
    expected_output: dict,
) -> str:
    """
    Строит prompt для field-by-field review.
    Использует только beta reasoning fields — не трогает deterministic verdict.
    """
    case_desc   = trainer_case.get("description_user", "")[:300]
    expected_df = (expected_output.get("decisive_factor") or "")[:200]
    verdict_mode = expected_output.get("decision_mode", "")

    main_risk   = user_output.get("_beta_main_risk", "")      or "—"
    risk_why    = user_output.get("_beta_risk_reasoning", "")  or "—"
    actions     = user_output.get("_beta_actions", "")         or "—"
    df          = (user_output.get("decisive_factor") or "")   or "—"
    challenger  = user_output.get("_beta_challenger", "")      or "—"

    typical_mistake = (
        trainer_case.get("typical_mistake") or
        trainer_case.get("common_mistake", "—")
    )

    return "\n".join([
        "КОНТЕКСТ КЕЙСА:",
        f"Описание: {case_desc}",
        f"Ожидаемое решение: {verdict_mode}",
        f"Эталонный decisive factor: {expected_df}",
        f"Типичная ошибка: {typical_mistake}",
        "",
        "ОТВЕТЫ АНАЛИТИКА ПО ПОЛЯМ:",
        f"main_risk (основной риск-вопрос): {main_risk}",
        f"risk_reasoning (почему это риск): {risk_why}",
        f"actions (действия): {actions}",
        f"decisive_factor (главная причина решения): {df}",
        f"challenger (почему не альтернатива): {challenger}",
        "",
        "Разбери каждое поле отдельно согласно system prompt.",
        "Обрати внимание: не смешиваются ли main_risk и risk_reasoning?",
        "Не повторяет ли decisive_factor просто main_risk?",
        "Достаточно ли конкретны actions?",
    ])
