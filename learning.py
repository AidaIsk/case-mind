# learning.py
#
# Error Aggregation MVP — превращает self-review в обучение.
# Никаких внешних зависимостей: только стандартная библиотека.
#
# Публичный API:
#   extract_learning_signal(output)  → сигнал из одного кейса
#   aggregate_errors(outputs)        → сводка по набору кейсов
#   detect_weak_zone(stats)          → диагноз системной слабости


from collections import Counter


# ---------------------------------------------------------------------------
# 1. Извлечение сигнала из одного structured output
# ---------------------------------------------------------------------------

def extract_learning_signal(output: dict) -> dict:
    """
    Извлекает обучающий сигнал из одного structured output.

    Принимает только поля, которые нужны для агрегации —
    не хранит ни клиентских данных, ни текстов полей.

    Возвращает:
        {
            "error_type":       str,   # NONE | OVER_REJECT | ...
            "confidence_score": int,   # 1–5
            "decision_mode":    str,   # edd | reject | approve
            "risk_level":       str,   # Низкий | Средний | Высокий
        }
    """
    return {
        "error_type":       output.get("error_type", "NONE"),
        "confidence_score": output.get("confidence_score", 0),
        "decision_mode":    output.get("decision_mode", "unknown"),
        "risk_level":       output.get("risk_level", "unknown"),
    }


# ---------------------------------------------------------------------------
# 2. Агрегация по набору кейсов
# ---------------------------------------------------------------------------

def aggregate_errors(outputs: list[dict]) -> dict:
    """
    Принимает список structured outputs (или learning signals).
    Возвращает агрегированную статистику.

    Структура ответа:
    {
        "total_cases":        int,
        "error_rate":         float,   # доля кейсов с error_type != NONE, 0.0–1.0
        "error_distribution": {str: int},
        "avg_confidence":     float,
        "by_mode": {
            "<mode>": {
                "count":              int,
                "error_distribution": {str: int},
                "avg_confidence":     float,
            }
        }
    }
    """
    if not outputs:
        return {
            "total_cases":        0,
            "error_rate":         0.0,
            "error_distribution": {},
            "avg_confidence":     0.0,
            "by_mode":            {},
        }

    signals = [extract_learning_signal(o) for o in outputs]
    total = len(signals)

    # --- глобальные метрики ---
    error_counts_all    = Counter(s["error_type"] for s in signals)
    error_counts_errors = Counter(s["error_type"] for s in signals if s["error_type"] != "NONE")
    error_cases         = sum(error_counts_errors.values())
    error_rate          = round(error_cases / total, 3)

    valid_scores = [s["confidence_score"] for s in signals
                    if isinstance(s["confidence_score"], int) and 1 <= s["confidence_score"] <= 5]
    avg_confidence = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 0.0

    # --- разбивка по decision_mode ---
    by_mode: dict[str, dict] = {}
    modes = {s["decision_mode"] for s in signals}

    for mode in sorted(modes):
        mode_signals       = [s for s in signals if s["decision_mode"] == mode]
        mode_errors_all    = Counter(s["error_type"] for s in mode_signals)
        mode_errors_errors = Counter(s["error_type"] for s in mode_signals if s["error_type"] != "NONE")
        mode_scores        = [s["confidence_score"] for s in mode_signals
                              if isinstance(s["confidence_score"], int) and 1 <= s["confidence_score"] <= 5]
        mode_avg           = round(sum(mode_scores) / len(mode_scores), 2) if mode_scores else 0.0

        by_mode[mode] = {
            "count":                     len(mode_signals),
            "error_distribution_all":    dict(mode_errors_all),
            "error_distribution_errors": dict(mode_errors_errors),
            "avg_confidence":            mode_avg,
        }

    return {
        "total_cases":               total,
        "error_rate":                error_rate,
        "error_distribution_all":    dict(error_counts_all),
        "error_distribution_errors": dict(error_counts_errors),
        "avg_confidence":            avg_confidence,
        "by_mode":                   by_mode,
    }


# ---------------------------------------------------------------------------
# 3. Диагностика системной слабости
# ---------------------------------------------------------------------------

# Минимальный порог: ошибка считается системной, если встречается
# в >= THRESHOLD доле от всех кейсов с ошибками.
_DOMINANCE_THRESHOLD = 0.40

# Порог "низкой уверенности" по среднему confidence_score.
_LOW_CONFIDENCE_THRESHOLD = 2.5


def detect_weak_zone(stats: dict) -> str:
    """
    Анализирует aggregate_errors() и возвращает текстовый диагноз
    системной зоны слабости.

    Приоритет диагнозов (от самого критичного):
      1. Доминирующий error_type (>= 40% всех ошибочных кейсов)
      2. Низкий средний confidence_score (< 2.5)
      3. Высокий error_rate (>= 50% кейсов с ошибками)
      4. Проблема конкретного mode (если один mode даёт ≥ 60% ошибок)
      5. Нет выраженной зоны слабости
    """
    total         = stats.get("total_cases", 0)
    error_dist    = stats.get("error_distribution_errors", {})
    avg_conf      = stats.get("avg_confidence", 0.0)
    error_rate    = stats.get("error_rate", 0.0)
    by_mode       = stats.get("by_mode", {})

    if total == 0:
        return "Недостаточно данных для анализа."

    # Ошибочные кейсы (NONE уже исключён в error_distribution_errors)
    error_counts = error_dist
    total_errors = sum(error_counts.values())

    # --- 1. Доминирующий тип ошибки ---
    if total_errors > 0:
        dominant_type, dominant_count = max(error_counts.items(), key=lambda x: x[1])
        dominance_ratio = dominant_count / total_errors

        if dominance_ratio >= _DOMINANCE_THRESHOLD:
            labels = {
                "OVER_REJECT":          "Склонность к избыточному reject в borderline кейсах",
                "UNDER_REJECT":         "Систематическое занижение тяжести рисков (under-reject)",
                "WEAK_RATIONALE":       "Слабое обоснование решений (WEAK_RATIONALE)",
                "MISSED_SIGNAL":        "Пропуск важных red flags и risk signals",
                "CDD_LOGIC_GAP":        "Нарушение логики CDD: путаница incomplete/impossible",
                "INCONSISTENT_DECISION":"Внутренние противоречия в structured output",
            }
            label = labels.get(dominant_type, f"Доминирующая ошибка: {dominant_type}")
            pct   = round(dominance_ratio * 100)
            return f"{label} ({pct}% ошибочных кейсов)"

    # --- 2. Низкий средний confidence ---
    if avg_conf < _LOW_CONFIDENCE_THRESHOLD and total >= 3:
        return (
            f"Низкий средний уровень уверенности ({avg_conf}/5) — "
            "reasoning системно опирается на неполные данные"
        )

    # --- 3. Высокий error_rate ---
    if error_rate >= 0.50 and total >= 3:
        pct = round(error_rate * 100)
        return (
            f"Высокий процент кейсов с аналитическими ошибками ({pct}%) — "
            "требуется общий аудит reasoning"
        )

    # --- 4. Проблемный mode ---
    for mode, mode_stats in by_mode.items():
        mode_errors      = mode_stats.get("error_distribution_errors", {})
        mode_error_count = sum(mode_errors.values())
        if total_errors > 0 and mode_error_count / total_errors >= 0.60 and mode_stats["count"] >= 3:
            mode_label = {"edd": "EDD/escalation", "reject": "Reject", "approve": "Approve"}.get(mode, mode)
            return (
                f"Концентрация ошибок в кейсах типа {mode_label} "
                f"({mode_error_count} из {total_errors} ошибочных)"
            )

    # --- 5. Нет выраженной зоны ---
    if error_rate == 0.0:
        return "Системных аналитических ошибок не выявлено."
    return "Выраженной зоны слабости не обнаружено — ошибки распределены равномерно."


# ---------------------------------------------------------------------------
# 4. Удобная точка входа: сводка по списку outputs
# ---------------------------------------------------------------------------

def summarize(outputs: list[dict]) -> dict:
    """
    Полная сводка: stats + weak_zone.
    Удобна для вызова из CLI или Streamlit-страницы статистики.

    Возвращает:
        {
            **aggregate_errors(outputs),
            "weak_zone": str,
        }
    """
    stats = aggregate_errors(outputs)
    stats["weak_zone"] = detect_weak_zone(stats)
    return stats