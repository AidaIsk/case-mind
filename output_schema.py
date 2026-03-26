# output_schema.py

REQUIRED_OUTPUT_KEYS = [
    "decision_mode",
    "decision",
    "edd_required",
    "cdd_status",
    "risk_level",
    "decision_summary",
    "case_overview",
    "key_risk_factors",
    "cdd_assessment",
    "analysis",
    "decision_rationale",
    "required_actions",
    "reject_reason_type",
]

ALLOWED_DECISION_MODES = {"edd", "reject", "approve"}
ALLOWED_DECISIONS = {"Эскалация", "Отказать", "Одобрить"}
ALLOWED_EDD_VALUES = {"Да", "Нет"}
ALLOWED_CDD_STATUS = {
    "Complete",
    "Incomplete",
    "Incomplete and cannot be completed",
    "Complete but risk not acceptable",
}
ALLOWED_RISK_LEVELS = {"Низкий", "Средний", "Высокий"}
ALLOWED_REJECT_REASON_TYPES = {"CDD_FAILURE", "RISK_UNACCEPTABLE", "NONE"}


def validate_output_structure(output: dict) -> tuple[bool, list[str]]:
    errors = []

    if not isinstance(output, dict):
        return False, ["Output is not a dict"]

    for key in REQUIRED_OUTPUT_KEYS:
        if key not in output:
            errors.append(f"Missing key: {key}")

    if errors:
        return False, errors

    if output["reject_reason_type"] not in ALLOWED_REJECT_REASON_TYPES:
        errors.append(f"Invalid reject_reason_type: {output['reject_reason_type']}")

    if output["decision_mode"] not in ALLOWED_DECISION_MODES:
        errors.append(f"Invalid decision_mode: {output['decision_mode']}")

    if output["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"Invalid decision: {output['decision']}")

    if output["edd_required"] not in ALLOWED_EDD_VALUES:
        errors.append(f"Invalid edd_required: {output['edd_required']}")

    if output["cdd_status"] not in ALLOWED_CDD_STATUS:
        errors.append(f"Invalid cdd_status: {output['cdd_status']}")

    if output["risk_level"] not in ALLOWED_RISK_LEVELS:
        errors.append(f"Invalid risk_level: {output['risk_level']}")

    if not isinstance(output["decision_summary"], str):
        errors.append("decision_summary must be a string")

    if not isinstance(output["case_overview"], str):
        errors.append("case_overview must be a string")

    if not isinstance(output["analysis"], str):
        errors.append("analysis must be a string")

    if not isinstance(output["decision_rationale"], str):
        errors.append("decision_rationale must be a string")

    if not isinstance(output["key_risk_factors"], list):
        errors.append("key_risk_factors must be a list")

    if not isinstance(output["required_actions"], list):
        errors.append("required_actions must be a list")

    cdd_assessment = output["cdd_assessment"]
    if not isinstance(cdd_assessment, dict):
        errors.append("cdd_assessment must be an object")
    else:
        for subkey in ["confirmed", "not_confirmed", "conclusion"]:
            if subkey not in cdd_assessment:
                errors.append(f"Missing cdd_assessment.{subkey}")

        if "confirmed" in cdd_assessment and not isinstance(cdd_assessment["confirmed"], list):
            errors.append("cdd_assessment.confirmed must be a list")

        if "not_confirmed" in cdd_assessment and not isinstance(cdd_assessment["not_confirmed"], list):
            errors.append("cdd_assessment.not_confirmed must be a list")

        if "conclusion" in cdd_assessment and not isinstance(cdd_assessment["conclusion"], str):
            errors.append("cdd_assessment.conclusion must be a string")

    if len(output["key_risk_factors"]) > 5:
        errors.append("key_risk_factors must contain at most 5 items")

    if len(output["required_actions"]) > 6:
        errors.append("required_actions must contain at most 6 items")

    return len(errors) == 0, errors


def build_fallback_output(case_data: dict, error_message: str) -> dict:
    """
    Если structured output сломался, UI всё равно сможет что-то показать.
    """
    recommendation = case_data.get("recommendation", "Эскалация")
    risk_level = case_data.get("selected_risk_level", "Средний")

    if recommendation == "Отказать":
        decision_mode = "reject"
        edd_required = "Нет"
        cdd_status = "Incomplete and cannot be completed"
        reject_reason_type = "CDD_FAILURE"
    elif recommendation == "Одобрить":
        decision_mode = "approve"
        edd_required = "Нет"
        cdd_status = "Complete"
        reject_reason_type = "NONE"
    else:
        decision_mode = "edd"
        edd_required = "Да"
        cdd_status = "Incomplete"
        reject_reason_type = "NONE"

    return {
        "decision_mode": decision_mode,
        "decision": recommendation,
        "edd_required": edd_required,
        "cdd_status": cdd_status,
        "risk_level": risk_level,
        "decision_summary": "Структурированный output не был корректно сгенерирован. Использован fallback-режим.",
        "case_overview": f"Клиент: {case_data.get('client_name', '—')}. Тип кейса: {case_data.get('case_type', '—')}.",
        "key_risk_factors": ["Требуется ручная проверка output"],
        "cdd_assessment": {
            "confirmed": [],
            "not_confirmed": [],
            "conclusion": f"Требуется ручная валидация structured output. Ошибка: {error_message}",
        },
        "analysis": "LLM output не прошёл валидацию структуры, поэтому note требует ручной проверки.",
        "decision_rationale": "Использован технический fallback до исправления structured output.",
        "required_actions": ["Проверить prompt, JSON output и валидацию структуры."],
        "reject_reason_type": reject_reason_type,
    }