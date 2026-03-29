# trainer/trainer_analytics.py
#
# Stage 3B — Progress & Weak Zones.
# Отвечает на вопросы: куда движется аналитик, где слабее, что повторять.
#
# Публичный API:
#   summarize_trainer_runs(runs, trainer_cases) -> dict
#   detect_score_trend(runs)                    -> str
#   detect_trainer_weak_zone(runs, cases)       -> str

from collections import Counter


# ---------------------------------------------------------------------------
# Пороги для определения тренда
# ---------------------------------------------------------------------------

_TREND_THRESHOLD = 5   # разница в очках между двумя окнами для фиксации тренда
_WINDOW_SIZE     = 5   # размер окна для сравнения


# ---------------------------------------------------------------------------
# 1. Тренд score
# ---------------------------------------------------------------------------

def detect_score_trend(runs: list[dict]) -> str:
    """
    Определяет тренд score.

    Режимы по количеству прогонов:
        0–2   → "not_enough_data"
        3–5   → предварительный тренд ("preliminary_improving" и т.д.)
        6+    → обычный тренд ("improving" / "declining" / "stable")
    """
    n = len(runs)
    scores = [r.get("score", 0) for r in runs]

    if n < 3:
        return "not_enough_data"

    # Предварительный тренд: сравниваем первую и вторую половины
    if n < _WINDOW_SIZE * 2:
        mid = n // 2
        first_half  = scores[:mid]
        second_half = scores[mid:]
        if not first_half or not second_half:
            return "not_enough_data"
        avg_first  = sum(first_half)  / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        delta = avg_second - avg_first
        if delta >= _TREND_THRESHOLD:
            return "preliminary_improving"
        if delta <= -_TREND_THRESHOLD:
            return "preliminary_declining"
        return "preliminary_stable"

    # Полный тренд: два окна по _WINDOW_SIZE
    recent   = scores[-_WINDOW_SIZE:]
    previous = scores[-_WINDOW_SIZE * 2 : -_WINDOW_SIZE]
    avg_recent   = sum(recent)   / len(recent)
    avg_previous = sum(previous) / len(previous)
    delta = avg_recent - avg_previous

    if delta >= _TREND_THRESHOLD:
        return "improving"
    if delta <= -_TREND_THRESHOLD:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# 2. Weak zone
# ---------------------------------------------------------------------------

def detect_trainer_weak_zone(runs: list[dict], trainer_cases: list[dict]) -> str:
    """
    Диагностирует главную зону слабости на основе trainer runs.

    Алгоритм:
    1. Находит наиболее частый root_cause (кроме NONE).
    2. Пытается связать его с темой кейса и/или decision_mode.
    3. Возвращает человекочитаемую строку-диагноз.
    """
    if not runs:
        return "Недостаточно данных для анализа."

    # Строим индекс тем по case_id
    theme_by_case_id = {c["case_id"]: c.get("theme", "") for c in (trainer_cases or [])}
    mode_by_case_id  = {
        c["case_id"]: c.get("expected_output", {}).get("decision_mode", "")
        for c in (trainer_cases or [])
    }

    # Считаем ошибочные прогоны
    error_runs = [r for r in runs if r.get("root_cause", "NONE") != "NONE"]

    if not error_runs:
        return "Системных слабых зон не выявлено — все прогоны без ошибок."

    # Самый частый root_cause
    root_cause_counts = Counter(r["root_cause"] for r in error_runs)
    dominant_root, dominant_count = root_cause_counts.most_common(1)[0]
    dominance_pct = round(dominant_count / len(error_runs) * 100)

    # Среди прогонов с этой ошибкой — самая частая тема и режим
    dominant_runs = [r for r in error_runs if r.get("root_cause") == dominant_root]
    case_ids = [r.get("trainer_case_id", "") for r in dominant_runs]

    themes = [theme_by_case_id.get(cid, "") for cid in case_ids if theme_by_case_id.get(cid)]
    modes  = [mode_by_case_id.get(cid, "")  for cid in case_ids if mode_by_case_id.get(cid)]

    top_theme = Counter(themes).most_common(1)[0][0] if themes else ""
    top_mode  = Counter(modes).most_common(1)[0][0]  if modes  else ""

    # Человекочитаемые метки
    root_labels = {
        "MISREAD_CDD_STATUS":   "путаница в статусах CDD (Incomplete vs Cannot be completed)",
        "MISSED_SOF_GAP":       "пропуск пробела по SoF",
        "MISSED_UBO_BLOCKER":   "пропуск блокера по UBO",
        "MISSED_ADVERSE_MEDIA": "недооценка adverse media",
        "OVER_REJECT":          "избыточный отказ (EDD был бы уместнее)",
        "UNDER_REJECT":         "недостаточно жёсткое решение",
        "WEAK_DECISIVE_FACTOR": "расплывчатый decisive factor",
        "WEAK_SIGNAL_TRACE":    "неполный signal trace",
        "WEAK_RATIONALE":       "слабое обоснование решения",
    }
    mode_labels = {"edd": "EDD", "reject": "Reject", "approve": "Approve"}

    root_label = root_labels.get(dominant_root, dominant_root)
    mode_str   = f" / {mode_labels.get(top_mode, top_mode)}" if top_mode else ""
    theme_str  = f" в кейсах «{top_theme}»" if top_theme else ""

    return (
        f"Основная слабая зона: {root_label}{theme_str}{mode_str} "
        f"({dominance_pct}% ошибочных прогонов)"
    )


# ---------------------------------------------------------------------------
# 3. Сводка по всем прогонам
# ---------------------------------------------------------------------------

def summarize_trainer_runs(runs: list[dict], trainer_cases: list[dict] | None = None) -> dict:
    """
    Полная аналитическая сводка по истории тренировочных прогонов.

    Args:
        runs:           список записей из trainer_runs.json
        trainer_cases:  список кейсов из trainer_cases.py (для тем)

    Returns:
        dict со структурой, описанной в Stage 3B ТЗ.
    """
    if not runs:
        return {
            "total_runs":            0,
            "avg_score":             0.0,
            "correct_decision_rate": 0.0,
            "score_trend":           "not_enough_data",            "root_cause_distribution": {},
            "theme_distribution":    {},
            "weak_zone":             "Недостаточно данных для анализа.",
        }

    trainer_cases = trainer_cases or []

    total = len(runs)
    scores = [r.get("score", 0) for r in runs]
    avg_score = round(sum(scores) / total, 1)

    correct = sum(1 for r in runs if r.get("is_correct_decision"))
    correct_rate = round(correct / total * 100, 1)

    # Распределение root causes
    root_counts = Counter(r.get("root_cause", "NONE") for r in runs)

    # Распределение тем кейсов
    theme_by_case_id = {c["case_id"]: c.get("theme", "Другое") for c in trainer_cases}
    themes = [theme_by_case_id.get(r.get("trainer_case_id", ""), "Другое") for r in runs]
    theme_counts = Counter(themes)

    return {
        "total_runs":            total,
        "avg_score":             avg_score,
        "correct_decision_rate": correct_rate,
        "score_trend":           detect_score_trend(runs),
        "root_cause_distribution": dict(root_counts.most_common()),
        "theme_distribution":    dict(theme_counts.most_common()),
        "weak_zone":             detect_trainer_weak_zone(runs, trainer_cases),
    }


# ---------------------------------------------------------------------------
# 4. Следующий непройденный кейс за сегодня
# ---------------------------------------------------------------------------

def get_next_unfinished_trainer_case_for_today(
    runs: list[dict],
    trainer_cases: list[dict],
    current_case_id: str | None = None,
) -> dict | None:
    """
    Возвращает следующий тренировочный кейс, который аналитик ещё не решал сегодня.

    Логика:
    - Смотрит сегодняшнюю дату в trainer_runs.json.
    - Определяет case_id, уже пройденные сегодня.
    - Выбирает первый кейс из библиотеки, не вошедший в сегодняшние прогоны.
    - Если current_case_id задан — исключает его из кандидатов (не возвращать тот же кейс).
    - Если все кейсы пройдены — возвращает None.
    """
    from datetime import date
    today_str = date.today().strftime("%Y-%m-%d")

    done_today = {
        r.get("trainer_case_id")
        for r in runs
        if r.get("saved_at", "").startswith(today_str)
    }

    for case in trainer_cases:
        cid = case["case_id"]
        if cid in done_today:
            continue
        if cid == current_case_id:
            continue
        return case

    return None


# ---------------------------------------------------------------------------
# 5. Навигация по кейсам — три режима
# ---------------------------------------------------------------------------

import random as _random


def get_next_trainer_case(
    runs: list[dict],
    trainer_cases: list[dict],
    current_case_id: str | None = None,
    mode: str = "unfinished_today",
) -> dict | None:
    """
    Возвращает следующий тренировочный кейс в зависимости от режима.

    Режимы:
        "sequential"       — следующий по порядку в библиотеке
        "random"           — случайный, желательно не текущий
        "unfinished_today" — первый не пройденный сегодня

    Возвращает None если кейсов не осталось (актуально для unfinished_today).
    """
    if not trainer_cases:
        return None

    if mode == "sequential":
        return _next_sequential(trainer_cases, current_case_id)

    if mode == "random":
        return _next_random(trainer_cases, current_case_id)

    # default: unfinished_today
    return get_next_unfinished_trainer_case_for_today(runs, trainer_cases, current_case_id)


def _next_sequential(trainer_cases: list[dict], current_case_id: str | None) -> dict:
    """Следующий кейс по порядку; при достижении конца — возвращается к первому."""
    if not current_case_id:
        return trainer_cases[0]
    ids = [c["case_id"] for c in trainer_cases]
    try:
        idx = ids.index(current_case_id)
    except ValueError:
        return trainer_cases[0]
    next_idx = (idx + 1) % len(trainer_cases)
    return trainer_cases[next_idx]


def _next_random(trainer_cases: list[dict], current_case_id: str | None) -> dict:
    """Случайный кейс, предпочтительно не текущий."""
    candidates = [c for c in trainer_cases if c["case_id"] != current_case_id]
    pool = candidates if candidates else trainer_cases
    return _random.choice(pool)
