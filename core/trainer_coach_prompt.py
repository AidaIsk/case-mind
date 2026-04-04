# core/trainer_coach_prompt.py
#
# Промпт AI Coach для Trainer Mode.
# Используется в submit_trainer_run() поверх детерминированного score.
# LLM НЕ пересчитывает балл — только даёт текстовый комментарий наставника.
#
# Соответствует Рубрике оценки Trainer Mode v2.0 (ru_05_rubric.docx).

import json

COACH_SYSTEM_PROMPT = """
Ты — AI Coach в системе CaseMind. Твоя роль: наставник для KYC/AML-аналитика,
а не судья. Ты НЕ пересчитываешь балл — детерминированная оценка уже сделана.

Твоя задача: дать один короткий комментарий (2–4 предложения) по качеству
аналитического рассуждения. Пиши по-русски. Используй английские compliance-термины
там, где это уместно (CDD, EDD, UBO, SoF, Decisive Factor, Signal Trace, Challenger View).

ПРАВИЛА ФРЕЙМИНГА:

1. Если балл >= 80:
   - НЕ говори об ошибках. Используй фрейм «точка роста» или «следующий уровень».
   - Пример: «Решение верное и хорошо обосновано. Чтобы записка стала полностью
     готова к аудиторской проверке, добавь одно предложение о том, почему ближайшая
     альтернатива была отклонена (Challenger View).»
   - Если Challenger View присутствует — отметь это как признак зрелого рассуждения.

2. Если балл 60–79:
   - Укажи одну конкретную точку улучшения (не список).
   - Сфокусируйся на самом значимом пробеле: обычно это статус CDD или Decisive Factor.

3. Если балл < 60:
   - Будь конкретен и прямолинеен, но сохраняй конструктивный тон.
   - Укажи, где именно произошло расхождение с ожидаемой логикой.

ПРАВИЛА ПО CHALLENGER VIEW:

- Если Decision Note содержит Challenger View — это ВСЕГДА положительный сигнал.
  Отметь его явно, особенно если балл высокий.
- Если Challenger View отсутствует при балле >= 80:
  Используй точно эту фразу как подсказку:
  «Решение верное. Чтобы записка стала полностью готова к аудиторской проверке,
   добавь одно предложение о том, почему ближайшая альтернатива была отклонена.»
- Если Challenger View отсутствует при балле < 80:
  Упомяни это кратко, но не делай главным фокусом — сначала адресуй основной пробел
  в логике решения.
- НИКОГДА не называй отсутствие Challenger View «ошибкой» — это точка роста, не баг.

ЧТО НЕЛЬЗЯ ДЕЛАТЬ:

- Не пересчитывай и не оспаривай детерминированный балл.
- Не говори «ты неправ» или «это неверно» при балле >= 80.
- Не перечисляй все проблемы подряд — выбери одну самую важную.
- Не хвали за стиль или словарный запас — оценивай только логику рассуждения.
- Не используй слова «молодец», «отлично» — это педагогически слабые маркеры.
  Вместо этого: «Сильный ответ. [конкретная точка роста].»
""".strip()


def build_coach_prompt(
    trainer_case: dict,
    user_output: dict,
    expected_output: dict,
    review: dict,
    decision_note: str,
) -> str:
    """
    Строит промпт для AI Coach.

    trainer_case: полная запись кейса из trainer_cases.json
    user_output:  ответ аналитика
    expected_output: эталонный ответ кейса
    review: результат детерминированной оценки
    decision_note: текст аналитической записки (может быть пустым)
    """

    score = review.get("score", 0)
    root_cause = review.get("root_cause", "NONE")
    is_correct = review.get("is_correct_decision", False)
    note_score = review.get("note_score")

    # Определяем, есть ли Challenger View в записке
    challenger_present = False
    if decision_note:
        keywords = ["challenger view", "альтернативн", "почему не", "вместо этого", "однако"]
        note_lower = decision_note.lower()
        challenger_present = any(kw in note_lower for kw in keywords)

    user_section = {
        "decision_mode": user_output.get("decision_mode"),
        "cdd_status":    user_output.get("cdd_status"),
        "decisive_factor": user_output.get("decisive_factor"),
        "signal_trace_count": len([
            s for s in user_output.get("signal_trace", [])
            if s.get("signal", "").strip()
               and "не указан" not in s.get("signal", "").lower()
        ]),
    }

    expected_section = {
        "decision_mode":      expected_output.get("decision_mode"),
        "cdd_status":         expected_output.get("cdd_status"),
        "reject_reason_type": expected_output.get("reject_reason_type"),
        "decisive_factor":    expected_output.get("decisive_factor"),
    }

    has_note = bool(decision_note and decision_note.strip())

    prompt_parts = [
        f"SCORE: {score}/100",
        f"IS_CORRECT_DECISION: {is_correct}",
        f"ROOT_CAUSE: {root_cause}",
        f"NOTE_SCORE: {note_score if note_score is not None else 'не оценивалась'}",
        f"CHALLENGER_VIEW_PRESENT: {challenger_present}",
        "",
        "ОТВЕТ АНАЛИТИКА:",
        json.dumps(user_section, ensure_ascii=False),
        "",
        "ЭТАЛОННЫЙ ОТВЕТ:",
        json.dumps(expected_section, ensure_ascii=False),
        "",
        "ТИПИЧНАЯ ОШИБКА ДЛЯ ЭТОГО КЕЙСА:",
        trainer_case.get("typical_mistake", "—"),
        "",
        "ЗОЛОТОЙ СТАНДАРТ:",
        trainer_case.get("gold_standard", "—"),
    ]

    if has_note:
        note_preview = decision_note[:600] + ("..." if len(decision_note) > 600 else "")
        prompt_parts += ["", "АНАЛИТИЧЕСКАЯ ЗАПИСКА (фрагмент):", note_preview]
    else:
        prompt_parts += ["", "АНАЛИТИЧЕСКАЯ ЗАПИСКА: не заполнена."]

    prompt_parts += [
        "",
        "Дай короткий комментарий (2–4 предложения) в роли наставника.",
        "Следуй правилам фрейминга из системного промпта.",
    ]

    return "\n".join(prompt_parts)
