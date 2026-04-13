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

# ── Beta whitelist ────────────────────────────────────────────────────────
# Временный фильтр для первой beta: показываем только 5 кейсов.
# Чтобы снять фильтр — установить BETA_MODE = False.
# Чтобы добавить кейс — добавить case_id в BETA_CASE_IDS.
BETA_MODE     = True
BETA_CASE_IDS = {"EASY-01", "EASY-02", "MED-01", "MED-02", "ADV-01"}


def _get_beta_next_case(current_case_id: str | None, nav_mode: str) -> dict | None:
    """
    Beta-aware wrapper вокруг get_next_trainer_case_by_mode().
    Если BETA_MODE=True — возвращает только кейсы из BETA_CASE_IDS.
    Если BETA_MODE=False — работает как обычная навигация.
    """
    if not BETA_MODE:
        return get_next_trainer_case_by_mode(current_case_id, nav_mode)

    # Перебираем пока не найдём beta-кейс (max 20 итераций против бесконечного цикла)
    seen = set()
    candidate_id = current_case_id
    for _ in range(20):
        candidate = get_next_trainer_case_by_mode(candidate_id, nav_mode)
        if candidate is None:
            return None
        if candidate["case_id"] in BETA_CASE_IDS:
            return candidate
        if candidate["case_id"] in seen:
            return None   # зациклились — нет доступных beta-кейсов
        seen.add(candidate["case_id"])
        candidate_id = candidate["case_id"]
    return None

# ── ИЗМЕНЕНИЕ: добавлен пункт 7 (Challenger View) ────────────────────────
_NOTE_TEMPLATE = """**Шаблон аналитической записки:**

1. **Клиент / кейс** — кто клиент, тип кейса, страна, вид деятельности  
2. **Факты** — UBO, SoF, документы, результаты screening (sanctions, PEP, adverse media)  
3. **Red flags / триггеры** — что привлекло внимание  
4. **Анализ и уровень риска** — что именно вызывает вопросы и почему это важно  
5. **Решение** — какое решение принято  
6. **Аргументация** — почему именно это решение, ссылка на ключевой фактор  
7. **Challenger View** — одно предложение: почему ближайший альтернативный исход слабее  

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


# ── AI Mentor Block ───────────────────────────────────────────────────────

def _render_mentor_block(review: dict) -> None:
    """
    Рендерит AI Mentor как первый главный блок разбора.
    Поддерживает новый 3-block contract и старый flat contract (backward compat).
    ai_mentor=None → мягкий fallback.
    """
    mentor = review.get("ai_mentor")
    status = review.get("ai_mentor_status", "not_available")

    if not mentor or not isinstance(mentor, dict):
        st.caption("ℹ️ Разбор от наставника сейчас недоступен — ниже стандартный review.")
        if status not in ("not_available",):
            _STATUS_RU = {
                "api_error":   "Ошибка при вызове API",
                "parse_error": "Ответ модели не удалось разобрать как JSON",
                "missing_key": "Ответ модели не содержит ожидаемых полей",
            }
            with st.expander("🔧 Debug: статус наставника", expanded=False):
                st.caption(f"Статус: `{status}` — {_STATUS_RU.get(status, status)}")
        return

    st.subheader("🎓 Разбор от наставника")

    # ── Opening ───────────────────────────────────────────────────────
    opening = mentor.get("opening") or mentor.get("mentor_summary", "")
    if opening:
        st.info(opening)

    # ── Определяем тип contract ────────────────────────────────────────
    is_3block = "verdict_block" in mentor or "logic_block" in mentor or "note_block" in mentor

    if is_3block:
        _render_mentor_3block(mentor, review)
    else:
        _render_mentor_flat(mentor)

    st.divider()


def _render_mentor_3block(mentor: dict, review: dict) -> None:
    """Рендерит новый 3-block mentor contract."""

    # ── Блок 1: Вердикт ───────────────────────────────────────────────
    vb = mentor.get("verdict_block", {})
    if vb:
        with st.container():
            st.markdown("**📋 Решение**")
            d_ok   = vb.get("decision_ok", True)
            cdd_ok = vb.get("cdd_ok", True)
            c1, c2 = st.columns(2)
            c1.markdown(f"{'✅' if d_ok else '❌'} Режим решения")
            c2.markdown(f"{'✅' if cdd_ok else '❌'} Статус CDD")
            if vb.get("summary"):
                st.caption(vb["summary"])

    # ── Блок 2: Логика / decisive factor ──────────────────────────────
    lb = mentor.get("logic_block", {})
    if lb:
        st.markdown("**🔍 Decisive factor и сигналы**")
        df_verdict = lb.get("decisive_factor_verdict", "acceptable")
        _DF_ICON = {"strong": "✅", "acceptable": "🟡", "weak": "🔴"}
        icon = _DF_ICON.get(df_verdict, "🟡")

        if lb.get("decisive_factor_comment"):
            st.markdown(f"{icon} {lb['decisive_factor_comment']}")

        stronger = lb.get("stronger_decisive_factor", "")
        if stronger:
            st.success(f"**Точнее:** {stronger}")

        sig_strong = lb.get("signals_strong", [])
        sig_weak   = lb.get("signals_weak", [])
        if sig_strong or sig_weak:
            c1, c2 = st.columns(2)
            if sig_strong:
                with c1:
                    for s in sig_strong:
                        st.caption(f"✅ {s}")
            if sig_weak:
                with c2:
                    for s in sig_weak:
                        st.caption(f"⚠️ {s}")

    # ── Блок 3: Записка ───────────────────────────────────────────────
    nb = mentor.get("note_block", {})
    if nb:
        note_verdict = nb.get("note_verdict", "not_written")
        if note_verdict == "not_written":
            st.caption("📝 Записка не была заполнена.")
        else:
            _NV_LABEL = {
                "strong":    "✅ Записка сильная",
                "acceptable": "🟡 Записка приемлемая",
                "weak":      "🔴 Записка требует доработки",
                "generated": "📝 Рабочий вариант записки",
            }
            label = _NV_LABEL.get(note_verdict, "📝 Записка")
            # generated и weak открываем сразу — это главный учебный контент
            expanded = note_verdict in ("weak", "generated")
            with st.expander(label, expanded=expanded):
                if nb.get("what_works"):
                    st.markdown(f"✅ {nb['what_works']}")
                if nb.get("what_to_tighten"):
                    st.markdown(f"⚠️ {nb['what_to_tighten']}")
                ref = nb.get("short_reference", "")
                if ref:
                    if note_verdict == "generated":
                        st.markdown("На основе твоих ответов — рабочий вариант записки:")
                    else:
                        st.markdown("**Рабочий вариант:**")
                    st.info(ref)

    # ── Score explanation ──────────────────────────────────────────────
    score_exp = mentor.get("score_explanation", "")
    if score_exp:
        st.caption(f"💬 {score_exp}")

    # ── Drill next ────────────────────────────────────────────────────
    drill = mentor.get("drill_next", "")
    if drill:
        st.markdown(f"**➡️ В следующем кейсе:** {drill}")


def _render_mentor_flat(mentor: dict) -> None:
    """Рендерит старый flat contract (backward compat)."""
    main_focus   = mentor.get("main_focus") or mentor.get("main_gap", "")
    what_tighten = mentor.get("what_to_tighten", [])
    if main_focus:
        st.markdown(f"**Главное, что стоит подтянуть:** {main_focus}")
    if what_tighten:
        for item in what_tighten:
            st.caption(f"• {item}")
    sv = mentor.get("stronger_version", {})
    if not sv:
        df   = mentor.get("stronger_decisive_factor", "")
        note = mentor.get("short_reference_note", "")
        if df or note:
            sv = {"decisive_factor": df, "short_answer": note}
    if sv:
        if sv.get("decisive_factor"):
            st.markdown("**Как это сказать точнее:**")
            st.success(sv["decisive_factor"])
        if sv.get("short_answer"):
            with st.expander("📄 Рабочий вариант", expanded=False):
                st.write(sv["short_answer"])
    why = mentor.get("why_this_works") or mentor.get("why_it_matters", "")
    if why:
        st.caption(f"💡 {why}")
    drill = mentor.get("drill_next") or mentor.get("next_step", "")
    if drill:
        st.markdown(f"**➡️ В следующем кейсе:** {drill}")




# ── Field Review Block ────────────────────────────────────────────────────

_FIELD_LABELS = {
    "main_risk":       "Основной риск-вопрос",
    "risk_reasoning":  "Почему это риск",
    "actions":         "Действия",
    "decisive_factor": "Главная причина решения",
    "challenger":      "Почему не альтернатива",
}

def _render_field_review(review: dict) -> None:
    """
    Рендерит field-by-field teaching review.
    Показывается после mentor block и score, до detailed review.
    Если field_review = None — ничего не показывает.
    """
    fr = review.get("field_review")
    if not fr or not isinstance(fr, dict):
        return

    # Проверяем что хотя бы одно поле не null
    if not any(fr.get(k) for k in _FIELD_LABELS):
        return

    with st.expander("🔬 Разбор по полям", expanded=True):
        st.caption("Как звучало каждое поле — и где можно было сказать точнее.")

        for field_key, field_label in _FIELD_LABELS.items():
            field_data = fr.get(field_key)
            if not field_data or not isinstance(field_data, dict):
                continue

            user_text = field_data.get("user_text", "")
            good      = field_data.get("what_is_good", "")
            mixed     = field_data.get("what_is_mixed", "")
            stronger  = field_data.get("stronger_version", "")

            if not any([user_text, good, mixed, stronger]):
                continue

            st.markdown(f"**{field_label}**")
            # user_text — показываем первым, компактно
            if user_text and user_text != "—":
                st.caption(f"Ты написала: _{user_text}_")
            c1, c2 = st.columns(2)
            if good:
                c1.markdown(f"✅ {good}")
            if mixed:
                c2.markdown(f"⚠️ {mixed}")
            if stronger:
                st.success(f"→ {stronger}")
            st.divider()



# ── Notes Compare Block ───────────────────────────────────────────────────

def _render_notes_compare(review: dict) -> None:
    """
    Финальный учебный блок: Твоя записка vs Референсная записка.
    Показывается после mentor и field review.
    Если оба поля None — ничего не показывает.
    """
    user_note = review.get("user_note")
    ref_note  = review.get("reference_note")

    if not user_note and not ref_note:
        return

    st.subheader("📄 Записки")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Твоя записка**")
        st.caption("Собрана из твоих ответов выше.")
        if user_note:
            st.info(user_note)
        else:
            st.caption("_Заполни reasoning blocks чтобы увидеть свою записку._")

    with c2:
        st.markdown("**Референсная записка**")
        st.caption("Один из сильных вариантов упаковки этого кейса.")
        if ref_note:
            st.success(ref_note)
        else:
            st.caption("_Референс недоступен для этого кейса._")

    st.divider()


def _render_review(review: dict, expected_output: dict, trainer_case: dict, nav_mode: str, run_id: str, case_id: str):
    """Отображает результаты review — краткий или подробный режим."""
    st.divider()

    # ── AI Mentor Block — показывается первым если есть ──────────────────
    _render_mentor_block(review)

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

    has_mentor = bool(review.get("ai_mentor"))

    # coach_message: показываем только если mentor недоступен
    if review.get("coach_message") and not has_mentor:
        st.info(f"💬 **Наставник:** {review['coach_message']}")

    # ai_coach_comment: если mentor есть → в expander (не конкурирует визуально)
    #                   если mentor нет → показываем как раньше
    ai_comment = review.get("ai_coach_comment")
    if ai_comment:
        if has_mentor:
            with st.expander("Дополнительный комментарий системы", expanded=False):
                st.write(ai_comment)
        else:
            st.markdown("**🤖 AI Coach:**")
            st.write(ai_comment)

    if combined:
        st.success(f"**Итог:** {combined}")

    # ── Field-by-field teaching review ──────────────────────────────────
    _render_field_review(review)

    # ── Notes compare: Твоя записка vs Референсная ────────────────────
    _render_notes_compare(review)

    # ── Подробный режим ─────────────────────────────────────────────────
    if review_mode == "Подробный":
        col_g, col_m = st.columns(2)
        with col_g:
            st.markdown("**✅ Что верно:**")
            for item in review.get("what_was_good", []):
                st.write(f"- {item}")
        _missed = [x for x in review.get("what_was_missed", []) if x and x.strip() != "—"]
        if _missed:
            with col_m:
                st.markdown("**❌ Что пропущено:**")
                for item in _missed:
                    st.write(f"- {item}")

        if review.get("what_to_recheck"):
            st.markdown("**🔁 Что перепроверить:**")
            for item in review["what_to_recheck"]:
                st.write(f"- {item}")

        if note_rev:
            _nq_label = _NQ_RU.get(note_rev.get("note_quality", ""), "")
            _expander_title = f"📝 Оценка записки — {_nq_label}" if _nq_label else "📝 Оценка записки"
            with st.expander(_expander_title, expanded=False):
                if note_sc is not None:
                    st.caption(f"Note score: {note_sc}/100")
                st.write(note_rev.get("note_summary", "—"))
                if note_rev.get("note_issues"):
                    for issue in note_rev["note_issues"]:
                        st.caption(f"• {issue}")
        elif note_sc is None and not has_mentor:
            st.caption("📝 Записка не заполнена.")

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
    next_c = _get_beta_next_case(case_id, nav_en)
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


# ── Trainer Onboarding Block ──────────────────────────────────────────────

def _render_trainer_onboarding() -> None:
    """
    Onboarding block в начале вкладки Тренажёр.
    Компактная 2-колонка: для кого / что тренирует / как пройти / принцип.
    """
    with st.expander("ℹ️ Как работает этот тренажёр и чему он учит", expanded=True):
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(
                "**Для кого:** junior и early-middle KYC/AML аналитик, "
                "которому нужно принимать защищаемые решения по кейсам.  \n\n"
                "**Что тренирует:**  \n"
                "— логику Approve / EDD / Reject  \n"
                "— различение closable gap и structural blocker  \n"
                "— decisive factor: одна главная причина  \n"
                "— короткую защищаемую аналитическую записку"
            )

        with col_b:
            st.markdown(
                "**Как пройти:**  \n"
                "1. Выберите кейс  \n"
                "2. Заполните reasoning blocks  \n"
                "3. Получите mentor review и референсную записку  \n\n"
                "**Принцип:** AI helps reasoning, not decision-making.  \n"
                "Система помогает структурировать логику — "
                "решение остаётся за аналитиком."
            )




def _render_trainer_methodology() -> None:
    """
    Методологическая база: 4 опоры логики решений.
    Виден сразу, без expander. Оформлен через st.info для заметности.
    """
    with st.container():
        st.markdown("**📚 На чём основана логика решений**")
        c1, c2 = st.columns(2)
        with c1:
            st.info(
                "**Risk-Based Approach** — решение строится на совокупности "
                "сигналов и их значимости, а не на одном факте.  \n\n"
                "**CDD completeness** — незавершённый CDD блокирует "
                "финальное решение: нужен EDD или отказ."
            )
        with c2:
            st.info(
                "**Closable gap vs structural blocker** — "
                "информацию можно получить через EDD, "
                "или её невозможно установить — тогда Reject.  \n\n"
                "**Decisive factor + challenger view** — одна главная причина "
                "решения, которая выдерживает альтернативную интерпретацию."
            )


def render_trainer_tab():
    st.header("Тренажёр")
    st.caption("Разбери учебный кейс, запиши ответ и аналитическую записку — получи разбор.")

    _render_trainer_onboarding()
    _render_trainer_methodology()
    st.divider()

    _render_progress()

    cases = get_trainer_cases()
    # Beta filter: показываем только whitelisted кейсы
    if BETA_MODE:
        cases = [c for c in cases if c["case_id"] in BETA_CASE_IDS]
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
            next_c   = _get_beta_next_case(current, nav_en)
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

    with st.form(key=f"trainer_form_{case_id}"):

        # ── Блок 1: Факты ────────────────────────────────────────────────
        st.markdown("**1. Какие 2–4 ключевых факта установлены по кейсу?**")
        st.caption("Только наблюдаемые факты: что установлено, что выявлено, что не подтверждено. Не пиши сюда риски или выводы.")
        key_facts = st.text_area(
            "Факты", placeholder="Факт 1 / Факт 2 / Факт 3",
            key=f"facts_{case_id}", height=100, label_visibility="collapsed",
        )

        # ── Блок 2 + 3: Риск + Почему ───────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**2. Что здесь основной риск-вопрос?**")
            st.caption("Один главный risk-вопрос кейса. Не пиши сюда итоговое решение и не перечисляй все флаги.")  
            main_risk = st.text_area(
                "Риск", placeholder="Основной риск-вопрос кейса",
                key=f"risk_q_{case_id}", height=80, label_visibility="collapsed",
            )
        with c2:
            st.markdown("**3. Почему именно это создаёт риск?**")
            st.caption("Объясни ПОЧЕМУ факт создаёт риск: [факт] означает [риск] потому что... Не повторяй outcome.")  
            risk_reasoning = st.text_area(
                "Reasoning", placeholder="Почему это важно для CDD/KYC",
                key=f"risk_why_{case_id}", height=80, label_visibility="collapsed",
            )

        # ── Блок 4: Действия ─────────────────────────────────────────────
        st.markdown("**4. Какие действия нужны?**")
        st.caption("Конкретные шаги: что запросить, что проверить. Не ограничивайся словом «EDD» — назови конкретное действие.")
        actions = st.text_area(
            "Действия", placeholder="Запросить ... / Проверить ... / Уточнить ...",
            key=f"actions_{case_id}", height=80, label_visibility="collapsed",
        )

        # ── Блок 5 + 6: Решение + Decisive Factor ───────────────────────
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**5. Какой outcome нужен?**")
            dm_ru = st.selectbox(
                "Решение", list(_DM_RU.values()), key=f"dm_{case_id}",
                label_visibility="collapsed",
            )
            cdd_ru = st.selectbox(
                "Статус CDD", list(_CDD_RU.values()),
                help="Незавершённый CDD vs структурный барьер.",
                key=f"cdd_{case_id}",
            )
            risk_ru = st.selectbox(
                "Уровень риска", ["Низкий", "Средний", "Высокий"],
                index=2, key=f"risk_{case_id}",
            )
        with c4:
            st.markdown("**6. Одна главная причина решения**")
            st.caption("Одна причина, которая перевешивает всё. Структура: [факт] → [что означает для решения]. Не пересказывай все риски.")  
            df = st.text_area(
                "Decisive factor",
                placeholder="[конкретный факт] → [что это означает для решения]",
                key=f"df_{case_id}", height=100, label_visibility="collapsed",
            )

        # ── Блок 7: Challenger View ───────────────────────────────────────
        st.markdown("**7. Почему не ближайшая альтернатива?**")
        st.caption("Почему ближайший альтернативный исход слабее. Не повторяй decisive factor — объясни, что делает альтернативу неверной.")  
        challenger = st.text_area(
            "Challenger view",
            placeholder="Потому что... / В отличие от... / Альтернативный вывод был бы слабее, потому что...",
            key=f"challenger_{case_id}", height=70, label_visibility="collapsed",
        )

        # ── Уверенность (скрыта в details, не доминирует) ───────────────
        with st.expander("Дополнительно", expanded=False):
            conf = st.slider(
                "Уверенность в решении", 1, 5, 3,
                help="Для аналитики: помогает отловить ошибки при высокой уверенности.",
                key=f"conf_{case_id}",
            )

        submitted = st.form_submit_button("🔍 Получить разбор")

    # Нет add/remove signal кнопок в beta — сигналы строятся из facts
    add_s = rem_s = False

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
    if dm == "reject":
        rr = "CDD_FAILURE" if "cannot be completed" in cdd.lower() else "RISK_UNACCEPTABLE"
    else:
        rr = "NONE"

    # В Beta v1 signal_trace строится из key_facts — не из отдельных полей
    sd = {"edd": "SUPPORTS_ESCALATION", "reject": "SUPPORTS_REJECT"}.get(dm, "SUPPORTS_DECISION")
    facts_lines = [l.strip() for l in (key_facts or "").splitlines() if l.strip()]
    trace = [{"signal": t, "category": "OTHER",
               "impact": "DECISIVE" if i == 0 else "HIGH",
               "direction": sd, "comment": "Факт аналитика."} for i, t in enumerate(facts_lines)]
    while len(trace) < 2:
        trace.append({"signal": "Дополнительный контекст не указан.", "category": "OTHER",
                      "impact": "LOW", "direction": "MITIGATING", "comment": "Автоматически добавлен."})

    user_output = {
        "decision_mode": dm, "decision": _DM_RU[dm],
        "edd_required": "Да" if dm == "edd" else "Нет",
        "cdd_status": cdd, "risk_level": risk_ru,
        "reject_reason_type": rr,
        "decisive_factor": df.strip() or "—",
        "error_type": "NONE", "confidence_score": conf, "signal_trace": trace,
        "decision_summary": "", "case_overview": "", "key_risk_factors": [],
        "cdd_assessment": {"confirmed": [], "not_confirmed": [], "conclusion": ""},
        "analysis": "", "decision_rationale": "", "required_actions": [],
        "self_review": {"summary": "", "main_gap": "", "what_to_recheck": []},
        # ── Beta v1: reasoning blocks — видны только Mentor, не deterministic core ──
        "_beta_key_facts":      key_facts.strip()   if key_facts   else "",
        "_beta_main_risk":      main_risk.strip()   if main_risk   else "",
        "_beta_risk_reasoning": risk_reasoning.strip() if risk_reasoning else "",
        "_beta_actions":        actions.strip()     if actions     else "",
        "_beta_challenger":     challenger.strip()  if challenger  else "",
    }

    # В Beta v1 Decision Note не обязательна — генерируется системой
    dn = ""   # пустая строка → note_review не запускается, Mentor сгенерирует note

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
    # Показываем review: либо только что посчитанный, либо сохранённый из session_state
    _last = st.session_state.get("last_trainer_review")
    if _last and _last.get("case_id") == case_id:
        _render_review(
            _last["review"], _last["expected_output"],
            _last["trainer_case"], _last["nav_mode"],
            _last["run_id"], case_id,
        )
