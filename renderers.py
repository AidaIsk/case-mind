# renderers.py

_CDD_STATUS_LABELS = {
    "Complete": "CDD завершён",
    "Incomplete": "CDD не завершён",
    "Incomplete and cannot be completed": "CDD не может быть завершён",
    "Complete but risk not acceptable": "CDD завершён, риск не является приемлемым",
}

_REJECT_REASON_LABELS = {
    "CDD_FAILURE": "Невозможность завершить CDD",
    "RISK_UNACCEPTABLE": "Неприемлемый риск",
    "NONE": None,
}


def _render_list(items: list[str]) -> list[str]:
    if not items:
        return ["- —"]
    return [f"- {item}" for item in items]


def render_edd_note(output: dict) -> str:
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

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))
    lines.append("")

    lines.append("## Required Actions")
    lines.extend(_render_list(output.get("required_actions", [])))

    return "\n".join(lines)


def render_reject_note(output: dict) -> str:
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

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))
    lines.append("")

    actions = output.get("required_actions", [])
    if actions:
        lines.append("## Procedural Actions")
        lines.extend(_render_list(actions))

    return "\n".join(lines)


def render_approve_note(output: dict) -> str:
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

    lines.append("## Decision")
    lines.append(output.get("decision_rationale", "—"))

    return "\n".join(lines)


def render_decision_note(output: dict) -> str:
    mode = output.get("decision_mode")

    if mode == "reject":
        return render_reject_note(output)
    if mode == "approve":
        return render_approve_note(output)
    return render_edd_note(output)