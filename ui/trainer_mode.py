# ui/trainer_mode.py  —  Trainer Mode v2
# Decision Note mode, три режима навигации, coach_message, фильтр истории.

import streamlit as st

from core.services import (
    get_trainer_cases,
    get_trainer_case,
    submit_trainer_run,
    get_trainer_runs,
    get_trainer_progress_summary,
    get_next_trainer_case_by_mode,
)

# ── Словари локализации ──────────────────────────────────────────────────

_DECISION_MODE_RU  = {"approve": "Одобрить", "edd": "Эскалация (EDD)", "reject": "Отказать"}
_DECISION_MODE_EN  = {v: k for k, v in _DECISION_MODE_RU.items()}
_CDD_STATUS_RU     = {
    "Complete":                           "CDD завершён",
    "Incomplete":                         "CDD не завершён",
    "Incomplete and cannot be completed": "CDD не может быть завершён",
    "Complete but risk not acceptable":   "CDD завершён, но риск неприемлем",
}
_CDD_STATUS_EN     = {v: k for k, v in _CDD_STATUS_RU.items()}
_REJECT_REASON_RU  = {
    "NONE": "Нет", "CDD_FAILURE": "CDD не может быть завершён",
    "RISK_UNACCEPTABLE": "Неприемлемый риск",
}
_REJECT_REASON_EN  = {v: k for k, v in _REJECT_REASON_RU.items()}
_TREND_LABEL       = {
    "improving": "📈 Растёт", "declining": "📉 Снижается", "stable": "➡️ Стабильно",
    "preliminary_improving": "📈 Предварительно растёт",
    "preliminary_declining": "📉 Предварительно снижается",
    "preliminary_stable":    "➡️ Предварительно стабильно",
    "not_enough_data": "⏳ Недостаточно данных",
}
_ROOT_CAUSE_RU     = {
    "NONE": "Ошибок не выявлено", "MISREAD_CDD_STATUS": "Неверный статус CDD",
    "MISSED_SOF_GAP": "Пропущен пробел по SoF",
    "MISSED_UBO_BLOCKER": "Пропущен блокер по UBO",
    "MISSED_ADVERSE_MEDIA": "Не выявлен adverse media",
    "OVER_REJECT": "Избыточный отказ", "UNDER_REJECT": "Недостаточно жёсткое решение",
    "WEAK_DECISIVE_FACTOR": "Расплывчатый decisive factor",
    "WEAK_SIGNAL_TRACE": "Неполный signal trace", "WEAK_RATIONALE": "Слабое обоснование",
}
_NOTE_QUALITY_RU   = {"strong": "✅ Сильная", "acceptable": "🟡 Приемлемая", "weak": "🔴 Слабая"}
_DIFFICULTY_ICON   = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
_NAV_MODES         = {"unfinished_today": "Непройденный сегодня", "sequential": "Подряд", "random": "Случайный"}
MAX_SIGNALS        = 8


# ── Блок прогресса ───────────────────────────────────────────────────────

def _score_icon(score):
    return "🟢" if score >= 85 else ("🟡" if score >= 60 else "🔴")


def _render_progress_summary():
    summary = get_trainer_progress_summary()
    if summary["total_runs"] == 0:
        st.info("Пока нет прогонов. Реши первый кейс — и здесь появится статистика.")
        return
    st.subheader("Прогресс")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Прогонов",       summary["total_runs"])
    c2.metric("Средний score",  f"{summary['avg_score']} / 100")
    c3.metric("Верных решений", f"{summary['correct_decision_rate']}%")
    c4.metric("Тренд",          _TREND_LABEL.get(summary["score_trend"], "—"))
    st.warning(f"⚠️ **Слабая зона:** {summary['weak_zone']}")
    dist = {k: v for k, v in summary.get("root_cause_distribution", {}).items() if k != "NONE"}
    if dist:
        top3 = list(dist.items())[:3]
        st.caption("Частые причины ошибок: " + "  |  ".join(
            f"**{_ROOT_CAUSE_RU.get(k, k)}**: {v}" for k, v in top3
        ))
    st.divider()


# ── История прогонов с фильтром ──────────────────────────────────────────

def _render_trainer_history():
    runs = get_trainer_runs()
    if not runs:
        return

    st.subheader("История прогонов")

    # Фильтр
    filter_mode = st.radio(
        "Показывать:",
        ["Все", "Только ошибки", "Только низкий score"],
        horizontal=True,
        key="history_filter",
    )

    filtered = list(reversed(runs))
    if filter_mode == "Только ошибки":
        filtered = [r for r in filtered
                    if r.get("root_cause", "NONE") != "NONE"
                    or r.get("error_type", "NONE") != "NONE"]
    elif filter_mode == "Только низкий score":
        filtered = [r for r in filtered if r.get("score", 100) < 60]

    if not filtered:
        st.info("Нет прогонов, соответствующих фильтру.")
        return

    for run in filtered[:10]:
        score   = run.get("score", 0)
        icon    = _score_icon(score)
        root    = _ROOT_CAUSE_RU.get(run.get("root_cause", ""), "—")
        correct = "✅" if run.get("is_correct_decision") else "❌"
        note_sc = run.get("note_score")
        note_str = f"  |  📝 Note: {note_sc}" if note_sc is not None else ""

        with st.expander(
            f"{run.get('saved_at', '—')}  |  {run.get('trainer_case_id', '—')}  "
            f"|  {icon} {score}/100  |  {correct}{note_str}",
            expanded=False,
        ):
            st.write(f"**Run ID:** `{run.get('run_id', '—')}`")
            st.write(f"**Диагноз:** {root}")
            coach = run.get("review", {}).get("coach_message", "")
            if coach:
                st.info(f"💬 {coach}")
            if run.get("decision_note"):
                with st.expander("Аналитическая записка", expanded=False):
                    st.write(run["decision_note"])


# ── Главная вкладка ───────────────────────────────────────────────────────

def render_trainer_tab():
    st.header("Trainer Mode")
    st.caption("Разбери учебный кейс, запиши ответ и аналитическую записку — получи разбор.")

    _render_progress_summary()

    cases = get_trainer_cases()
    if not cases:
        st.warning("Тренировочные кейсы не найдены.")
        return

    # ── Режим навигации ───────────────────────────────────────────────────
    col_nav, col_btn = st.columns([3, 2])
    with col_nav:
        nav_mode_ru = st.radio(
            "Режим следующего кейса:",
            list(_NAV_MODES.values()),
            horizontal=True,
            index=0,
            key="trainer_nav_mode",
        )
    nav_mode_en = {v: k for k, v in _NAV_MODES.items()}[nav_mode_ru]

    with col_btn:
        st.write("")
        st.write("")
        if st.button("⏭️ Следующий кейс"):
            current = st.session_state.get("trainer_selected_case_id")
            next_case = get_next_trainer_case_by_mode(current, nav_mode_en)
            if next_case is None:
                st.success("✅ На сегодня все кейсы уже пройдены.")
            else:
                st.session_state["trainer_selected_case_id"] = next_case["case_id"]
                st.rerun()

    # ── Selectbox ─────────────────────────────────────────────────────────
    options_label = [
        f"{c['case_id']} — {_DIFFICULTY_ICON.get(c['difficulty'], '⚪')} {c['difficulty'].capitalize()} — {c['theme']}"
        for c in cases
    ]
    options_id = [c["case_id"] for c in cases]
    default_idx = 0
    saved_id = st.session_state.get("trainer_selected_case_id")
    if saved_id and saved_id in options_id:
        default_idx = options_id.index(saved_id)

    selected_label = st.selectbox("Выбери кейс", options_label, index=default_idx, key="trainer_case_select")
    case_id = options_id[options_label.index(selected_label)]
    st.session_state["trainer_selected_case_id"] = case_id

    trainer_case = get_trainer_case(case_id)
    if not trainer_case:
        st.error(f"Кейс {case_id} не найден.")
        return

    # ── Описание кейса ────────────────────────────────────────────────────
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
            st.write(f"**UBO:** {cd.get('beneficial_owner_identified', '—')}")
            st.write(f"**SoF:** {cd.get('source_of_funds_summary') or '❌ не указан'}")
            st.write(f"**Документы:** {cd.get('supporting_documents_provided', '—')}")
            st.write(f"**Adverse media:** {cd.get('adverse_media_result', '—')}")
        if cd.get("red_flags_selected"):
            st.write(f"**Red flags:** {', '.join(cd['red_flags_selected'])}")
        if cd.get("unresolved_screening_issues"):
            st.warning(f"**Нерешённые вопросы:** {cd['unresolved_screening_issues']}")

    st.divider()

    # ── Форма ответа ──────────────────────────────────────────────────────
    st.subheader("Твой ответ")

    sig_key = f"signals_{case_id}"
    if sig_key not in st.session_state:
        st.session_state[sig_key] = ["", ""]

    with st.form(key=f"trainer_form_{case_id}"):
        col_a, col_b = st.columns(2)
        with col_a:
            decision_ru = st.selectbox("Решение", list(_DECISION_MODE_RU.values()), key=f"dm_{case_id}")
            cdd_ru      = st.selectbox("Статус CDD", list(_CDD_STATUS_RU.values()), key=f"cdd_{case_id}")
            reason_ru   = st.selectbox("Тип отказа", list(_REJECT_REASON_RU.values()), key=f"rr_{case_id}")
        with col_b:
            confidence = st.slider(
                "Уверенность (confidence_score)", 1, 5, 3,
                help="Насколько ты уверена в своём решении. "
                     "Используется для анализа переуверенности и недоуверенности.",
                key=f"conf_{case_id}",
            )
            decisive_factor = st.text_area(
                "Ключевой фактор решения (decisive_factor)",
                placeholder="Одна конкретная формулировка главного перевешивающего фактора",
                key=f"df_{case_id}", height=90,
            )

        # Динамические сигналы
        st.markdown("**Сигналы (signal_trace)**")
        signal_inputs = []
        for i, val in enumerate(st.session_state[sig_key]):
            sig_val = st.text_input(
                f"Сигнал {i + 1}", value=val,
                placeholder="Конкретный наблюдаемый факт",
                key=f"sig_{case_id}_{i}",
            )
            signal_inputs.append(sig_val)

        col_add, col_rem, _ = st.columns([1, 1, 4])
        add_signal = col_add.form_submit_button("＋ Добавить сигнал")
        rem_signal = col_rem.form_submit_button("－ Удалить последний")

        # ── Decision Note ──────────────────────────────────────────────────
        st.markdown("---")
        decision_note = st.text_area(
            "Decision Note (аналитическая записка)",
            placeholder=(
                "Напиши краткую аналитическую записку по кейсу: "
                "кто клиент, ключевые факты, red flags, анализ рисков, решение и аргументация."
            ),
            key=f"note_{case_id}",
            height=220,
        )

        submitted = st.form_submit_button("🔍 Получить разбор")

    # Обработка ± сигналов
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

    sig_dir = {"edd": "SUPPORTS_ESCALATION", "reject": "SUPPORTS_REJECT"}.get(decision_mode, "SUPPORTS_DECISION")
    filled  = [s.strip() for s in signal_inputs if s.strip()]
    signal_trace = [
        {"signal": t, "category": "OTHER",
         "impact": "DECISIVE" if i == 0 else "HIGH",
         "direction": sig_dir, "comment": "Сигнал аналитика."}
        for i, t in enumerate(filled)
    ]
    while len(signal_trace) < 2:
        signal_trace.append({"signal": "Дополнительный контекст не указан.", "category": "OTHER",
                              "impact": "LOW", "direction": "MITIGATING", "comment": "Автоматически добавлен."})

    user_output = {
        "decision_mode": decision_mode, "decision": _DECISION_MODE_RU[decision_mode],
        "edd_required": "Да" if decision_mode == "edd" else "Нет",
        "cdd_status": cdd_status,
        "risk_level": trainer_case["case_data"].get("selected_risk_level", "Средний"),
        "reject_reason_type": reject_reason,
        "decisive_factor": decisive_factor.strip() or "—",
        "error_type": "NONE", "confidence_score": confidence,
        "signal_trace": signal_trace,
        "decision_summary": "", "case_overview": "", "key_risk_factors": [],
        "cdd_assessment": {"confirmed": [], "not_confirmed": [], "conclusion": ""},
        "analysis": "", "decision_rationale": "", "required_actions": [],
        "self_review": {"summary": "", "main_gap": "", "what_to_recheck": []},
    }

    with st.spinner("Анализирую ответ..."):
        review, run_id = submit_trainer_run(
            case_id, user_output, trainer_case["expected_output"],
            decision_note=decision_note,
        )

    st.session_state[sig_key] = ["", ""]

    # ── Результаты review ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Разбор")

    score  = review["score"]
    c1, c2 = st.columns(2)
    c1.metric("Score", f"{_score_icon(score)} {score} / 100")
    c2.metric("Диагноз", _ROOT_CAUSE_RU.get(review["root_cause"], review["root_cause"]))

    # Coach message — заметный блок
    if review.get("coach_message"):
        st.info(f"💬 **Наставник:** {review['coach_message']}")

    # Note review
    if review.get("note_review"):
        nr = review["note_review"]
        n_score = nr["note_score"]
        n_qual  = _NOTE_QUALITY_RU.get(nr["note_quality"], nr["note_quality"])
        st.write(f"**Аналитическая записка:** {n_qual}  —  score {n_score}/100")
        if nr["note_issues"]:
            with st.expander("Замечания к записке", expanded=False):
                for issue in nr["note_issues"]:
                    st.write(f"- {issue}")
    elif decision_note.strip():
        st.caption("Записка получена, но оценка недоступна.")
    else:
        st.caption("Decision Note не была заполнена.")

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

    with st.expander("📖 Эталонный ответ", expanded=False):
        exp = trainer_case["expected_output"]
        st.write(f"**Решение:** {_DECISION_MODE_RU.get(exp.get('decision_mode', ''), '—')}")
        st.write(f"**Статус CDD:** {_CDD_STATUS_RU.get(exp.get('cdd_status', ''), '—')}")
        st.write(f"**Тип отказа:** {_REJECT_REASON_RU.get(exp.get('reject_reason_type', ''), '—')}")
        st.write(f"**Ключевой фактор:** {exp.get('decisive_factor', '—')}")
        for sig in exp.get("signal_trace", []):
            st.write(f"- [{sig['impact']}] {sig['signal']}")

    # Кнопка следующего
    next_case = get_next_trainer_case_by_mode(case_id, nav_mode_en)
    if next_case is None and nav_mode_en == "unfinished_today":
        st.success("✅ На сегодня все кейсы уже пройдены!")
    elif next_case:
        if st.button(f"⏭️ Следующий: {next_case['case_id']} — {next_case['theme']}"):
            st.session_state["trainer_selected_case_id"] = next_case["case_id"]
            st.rerun()

    st.caption(f"Run ID: `{run_id}`")
    st.divider()

    _render_trainer_history()
