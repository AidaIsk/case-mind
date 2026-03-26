def get_cdd_status_and_system_decision(case_data: dict):
    bo_missing = case_data.get("beneficial_owner_identified") == "Нет"
    sof_missing = not case_data.get("source_of_funds_summary", "").strip()
    docs_missing = case_data.get("supporting_documents_provided") == "Нет"
    econ_not_clear = case_data.get("economic_rationale_clear") == "Не понятен"

    cdd_complete = not (bo_missing or sof_missing or econ_not_clear or docs_missing)

    # 1. UBO missing = hard blocker
    if bo_missing:
        return False, "Отказать", "Заблокировано"

    # 2. Если CDD incomplete, но пробелы теоретически можно закрыть документами → Эскалация
    if sof_missing or docs_missing or econ_not_clear:
        return False, "Эскалация", "Ограничено"

    # 3. Даже при complete CDD может быть escalation по риск-контексту
    if case_data.get("risk_manageable") == "Нет":
        return True, "Отказать", "Ограничено"

    if case_data.get("high_risk_jurisdiction_involved") == "Да":
        return True, "Эскалация", "Ограничено"

    return True, "Одобрить", "Разрешено"