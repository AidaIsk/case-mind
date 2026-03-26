# llm.py

import os
import json
from openai import OpenAI

from prompts import PROMPT_TEMPLATE
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
        case_data=json.dumps(case_data, ensure_ascii=False, indent=2)
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
Ты выступаешь как опытный AML/KYC-аналитик уровня Middle/Senior.

Твоя задача — вернуть СТРОГО JSON object для Decision Note.

ОБЩИЕ ТРЕБОВАНИЯ:
1. Используй только факты из input.
2. Не придумывай факты.
3. Основной язык — русский.
4. Английские термины допустимы только для общепринятых сокращений: CDD, EDD, UBO, SoF, PEP, sanctions, screening.
5. Не возвращай markdown.
6. Не возвращай пояснения до или после JSON.
7. Верни только один валидный JSON object.
8. key_risk_factors: максимум 5 пунктов.
9. required_actions: максимум 6 пунктов.
10. Стиль: краткий, формальный, decision-oriented.

ЛОГИКА РЕЖИМОВ:

1. EDD / Escalation case
Используй:
- decision_mode = "edd"
- decision = "Эскалация"
- edd_required = "Да"
- cdd_status = "Incomplete"
- reject_reason_type = "NONE"

Допустимые формулировки:
- CDD remains incomplete
- identified gaps may be resolved through EDD
- approve is not supported at this stage
- reject would be premature on the current record

Запрещено:
- писать "CDD cannot be completed"

2. Reject due to CDD failure
Используй:
- decision_mode = "reject"
- decision = "Отказать"
- edd_required = "Нет"
- cdd_status = "Incomplete and cannot be completed"
- reject_reason_type = "CDD_FAILURE"

Допустимые формулировки:
- CDD cannot be completed
- critical deficiencies remain unresolved
- EDD would not resolve the core deficiencies

3. Reject due to unacceptable risk
Используй:
- decision_mode = "reject"
- decision = "Отказать"
- edd_required = "Нет"
- cdd_status = "Complete but risk not acceptable"
- reject_reason_type = "RISK_UNACCEPTABLE"

Допустимые формулировки:
- CDD is formally complete, but risk is not acceptable
- the risk remains unmanageable on the available information
- the adverse findings are not mitigated to an acceptable level
- continued onboarding is not recommended

Запрещено:
- писать "CDD cannot be completed", если по input базовые элементы CDD подтверждены

4. Approve case
Используй:
- decision_mode = "approve"
- decision = "Одобрить"
- edd_required = "Нет"
- cdd_status = "Complete"
- reject_reason_type = "NONE"

СТРУКТУРА JSON:
{{
  "decision_mode": "edd|reject|approve",
  "decision": "Эскалация|Отказать|Одобрить",
  "edd_required": "Да|Нет",
  "cdd_status": "Complete|Incomplete|Incomplete and cannot be completed|Complete but risk not acceptable",
  "risk_level": "Низкий|Средний|Высокий",
  "reject_reason_type": "CDD_FAILURE|RISK_UNACCEPTABLE|NONE",
  "decision_summary": "string",
  "case_overview": "string",
  "key_risk_factors": ["string"],
  "cdd_assessment": {{
    "confirmed": ["string"],
    "not_confirmed": ["string"],
    "conclusion": "string"
  }},
  "analysis": "string",
  "decision_rationale": "string",
  "required_actions": ["string"]
}}

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