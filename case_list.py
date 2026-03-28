import streamlit as st

from services import get_all_cases


def render_case_list_tab():
    st.header("Список кейсов")

    cases = get_all_cases()

    if not cases:
        st.info("Сохранённых кейсов пока нет.")
        return

    for i, record in enumerate(reversed(cases), start=1):
        case_data = record.get("case_data", {})
        title = (
            f"{i}. "
            f"{case_data.get('case_id', 'Без ID')} | "
            f"{case_data.get('client_name', 'Без названия')} | "
            f"{case_data.get('recommendation', '—')}"
        )

        with st.expander(title):
            st.write(f"**Тип кейса:** {case_data.get('case_type', '—')}")
            st.write(f"**Тип клиента:** {case_data.get('client_type', '—')}")
            st.write(f"**Риск:** {case_data.get('selected_risk_level', '—')}")
            st.write(f"**Сохранён:** {record.get('saved_at', '—')}")

            if st.button("Открыть кейс", key=f"open_case_{i}"):
                st.session_state["selected_case_record"] = record
                st.success("Кейс загружен во вкладку «Кейс».")