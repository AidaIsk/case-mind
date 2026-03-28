# renderers.py
#
# Слой рендеринга — превращает валидный JSON в читаемую Аналитическую записку.
#
# Бизнес-назначение: Decision Note — это не просто отчёт, это юридический
# артефакт, который аналитик подписывает своим именем и который может быть
# запрошен регулятором. Порядок блоков в записке отражает логику
# compliance-рассуждения: факты → сигналы → ключевой фактор → оценка качества
# → решение. Если убрать любой из блоков — записка теряет структуру,
# необходимую для аудита, и становится просто текстом без навигации.

# Словари перевода enum-значений в читаемые метки.
# CDD-статусы — не просто ярлыки: каждый из них несёт регуляторный смысл.
# "Incomplete and cannot be completed" — это юридически значимая формулировка:
# она означает, что банк предпринял все разумные меры, но UBO/SoF
# установить невозможно. Именно эта формулировка защищает банк
# при оспаривании отказа в суде или перед регулятором.
_CDD_STATUS_LABELS = {
    "Complete": "CDD завершён",
    "Incomplete": "CDD не завершён",
    "Incomplete and cannot be completed": "CDD не может быть завершён",
    "Complete but risk not acceptable": "CDD завершён, риск не является приемлемым",
}

# Разделение причин отказа критично для отчётности:
# CDD_FAILURE и RISK_UNACCEPTABLE требуют разных действий от клиента
# и разной документации в compliance-файле.
_REJECT_REASON_LABELS = {
    "CDD_FAILURE": "Невозможность завершить CDD",
    "RISK_UNACCEPTABLE": "Неприемлемый риск",
    "NONE": None,
}


def _render_list(items: list[str]) -> list[str]:
    if not items:
        return ["- —"]
    return [f"- {item}" for item in items]


def _render_self_review(output: dict) -> list[str]:
    """
    Блок Self-Review в записке — это инструмент второй линии защиты.
    Надзорный офицер видит: какой тип ошибки зафиксирован, насколько
    аналитик уверен в reasoning и что стоит перепроверить —
    не перечитывая весь кейс. Убрать этот блок значит лишить
    руководство механизма быстрого контроля качества решений.
    """
    lines = []
    error_type = output.get("error_type", "—")
    confidence_score = output.get("confidence_score", "—")
    sr = output.get("self_review", {})

    lines.append("## Self-Review")
    lines.append(f"**Тип ошибки:** {error_type}  ")
    lines.append(f"**Уверенность:** {confidence_score}/5")
    lines.append("")
    lines.append(f"**Краткая самооценка:** {sr.get('summary', '—')}")
    lines.append(f"**Главный gap:** {sr.get('main_gap', '—')}")
    lines.append("")
    lines.append("**Что перепроверить:**")
    lines.extend(_render_list(sr.get("what_to_recheck", [])))
    lines.append("")
    return lines


def _render_signal_trace(output: dict) -> list[str]:
    """
    Signal Trace — explainability-артефакт для регулятора и аудитора.
    Он отвечает на вопрос: "Из каких конкретных фактов вытекает это решение?"
    Без него Decision Note — это мнение аналитика без обоснования.
    С ним — прослеживаемая цепочка от наблюдения к выводу,
    что соответствует принципам прозрачности AI-систем в финансовом секторе.
    """
    lines = []
    trace = output.get("signal_trace", [])

    lines.append("## Signal Trace")
    if not trace:
        lines.append("- —")
    else:
        for sig in trace:
            impact = sig.get("impact", "—")
            signal = sig.get("signal", "—")
            comment = sig.get("comment", "").strip()
            prefix = f"[{impact}]"
            lines.append(f"- {prefix} {signal}")
            if comment:
                lines.append(f"  _{comment}_")
    lines.append("")
    return lines


def render_edd_note(output: dict) -> str:
    # EDD-записка: CDD не завершён, но пробелы закрываемы.
    # Required Actions здесь обязательны — без них записка
    # не отвечает на вопрос "что делать дальше",
    # что делает эскалацию формальной, а не действенной.
    lines = []

    lines.append("## Decision Summary")
    cdd_status_label = _CDD_STATUS_LABELS.get(output.get("cdd_status", ""), output.get("cdd_status", "—"))

    lines.append(f"**Решение:** {output.get('decision', '—')}  ")
    lines.append(f"**Статус CDD:** {cdd_status_label}  ")
    lines.append(f"**Уровень риска:** {output.get('risk_level', '—')}  ")
    lines.append(f"**EDD:** {output.get('edd_required', '—')}")
    lines.append("")
    lines.append(output.get("decision_summary", "—"))
    lines.append("")

    lines.append("## Case Overview")
    lines.append(output.get("case_overview", "—"))
    lines.append("")

    lines.append("## Key Risk Factors")
    lines.extend(_render_list(output.get("key_risk_factors", [])))
    lines.append("")

    cdd = output.get("cdd_assessment", {})

    lines.append("## CDD Assessment")
    lines.append("**Подтверждено:**")
    lines.extend(_render_list(cdd.get("confirmed", [])))
    lines.append("")
    lines.append("**Не подтверждено:**")
    lines.extend(_render_list(cdd.get("not_confirmed", [])))
    lines.append("")
    lines.append(f"**Вывод:** {cdd.get('conclusion', '—')}")
    lines.append("")

    lines.append("## Analysis")
    lines.append(output.get("analysis", "—"))
    lines.append("")

    lines.extend(_render_signal_trace(output))

    lines.append("## Decisive Factor")
    lines.append(output.get("decisive_factor", "—"))
    lines.append("")

    lines.extend(_render_self_review(output))

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))
    lines.append("")

    lines.append("## Required Actions")
    lines.extend(_render_list(output.get("required_actions", [])))

    return "\n".join(lines)


def render_reject_note(output: dict) -> str:
    # Reject-записка: два принципиально разных основания.
    # CDD_FAILURE — невозможно установить UBO или SoF,
    #   отказ обязателен независимо от уровня риска.
    # RISK_UNACCEPTABLE — CDD завершён, но risk appetite превышен
    #   (adverse media, Sanctions, PEP-связи не сняты).
    # Смешение этих оснований в одной формулировке делает
    # отказ уязвимым для оспаривания: клиент вправе спросить,
    # что именно было проблемой — данные или риск.
    lines = []

    reject_reason_type = output.get("reject_reason_type", "NONE")
    cdd_status_label = _CDD_STATUS_LABELS.get(output.get("cdd_status", ""), output.get("cdd_status", "—"))
    reject_label = _REJECT_REASON_LABELS.get(reject_reason_type)

    lines.append("## Decision Summary")
    lines.append(f"**Решение:** {output.get('decision', '—')}  ")
    lines.append(f"**Статус CDD:** {cdd_status_label}  ")
    lines.append(f"**Уровень риска:** {output.get('risk_level', '—')}  ")
    lines.append(f"**EDD:** {output.get('edd_required', '—')}  ")

    if reject_label:
        lines.append(f"**Тип отказа:** {reject_label}")

    lines.append("")
    lines.append(output.get("decision_summary", "—"))
    lines.append("")

    lines.append("## Case Overview")
    lines.append(output.get("case_overview", "—"))
    lines.append("")

    lines.append("## Key Risk Factors")
    lines.extend(_render_list(output.get("key_risk_factors", [])))
    lines.append("")

    cdd = output.get("cdd_assessment", {})

    lines.append("## CDD Assessment")
    lines.append("**Подтверждено:**")
    lines.extend(_render_list(cdd.get("confirmed", [])))
    lines.append("")
    lines.append("**Не подтверждено:**")
    lines.extend(_render_list(cdd.get("not_confirmed", [])))
    lines.append("")
    lines.append(f"**Вывод:** {cdd.get('conclusion', '—')}")
    lines.append("")

    lines.append("## Analysis")
    lines.append(output.get("analysis", "—"))
    lines.append("")

    lines.extend(_render_signal_trace(output))

    lines.append("## Decisive Factor")
    lines.append(output.get("decisive_factor", "—"))
    lines.append("")

    lines.extend(_render_self_review(output))

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))
    lines.append("")

    actions = output.get("required_actions", [])
    if actions:
        lines.append("## Procedural Actions")
        lines.extend(_render_list(actions))

    return "\n".join(lines)


def render_approve_note(output: dict) -> str:
    # Approve-записка: CDD завершён, risk appetite не превышен.
    # Даже при положительном решении записка должна документировать
    # подтверждённые элементы CDD — это защита банка при последующей
    # проверке: если клиент окажется вовлечён в схему,
    # записка покажет, что на момент onboarding все проверки были пройдены.
    lines = []

    cdd_status_label = _CDD_STATUS_LABELS.get(output.get("cdd_status", ""), output.get("cdd_status", "—"))

    lines.append("## Decision Summary")
    lines.append(f"**Решение:** {output.get('decision', '—')}  ")
    lines.append(f"**Статус CDD:** {cdd_status_label}  ")
    lines.append(f"**Уровень риска:** {output.get('risk_level', '—')}  ")
    lines.append(f"**EDD:** {output.get('edd_required', '—')}")
    lines.append("")
    lines.append(output.get("decision_summary", "—"))
    lines.append("")

    lines.append("## Case Overview")
    lines.append(output.get("case_overview", "—"))
    lines.append("")

    lines.append("## Key Risk Factors")
    lines.extend(_render_list(output.get("key_risk_factors", [])))
    lines.append("")

    cdd = output.get("cdd_assessment", {})

    lines.append("## CDD Assessment")
    lines.append("**Подтверждено:**")
    lines.extend(_render_list(cdd.get("confirmed", [])))
    lines.append("")
    lines.append("**Не подтверждено:**")
    lines.extend(_render_list(cdd.get("not_confirmed", [])))
    lines.append("")
    lines.append(f"**Вывод:** {cdd.get('conclusion', '—')}")
    lines.append("")

    lines.append("## Analysis")
    lines.append(output.get("analysis", "—"))
    lines.append("")

    lines.extend(_render_signal_trace(output))

    lines.append("## Decisive Factor")
    lines.append(output.get("decisive_factor", "—"))
    lines.append("")

    lines.extend(_render_self_review(output))

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))

    return "\n".join(lines)


def render_decision_note(output: dict) -> str:
    # Маршрутизация по decision_mode — не просто выбор шаблона.
    # Каждый режим имеет свою структуру, потому что аудитор
    # читает EDD-записку иначе, чем Reject: в EDD он ищет
    # Required Actions, в Reject — основание и тип отказа,
    # в Approve — подтверждённые элементы CDD.
    mode = output.get("decision_mode")

    if mode == "reject":
        return render_reject_note(output)
    if mode == "approve":
        return render_approve_note(output)
    return render_edd_note(output)