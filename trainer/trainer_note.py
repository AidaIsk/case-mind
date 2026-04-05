# trainer/trainer_note.py
#
# Оценка Decision Note (аналитической записки) в Trainer Mode.
#
# Методологический принцип (Step 4):
#   - логика важнее объёма
#   - короткая, но точная записка может получить высокий score
#   - длина НЕ является прокси качества
#   - штраф только за отсутствие логики, reasoning и нейтрального тона
#
# Критерии оценки (каждый независимый):
#   1. Outcome present          — есть ли решение в тексте
#   2. Risk driver / decisive   — назван ли главный фактор
#   3. Rationale / explainability — объяснено ли почему именно это решение
#   4. Facts vs analysis        — разделены ли наблюдения и выводы
#   5. Neutral tone             — нет обвинительной лексики
#   6. Challenger view (light)  — хотя бы одна фраза "почему не альтернатива"
#
# Публичный API:
#   evaluate_decision_note(note, user_output, expected_output) -> dict

# ---------------------------------------------------------------------------
# Критерии — ключевые слова для каждого
# ---------------------------------------------------------------------------

# 1. Outcome — решение присутствует
_OUTCOME_KEYWORDS = [
    "одобрить", "approve", "одобрен", "принять",
    "отказать", "reject", "отказ",
    "эскалация", "edd", "усиленная проверка", "escalation",
    "рекомендую", "рекомендуется", "решение",
]

# 2. Risk driver — главный фактор назван
_RISK_DRIVER_KEYWORDS = [
    "ключевой фактор", "decisive", "основной риск", "главный риск",
    "источник средств", "sof", "ubo", "бенефициар", "владелец",
    "структурный барьер", "невозможно установить", "не может быть верифицирован",
    "экономический смысл", "платёжные реквизиты", "ценообразование",
    "пробел", "gap", "блокер", "не подтверждён", "не установлен",
    "расхождение", "несоответствие", "аномали",
]

# 3. Rationale — объяснение решения (потому что, поэтому, следовательно...)
_RATIONALE_KEYWORDS = [
    "поскольку", "потому что", "так как", "следовательно", "таким образом",
    "в связи с", "на основании", "вследствие", "это означает",
    "данные указывают", "что указывает", "свидетельствует", "подтверждает",
    "не позволяет", "делает невозможным", "является основанием",
    "означает что", "что делает", "обоснован",
]

# 4. Facts vs analysis — факты отделены от выводов
_FACTS_KEYWORDS = [
    "установлено", "предоставлен", "выявлено", "зарегистрирован",
    "согласно", "по данным", "документально", "подтверждено",
    "screening", "скрининг", "adverse media", "санкц", "pep",
    "документ", "договор", "контракт", "инвойс",
]
_ANALYSIS_KEYWORDS = [
    "риск", "анализ", "оценка", "вывод", "заключение",
    "указывает", "свидетельствует", "означает", "следует",
    "неприемлем", "приемлем", "управляем", "неуправляем",
    "превышает", "соответствует", "не соответствует",
]

# 5. Accusatory tone — обвинительная лексика (штраф)
_ACCUSATORY_PHRASES = [
    "явно отмывает", "явно скрывает", "очевидно преступ", "мошенничест",
    "злоумышленник", "преступная схема", "незаконная деятельность",
    "нарушает закон", "уголовн", "намеренно обманывает",
]

# 6. Challenger View (light) — почему не альтернатива
_CHALLENGER_KEYWORDS = [
    "challenger", "альтернатив", "вместо", "почему не",
    "хотя можно было", "можно было бы", "однако", "тем не менее",
    "в отличие от", "в противовес", "не edd", "не approve",
    "не reject", "не отказ", "не одобрени",
]

# Consistency mapping: какие тона конфликтуют с decision_mode
_CONFLICT_TONES = {
    "approve": {"reject_tone"},
    "reject":  {"approve_tone"},
    "edd":     {"approve_tone"},     # edd допускает reject_tone (gap недозакрыт)
}

_REJECT_TONE_SIGNALS = [
    "отказать", "reject", "отказ", "рекомендую отказать", "cdd_failure",
    "cdd не может быть завершён", "невозможно завершить",
]
_APPROVE_TONE_SIGNALS = [
    "одобрить", "approve", "риск приемлем", "cdd завершён", "можно принять",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _detect_consistency(note_lower: str, user_mode: str) -> tuple[bool, str | None]:
    """
    Возвращает (ok, conflict_description).
    Конфликт: approve-тон в reject-кейсе или reject-тон в approve-кейсе.
    """
    has_reject  = _has_any(note_lower, _REJECT_TONE_SIGNALS)
    has_approve = _has_any(note_lower, _APPROVE_TONE_SIGNALS)

    if user_mode == "approve" and has_reject and not has_approve:
        return False, "Записка написана в reject-тоне, но решение — Approve."
    if user_mode == "reject" and has_approve and not has_reject:
        return False, "Записка написана в approve-тоне, но решение — Отказать."
    return True, None


def _has_facts_and_analysis(note_lower: str) -> bool:
    """Проверяет, что в записке есть и факты, и аналитические выводы."""
    has_facts    = _has_any(note_lower, _FACTS_KEYWORDS)
    has_analysis = _has_any(note_lower, _ANALYSIS_KEYWORDS)
    return has_facts and has_analysis


def _check_accusatory(note_lower: str) -> bool:
    """True если выявлена обвинительная лексика."""
    return _has_any(note_lower, _ACCUSATORY_PHRASES)


def _check_risk_driver_in_note(decisive_factor: str, note_lower: str) -> bool:
    """
    Проверяет, отражён ли главный фактор решения в записке.
    Использует смысловые ключевые слова (не exact match).
    Если decisive_factor пустой — проверяем generic risk driver keywords.
    """
    if not decisive_factor or decisive_factor == "—":
        return _has_any(note_lower, _RISK_DRIVER_KEYWORDS)

    # Берём слова > 5 символов из decisive_factor — более семантически значимые
    df_words = [w for w in decisive_factor.lower().split() if len(w) > 5]
    if not df_words:
        return _has_any(note_lower, _RISK_DRIVER_KEYWORDS)

    # Смягчённый порог: 25% слов из decisive_factor — достаточно для "отражён"
    matches = sum(1 for w in df_words if w in note_lower)
    return matches / len(df_words) >= 0.25


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

def evaluate_decision_note(
    decision_note: str,
    user_output: dict,
    expected_output: dict,
) -> dict:
    """
    Оценивает Decision Note аналитика.

    Критерии качества (не длина как прокси):
      1. Outcome present         — решение названо
      2. Risk driver             — главный фактор назван
      3. Rationale               — объяснение решения
      4. Facts vs analysis       — разделение наблюдений и выводов
      5. Neutral tone            — отсутствие обвинительной лексики
      6. Challenger view (light) — хотя бы намёк на "почему не альтернатива"

    Штраф за:
      - отсутствие каждого критерия
      - обвинительную лексику
      - противоречие с structured output

    НЕ штрафует за:
      - краткость саму по себе
      - отсутствие минимальной длины (нет hard length threshold)
    """
    issues  = []
    note    = (decision_note or "").strip()
    nl      = note.lower()

    # Hard minimum: совсем пустая или нечитаемая записка
    if len(note) < 30:
        return {
            "note_score":          0,
            "note_quality":        "weak",
            "note_summary":        "Записка слишком короткая для анализа.",
            "note_issues":         ["Записка не содержит достаточного текста."],
            "note_consistency_ok": False,
        }

    user_mode       = user_output.get("decision_mode", "")
    decisive_factor = user_output.get("decisive_factor", "")

    # ── Критерий 1: Outcome (20 баллов) ──────────────────────────────────
    has_outcome = _has_any(nl, _OUTCOME_KEYWORDS)
    if not has_outcome:
        issues.append("Решение (outcome) не упомянуто в тексте записки.")

    # ── Критерий 2: Risk driver / decisive factor (20 баллов) ────────────
    has_driver = _check_risk_driver_in_note(decisive_factor, nl)
    if not has_driver:
        issues.append("Ключевой фактор решения (risk driver) не отражён в тексте.")

    # ── Критерий 3: Rationale / explainability (20 баллов) ───────────────
    has_rationale = _has_any(nl, _RATIONALE_KEYWORDS)
    if not has_rationale:
        issues.append("Не видно объяснения, почему выбран именно этот outcome.")

    # ── Критерий 4: Facts vs analysis (15 баллов) ────────────────────────
    has_facts_and_analysis = _has_facts_and_analysis(nl)
    if not has_facts_and_analysis:
        issues.append("Не видно разделения между фактами и аналитическими выводами.")

    # ── Критерий 5: Neutral tone (15 баллов) — штраф за обвинения ────────
    is_accusatory = _check_accusatory(nl)
    if is_accusatory:
        issues.append("Выявлена обвинительная лексика — записка должна быть нейтральной.")

    # ── Consistency: соответствие structured output ───────────────────────
    consistency_ok, conflict_msg = _detect_consistency(nl, user_mode)
    if not consistency_ok:
        issues.append(conflict_msg)

    # ── Критерий 6: Challenger View light (10 баллов) ─────────────────────
    has_challenger = _has_any(nl, _CHALLENGER_KEYWORDS)
    # Не штрафуем жёстко за отсутствие — только бонус за наличие

    # ── Score ─────────────────────────────────────────────────────────────
    score = 0
    score += 20 if has_outcome              else 0
    score += 20 if has_driver              else 0
    score += 20 if has_rationale           else 0
    score += 15 if has_facts_and_analysis  else 0
    score += 15 if not is_accusatory       else 0   # нейтральный тон = +15
    score += 10 if has_challenger          else 0   # light challenger view = бонус

    # Штраф за противоречие с решением (поверх баллов)
    if not consistency_ok:
        score = max(0, score - 20)

    score = min(score, 100)

    # ── Quality ───────────────────────────────────────────────────────────
    if score >= 75 and not issues:
        quality = "strong"
        summary = "Записка профессиональная: решение обосновано, тон нейтральный."
    elif score >= 75 and issues:
        quality = "acceptable"
        summary = "Записка сильная, но есть незначительные пробелы."
    elif score >= 50:
        quality = "acceptable"
        summary = "Записка приемлемая, но не хватает части критериев качества."
    else:
        quality = "weak"
        summary = "Записка требует доработки: отсутствует логика или нейтральный тон."

    return {
        "note_score":          score,
        "note_quality":        quality,
        "note_summary":        summary,
        "note_issues":         issues,
        "note_consistency_ok": consistency_ok,
        # Детализация по критериям — для диагностики
        "note_criteria": {
            "outcome":          has_outcome,
            "risk_driver":      has_driver,
            "rationale":        has_rationale,
            "facts_analysis":   has_facts_and_analysis,
            "neutral_tone":     not is_accusatory,
            "challenger_view":  has_challenger,
            "consistency":      consistency_ok,
        },
    }
