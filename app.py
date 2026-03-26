import streamlit as st

from ui.new_case import render_new_case_tab
from ui.case_view import render_case_view_tab
from ui.case_list import render_case_list_tab

st.set_page_config(page_title="CaseMind", layout="wide")

st.title("CaseMind — Система поддержки решений для KYC/AML")
st.caption("Прототип системы принятия и объяснения решений для KYC/AML-аналитика")

tab1, tab2, tab3 = st.tabs(["Новый кейс", "Кейс", "Список кейсов"])

with tab1:
    render_new_case_tab()

with tab2:
    render_case_view_tab()

with tab3:
    render_case_list_tab()