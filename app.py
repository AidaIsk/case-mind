# app.py

import streamlit as st

from ui.new_case import render_new_case_tab
from ui.case_view import render_case_view_tab
from ui.case_list import render_case_list_tab
from ui.trainer_mode import render_trainer_tab

st.set_page_config(page_title="CaseMind", layout="wide")

st.title("CaseMind — Система поддержки решений для KYC/AML")
st.caption("Прототип системы принятия и объяснения решений для KYC/AML-аналитика")

# Beta flag: Тренажёр первой вкладкой для beta-пользователей.
# Чтобы вернуть старый порядок — установить BETA_FIRST_TAB = False.
BETA_FIRST_TAB = True

if BETA_FIRST_TAB:
    tab1, tab2, tab3, tab4 = st.tabs(["Тренажёр", "Новый кейс", "Кейс", "Список кейсов"])
    with tab1: render_trainer_tab()
    with tab2: render_new_case_tab()
    with tab3: render_case_view_tab()
    with tab4: render_case_list_tab()
else:
    tab1, tab2, tab3, tab4 = st.tabs(["Новый кейс", "Кейс", "Список кейсов", "Тренажёр"])
    with tab1: render_new_case_tab()
    with tab2: render_case_view_tab()
    with tab3: render_case_list_tab()
    with tab4: render_trainer_tab()
