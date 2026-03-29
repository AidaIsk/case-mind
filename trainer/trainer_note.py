# trainer/trainer_note.py
#
# Оценка Decision Note (аналитической записки) в Trainer Mode.
#
# Принцип: без тяжёлого NLP — только эвристики на ключевые слова,
# длину и консистентность со structured output.
#
# Публичный API:
#   evaluate_decision_note(note, user_output, expected_output) -> dict

# ---------------------------------------------------------------------------
# Ключевые слова для проверки логических блоков
# ---------------------------------------------------------------------------

_BLOCK_KEYWORDS = {
    "client": [
        "клиент", "компания", "организация", "зарегистрирован", "деятельност",
        "onboarding", "кейс", "тип", "страна", "вид",
    ],
    "facts": [
        "ubo", "sof", "документ", "скрининг", "screening", "санкц", "pep",
        "adverse", "публикац", "источник", "средств", "учредитель", "бенефициар",
        "владелец", "операц", "сумма", "контрагент", "geography", "юрисдикц",
    ],
    "analysis": [
        "риск", "анализ", "поскольку", "следовательно", "таким образом",
        "однако", "несмотря", "указывает", "свидетельствует", "означает",
        "проблем", "пробел", "gap", "блокер", "подтвержден", "не подтвержден",
        "неприемлем", "завершён", "невозможно",
    ],
    "decision": [
        "решение", "одобрить", "отказать", "эскалация", "edd", "reject",
        "approve", "рекомендую", "рекомендуется", "вывод", "итог",
        "основани", "причин", "потому что", "так как",
    ],
}

# Минимальная длина полноценной записки (символов)
_MIN_NOTE_LENGTH = 150
_WEAK_NOTE_LENGTH = 80

# Сигналы reject-тональности в тексте
_REJECT_SIGNALS = [
    "невозможно завершить", "не может быть завершён", "отказать",
    "неприемлем", "cdd_failure", "reject", "заблокирован",
    "отказ", "рекомендую отказать", "необходимо отказать",
    "завершение cdd невозможно", "невозможно завершить cdd",
    "не может быть завершен", "cdd не может",
]
_EDD_SIGNALS = [
    "эскалация", "edd", "запросить", "дозапросить", "уточнить",
    "получить документы", "пробел закрываем", "запрос документов",
    "требуется edd", "усиленная проверка",
]
_APPROVE_SIGNALS = [
    "одобрить", "approve", "подтверждён", "cdd завершён",
    "риск приемлем", "можно принять", "принять клиента",
]


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _note_lower(note: str) -> str:
    return note.lower()


def _count_blocks(note_lower: str) -> dict[str, bool]:
    """Проверяет наличие 4 логических блоков записки."""
    return {
        block: any(kw in note_lower for kw in keywords)
        for block, keywords in _BLOCK_KEYWORDS.items()
    }


def _detect_note_tone(note_lower: str) -> str:
    """Определяет тональность записки: reject / edd / approve / neutral."""
    reject_hits  = sum(1 for s in _REJECT_SIGNALS  if s in note_lower)
    edd_hits     = sum(1 for s in _EDD_SIGNALS      if s in note_lower)
    approve_hits = sum(1 for s in _APPROVE_SIGNALS  if s in note_lower)

    # Если есть явные reject-конструкции ("рекомендую отказать",
    # "необходимо отказать") — тон reject даже при единственном совпадении
    strong_reject = ["рекомендую отказать", "необходимо отказать",
                     "завершение cdd невозможно", "cdd не может"]
    if any(p in note_lower for p in strong_reject):
        return "reject"

    if reject_hits > edd_hits and reject_hits > approve_hits:
        return "reject"
    if edd_hits > reject_hits and edd_hits > approve_hits:
        return "edd"
    if approve_hits > 0 and reject_hits == 0:
        return "approve"
    return "neutral"


def _check_decisive_factor_in_note(decisive_factor: str, note_lower: str) -> bool:
    """Проверяет, отражён ли decisive_factor в тексте записки (нечёткое совпадение)."""
    if not decisive_factor or decisive_factor == "—":
        return False
    df_words = {w for w in decisive_factor.lower().split() if len(w) > 4}
    if not df_words:
        return False
    matches = sum(1 for w in df_words if w in note_lower)
    return matches / len(df_words) >= 0.35


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

    Проверяет:
    1. Структуру — есть ли 4 логических блока.
    2. Длину — не слишком ли короткая записка.
    3. Консистентность со structured output.
    4. Отражение decisive_factor.

    Returns:
        dict с полями note_score, note_quality, note_summary,
        note_issues, note_consistency_ok.
    """
    issues = []
    note = (decision_note or "").strip()
    note_lower = _note_lower(note)

    # ── 1. Длина ──────────────────────────────────────────────────────────
    if len(note) < _WEAK_NOTE_LENGTH:
        issues.append("Записка слишком короткая — недостаточно для анализа кейса.")
        return {
            "note_score":        0,
            "note_quality":      "weak",
            "note_summary":      "Записка слишком короткая.",
            "note_issues":       issues,
            "note_consistency_ok": False,
        }

    # ── 2. Структура (4 блока) ────────────────────────────────────────────
    blocks = _count_blocks(note_lower)
    missing_blocks = [b for b, present in blocks.items() if not present]

    block_labels = {
        "client":   "описание клиента / кейса",
        "facts":    "факты (UBO, SoF, документы, screening)",
        "analysis": "анализ рисков",
        "decision": "решение и аргументация",
    }
    for b in missing_blocks:
        issues.append(f"Не найден блок: {block_labels[b]}.")

    blocks_found = 4 - len(missing_blocks)

    # ── 3. Консистентность со structured output ───────────────────────────
    user_mode  = user_output.get("decision_mode", "")
    note_tone  = _detect_note_tone(note_lower)
    consistency_ok = True

    # Конфликт: какая тональность недопустима для каждого decision_mode
    # EDD конфликтует и с approve и с reject (записка должна говорить о пробелах)
    mode_tone_conflicts = {
        "approve": {"reject"},
        "reject":  {"approve"},
        "edd":     {"approve", "reject"},
    }
    conflicts = mode_tone_conflicts.get(user_mode, set())
    if note_tone in conflicts:
        issues.append(
            f"Записка противоречит решению: structured output = «{user_mode}», "
            f"но тональность записки указывает на «{note_tone}»."
        )
        consistency_ok = False

    # ── 4. Decisive factor в тексте ───────────────────────────────────────
    decisive_factor = user_output.get("decisive_factor", "")
    df_reflected = _check_decisive_factor_in_note(decisive_factor, note_lower)
    if not df_reflected and decisive_factor and decisive_factor != "—":
        issues.append("Ключевой фактор решения (decisive factor) не отражён в тексте записки.")

    # ── 5. Score ─────────────────────────────────────────────────────────
    score = 0
    score += 30 * blocks_found // 4        # до 30 баллов за структуру
    score += 20 if consistency_ok else 0   # 20 баллов за консистентность
    score += 20 if df_reflected else 0     # 20 баллов за decisive factor
    score += 15 if len(note) >= _MIN_NOTE_LENGTH else 7  # 15/7 за длину
    score += 15 if not missing_blocks else 0              # бонус за полноту

    score = min(score, 100)

    # ── 6. Quality ────────────────────────────────────────────────────────
    if score >= 75 and not issues:
        quality = "strong"
        summary = "Записка структурирована, консистентна с решением, ключевой фактор отражён."
    elif score >= 50:
        quality = "acceptable"
        summary = "Записка приемлемая, но есть пробелы в структуре или обосновании."
    else:
        quality = "weak"
        summary = "Записка требует доработки: недостаточно структуры или есть противоречия."

    return {
        "note_score":         score,
        "note_quality":       quality,
        "note_summary":       summary,
        "note_issues":        issues,
        "note_consistency_ok": consistency_ok,
    }
