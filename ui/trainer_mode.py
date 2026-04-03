# ui/trainer_mode.py  —  Trainer Mode v2 micro-polish
# combined_summary, краткий/подробный review, шаблон записки,
# визуальное сравнение score, фильтр "сегодня", empty-states.

import streamlit as st
from datetime import date as _date

from core.services import (
    get_trainer_cases,
    get_trainer_case,
    submit_trainer_run,
    get_trainer_runs,
    get_trainer_progress_summary,
    get_next_trainer_case_by_mode,
)

# ── Словари ──────────────────────────────────────────────────────────────

_DM_RU   = {"approve": "Одобрить", "edd": "Эскалация (EDD)", "reject": "Отказать"}
_DM_EN   = {v: k for k, v in _DM_RU.items()}
_CDD_RU  = {
    "Complete":                           "CDD завершён",
    "Incomplete":                         "CDD не завершён",
    "Incomplete and cannot be completed": "CDD не может быть завершён",
    "Complete but risk not acceptable":   "CDD завершён, но риск неприемлем",
}
_CDD_EN  = {v: k for k, v in _CDD_RU.items()}
_RR_RU   = {"NONE": "Нет", "CDD_FAILURE": "CDD не может быть завершён",
             "RISK_UNACCEPTABLE": "Неприемлемый риск"}
_RR_EN   = {v: k for k, v in _RR_RU.items()}
_TREND   = {
    "improving": "📈 Растёт", "declining": "📉 Снижается", "stable": "➡️ Стабильно",
    "preliminary_improving": "📈 Предварительно растёт",
    "preliminary_declining": "📉 Предварительно снижается",
    "preliminary_stable":    "➡️ Предварительно стабильно",
    "not_enough_data": "⏳ Недостаточно данных",
}
_RC_RU   = {
    "NONE": "Ошибок не выявлено", "MISREAD_CDD_STATUS": "Неверный статус CDD",
    "MISSED_SOF_GAP": "Пропущен пробел по SoF",
    "MISSED_UBO_BLOCKER": "Пропущен блокер по UBO",
    "MISSED_ADVERSE_MEDIA": "Не выявлен adverse media",
    "OVER_REJECT": "Избыточный отказ", "UNDER_REJECT": "Недостаточно жёсткое решение",
    "WEAK_DECISIVE_FACTOR": "Расплывчатый decisive factor",
    "WEAK_SIGNAL_TRACE": "Неполный signal trace", "WEAK_RATIONALE": "Слабое обоснование",
}
_NQ_RU   = {"strong": "✅ Сильная", "acceptable": "🟡 Приемлемая", "weak": "🔴 Слабая"}
_D_ICON  = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
_NAV     = {"unfinished_today": "Непройденный сегодня", "sequential": "Подряд", "random": "Случайный"}
MAX_SIG  = 8

_NOTE_TEMPLATE = """**Шаблон аналитической записки:**

1. **Клиент / кейс** — кто клиент, тип кейса, страна, вид деятельности  
2. **Факты** — UBO, SoF, документы, результаты screening (sanctions, PEP, adverse media)  
3. **Red flags / триггеры** — что привлекло внимание  
4. **Анализ и уровень риска** — что именно вызывает вопросы и почему это важно  
5. **Решение** — какое решение принято  
6. **Аргументация** — почему именно это решение, ссылка на ключевой фактор  

*Не подглядывай в данные кейса — пиши по памяти из формы выше.*"""


def _sicon(score):
    return "🟢" if score >= 85 else ("🟡" if score >= 60 else "🔴")


# ── Прогресс ─────────────────────────────────────────────────────────────

def _render_progress():
    s = get_trainer_progress_summary()
    if s["total_runs"] == 0:
        st.info("Пока нет прогонов — реши первый кейс, и здесь появится статистика.")
        return
    st.subheader("Прогресс")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Прогонов",       s["total_runs"])
    c2.metric("Средний score",  f"{s['avg_score']} / 100")
    c3.metric("Верных решений", f"{s['correct_decision_rate']}%")
    c4.metric("Тренд",          _TREND.get(s["score_trend"], "—"))
    st.warning(f"⚠️ **Слабая зона:** {s['weak_zone']}")
    dist = {k: v for k, v in s.get("root_cause_distribution", {}).items() if k != "NONE"}
    if dist:
        st.caption("Частые причины: " + "  |  ".join(
            f"**{_RC_RU.get(k, k)}**: {v}" for k, v in list(dist.items())[:3]))
    st.divider()


# ── История прогонов ──────────────────────────────────────────────────────

def _render_history():
    runs = get_trainer_runs()
    st.subheader("История прогонов")

    # Фильтр — теперь 4 варианта
    flt = st.radio(
        "Показывать:",
        ["Все", "Только ошибки", "Только низкий score", "Только сегодня"],
        horizontal=True, key="history_filter",
    )

    today = _date.today().strftime("%Y-%m-%d")
    filtered = list(reversed(runs))

    if flt == "Только ошибки":
        filtered = [r for r in filtered
                    if r.get("root_cause", "NONE") != "NONE"
                    or r.get("error_type", "NONE") != "NONE"]
    elif flt == "Только низкий score":
        filtered = [r for r in filtered if r.get("score", 100) < 60]
    elif flt == "Только сегодня":
        filtered = [r for r in filtered if r.get("saved_at", "").startswith(today)]

    # Empty-states
    if not runs:
        st.info("Пока нет прогонов — реши первый кейс, и здесь появится история.")
        return
    if not filtered:
        empty_msgs = {
            "Только ошибки":      "Ошибок по выбранному фильтру не найдено.",
            "Только низкий score":"Низких score пока нет — это хороший знак. 🎉",
            "Только сегодня":     "Сегодня ещё нет прогонов.",
        }
        st.info(empty_msgs.get(flt, "Нет прогонов по выбранному фильтру."))
        return

    for run in filtered[:10]:
        score     = run.get("score", 0)
        note_sc   = run.get("note_score")
        icon      = _sicon(score)
        root      = _RC_RU.get(run.get("root_cause", ""), "—")
        correct   = "✅" if run.get("is_correct_decision") else "❌"
        note_part = f"  |  📝 {note_sc}" if note_sc is not None else ""
        combined  = run.get("review", {}).get("combined_summary", "")

        with st.expander(
            f"{run.get('saved_at', '—')}  |  {run.get('trainer_case_id', '—')}  "
            f"|  {icon} {score}/100{note_part}  |  {correct}",
            expanded=False,
        ):
            st.write(f"**Диагноз:** {root}")
            if combined:
                st.write(f"**Итог:** {combined}")
            coach = run.get("review", {}).get("coach_message", "")
            if coach:
                st.info(f"💬 {coach}")
            if run.get("decision_note"):
                with st.expander("Аналитическая записка", expanded=False):
                    st.write(run["decision_note"])


# ── Результаты review ────────────────────────────────────────────────────

def _render_review(review: dict, expected_output: dict, trainer_case: dict, nav_mode: str, run_id: str, case_id: str):
    """Отображает результаты review — краткий или подробный режим."""
    st.divider()
    st.subheader("Разбор")

    score    = review["score"]
    note_sc  = review.get("note_score")
    note_rev = review.get("note_review")
    combined = review.get("combined_summary", "")
    root     = _RC_RU.get(review["root_cause"], review["root_cause"])

    # Режим review
    review_mode = st.radio(
        "Режим разбора:", ["Краткий", "Подробный"],
        horizontal=True, key=f"review_mode_{run_id}",
    )

    # ── Всегда: score + диагноз + coach + combined ──────────────────────
    c1, c2 = st.columns(2)
    c1.metric("Score", f"{_sicon(score)} {score} / 100")
    c2.metric("Диагноз", root)

    if review.get("coach_message"):
        st.info(f"💬 **Наставник:** {review['coach_message']}")

    # AI Coach Comment — генерируется LLM поверх deterministic review
    ai_comment = review.get("ai_coach_comment")
    if ai_comment:
        st.markdown("**🤖 AI Coach:**")
        st.write(ai_comment)
    # Если None — просто ничего не показываем, Trainer работает как раньше

    if combined:
        st.success(f"**Итог:** {combined}")

    # ── Сравнение score и note_score ────────────────────────────────────
    if note_sc is not None:
        st.markdown("**Сравнение оценок**")
        sc1, sc2 = st.columns(2)
        sc1.metric("Structured score", f"{_sicon(score)} {score} / 100")
        sc2.metric("Decision Note score", f"{_sicon(note_sc)} {note_sc} / 100")

        delta = score - note_sc
        if abs(delta) >= 15:
            if delta > 0:
                st.caption("💡 Ты лучше определяешь решение, чем формулируешь аналитическую записку.")
            else:
                st.caption("💡 Записка звучит лучше, чем структурная логика решения.")
    else:
        sc1, _ = st.columns(2)
        sc1.metric("Structured score", f"{_sicon(score)} {score} / 100")
        st.caption("Decision Note не была заполнена — оценка недоступна.")

    # ── Подробный режим ─────────────────────────────────────────────────
    if review_mode == "Подробный":
        col_g, col_m = st.columns(2)
        with col_g:
            st.markdown("**✅ Что верно:**")
            for item in review.get("what_was_good", []):
                st.write(f"- {item}")
        with col_m:
            st.markdown("**❌ Что пропущено:**")
            for item in review.get("what_was_missed", []):
                st.write(f"- {item}")

        if review.get("what_to_recheck"):
            st.markdown("**🔁 Что перепроверить:**")
            for item in review["what_to_recheck"]:
                st.write(f"- {item}")

        if note_rev:
            with st.expander("Разбор аналитической записки", expanded=False):
                nq = _NQ_RU.get(note_rev.get("note_quality", ""), "")
                st.write(f"**Качество:** {nq}  —  score {note_sc}/100")
                st.write(f"**Резюме:** {note_rev.get('note_summary', '—')}")
                if note_rev.get("note_issues"):
                    for issue in note_rev["note_issues"]:
                        st.write(f"- {issue}")

        with st.expander("📖 Эталонный ответ", expanded=False):
            exp = expected_output
            st.write(f"**Решение:** {_DM_RU.get(exp.get('decision_mode', ''), '—')}")
            st.write(f"**Статус CDD:** {_CDD_RU.get(exp.get('cdd_status', ''), '—')}")
            st.write(f"**Тип отказа:** {_RR_RU.get(exp.get('reject_reason_type', ''), '—')}")
            st.write(f"**Ключевой фактор:** {exp.get('decisive_factor', '—')}")
            for sig in exp.get("signal_trace", []):
                st.write(f"- [{sig['impact']}] {sig['signal']}")

    # ── Кнопка следующего ───────────────────────────────────────────────
    nav_en = {v: k for k, v in _NAV.items()}[nav_mode]
    next_c = get_next_trainer_case_by_mode(case_id, nav_en)
    if next_c is None and nav_en == "unfinished_today":
        st.success("✅ На сегодня все кейсы уже пройдены!")
    elif next_c:
        if st.button(f"⏭️ Следующий: {next_c['case_id']} — {next_c.get('title_user', next_c['case_id'])}"):
            st.session_state["trainer_selected_case_id"] = next_c["case_id"]
            st.rerun()

    st.caption(f"Run ID: `{run_id}`")
    st.divider()
    _render_history()


# ── Главная вкладка ───────────────────────────────────────────────────────

def render_trainer_tab():
    st.header("Trainer Mode")
    st.caption("Разбери учебный кейс, запиши ответ и аналитическую записку — получи разбор.")

    _render_progress()

    cases = get_trainer_cases()
    if not cases:
        st.warning("Тренировочные кейсы не найдены.")
        return

    # Навигация
    col_nav, col_btn = st.columns([3, 2])
    with col_nav:
        nav_mode = st.radio(
            "Режим следующего кейса:", list(_NAV.values()),
            horizontal=True, index=0, key="trainer_nav_mode",
        )
    with col_btn:
        st.write(""); st.write("")
        if st.button("⏭️ Следующий кейс"):
            current  = st.session_state.get("trainer_selected_case_id")
            nav_en   = {v: k for k, v in _NAV.items()}[nav_mode]
            next_c   = get_next_trainer_case_by_mode(current, nav_en)
            if next_c is None:
                st.success("✅ На сегодня все кейсы уже пройдены.")
            else:
                st.session_state["trainer_selected_case_id"] = next_c["case_id"]
                st.rerun()

    # Selectbox
    labels = [
        f"{c['case_id']} — {c.get('title_user', c['case_id'])}"
        for c in cases
    ]
    ids = [c["case_id"] for c in cases]
    def_idx = 0
    if st.session_state.get("trainer_selected_case_id") in ids:
        def_idx = ids.index(st.session_state["trainer_selected_case_id"])

    sel = st.selectbox("Выбери кейс", labels, index=def_idx, key="trainer_case_select")
    case_id = ids[labels.index(sel)]
    st.session_state["trainer_selected_case_id"] = case_id

    tc = get_trainer_case(case_id)
    if not tc:
        st.error(f"Кейс {case_id} не найден.")
        return

    # Описание
    st.subheader(f"{tc['case_id']} — {tc.get('title_user', tc['case_id'])}")
    st.info(tc.get("description_user", tc.get("description", "")))

    with st.expander("📋 Данные кейса", expanded=False):
        cd = tc["case_data"]
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Клиент:** {cd.get('client_name', '—')}")
            st.write(f"**Тип:** {cd.get('client_type', '—')}")
            st.write(f"**Страна:** {cd.get('registration_country', '—')}")
            st.write(f"**Деятельность:** {cd.get('business_activity', '—')}")
            st.write(f"**Тип кейса:** {cd.get('case_type', '—')}")
        with c2:
            st.write(f"**UBO установлен:** {cd.get('beneficial_owner_identified', '—')}")
            sof = cd.get("source_of_funds_summary", "")
            st.write(f"**Источник средств:** {sof if sof else 'не указан'}")
            st.write(f"**Документы:** {cd.get('supporting_documents_provided', '—')}")
            st.write(f"**Sanctions / PEP / Adverse media:** "
                     f"{cd.get('sanctions_result','—')} / "
                     f"{cd.get('pep_result','—')} / "
                     f"{cd.get('adverse_media_result','—')}")

        # Документы из user-facing поля — без аналитической интерпретации
        docs = tc.get("documents_provided", [])
        if docs:
            st.write(f"**Предоставленные документы:** {', '.join(docs)}")

        # "Дополнительные наблюдения" — только факты, без готового вывода
        observations = tc.get("questions_or_conflict") or cd.get("unresolved_screening_issues", "")
        if observations:
            st.info(f"**Дополнительные наблюдения:** {observations}")

    st.divider()
    st.subheader("Твой ответ")

    sig_key = f"signals_{case_id}"
    if sig_key not in st.session_state:
        st.session_state[sig_key] = ["", ""]

    with st.form(key=f"trainer_form_{case_id}"):
        ca, cb = st.columns(2)
        with ca:
            dm_ru  = st.selectbox("Решение", list(_DM_RU.values()), key=f"dm_{case_id}")
            cdd_ru = st.selectbox(
                "Статус CDD", list(_CDD_RU.values()),
                help="Помогает отличать незавершённый CDD от ситуации, где CDD действительно не может быть завершён.",
                key=f"cdd_{case_id}",
            )
            risk_ru = st.selectbox(
                "Уровень риска",
                ["Низкий", "Средний", "Высокий"],
                index=2,
                key=f"risk_{case_id}",
            )
        with cb:
            conf = st.slider(
                "Уверенность в решении", 1, 5, 3,
                help="Показывает, насколько ты уверен(а) в своём решении. "
                     "Помогает анализировать не только ошибки, но и ошибки при высокой уверенности.",
                key=f"conf_{case_id}",
            )
            df = st.text_area(
                "Ключевой фактор решения",
                placeholder="Одна конкретная формулировка главного перевешивающего фактора",
                key=f"df_{case_id}", height=90,
            )

        st.markdown("**Сигналы (signal_trace)**")
        sigs = []
        for i, val in enumerate(st.session_state[sig_key]):
            sv = st.text_input(f"Сигнал {i+1}", value=val,
                               placeholder="Конкретный наблюдаемый факт",
                               key=f"sig_{case_id}_{i}")
            sigs.append(sv)

        ca2, cb2, _ = st.columns([1, 1, 4])
        add_s = ca2.form_submit_button("＋ Добавить сигнал")
        rem_s = cb2.form_submit_button("－ Удалить последний")

        # Шаблон-подсказка для Decision Note
        with st.expander("💡 Подсказка по структуре аналитической записки", expanded=False):
            st.markdown(_NOTE_TEMPLATE)

        dn = st.text_area(
            "Decision Note (аналитическая записка)",
            placeholder=(
                "Напиши краткую аналитическую записку: "
                "кто клиент, факты, red flags, анализ, решение, аргументация."
            ),
            key=f"note_{case_id}", height=220,
        )
        submitted = st.form_submit_button("🔍 Получить разбор")

    if add_s:
        if len(st.session_state[sig_key]) < MAX_SIG:
            st.session_state[sig_key] = sigs + [""]
        st.rerun()
    if rem_s:
        if len(st.session_state[sig_key]) > 2:
            st.session_state[sig_key] = sigs[:-1]
        st.rerun()

    if not submitted:
        # Показываем сохранённый review если он есть для текущего кейса
        _last = st.session_state.get("last_trainer_review")
        if _last and _last.get("case_id") == case_id:
            _render_review(
                _last["review"], _last["expected_output"],
                _last["trainer_case"], _last["nav_mode"],
                _last["run_id"], case_id,
            )
        return

    # Сборка user_output
    dm  = _DM_EN[dm_ru]
    cdd = _CDD_EN[cdd_ru]
    # reject_reason_type выводится автоматически из decision_mode и cdd_status —
    # пользователь не должен выбирать внутреннюю taxonomy напрямую
    if dm == "reject":
        if "cannot be completed" in cdd.lower():
            rr = "CDD_FAILURE"
        else:
            rr = "RISK_UNACCEPTABLE"
    else:
        rr = "NONE"

    sd = {"edd": "SUPPORTS_ESCALATION", "reject": "SUPPORTS_REJECT"}.get(dm, "SUPPORTS_DECISION")
    filled = [s.strip() for s in sigs if s.strip()]
    trace  = [{"signal": t, "category": "OTHER",
               "impact": "DECISIVE" if i == 0 else "HIGH",
               "direction": sd, "comment": "Сигнал аналитика."} for i, t in enumerate(filled)]
    while len(trace) < 2:
        trace.append({"signal": "Дополнительный контекст не указан.", "category": "OTHER",
                      "impact": "LOW", "direction": "MITIGATING", "comment": "Автоматически добавлен."})

    user_output = {
        "decision_mode": dm, "decision": _DM_RU[dm],
        "edd_required": "Да" if dm == "edd" else "Нет",
        "cdd_status": cdd, "risk_level": risk_ru,
        "reject_reason_type": rr, "decisive_factor": df.strip() or "—",
        "error_type": "NONE", "confidence_score": conf, "signal_trace": trace,
        "decision_summary": "", "case_overview": "", "key_risk_factors": [],
        "cdd_assessment": {"confirmed": [], "not_confirmed": [], "conclusion": ""},
        "analysis": "", "decision_rationale": "", "required_actions": [],
        "self_review": {"summary": "", "main_gap": "", "what_to_recheck": []},
    }

    with st.spinner("Анализирую ответ..."):
        review, run_id = submit_trainer_run(case_id, user_output, tc["expected_output"], decision_note=dn)

    # Сохраняем review в session_state — чтобы пережить rerun при переключении режима
    st.session_state["last_trainer_review"] = {
        "review":          review,
        "run_id":          run_id,
        "case_id":         case_id,
        "expected_output": tc["expected_output"],
        "trainer_case":    tc,
        "nav_mode":        nav_mode,
    }
    st.session_state[sig_key] = ["", ""]

    # Показываем review: либо только что посчитанный, либо сохранённый из session_state
    _last = st.session_state.get("last_trainer_review")
    if _last and _last.get("case_id") == case_id:
        _render_review(
            _last["review"], _last["expected_output"],
            _last["trainer_case"], _last["nav_mode"],
            _last["run_id"], case_id,
        )
