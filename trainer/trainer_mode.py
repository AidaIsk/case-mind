# ui/trainer_mode.py
# UI-слой Trainer Mode. Только импорты из core.services — никакой бизнес-логики.

import streamlit as st

from core.services import (
    get_trainer_cases,
    get_trainer_case,
    submit_trainer_run,
    get_trainer_runs,
)

_DIFFICULTY_ICON = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
_ROOT_CAUSE_RU = {
    "NONE":                 "Ошибок не выявлено",
    "MISREAD_CDD_STATUS":   "Неверный статус CDD",
    "MISSED_SOF_GAP":       "Пропущен пробел по SoF",
    "MISSED_UBO_BLOCKER":   "Пропущен блокер по UBO",
    "MISSED_ADVERSE_MEDIA": "Не выявлен adverse media",
    "OVER_REJECT":          "Избыточный отказ",
    "UNDER_REJECT":         "Недостаточно жёсткое решение",
    "WEAK_DECISIVE_FACTOR": "Слабый decisive factor",
    "WEAK_SIGNAL_TRACE":    "Слабый signal trace",
    "WEAK_RATIONALE":       "Слабое обоснование",
}
_MODE_OPTIONS = {
    "edd":     "Эскалация (EDD)",
    "reject":  "Отказать",
    "approve": "Одобрить",
}
_CDD_OPTIONS = [
    "Complete",
    "Incomplete",
    "Incomplete and cannot be completed",
    "Complete but risk not acceptable",
]
_REASON_OPTIONS = ["NONE", "CDD_FAILURE", "RISK_UNACCEPTABLE"]


def _score_color(score: int) -> str:
    if score >= 85:
        return "🟢"
    if score >= 60:
        return "🟡"
    return "🔴"


def render_trainer_tab():
    st.header("Trainer Mode")
    st.caption("Разбери учебный кейс, получи structured output и сравни с эталоном.")

    cases = get_trainer_cases()
    if not cases:
        st.warning("Тренировочные кейсы не найдены.")
        return

    # ── Выбор кейса ──────────────────────────────────────────────────────
    case_options = {
        f"{c['case_id']} — {_DIFFICULTY_ICON.get(c['difficulty'], '⚪')} "
        f"{c['difficulty'].capitalize()} — {c['theme']}": c["case_id"]
        for c in cases
    }

    selected_label = st.selectbox(
        "Выбери тренировочный кейс",
        list(case_options.keys()),
        key="trainer_case_select",
    )
    case_id = case_options[selected_label]
    trainer_case = get_trainer_case(case_id)

    if not trainer_case:
        st.error(f"Кейс {case_id} не найден.")
        return

    # ── Описание и данные кейса ───────────────────────────────────────────
    st.subheader(f"Кейс {trainer_case['case_id']}")
    st.info(trainer_case["description"])

    with st.expander("📋 Данные кейса (case_data)", expanded=False):
        cd = trainer_case["case_data"]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Клиент:** {cd.get('client_name', '—')}")
            st.write(f"**Тип:** {cd.get('client_type', '—')}")
            st.write(f"**Страна:** {cd.get('registration_country', '—')}")
            st.write(f"**Деятельность:** {cd.get('business_activity', '—')}")
            st.write(f"**Тип кейса:** {cd.get('case_type', '—')}")
        with col2:
            st.write(f"**UBO установлен:** {cd.get('beneficial_owner_identified', '—')}")
            st.write(f"**SoF:** {cd.get('source_of_funds_summary', '—') or '❌ не указан'}")
            st.write(f"**Документы:** {cd.get('supporting_documents_provided', '—')}")
            st.write(f"**Adverse media:** {cd.get('adverse_media_result', '—')}")
            st.write(f"**Высокорисковая география:** {cd.get('high_risk_jurisdiction_involved', '—')}")

        if cd.get("red_flags_selected"):
            st.write(f"**Red flags:** {', '.join(cd['red_flags_selected'])}")
        if cd.get("unresolved_screening_issues"):
            st.warning(f"**Неснятые вопросы по screening:** {cd['unresolved_screening_issues']}")

    st.divider()

    # ── Форма ответа аналитика ────────────────────────────────────────────
    st.subheader("Твой ответ")
    st.caption("Заполни structured output на основе данных кейса.")

    with st.form(key=f"trainer_form_{case_id}"):
        col_a, col_b = st.columns(2)

        with col_a:
            decision_mode = st.selectbox(
                "decision_mode",
                list(_MODE_OPTIONS.keys()),
                format_func=lambda x: _MODE_OPTIONS[x],
                key=f"dm_{case_id}",
            )
            cdd_status = st.selectbox(
                "cdd_status",
                _CDD_OPTIONS,
                key=f"cdd_{case_id}",
            )
            reject_reason = st.selectbox(
                "reject_reason_type",
                _REASON_OPTIONS,
                key=f"rr_{case_id}",
            )
            confidence = st.slider(
                "confidence_score", 1, 5, 3,
                key=f"conf_{case_id}",
            )

        with col_b:
            error_type = st.selectbox(
                "error_type",
                ["NONE", "OVER_REJECT", "UNDER_REJECT", "MISSED_SIGNAL",
                 "WEAK_RATIONALE", "CDD_LOGIC_GAP", "INCONSISTENT_DECISION"],
                key=f"et_{case_id}",
            )
            decisive_factor = st.text_area(
                "decisive_factor",
                placeholder="Одна формулировка главного перевешивающего фактора",
                key=f"df_{case_id}",
                height=80,
            )

        sig1 = st.text_input(
            "Сигнал 1 (DECISIVE)",
            placeholder="Источник средств по операции не подтверждён.",
            key=f"s1_{case_id}",
        )
        sig2 = st.text_input(
            "Сигнал 2",
            placeholder="Второй конкретный наблюдаемый факт",
            key=f"s2_{case_id}",
        )

        submitted = st.form_submit_button("🔍 Решить кейс и получить review")

    if not submitted:
        return

    # ── Сборка user_output ────────────────────────────────────────────────
    signal_trace = []
    if sig1.strip():
        signal_trace.append({
            "signal": sig1.strip(),
            "category": "OTHER",
            "impact": "DECISIVE",
            "direction": "SUPPORTS_ESCALATION" if decision_mode == "edd" else "SUPPORTS_REJECT" if decision_mode == "reject" else "SUPPORTS_DECISION",
            "comment": "Сигнал аналитика.",
        })
    if sig2.strip():
        signal_trace.append({
            "signal": sig2.strip(),
            "category": "OTHER",
            "impact": "HIGH",
            "direction": "SUPPORTS_ESCALATION" if decision_mode == "edd" else "SUPPORTS_REJECT" if decision_mode == "reject" else "SUPPORTS_DECISION",
            "comment": "Второй сигнал аналитика.",
        })
    # Минимум 2 сигнала для валидации
    if len(signal_trace) < 2:
        signal_trace.append({
            "signal": "Дополнительный контекст не указан.",
            "category": "OTHER",
            "impact": "LOW",
            "direction": "MITIGATING",
            "comment": "Автоматически добавлен для соблюдения минимума signal_trace.",
        })

    decision_map = {"edd": "Эскалация", "reject": "Отказать", "approve": "Одобрить"}
    user_output = {
        "decision_mode":      decision_mode,
        "decision":           decision_map[decision_mode],
        "edd_required":       "Да" if decision_mode == "edd" else "Нет",
        "cdd_status":         cdd_status,
        "risk_level":         trainer_case["case_data"].get("selected_risk_level", "Средний"),
        "reject_reason_type": reject_reason,
        "decisive_factor":    decisive_factor.strip() or "—",
        "error_type":         error_type,
        "confidence_score":   confidence,
        "signal_trace":       signal_trace,
        "decision_summary":   "",
        "case_overview":      "",
        "key_risk_factors":   [],
        "cdd_assessment":     {"confirmed": [], "not_confirmed": [], "conclusion": ""},
        "analysis":           "",
        "decision_rationale": "",
        "required_actions":   [],
        "self_review":        {"summary": "", "main_gap": "", "what_to_recheck": []},
    }

    expected_output = trainer_case["expected_output"]

    with st.spinner("Анализирую ответ..."):
        review, run_id = submit_trainer_run(case_id, user_output, expected_output)

    # ── Результаты review ────────────────────────────────────────────────
    st.divider()
    st.subheader("Review")

    score = review["score"]
    score_icon = _score_color(score)
    root_cause = review["root_cause"]
    root_cause_label = _ROOT_CAUSE_RU.get(root_cause, root_cause)

    col_s, col_r = st.columns(2)
    with col_s:
        st.metric("Score", f"{score_icon} {score} / 100")
    with col_r:
        st.metric("Root cause", root_cause_label)

    st.write(f"**Резюме:** {review['review_summary']}")

    col_g, col_m = st.columns(2)
    with col_g:
        st.markdown("**✅ Что верно:**")
        for item in review["what_was_good"]:
            st.write(f"- {item}")
    with col_m:
        st.markdown("**❌ Что пропущено:**")
        for item in review["what_was_missed"]:
            st.write(f"- {item}")

    if review["what_to_recheck"]:
        st.markdown("**🔁 Что перепроверить:**")
        for item in review["what_to_recheck"]:
            st.write(f"- {item}")

    # ── Эталонный ответ ───────────────────────────────────────────────────
    with st.expander("📖 Эталонный ответ", expanded=False):
        exp = trainer_case["expected_output"]
        st.write(f"**decision_mode:** {exp.get('decision_mode')}")
        st.write(f"**cdd_status:** {exp.get('cdd_status')}")
        st.write(f"**reject_reason_type:** {exp.get('reject_reason_type')}")
        st.write(f"**decisive_factor:** {exp.get('decisive_factor')}")
        st.write(f"**confidence_score:** {exp.get('confidence_score')}")
        st.markdown("**signal_trace:**")
        for sig in exp.get("signal_trace", []):
            st.write(f"- [{sig['impact']}] {sig['signal']}")

    st.caption(f"Run ID: `{run_id}`")
    st.divider()

    # ── История прогонов ──────────────────────────────────────────────────
    _render_trainer_history()


def _render_trainer_history():
    """Показывает последние 10 тренировочных прогонов."""
    runs = get_trainer_runs()
    if not runs:
        return

    st.subheader("История прогонов")
    recent = list(reversed(runs))[:10]

    for run in recent:
        score = run.get("score", 0)
        icon = _score_color(score)
        root = _ROOT_CAUSE_RU.get(run.get("root_cause", ""), run.get("root_cause", "—"))
        correct = "✅" if run.get("is_correct_decision") else "❌"

        with st.expander(
            f"{run.get('saved_at', '—')}  |  {run.get('trainer_case_id', '—')}  "
            f"|  {icon} {score}/100  |  Решение: {correct}",
            expanded=False,
        ):
            st.write(f"**Run ID:** `{run.get('run_id', '—')}`")
            st.write(f"**Root cause:** {root}")
            summary = run.get("review", {}).get("review_summary", "—")
            st.write(f"**Резюме:** {summary}")
