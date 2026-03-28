# llm.py
#
# Интеллектуальный слой системы — единственное место, где языковая модель
# получает данные кейса и формирует структурированный вывод.
#
# Бизнес-назначение: модель не принимает решение — она структурирует
# аналитическую логику аналитика в защищаемый compliance-артефакт.
# Все инструкции в промпте направлены на одно: гарантировать, что
# вывод будет соответствовать требованиям KYC/AML, а не просто
# "звучать убедительно". Регулятор оценивает не качество текста,
# а корректность reasoning и соответствие решения данным кейса.

import os
import json
from openai import OpenAI

from prompts import (
    PROMPT_TEMPLATE,
    LANGUAGE_POLICY,
    DECISION_POLICY,
    OUTPUT_STRUCTURE_POLICY,
    STYLE_POLICY,
)
from output_schema import validate_output_structure, build_fallback_output

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def is_llm_available() -> bool:
    return client is not None


def generate_decision_note(case_data: dict) -> str:
    """
    Старый режим: обычный текстовый note.
    Можно оставить на переходный период.
    """
    if client is None:
        return "Ошибка: не найден OPENAI_API_KEY."

    prompt = PROMPT_TEMPLATE.format(
        language_policy=LANGUAGE_POLICY,
        decision_policy=DECISION_POLICY,
        output_structure_policy=OUTPUT_STRUCTURE_POLICY,
        style_policy=STYLE_POLICY,
        case_data=json.dumps(case_data, ensure_ascii=False, indent=2),
    )

    try:
        response = client.responses.create(
            model="gpt-5.4",
            input=prompt,
        )
        return response.output_text
    except Exception as e:
        return f"Ошибка при генерации: {e}"


def get_structured_output_prompt(case_data: dict) -> str:
    # Промпт — это не просто инструкция для модели.
    # Это формализованная политика KYC/AML, переведённая в язык,
    # который модель может выполнить детерминированно.
    # Каждый блок ниже реализует конкретное бизнес-правило:
    # LANGUAGE_POLICY — предотвращает языковую неоднозначность в аудируемых документах.
    # DECISION_POLICY — реализует Risk-Based Approach: разные данные → разные режимы.
    # OUTPUT_STRUCTURE_POLICY — обеспечивает воспроизводимость формата для аудита.
    # STYLE_POLICY — гарантирует, что записка читается как compliance-документ,
    #   а не как технический отчёт или маркетинговый текст.
    return f"""
{LANGUAGE_POLICY}

{DECISION_POLICY}

{OUTPUT_STRUCTURE_POLICY}

{STYLE_POLICY}

STRUCTURED OUTPUT MODE:

Ты должен вернуть только один валидный JSON object.
Не возвращай markdown.
Не возвращай пояснения до или после JSON.
Не возвращай никакой текст вне JSON.

Дополнительные требования:
1. Используй только факты из input.
2. Не придумывай факты.
3. Все значения строковых полей должны быть на русском языке.
4. Допустимые английские термины внутри строк:
   - CDD
   - EDD
   - UBO
   - SoF
   - PEP
   - sanctions
   - adverse media
   - onboarding
   - screening
5. Не используй полные предложения на английском языке.
6. key_risk_factors: максимум 5 пунктов.
7. required_actions: максимум 6 пунктов.
8. Каждое поле должно быть заполнено по существу, без воды.

ЛОГИКА РЕЖИМОВ:

1. EDD / Escalation case
Используй:
- decision_mode = "edd"
- decision = "Эскалация"
- edd_required = "Да"
- cdd_status = "Incomplete"
- reject_reason_type = "NONE"

Для этого режима:
- CDD не завершён
- недостающая информация может быть получена
- кейс не может быть approved на текущем этапе
- reject преждевременен, если gaps могут быть закрыты через EDD

Разрешённые формулировки:
- "CDD не завершён"
- "Выявленные gaps могут быть закрыты через EDD"
- "На текущем этапе отсутствуют достаточные основания для положительного решения"

Запрещено:
- писать, что "CDD не может быть завершён"

2. Reject due to CDD failure
Используй:
- decision_mode = "reject"
- decision = "Отказать"
- edd_required = "Нет"
- cdd_status = "Incomplete and cannot be completed"
- reject_reason_type = "CDD_FAILURE"

Для этого режима:
- ключевые элементы CDD не подтверждены
- завершение CDD невозможно
- EDD не устранит core deficiencies

Разрешённые формулировки:
- "CDD не может быть завершён"
- "Критические deficiencies остаются неустранёнными"
- "EDD не устранит ключевые gaps"

3. Reject due to unacceptable risk
Используй:
- decision_mode = "reject"
- decision = "Отказать"
- edd_required = "Нет"
- cdd_status = "Complete but risk not acceptable"
- reject_reason_type = "RISK_UNACCEPTABLE"

Для этого режима:
- базовые элементы CDD подтверждены
- но риск остаётся неприемлемым
- негативные findings не снижены до приемлемого уровня
- продолжение onboarding не рекомендуется

Разрешённые формулировки:
- "CDD формально завершён, однако риск не является приемлемым"
- "Риск остаётся неуправляемым на основании доступной информации"
- "Выявленные adverse media / risk findings не снижены до приемлемого уровня"
- "Продолжение onboarding не рекомендуется"

Запрещено:
- писать, что "CDD не может быть завершён", если базовые элементы CDD подтверждены

4. Approve case
Используй:
- decision_mode = "approve"
- decision = "Одобрить"
- edd_required = "Нет"
- cdd_status = "Complete"
- reject_reason_type = "NONE"

Для этого режима:
- базовые элементы CDD подтверждены
- отсутствуют blockers для approval
- риск находится в приемлемых пределах

JSON SCHEMA:
{{
  "decision_mode": "edd|reject|approve",
  "decision": "Эскалация|Отказать|Одобрить",
  "edd_required": "Да|Нет",
  "cdd_status": "Complete|Incomplete|Incomplete and cannot be completed|Complete but risk not acceptable",
  "risk_level": "Низкий|Средний|Высокий",
  "reject_reason_type": "CDD_FAILURE|RISK_UNACCEPTABLE|NONE",
  "decision_summary": "string",
  "case_overview": "string",
  "key_risk_factors": [
    "string"
  ],
  "cdd_assessment": {{
    "confirmed": [
      "string"
    ],
    "not_confirmed": [
      "string"
    ],
    "conclusion": "string"
  }},
  "analysis": "string",
  "decisive_factor": "string",
  "decision_rationale": "string",
  "required_actions": [
    "string"
  ],
  "error_type": "NONE|OVER_REJECT|UNDER_REJECT|MISSED_SIGNAL|WEAK_RATIONALE|CDD_LOGIC_GAP|INCONSISTENT_DECISION",
  "confidence_score": 1,
  "self_review": {{
    "summary": "string",
    "main_gap": "string",
    "what_to_recheck": [
      "string"
    ]
  }},
  "signal_trace": [
    {{
      "signal": "string",
      "category": "CDD|SCREENING|GEOGRAPHY|SOF|ECONOMIC_RATIONALE|PROFILE_MISMATCH|OTHER",
      "impact": "LOW|MEDIUM|HIGH|DECISIVE",
      "direction": "SUPPORTS_DECISION|SUPPORTS_ESCALATION|SUPPORTS_REJECT|MITIGATING",
      "comment": "string"
    }}
  ]
}}

FIELD RULES:

decision_summary:
- 2–4 предложения
- кратко фиксирует итог решения
- без повторения всего кейса

case_overview:
- только сжатое factual summary кейса
- без аналитических выводов

key_risk_factors:
- 3–5 пунктов
- каждый пункт — это конкретный факт или наблюдение, не вывод
- ЗАПРЕЩЕНО: "риск признан неуправляемым", "совокупность факторов делает риск неприемлемым" —
  это выводы, они принадлежат analysis и decision_rationale
- без дублей

cdd_assessment.confirmed:
- только то, что действительно подтверждено по input
- не включай туда предположения

cdd_assessment.not_confirmed:
- только реально незакрытые gaps
- не дублируй confirmed

cdd_assessment.conclusion:
- 1–2 предложения
- должна быть согласована с cdd_status

analysis:
- 1 короткий аналитический абзац — максимум 2–3 предложения
- первое предложение: синтез ключевых факторов в одну мысль (не перечисление через запятую)
  Пример: "Совокупность adverse media и трансграничной посреднической модели формирует неуправляемый риск."
  Не: "adverse media, высокий репутационный риск, трансграничный характер… в совокупности формируют…"
- второе предложение (если нужно): почему именно это решение, а не другое
- без теории и общих объяснений

decisive_factor:
- ОДНА краткая формулировка — максимум 1–2 предложения
- это главный перевешивающий фактор решения, не пересказ всего analysis
- не список, не перечисление нескольких factors
- должен быть логически согласован с decision_mode, cdd_status, reject_reason_type и decision_rationale
- допускает только whitelist-термины на английском: CDD, EDD, UBO, SoF, PEP, sanctions, adverse media, onboarding, screening

Логика по режимам:
  EDD: главный незакрытый gap, из-за которого кейс нельзя одобрить сейчас, но можно продолжить через EDD
    Пример: "Источник средств по операции не подтверждён."
  Reject / CDD_FAILURE: критический CDD-blocker, делающий завершение CDD невозможным
    Пример: "Бенефициарный владелец не установлен и не может быть подтверждён."
  Reject / RISK_UNACCEPTABLE: главный неприемлемый risk finding
    Пример: "Негативные публикации о возможной вовлечённости в сомнительные посреднические схемы не были сняты."
  Approve: главный подтверждающий фактор, позволяющий принять клиента
    Пример: "Ключевые элементы CDD подтверждены, существенные blockers не выявлены."

decision_rationale:
- для Reject (RISK_UNACCEPTABLE): обязательно включи одну фразу — ключевой фактор отказа
  Формат: "Ключевым фактором отказа является [конкретное finding], указывающее на [конкретный риск]."
  Это делает решение защищаемым.
- затем 1 предложение о невозможности принять клиента — без повтора "CDD формально завершён",
  если это уже сказано в Summary или cdd_assessment.conclusion
  Пример: "Поскольку риск не снижен до приемлемого уровня, клиент не может быть принят."
- для Reject (CDD_FAILURE): прямой вывод о том, что завершение CDD невозможно
- для EDD и Approve: прямой ответ на вопрос "можно ли принять клиента на текущем этапе?"

required_actions:
- для EDD: конкретные следующие шаги
- для Reject: procedural actions допустимы
- для Approve: можно оставить пустой список, если дополнительных действий нет

error_type:
- Один главный тип аналитической ошибки reasoning, если она есть
- Выбери строго одно значение из enum:
  NONE              — существенная ошибка не выявлена
  OVER_REJECT       — reject слишком жёсткий; gaps закрываемы через EDD; CDD не невозможен
  UNDER_REJECT      — серьёзные blockers или risk findings игнорируются; reject логичнее
  MISSED_SIGNAL     — важный red flag не отражён в analysis / decisive_factor / rationale
  WEAK_RATIONALE    — вывод допустим, но обоснование слабое, расплывчатое, незащищаемое
  CDD_LOGIC_GAP     — перепутаны "incomplete" и "impossible to complete"; нарушена граница EDD/Reject
  INCONSISTENT_DECISION — поля решения внутренне противоречат друг другу

Правила выбора:
- NONE только если: решение логически согласовано, decisive_factor чёткий, rationale защищаемый
- OVER_REJECT только при decision_mode = reject
- UNDER_REJECT НЕЛЬЗЯ при decision_mode = reject (решение уже отказ)
- При любом error_type != NONE → confidence_score НЕ МОЖЕТ быть 5

confidence_score:
- Целое число от 1 до 5 — уровень уверенности в качестве аналитического вывода
- Это НЕ риск-скор клиента
- Шкала:
  1 — критичные gaps, слабый reasoning, внутренние противоречия
  2 — низкая уверенность, нужны дополнительные подтверждения
  3 — рабочая логика, но есть спорные места
  4 — решение защищаемо, reasoning последовательный
  5 — ключевые элементы подтверждены, логика устойчива
- ЗАПРЕЩЕНО ставить 5 если:
  - error_type != NONE
  - cdd_status = "Incomplete"
  - self_review.main_gap содержит указание на незакрытый существенный gap

self_review:
- summary: 1–2 предложения — краткая самооценка качества решения и его защищаемости
- main_gap: один главный недостаток текущего reasoning
  Если недостатков нет: "Существенных аналитических gaps не выявлено."
  Если error_type != NONE: main_gap обязан содержать конкретный gap — пустое или формальное значение недопустимо
- what_to_recheck: список 1–3 конкретных точек повторной проверки
  Примеры: UBO, SoF, screening findings, consistency of rationale, соответствие decision статусу CDD

signal_trace:
- список 2–6 конкретных сигналов, повлиявших на решение
- каждый объект = один наблюдаемый факт, а не общий вывод
  ЗАПРЕЩЕНО: "совокупность факторов", "риски в целом" — это выводы, не сигналы
  ПРАВИЛЬНО: "Источник средств по операции не подтверждён", "Негативные публикации не сняты"
- ровно один сигнал должен иметь impact = DECISIVE
- decisive_factor = краткая формулировка того же DECISIVE сигнала (должны совпадать по смыслу)
- signal: конкретная формулировка на русском языке (1 предложение)
- category: CDD | SCREENING | GEOGRAPHY | SOF | ECONOMIC_RATIONALE | PROFILE_MISMATCH | OTHER
- impact: LOW | MEDIUM | HIGH | DECISIVE
- direction: SUPPORTS_DECISION | SUPPORTS_ESCALATION | SUPPORTS_REJECT | MITIGATING
- comment: 1 предложение — почему этот сигнал важен для решения

Логика по режимам:
  EDD: сигналы объясняют, почему CDD не завершён, но пробелы закрываемы
    — НЕЛЬЗЯ писать "CDD невозможно завершить" или "завершение невозможно"
    — направление DECISIVE сигнала: SUPPORTS_ESCALATION
  Reject / CDD_FAILURE: сигналы указывают на невозможность завершить CDD
    — UBO, SoF, docs, economic rationale
    — направление DECISIVE сигнала: SUPPORTS_REJECT
  Reject / RISK_UNACCEPTABLE: CDD завершён, но риск неприемлем
    — сигналы — это risk findings (негативные публикации, репутационные риски)
    — НЕЛЬЗЯ включать сигналы о неполноте CDD (UBO не установлен и т.д.)
    — направление DECISIVE сигнала: SUPPORTS_REJECT
  Approve: нейтральные или подтверждающие сигналы
    — НЕЛЬЗЯ включать сигналы с direction = SUPPORTS_REJECT
    — направление DECISIVE сигнала: SUPPORTS_DECISION

СТИЛИСТИЧЕСКИЕ ПРАВИЛА (применяются ко всем строковым полям):

Запрещённые механические обороты — замени на более естественные:
- "Экономическое назначение отношений заявлено" → "Цель отношений заявлена"
- "Экономическое назначение заявлено" → "Цель взаимодействия обозначена"
- "приемлемость общего risk-профиля" → "приемлемость риск-профиля"
- "PEP не установлен" → "PEP не выявлен"
- "санкционные риски не установлены" → "совпадений по санкциям не выявлено"
- "adverse media не установлено" / "adverse media отсутствует" →
  пиши развёрнуто: "негативных публикаций не выявлено" или один раз "adverse media: совпадений нет"
- не повторяй "adverse media" больше одного раза в одном тексте

Общие принципы:
- пиши как аналитик, а не как шаблонный генератор
- избегай номинализаций ("установление факта наличия") — пиши просто ("факт подтверждён")
- не начинай подряд несколько пунктов одним словом

ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ОТВЕТОМ — ОБЯЗАТЕЛЬНО ВЫПОЛНИ КАЖДЫЙ ПУНКт:

1. ФОРМАТ: верни только JSON, без markdown-обёртки, без пояснений до и после.

2. ЯЗЫК — пройди по каждому строковому полю:
   - Найди любое предложение (заканчивающееся на точку), написанное на английском языке.
   - Если нашёл — ПЕРЕПИШИ его на русский.
   - Допустимые английские слова внутри русских предложений: CDD, EDD, UBO, SoF, PEP, sanctions, adverse media, onboarding, screening.
   - ЗАПРЕЩЕНЫ конструкции: "CDD is complete", "risk is not acceptable", "CDD cannot be completed", "not mitigated", "remains unmanageable", "continued onboarding is not recommended", "CDD remains incomplete" — любые полные клаузы на английском.

3. ЛОГИКА РЕЖИМОВ — проверь соответствие:
   - decision_mode = "edd" → cdd_status = "Incomplete", edd_required = "Да", reject_reason_type = "NONE"
   - decision_mode = "reject" + reject_reason_type = "CDD_FAILURE" → cdd_status = "Incomplete and cannot be completed"
   - decision_mode = "reject" + reject_reason_type = "RISK_UNACCEPTABLE" → cdd_status = "Complete but risk not acceptable"
   - decision_mode = "approve" → cdd_status = "Complete", edd_required = "Нет", reject_reason_type = "NONE"

4. ЗАПРЕТ ДЛЯ EDD-КЕЙСОВ — если decision_mode = "edd":
   - НЕЛЬЗЯ писать "CDD не может быть завершён" или "завершение CDD невозможно" в любом поле.
   - НЕЛЬЗЯ писать "EDD не устранит" в любом поле.
   - Правильные формулировки: "CDD не завершён", "gaps могут быть закрыты через EDD".

5. ЗАПРЕТ ДЛЯ RISK_UNACCEPTABLE-КЕЙСОВ — если reject_reason_type = "RISK_UNACCEPTABLE":
   - НЕЛЬЗЯ писать "CDD не может быть завершён".
   - Правильно: "CDD формально завершён, однако риск не является приемлемым".

6. DECISIVE_FACTOR — обязательная самопроверка:
   - поле заполнено (не пустая строка)
   - это одна мысль, а не перечисление нескольких факторов
   - соответствует decision_mode: EDD → незакрытый gap, Reject/CDD_FAILURE → CDD blocker,
     Reject/RISK_UNACCEPTABLE → неприемлемый risk finding, Approve → подтверждающий фактор

7. SELF-REVIEW CONSISTENCY — проверь перед ответом:
   - error_type != NONE → confidence_score не равен 5
   - cdd_status = "Incomplete" → confidence_score не равен 5
   - error_type = OVER_REJECT → decision_mode = "reject"
   - error_type = UNDER_REJECT → decision_mode НЕ "reject"
   - error_type != NONE → self_review.main_gap содержит конкретный gap, не пустую фразу
   - error_type = NONE → self_review.main_gap не содержит слов "критическ", "невозможн", "blocker"

8. SIGNAL TRACE — обязательная самопроверка:
   - в signal_trace есть ровно один сигнал с impact = DECISIVE
   - decisive_factor совпадает по смыслу с текстом этого DECISIVE сигнала
   - если decision_mode = "edd": ни один сигнал не содержит "невозможно завершить" или "не может быть завершён"
   - если reject_reason_type = "RISK_UNACCEPTABLE": ни один сигнал не говорит о неполноте CDD (UBO не установлен и т.д.)
   - если decision_mode = "approve": ни один сигнал не имеет direction = SUPPORTS_REJECT
   - сигналы конкретные ("Негативные публикации не сняты"), не общие ("риски неприемлемы")

INPUT CASE DATA:
{json.dumps(case_data, ensure_ascii=False, indent=2)}
""".strip()

def _extract_json_from_response(text: str) -> dict:
    """
    Извлекает JSON из ответа модели, даже если та добавила лишний текст.

    Бизнес-назначение: модель иногда предваряет JSON объяснением или
    оборачивает в markdown-блок. Без этого шага любое такое отклонение
    приводило бы к fallback, что снижает качество аудируемых записей.
    Строгий режим (raise) в конце гарантирует, что мы не примем
    случайный текст за корректный структурированный вывод.
    """
    text = text.strip()

    # 1. Пробуем сразу
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Пробуем вытащить от первой { до последней }
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and start < end:
        candidate = text[start:end + 1]
        return json.loads(candidate)

    raise ValueError("Не удалось извлечь JSON из ответа модели")


def generate_structured_decision_output(case_data: dict) -> dict:
    # Если ключ API недоступен — возвращаем fallback, а не падаем.
    # Это важно: отсутствие AI не должно блокировать compliance-процесс.
    # Кейс будет помечен как требующий ручной проверки, но не потеряется.
    if client is None:
        return build_fallback_output(case_data, "OPENAI_API_KEY не найден")

    prompt = get_structured_output_prompt(case_data)

    try:
        response = client.responses.create(
            model="gpt-5.4",
            input=prompt,
        )
        raw_text = response.output_text
        parsed = _extract_json_from_response(raw_text)

        # Валидация — обязательный этап, а не опциональная проверка.
        # Модель могла вернуть внутренне противоречивый JSON:
        # например, decision_mode = "edd" с cdd_status = "Complete",
        # или RISK_UNACCEPTABLE без единого риск-сигнала в trace.
        # Без этой проверки такие записи попали бы в cases.json
        # и могли быть использованы при аудите как корректные решения.
        is_valid, errors = validate_output_structure(parsed)
        if not is_valid:
            return build_fallback_output(case_data, "; ".join(errors))

        return parsed

    except Exception as e:
        return build_fallback_output(case_data, str(e))