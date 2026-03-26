from logic import get_cdd_status_and_system_decision


def _deduplicate(items: list[str]) -> list[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def validate_case(case_data: dict) -> dict:
    warnings = []
    blocking_errors = []

    recommendation = case_data.get("recommendation")
    risk_level = case_data.get("selected_risk_level")
    bo_identified = case_data.get("beneficial_owner_identified")
    supporting_documents = case_data.get("supporting_documents_provided")
    source_of_funds = case_data.get("source_of_funds_summary", "")
    economic_rationale = case_data.get("economic_rationale_clear")
    high_risk_geo = case_data.get("high_risk_jurisdiction_involved")
    ultimate_controller = case_data.get("ultimate_controller_description", "")
    sanctions_result = case_data.get("sanctions_result")
    pep_result = case_data.get("pep_result")
    adverse_media_result = case_data.get("adverse_media_result")
    red_flags = case_data.get("red_flags_selected", [])
    key_risk_driver = case_data.get("key_risk_driver", "")

    cdd_complete, system_decision, decision_status = get_cdd_status_and_system_decision(case_data)

    bo_missing = bo_identified == "Нет"
    docs_missing = supporting_documents == "Нет"
    sof_missing = not source_of_funds.strip()
    econ_not_clear = economic_rationale in ["Не понятен", "Частично"]
    high_risk_selected = risk_level == "Высокий"
    low_risk_selected = risk_level == "Низкий"

    # 1. Одна системная blocking error по конфликту решения аналитика с system logic
    if recommendation == "Одобрить" and system_decision != "Одобрить":
        blocking_errors.append(
            f"Положительное решение недопустимо. По логике системы кейс требует: {system_decision}."
        )

    # 2. Предметные blocking reasons
    if bo_missing:
        blocking_errors.append(
            "Не установлен бенефициарный владелец (UBO)."
        )

    if recommendation == "Одобрить" and sof_missing:
        blocking_errors.append(
            "Источник средств (SoF) не подтверждён."
        )

    if recommendation == "Одобрить" and docs_missing:
        blocking_errors.append(
            "Отсутствуют подтверждающие документы по клиенту или операции."
        )

    if recommendation == "Одобрить" and econ_not_clear:
        blocking_errors.append(
            "Экономический смысл операции не подтверждён."
        )

    if recommendation == "Одобрить" and high_risk_selected:
        blocking_errors.append(
            "Для данного кейса выбор Approve при уровне риска High недопустим."
        )

    if high_risk_geo == "Да" and low_risk_selected:
        blocking_errors.append(
            "При наличии high-risk geography уровень риска не может быть низким."
        )

    if docs_missing and low_risk_selected:
        blocking_errors.append(
            "При отсутствии подтверждающих документов уровень риска не может быть низким."
        )

    # 3. Warnings
    if red_flags and not key_risk_driver.strip():
        warnings.append(
            "Указаны red flags, но не заполнен ключевой драйвер риска."
        )

    if bo_missing and not ultimate_controller.strip():
        warnings.append(
            "UBO не установлен, и при этом не описан фактический контролирующий участник."
        )

    if (
        sanctions_result == "Совпадений нет"
        and pep_result == "Нет"
        and adverse_media_result == "Нет"
        and (bo_missing or sof_missing or docs_missing)
    ):
        warnings.append(
            "Отсутствие негативных screening-результатов не устраняет gaps по UBO, SoF и supporting documents."
        )

    blocking_errors = _deduplicate(blocking_errors)
    warnings = _deduplicate(warnings)

    return {
        "warnings": warnings,
        "blocking_errors": blocking_errors,
        "cdd_complete": cdd_complete,
        "system_decision": system_decision,
        "decision_status": decision_status,
    }