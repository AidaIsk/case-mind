from datetime import datetime


def format_risk(risk_value):
    if risk_value == "Высокий":
        return "Высокий"
    if risk_value == "Средний":
        return "Средний"
    if risk_value == "Низкий":
        return "Низкий"
    return risk_value or "—"


def get_rejection_reasons(case_data: dict) -> list[str]:
    reasons = []

    if case_data.get("beneficial_owner_identified") == "Нет":
        reasons.append("Бенефициарный владелец не установлен")

    if not case_data.get("source_of_funds_summary", "").strip():
        reasons.append("Не указан источник средств (SoF)")

    if case_data.get("supporting_documents_provided") == "Нет":
        reasons.append("Отсутствуют подтверждающие документы")

    if case_data.get("economic_rationale_clear") == "Не понятен":
        reasons.append("Экономический смысл операции не подтверждён")

    if case_data.get("high_risk_jurisdiction_involved") == "Да":
        reasons.append("Выявлена high-risk / чувствительная география")

    if case_data.get("risk_manageable") == "Нет":
        reasons.append("Риск признан неуправляемым")

    if case_data.get("unresolved_screening_issues", "").strip():
        reasons.append("Остались нерешённые вопросы по screening")

    red_flags = case_data.get("red_flags_selected", [])

    if any("оффшор" in x.lower() or "bvi" in x.lower() for x in red_flags):
        reasons.append("Есть признаки оффшорной или транзитной структуры")

    if any("номин" in x.lower() for x in red_flags):
        reasons.append("Есть признаки номинального владения")

    unique_reasons = []
    for r in reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)

    return unique_reasons[:5]


def get_required_actions(case_data: dict) -> list[str]:
    actions = []

    if case_data.get("beneficial_owner_identified") == "Нет":
        actions.append("Установить и документально подтвердить бенефициарного владельца")

    if not case_data.get("ultimate_controller_description", "").strip():
        actions.append("Уточнить, кто фактически контролирует клиента или сделку")

    if not case_data.get("source_of_funds_summary", "").strip():
        actions.append("Запросить и подтвердить источник средств (SoF) по операции")

    if case_data.get("supporting_documents_provided") == "Нет":
        actions.append("Получить подтверждающие документы по операции (договор, инвойс, акты, переписка, иные основания платежа)")

    if case_data.get("economic_rationale_clear") == "Не понятен":
        actions.append("Запросить объяснение экономического смысла операции и роли клиента в сделке")

    if case_data.get("matches_client_profile") in ["Нет", "Частично"]:
        actions.append("Подтвердить, почему операция соответствует профилю и деятельности клиента")

    if case_data.get("high_risk_jurisdiction_involved") == "Да":
        actions.append("Провести усиленную проверку по географии сделки и объяснить роль задействованных юрисдикций")

    if case_data.get("unresolved_screening_issues", "").strip():
        actions.append("Закрыть нерешённые screening-вопросы по клиенту или контрагенту")

    red_flags = case_data.get("red_flags_selected", [])

    if any("оффшор" in x.lower() or "bvi" in x.lower() for x in red_flags):
        actions.append("Подтвердить деловую цель участия оффшорного / внешнего контрагента и источник его средств")

    if any("номин" in x.lower() for x in red_flags):
        actions.append("Проверить отсутствие номинального владения и подтвердить самостоятельность клиента")

    if any("tbml" in x.lower() or "trade" in x.lower() for x in red_flags):
        actions.append("Подтвердить коммерческую логику сделки: маршрут товара, цену, роли сторон и экономическую функцию клиента")

    if any("документ" in x.lower() for x in red_flags):
        actions.append("Собрать полный комплект документов, подтверждающих операцию и её деловую цель")

    if case_data.get("missing_information_summary", "").strip():
        actions.append("Запросить недостающую информацию, указанную аналитиком в summary gaps")

    unique_actions = []
    for action in actions:
        if action not in unique_actions:
            unique_actions.append(action)

    return unique_actions[:6]


def build_case_timeline(case_data: dict) -> list[dict]:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    return [
        {
            "time": timestamp,
            "event": "Кейс создан / обновлён",
            "details": f"{case_data.get('case_type', '—')} • {case_data.get('client_name', '—')}",
        },
        {
            "time": timestamp,
            "event": "Сформирована аналитическая записка",
            "details": f"Риск: {case_data.get('selected_risk_level', '—')}",
        },
        {
            "time": timestamp,
            "event": "Принято решение",
            "details": f"{case_data.get('recommendation', '—')}",
        },
    ]