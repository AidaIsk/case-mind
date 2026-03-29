# ui/trainer_mode.py
# Trainer Mode UI — полностью на русском, без утечек правильного ответа.
# error_type определяется системой, не вводится пользователем.

import streamlit as st

from core.services import (
    get_trainer_cases,
    get_trainer_case,
    submit_trainer_run,
    get_trainer_runs,
    get_trainer_progress_summary,
    get_next_unfinished_trainer_case,
)

# ── Словари локализации ──────────────────────────────────────────────────

_DECISION_MODE_RU = {
    "approve": "Одобрить",
    "edd":     "Эскалация (EDD)",
    "reject":  "Отказать",
}
_DECISION_MODE_EN = {v: k for k, v in _DECISION_MODE_RU.items()}

_CDD_STATUS_RU = {
    "Complete":                            "CDD завершён",
    "Incomplete":                          "CDD не завершён",
    "Incomplete and cannot be completed":  "CDD не может быть завершён",
    "Complete but risk not acceptable":    "CDD завершён, но риск неприемлем",
}
_CDD_STATUS_EN = {v: k for k, v in _CDD_STATUS_RU.items()}

_REJECT_REASON_RU = {
    "NONE":             "Нет",
    "CDD_FAILURE":      "CDD не может быть завершён",
    "RISK_UNACCEPTABLE":"Неприемлемый риск",
}
_REJECT_REASON_EN = {v: k for k, v in _REJECT_REASON_RU.items()}

_TREND_LABEL = {
    "improving":             "📈 Растёт",
    "declining":             "📉 Снижается",
    "stable":                "➡️ Стабильно",
    "preliminary_improving": "📈 Предварительно растёт",
    "preliminary_declining": "📉 Предварительно снижается",
    "preliminary_stable":    "➡️ Предварительно стабильно",
    "not_enough_data":       "⏳ Недостаточно данных",
}

_ROOT_CAUSE_RU = {
    "NONE":                 "Ошибок не выявлено",
    "MISREAD_CDD_STATUS":   "Неверный статус CDD",
    "MISSED_SOF_GAP":       "Пропущен пробел по SoF",
    "MISSED_UBO_BLOCKER":   "Пропущен блокер по UBO",
    "MISSED_ADVERSE_MEDIA": "Не выявлен adverse media",
    "OVER_REJECT":          "Избыточный отказ",
    "UNDER_REJECT":         "Недостаточно жёсткое решение",
    "WEAK_DECISIVE_FACTOR": "Расплывчатый decisive factor",
    "WEAK_SIGNAL_TRACE":    "Неполный signal trace",
    "WEAK_RATIONALE":       "Слабое обоснование",
}

_DIFFICULTY_ICON = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}

MAX_SIGNALS = 8


# ── Блок прогресса ───────────────────────────────────────────────────────

def _render_progress_summary():
    summary = get_trainer_progress_summary()
    if summary["total_runs"] == 0:
        st.info("Пока нет прогонов. Реши первый кейс — и здесь появится статистика.")
        return

    st.subheader("Прогресс")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Прогонов",          summary["total_runs"])
    c2.metric("Средний score",     f"{summary['avg_score']} / 100")
    c3.metric("Верных решений",    f"{summary['correct_decision_rate']}%")
    c4.metric("Тренд",             _TREND_LABEL.get(summary["score_trend"], summary["score_trend"]))

    st.warning(f"⚠️ **Слабая зона:** {summary['weak_zone']}")

    dist = summary.get("root_cause_distribution", {})
    if dist:
        top3 = [(k, v) for k, v in dist.items() if k != "NONE"][:3]
        if top3:
            causes = "  |  ".join(f"**{_ROOT_CAUSE_RU.get(k, k)}**: {v}" for k, v in top3)
            st.caption(f"Частые причины ошибок: {causes}")

    st.divider()


# ── Основная вкладка ─────────────────────────────────────────────────────

def render_trainer_tab():
    st.header("Trainer Mode")
    st.caption("Разбери учебный кейс, запиши свой ответ и получи разбор.")

    _render_progress_summary()

    cases = get_trainer_cases()
    if not cases:
        st.warning("Тренировочные кейсы не найдены.")
        return

    # Кнопка "Следующий непройденный" — обновляет session_state
    if st.button("⏭️ Следующий непройденный сегодня"):
        current = st.session_state.get("trainer_selected_case_id")
        next_case = get_next_unfinished_trainer_case(current)
        if next_case is None:
            st.success("✅ На сегодня все кейсы уже пройдены.")
        else:
            st.session_state["trainer_selected_case_id"] = next_case["case_id"]
            st.rerun()

    # Selectbox с кейсами
    options_label = [
        f"{c['case_id']} — {_DIFFICULTY_ICON.get(c['difficulty'], '⚪')} {c['difficulty'].capitalize()} — {c['theme']}"
        for c in cases
    ]
    options_id = [c["case_id"] for c in cases]

    # Инициализируем выбор из session_state
    default_idx = 0
    saved_id = st.session_state.get("trainer_selected_case_id")
    if saved_id and saved_id in options_id:
        default_idx = options_id.index(saved_id)

    selected_label = st.selectbox(
        "Выбери кейс",
        options_label,
        index=default_idx,
        key="trainer_case_select",
    )
    case_id = options_id[options_label.index(selected_label)]
    st.session_state["trainer_selected_case_id"] = case_id

    trainer_case = get_trainer_case(case_id)
    if not trainer_case:
        st.error(f"Кейс {case_id} не найден.")
        return

    # ── Описание кейса (только description_user) ─────────────────────────
    st.subheader(f"Кейс {trainer_case['case_id']}")
    st.info(trainer_case.get("description_user", trainer_case.get("description", "")))

    with st.expander("📋 Данные кейса", expanded=False):
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
            st.warning(f"**Нерешённые вопросы по screening:** {cd['unresolved_screening_issues']}")

    st.divider()

    # ── Форма ответа ──────────────────────────────────────────────────────
    st.subheader("Твой ответ")

    # Инициализация session_state для сигналов
    sig_key = f"signals_{case_id}"
    if sig_key not in st.session_state:
        st.session_state[sig_key] = ["", ""]

    with st.form(key=f"trainer_form_{case_id}"):
        col_a, col_b = st.columns(2)

        with col_a:
            decision_ru = st.selectbox(
                "Решение",
                list(_DECISION_MODE_RU.values()),
                key=f"dm_{case_id}",
            )
            cdd_ru = st.selectbox(
                "Статус CDD",
                list(_CDD_STATUS_RU.values()),
                key=f"cdd_{case_id}",
            )
            reason_ru = st.selectbox(
                "Тип отказа",
                list(_REJECT_REASON_RU.values()),
                key=f"rr_{case_id}",
            )

        with col_b:
            confidence = st.slider(
                "Уверенность (confidence_score)", 1, 5, 3,
                help="1 — очень низкая, 5 — очень высокая",
                key=f"conf_{case_id}",
            )
            decisive_factor = st.text_area(
                "Ключевой фактор решения (decisive_factor)",
                placeholder="Одна конкретная формулировка главного перевешивающего фактора",
                key=f"df_{case_id}",
                height=100,
            )

        # Динамические сигналы
        st.markdown("**Сигналы (signal_trace)**")
        signal_inputs = []
        current_signals = st.session_state[sig_key]
        for i, val in enumerate(current_signals):
            sig_val = st.text_input(
                f"Сигнал {i + 1}",
                value=val,
                placeholder="Конкретный наблюдаемый факт",
                key=f"sig_{case_id}_{i}",
            )
            signal_inputs.append(sig_val)

        col_add, col_rem, _ = st.columns([1, 1, 4])
        add_signal = col_add.form_submit_button("＋ Добавить сигнал")
        rem_signal = col_rem.form_submit_button("－ Удалить последний")
        submitted  = st.form_submit_button("🔍 Получить разбор")

    # Обработка кнопок добавления/удаления (вне form — через rerun)
    if add_signal:
        if len(st.session_state[sig_key]) < MAX_SIGNALS:
            st.session_state[sig_key] = signal_inputs + [""]
        st.rerun()

    if rem_signal:
        if len(st.session_state[sig_key]) > 2:
            st.session_state[sig_key] = signal_inputs[:-1]
        st.rerun()

    if not submitted:
        return

    # ── Сборка user_output ────────────────────────────────────────────────
    decision_mode = _DECISION_MODE_EN[decision_ru]
    cdd_status    = _CDD_STATUS_EN[cdd_ru]
    reject_reason = _REJECT_REASON_EN[reason_ru]

    # Определяем direction сигналов по решению
    if decision_mode == "edd":
        sig_direction = "SUPPORTS_ESCALATION"
    elif decision_mode == "reject":
        sig_direction = "SUPPORTS_REJECT"
    else:
        sig_direction = "SUPPORTS_DECISION"

    signal_trace = []
    filled_signals = [s.strip() for s in signal_inputs if s.strip()]

    for i, sig_text in enumerate(filled_signals):
        signal_trace.append({
            "signal":    sig_text,
            "category":  "OTHER",
            "impact":    "DECISIVE" if i == 0 else "HIGH",
            "direction": sig_direction,
            "comment":   "Сигнал аналитика.",
        })

    # Минимум 2 сигнала
    while len(signal_trace) < 2:
        signal_trace.append({
            "signal":    "Дополнительный контекст не указан.",
            "category":  "OTHER",
            "impact":    "LOW",
            "direction": "MITIGATING",
            "comment":   "Автоматически добавлен.",
        })

    decision_label = _DECISION_MODE_RU[decision_mode]
    user_output = {
        "decision_mode":      decision_mode,
        "decision":           decision_label,
        "edd_required":       "Да" if decision_mode == "edd" else "Нет",
        "cdd_status":         cdd_status,
        "risk_level":         trainer_case["case_data"].get("selected_risk_level", "Средний"),
        "reject_reason_type": reject_reason,
        "decisive_factor":    decisive_factor.strip() or "—",
        "error_type":         "NONE",   # определяется системой после сравнения
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

    # Сбрасываем сигналы для следующего прогона
    st.session_state[sig_key] = ["", ""]

    # ── Результаты review ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Разбор")

    score = review["score"]
    score_icon = "🟢" if score >= 85 else ("🟡" if score >= 60 else "🔴")
    root_cause_label = _ROOT_CAUSE_RU.get(review["root_cause"], review["root_cause"])

    c1, c2 = st.columns(2)
    c1.metric("Score", f"{score_icon} {score} / 100")
    c2.metric("Диагноз", root_cause_label)

    st.write(f"**Резюме:** {review['review_summary']}")
    st.write(f"**Тип ошибки:** {review['error_type']}")

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

    # ── Эталонный ответ — ТОЛЬКО после review ────────────────────────────
    with st.expander("📖 Эталонный ответ", expanded=False):
        exp = trainer_case["expected_output"]
        st.write(f"**Решение:** {_DECISION_MODE_RU.get(exp.get('decision_mode', ''), exp.get('decision_mode', '—'))}")
        st.write(f"**Статус CDD:** {_CDD_STATUS_RU.get(exp.get('cdd_status', ''), exp.get('cdd_status', '—'))}")
        reason_en = exp.get("reject_reason_type", "NONE")
        st.write(f"**Тип отказа:** {_REJECT_REASON_RU.get(reason_en, reason_en)}")
        st.write(f"**Ключевой фактор:** {exp.get('decisive_factor', '—')}")
        st.write(f"**Уверенность:** {exp.get('confidence_score', '—')} / 5")
        st.markdown("**Сигналы:**")
        for sig in exp.get("signal_trace", []):
            st.write(f"- [{sig['impact']}] {sig['signal']}")

    # ── Кнопка следующего кейса ───────────────────────────────────────────
    next_case = get_next_unfinished_trainer_case(case_id)
    if next_case is None:
        st.success("✅ На сегодня все кейсы уже пройдены!")
    else:
        if st.button(f"⏭️ Следующий непройденный: {next_case['case_id']} — {next_case['theme']}"):
            st.session_state["trainer_selected_case_id"] = next_case["case_id"]
            st.rerun()

    st.caption(f"Run ID: `{run_id}`")
    st.divider()

    _render_trainer_history()


# ── История прогонов ──────────────────────────────────────────────────────

def _render_trainer_history():
    runs = get_trainer_runs()
    if not runs:
        return
    st.subheader("История прогонов")
    recent = list(reversed(runs))[:10]
    for run in recent:
        score  = run.get("score", 0)
        icon   = "🟢" if score >= 85 else ("🟡" if score >= 60 else "🔴")
        root   = _ROOT_CAUSE_RU.get(run.get("root_cause", ""), run.get("root_cause", "—"))
        correct = "✅" if run.get("is_correct_decision") else "❌"
        with st.expander(
            f"{run.get('saved_at', '—')}  |  {run.get('trainer_case_id', '—')}  "
            f"|  {icon} {score}/100  |  Решение: {correct}",
            expanded=False,
        ):
            st.write(f"**Run ID:** `{run.get('run_id', '—')}`")
            st.write(f"**Диагноз:** {root}")
            summary = run.get("review", {}).get("review_summary", "—")
            st.write(f"**Резюме:** {summary}")
