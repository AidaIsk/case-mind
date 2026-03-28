# case_view.py

import streamlit as st


_RISK_BADGE = {
    "Высокий": ("🔴", "danger"),
    "Средний": ("🟡", "warning"),
    "Низкий":  ("🟢", "success"),
}

_DECISION_BADGE = {
    "Одобрить":   "✅",
    "Отказать":   "❌",
    "Эскалация":  "⚠️",
}

_ERROR_TYPE_LABELS = {
    "NONE":                 "Ошибок не выявлено",
    "OVER_REJECT":          "Избыточный reject",
    "UNDER_REJECT":         "Занижение тяжести",
    "MISSED_SIGNAL":        "Пропущен сигнал",
    "WEAK_RATIONALE":       "Слабое обоснование",
    "CDD_LOGIC_GAP":        "Нарушение логики CDD",
    "INCONSISTENT_DECISION":"Внутреннее противоречие",
}


def _risk_badge(risk: str) -> str:
    icon, _ = _RISK_BADGE.get(risk, ("⚪", "secondary"))
    return f"{icon} {risk}"


def _confidence_bar(score) -> str:
    try:
        n = int(score)
    except (TypeError, ValueError):
        return "—"
    filled = "█" * n
    empty  = "░" * (5 - n)
    return f"{filled}{empty}  {n}/5"


def render_case_view_tab():
    st.header("Кейс")

    if "selected_case_record" in st.session_state:
        record    = st.session_state["selected_case_record"]
        case_data = record.get("case_data", {})
        so        = record.get("structured_output") or {}
        note      = record.get("decision_note", "")
        rejection_reasons = record.get("rejection_reasons", [])
        required_actions  = record.get("required_actions", [])
        timeline          = record.get("timeline", [])
    elif "last_case_data" in st.session_state:
        case_data = st.session_state["last_case_data"]
        so        = st.session_state.get("last_structured_output") or {}
        note      = st.session_state.get("last_decision_note", "")
        rejection_reasons = st.session_state.get("last_rejection_reasons", [])
        required_actions  = st.session_state.get("last_required_actions", [])
        timeline          = st.session_state.get("last_case_timeline", [])
    else:
        st.info("Пока нет сохранённого кейса. Заполни форму во вкладке «Новый кейс».")
        return

    if not case_data:
        st.info("Кейс пуст.")
        return

    # Блок 1: Профиль клиента
    st.subheader("Профиль клиента")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Клиент:** {case_data.get('client_name', '—')}")
        st.write(f"**Тип:** {case_data.get('client_type', '—')}")
        st.write(f"**Страна регистрации:** {case_data.get('registration_country', '—')}")
        st.write(f"**Деятельность:** {case_data.get('business_activity', '—')}")
    with col2:
        st.write(f"**UBO установлен:** {case_data.get('beneficial_owner_identified', '—')}")
        st.write(f"**Фактический контролёр:** {case_data.get('ultimate_controller_description', '—') or '—'}")
        st.write(f"**Тип кейса:** {case_data.get('case_type', '—')}")
        st.write(f"**ID кейса:** `{case_data.get('case_id', '—')}`")
    st.divider()

    # Блок 2: Решение
    st.subheader("Решение")
    risk      = so.get("risk_level") or case_data.get("selected_risk_level", "—")
    decision  = so.get("decision")   or case_data.get("recommendation", "—")
    cdd_status = so.get("cdd_status", "—")
    edd        = so.get("edd_required") or case_data.get("edd_required", "—")
    risk_icon, _ = _RISK_BADGE.get(risk, ("⚪", "secondary"))
    decision_icon = _DECISION_BADGE.get(decision, "")
    col3, col4, col5 = st.columns(3)
    with col3:
        st.metric("Решение", f"{decision_icon} {decision}")
    with col4:
        st.metric("Уровень риска", f"{risk_icon} {risk}")
    with col5:
        st.metric("EDD", edd)
    st.write(f"**Статус CDD:** {cdd_status}")
    st.divider()

    # Блок 3: Decisive Factor
    decisive_factor = so.get("decisive_factor", "").strip()
    if decisive_factor and decisive_factor != "—":
        st.subheader("Ключевой фактор решения")
        st.info(decisive_factor)
        st.divider()

    # Блок 4: CDD Assessment
    cdd_assessment = so.get("cdd_assessment", {})
    if cdd_assessment:
        st.subheader("CDD Assessment")
        col_c, col_nc = st.columns(2)
        with col_c:
            st.markdown("**Подтверждено**")
            for item in cdd_assessment.get("confirmed", []) or ["—"]:
                st.write(f"✓ {item}")
        with col_nc:
            st.markdown("**Не подтверждено**")
            not_confirmed = cdd_assessment.get("not_confirmed", [])
            for item in not_confirmed or ["—"]:
                st.write(f"✗ {item}")
        conclusion = cdd_assessment.get("conclusion", "").strip()
        if conclusion:
            st.caption(f"Вывод: {conclusion}")
        st.divider()

    # Блок 5: Rationale + полная нота
    rationale = so.get("decision_rationale", "").strip()
    if rationale:
        st.subheader("Обоснование решения")
        st.write(rationale)
    if note:
        with st.expander("Полная аналитическая записка"):
            st.markdown(note.replace("**", ""))
    st.divider()

    # Блок 6: Self-Review
    error_type  = so.get("error_type", "")
    confidence  = so.get("confidence_score", 0)
    self_review = so.get("self_review", {})
    if error_type or confidence:
        st.subheader("Self-Review")
        col6, col7 = st.columns(2)
        with col6:
            et_label = _ERROR_TYPE_LABELS.get(error_type, error_type or "—")
            st.write(f"**Тип ошибки:** {et_label}")
            st.write(f"**Уверенность:** `{_confidence_bar(confidence)}`")
        with col7:
            main_gap = self_review.get("main_gap", "").strip()
            if main_gap:
                st.write(f"**Главный gap:** {main_gap}")
            what = self_review.get("what_to_recheck", [])
            if what:
                st.write(f"**Перепроверить:** {', '.join(what)}")
        st.divider()

    # Блок 7: Причины / Required Actions
    if rejection_reasons or required_actions:
        col8, col9 = st.columns(2)
        with col8:
            if rejection_reasons:
                st.subheader("Причины / ограничения")
                for item in rejection_reasons:
                    st.write(f"- {item}")
        with col9:
            if required_actions:
                st.subheader("Required actions")
                for item in required_actions:
                    st.write(f"- {item}")
        st.divider()

    # Блок 8: Timeline
    if timeline:
        with st.expander("Timeline"):
            for item in timeline:
                st.write(f"**{item['time']}** — {item['event']}: {item['details']}")
