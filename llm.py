# llm.py

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
  "decision_rationale": "string",
  "required_actions": [
    "string"
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

INPUT CASE DATA:
{json.dumps(case_data, ensure_ascii=False, indent=2)}
""".strip()

def _extract_json_from_response(text: str) -> dict:
    """
    Пытаемся аккуратно извлечь JSON даже если модель случайно добавила лишнее.
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

        is_valid, errors = validate_output_structure(parsed)
        if not is_valid:
            return build_fallback_output(case_data, "; ".join(errors))

        return parsed

    except Exception as e:
        return build_fallback_output(case_data, str(e))