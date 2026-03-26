import streamlit as st

from logic import get_cdd_status_and_system_decision


def render_case_view_tab():
    st.header("Кейс")

    if "selected_case_record" in st.session_state:
        selected_record = st.session_state["selected_case_record"]
        case_data = selected_record.get("case_data", {})
        note = selected_record.get("decision_note", "")
        rejection_reasons = selected_record.get("rejection_reasons", [])
        required_actions = selected_record.get("required_actions", [])
        timeline = selected_record.get("timeline", [])
    elif "last_case_data" in st.session_state:
        case_data = st.session_state["last_case_data"]
        note = st.session_state.get("last_decision_note", "")
        rejection_reasons = st.session_state.get("last_rejection_reasons", [])
        required_actions = st.session_state.get("last_required_actions", [])
        timeline = st.session_state.get("last_case_timeline", [])
    else:
        case_data = None

    if not case_data:
        st.info("Пока нет сохранённого кейса. Заполни форму во вкладке «Новый кейс».")
        return

    cdd_complete, system_decision, decision_status = get_cdd_status_and_system_decision(case_data)

    st.subheader("Профиль клиента")
    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Клиент:** {case_data.get('client_name', '—')}")
        st.write(f"**Страна:** {case_data.get('registration_country', '—')}")
        st.write(f"**Деятельность:** {case_data.get('business_activity', '—')}")

    with col2:
        st.write(f"**Тип клиента:** {case_data.get('client_type', '—')}")
        st.write(f"**Фактический контролер:** {case_data.get('ultimate_controller_description', '—') or '—'}")
        st.write(f"**UBO:** {case_data.get('beneficial_owner_identified', '—')}")

    st.divider()

    st.subheader("Решение по кейсу")
    col3, col4, col5 = st.columns(3)

    with col3:
        st.metric("Решение", case_data.get("recommendation", "—"))
    with col4:
        st.metric("Статус", decision_status)
    with col5:
        st.metric("CDD статус", "Завершён" if cdd_complete else "Не завершён")

    st.markdown(f"**Системное решение:** {system_decision}")
    st.markdown(f"**EDD:** {case_data.get('edd_required', '—')}")

    st.divider()

    st.subheader("Причины / ограничения")
    if rejection_reasons:
        for item in rejection_reasons:
            st.write(f"- {item}")
    else:
        st.write("—")

    st.subheader("Required actions")
    if required_actions:
        for item in required_actions:
            st.write(f"- {item}")
    else:
        st.write("—")

    st.subheader("Timeline")
    if timeline:
        for item in timeline:
            st.write(f"**{item['time']}** — {item['event']}: {item['details']}")

    st.subheader("Decision Note")
    with st.expander("Открыть записку"):
        st.markdown(note.replace("**", ""))