import streamlit as st

from services import get_all_cases

_RISK_ICON = {"Высокий": "🔴", "Средний": "🟡", "Низкий": "🟢"}
_DECISION_ICON = {"Одобрить": "✅", "Отказать": "❌", "Эскалация": "⚠️"}


def render_case_list_tab():
    st.header("Список кейсов")

    cases = get_all_cases()

    if not cases:
        st.info("Сохранённых кейсов пока нет.")
        return

    for i, record in enumerate(reversed(cases), start=1):
        case_data = record.get("case_data", {})

        # Читаем быстрые поля — сначала из верхнего уровня, fallback в case_data
        risk      = record.get("risk_level") or case_data.get("selected_risk_level", "—")
        decision  = record.get("decision")   or case_data.get("recommendation", "—")
        case_id   = record.get("case_id")    or case_data.get("case_id", "Без ID")
        client    = case_data.get("client_name", "Без названия")
        saved_at  = record.get("saved_at", "—")
        decisive  = record.get("decisive_factor", "")
        error_t   = record.get("error_type", "")

        risk_icon     = _RISK_ICON.get(risk, "⚪")
        decision_icon = _DECISION_ICON.get(decision, "")

        title = (
            f"{i}. {case_id} | {client} | "
            f"{decision_icon} {decision} | {risk_icon} {risk}"
        )

        with st.expander(title):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Тип кейса:** {case_data.get('case_type', '—')}")
                st.write(f"**Тип клиента:** {case_data.get('client_type', '—')}")
                st.write(f"**Сохранён:** {saved_at}")
            with col2:
                if decisive and decisive != "—":
                    st.write(f"**Ключевой фактор:** {decisive}")
                if error_t and error_t != "—":
                    st.write(f"**Тип ошибки:** {error_t}")

            if st.button("Открыть кейс", key=f"open_case_{i}"):
                st.session_state["selected_case_record"] = record
                st.success("Кейс загружен во вкладку «Кейс».")