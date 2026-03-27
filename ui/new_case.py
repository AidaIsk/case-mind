# ui/new_case.py
# UI-слой. Импортирует только из services и llm (только is_llm_available).
# Никакой бизнес-логики, никаких прямых обращений к storage/schemas/logic.

import streamlit as st

from llm import is_llm_available
from services import process_case, save_result, build_case_input


def render_new_case_tab():
    # Сбрасываем выбранный из истории кейс при входе во вкладку
    if "selected_case_record" in st.session_state:
        del st.session_state["selected_case_record"]

    with st.form("case_form"):
        st.subheader("1. Общие сведения")
        case_id = st.text_input("ID кейса")
        case_type = st.selectbox("Тип кейса", ["Onboarding", "Review", "Trigger"])
        client_type = st.selectbox("Тип клиента", ["Физическое лицо", "Юридическое лицо"])

        st.subheader("2. Клиент и владение")
        client_name = st.text_input("Название клиента")
        registration_country = st.text_input("Страна регистрации")
        business_activity = st.text_area("Вид деятельности")
        bo_identified = st.selectbox("Бенефициар установлен?", ["Да", "Нет"])
        bo_details = st.text_area("Детали по бенефициару")
        ultimate_controller = st.text_area("Фактический контролер / ultimate controller")

        st.subheader("3. География")
        client_country = st.text_input("Страна клиента")
        counterparty_countries = st.text_input("Страны контрагентов (через запятую)")
        high_risk_geo = st.selectbox(
            "Есть high-risk / FATF-чувствительная география?", ["Да", "Нет"]
        )

        st.subheader("4. Средства и операция")
        source_of_funds = st.text_area("Источник средств (SoF)")
        transaction_amount = st.text_input("Сумма операции")
        transaction_description = st.text_area("Описание операции")
        supporting_documents = st.selectbox("Подтверждающие документы есть?", ["Да", "Нет"])

        st.subheader("5. Экономический смысл")
        purpose_of_relationship = st.text_area("Цель отношений")
        product_or_service = st.text_area("Описание продукта / услуги")
        economic_rationale = st.selectbox(
            "Экономический смысл операции",
            ["Понятен", "Не понятен", "Частично"]
        )
        matches_profile = st.selectbox(
            "Соответствует профилю клиента?",
            ["Да", "Нет", "Частично"]
        )

        st.subheader("6. Screening")
        sanctions_result = st.selectbox("Sanctions", ["Совпадений нет", "Есть совпадение", "Не завершено"])
        pep_result = st.selectbox("PEP", ["Нет", "Да", "Не завершено"])
        adverse_media_result = st.selectbox("Adverse media", ["Нет", "Есть", "Не завершено"])
        unresolved_issues = st.text_area("Нерешённые screening-вопросы")

        st.subheader("7. Оценка риска")
        red_flags = st.text_area("Red flags (каждый с новой строки)")
        mitigating_factors = st.text_area("Смягчающие факторы (каждый с новой строки)")
        key_risk_driver = st.text_area("Ключевой драйвер риска")
        risk_manageable = st.selectbox("Риск управляем?", ["Да", "Нет", "Неясно"])

        st.subheader("8. Решение аналитика")
        risk_level = st.selectbox("Уровень риска", ["Низкий", "Средний", "Высокий"])
        recommendation = st.selectbox("Рекомендация", ["Одобрить", "Эскалация", "Отказать"])
        edd_required = st.selectbox("EDD требуется?", ["Да", "Нет"])
        decision_rationale = st.text_area("Обоснование решения")
        missing_info = st.text_area("Недостающая информация")

        submitted = st.form_submit_button("Сгенерировать Decision Note")

    if not submitted:
        return

    if not is_llm_available():
        st.error("Не найден OPENAI_API_KEY. Добавь ключ в переменные окружения.")
        return

    case_data = build_case_input(
        case_id, case_type, client_type, client_name,
        registration_country, business_activity,
        bo_identified, bo_details, ultimate_controller,
        client_country, counterparty_countries, high_risk_geo,
        source_of_funds, transaction_amount, transaction_description,
        supporting_documents, purpose_of_relationship, product_or_service,
        economic_rationale, matches_profile,
        sanctions_result, pep_result, adverse_media_result, unresolved_issues,
        red_flags, mitigating_factors, key_risk_driver, risk_manageable,
        risk_level, recommendation, edd_required, decision_rationale, missing_info,
    )

    with st.spinner("Обрабатываю кейс..."):
        result = process_case(case_data)

    validation = result["validation"]

    st.subheader("Проверка кейса")

    if validation["warnings"]:
        st.warning("Предупреждения:")
        for w in validation["warnings"]:
            st.write(f"- {w}")

    if not result["ok"]:
        st.error("Генерация заблокирована из-за логических ошибок:")
        for err in validation["blocking_errors"]:
            st.write(f"- {err}")
        return

    structured_output = result["structured_output"]
    note = result["note"]

    st.session_state["last_case_data"] = case_data
    st.session_state["last_structured_output"] = structured_output
    st.session_state["last_decision_note"] = note
    st.session_state["last_rejection_reasons"] = result["rejection_reasons"]
    st.session_state["last_required_actions"] = result["required_actions"]
    st.session_state["last_case_timeline"] = result["timeline"]

    save_result(case_data, result)

    st.subheader("Аналитическая записка")
    clean_note = note.replace("**", "")
    with st.expander("Открыть аналитическую записку"):
        st.markdown(clean_note)