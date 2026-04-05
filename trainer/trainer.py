# trainer.py
#
# Trainer Core MVP — модуль оценки ответа аналитика.
#
# Основной цикл: solve → compare → review → store
#
# Бизнес-назначение: система не просто фиксирует ошибку,
# но называет её тип (root_cause) и объясняет, что именно
# пошло не так. Это переводит CaseMind из DSS в Cognitive Trainer.

import json
import os
import uuid
from datetime import datetime


# Путь к trainer_runs.json вычисляется относительно корня проекта.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAINER_RUNS_FILE = os.path.join(_PROJECT_ROOT, "data", "trainer_runs.json")

# ---------------------------------------------------------------------------
# Root Cause — классификация причин ошибок
# ---------------------------------------------------------------------------

ROOT_CAUSE_LABELS = {
    "MISREAD_CDD_STATUS":    "Неверно определён статус CDD (Incomplete vs Cannot be completed)",
    "MISSED_SOF_GAP":        "Не зафиксирован ключевой пробел по источнику средств (SoF)",
    "MISSED_UBO_BLOCKER":    "Пропущен критический блокер по бенефициарному владельцу (UBO)",
    "MISSED_ADVERSE_MEDIA":  "Не выявлен или недооценён adverse media как risk finding",
    "OVER_REJECT":           "Применён отказ там, где достаточно EDD (пробел закрываем)",
    "UNDER_REJECT":          "Применён EDD или Approve там, где данные требуют отказа",
    "WEAK_DECISIVE_FACTOR":  "Decisive factor сформулирован расплывчато или не соответствует данным",
    "WEAK_SIGNAL_TRACE":     "Signal trace не отражает ключевые сигналы кейса",
    "WEAK_RATIONALE":        "Reasoning в целом верен, но обоснование незащищаемо",
    "NONE":                  "Существенных ошибок не выявлено",
}

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

# Deterministic score: судит только логику решения. Max = 70.
# decisive_factor и signal_trace вынесены в semantic layer (Step 1).
# Guiding principle: правильная логика + тот же смысл другими словами = засчитано.
SCORE_WEIGHTS = {
    "decision_mode":       30,   # бинарный — approve / edd / reject
    "cdd_status":          20,   # бинарный — complete / incomplete / cannot be completed
    "reject_reason_type":  10,   # бинарный — CDD_FAILURE / RISK_UNACCEPTABLE / NONE
    "self_review_quality": 10,   # качество self-assessment аналитика
    # decisive_factor и signal_trace убраны: они судят wording, не логику.
    # Вместо этого используется _apply_semantic_score() ниже.
}

# Semantic score: судит смысл, не слова. Max = 30.
# Применяется в services.py через _apply_semantic_score().
SEMANTIC_WEIGHTS = {
    "decisive_factor": 20,   # был 15, повышен — decisive factor важнее trace
    "signal_trace":    10,   # был 15, понижен — trace менее критичен для смысла
}


# ---------------------------------------------------------------------------
# 1. Сравнение отдельных компонентов
# ---------------------------------------------------------------------------

def _compare_decision_mode(user: dict, expected: dict) -> bool:
    return user.get("decision_mode") == expected.get("decision_mode")


def _compare_cdd_status(user: dict, expected: dict) -> bool:
    return user.get("cdd_status") == expected.get("cdd_status")


def _compare_reject_reason_type(user: dict, expected: dict) -> bool:
    return user.get("reject_reason_type") == expected.get("reject_reason_type")


def _score_decisive_factor(user: dict, expected: dict) -> str:
    """
    Возвращает "match" / "partial" / "miss" для decisive_factor.

    Архитектурный принцип: этот слой — только sanity-check.
    Он НЕ является semantic evaluator — это роль LLM в semantic_review.py.

    Sanity-check ловит только очевидные проблемы:
      - пустое поле
      - явная несогласованность с decision_mode
      - перечисление вместо одной мысли

    Для всего остального возвращает "partial" как conservative default.
    LLM в run_semantic_review() перезаписывает на "match"/"partial"/"miss"
    по смыслу — без ограничений по словарю.

    Принцип: правильная логика + тот же смысл другими словами = засчитано.
    """
    user_df = (user.get("decisive_factor") or "").strip()
    mode    = user.get("decision_mode", "")

    # ── Miss 1: поле пустое или прочерк ──────────────────────────────
    if not user_df or user_df in ("—", "-", ""):
        return "miss"

    # ── Miss 2: слишком короткое — не может быть одной мыслью ────────
    if len(user_df) < 15:
        return "miss"

    user_lower = user_df.lower()

    # ── Miss 3: явная несогласованность с EDD ────────────────────────
    # EDD-решение не должно ссылаться на структурный барьер
    if mode == "edd":
        edd_blockers = [
            "невозможно завершить", "не может быть завершён",
            "не устраним", "cdd не может",
        ]
        if any(w in user_lower for w in edd_blockers):
            return "miss"

    # ── Partial 1: reject + слова о закрываемых gap ──────────────────
    # Reject-решение не должно описывать устранимый пробел как decisive
    if mode == "reject":
        closable = ["закрываем", "edd устранит", "edd закроет", "можно получить"]
        if any(w in user_lower for w in closable):
            return "partial"

    # ── Partial 2: перечисление вместо одной мысли ───────────────────
    if user_df.count(",") >= 3 and len(user_df) < 180:
        return "partial"

    # ── Conservative default: поле заполнено и структурно корректно ──
    # Semantic LLM решит match vs partial точнее. Не штрафуем keyword-матчем.
    return "partial"


def _compare_decisive_factor(user: dict, expected: dict) -> bool:
    """
    Обёртка для обратной совместимости.
    match/partial → True (не штрафуем за перефразировку)
    miss          → False

    Используется для root_cause diagnosis и UI "что пропущено".
    Не влияет на score (score идёт через _apply_semantic_score).
    """
    return _score_decisive_factor(user, expected) in ("match", "partial")


def _compare_signal_trace(user: dict, expected: dict) -> bool:
    """
    Проверяет, что DECISIVE сигнал пользователя совпадает по смыслу
    с DECISIVE сигналом эталона, и что категории сигналов пересекаются.
    """
    user_trace     = user.get("signal_trace", [])
    expected_trace = expected.get("signal_trace", [])

    if not user_trace or not expected_trace:
        return False

    # Категории DECISIVE сигналов должны совпадать
    user_decisive_cats = {
        s.get("category") for s in user_trace if s.get("impact") == "DECISIVE"
    }
    expected_decisive_cats = {
        s.get("category") for s in expected_trace if s.get("impact") == "DECISIVE"
    }
    if not user_decisive_cats & expected_decisive_cats:
        return False

    # Общие категории сигналов (хотя бы 50% пересечения)
    user_cats     = {s.get("category") for s in user_trace}
    expected_cats = {s.get("category") for s in expected_trace}
    overlap = len(user_cats & expected_cats) / max(len(expected_cats), 1)
    return overlap >= 0.5


def _compare_self_review_quality(user: dict, expected: dict) -> bool:
    """
    Проверяет, что error_type и confidence_score находятся в разумном диапазоне.
    Не требует точного совпадения — оценивает качество.
    """
    user_error    = user.get("error_type", "")
    expected_error = expected.get("error_type", "")
    user_conf     = user.get("confidence_score", 0)
    expected_conf = expected.get("confidence_score", 0)

    error_ok = (user_error == expected_error) or (
        user_error == "NONE" and expected_error == "NONE"
    )
    conf_ok = abs((user_conf or 0) - (expected_conf or 0)) <= 1

    return error_ok and conf_ok


# ---------------------------------------------------------------------------
# 2. Определение root cause
# ---------------------------------------------------------------------------

def _detect_root_cause(
    user: dict,
    expected: dict,
    correct_mode: bool,
    correct_cdd: bool,
    correct_reason: bool,
    correct_decisive: bool,
    correct_trace: bool,
) -> str:
    """
    Определяет главную причину ошибки по приоритету.
    Порядок важен: сначала самые серьёзные.
    """
    user_mode     = user.get("decision_mode", "")
    expected_mode = expected.get("decision_mode", "")
    user_cdd      = user.get("cdd_status", "")
    expected_cdd  = expected.get("cdd_status", "")

    # Перепутаны режимы в сторону смягчения (EDD вместо Reject)
    if not correct_mode:
        if expected_mode == "reject" and user_mode == "edd":
            return "UNDER_REJECT"
        if expected_mode == "reject" and user_mode == "approve":
            return "UNDER_REJECT"
        if expected_mode == "edd" and user_mode == "reject":
            return "OVER_REJECT"

    # Перепутан статус CDD — классический CDD_LOGIC_GAP
    if not correct_cdd:
        if "cannot be completed" in expected_cdd.lower() and "cannot" not in user_cdd.lower():
            # Аналитик думал, что пробел закрываем, хотя он структурный
            return "MISREAD_CDD_STATUS"
        if "cannot be completed" in user_cdd.lower() and "cannot" not in expected_cdd.lower():
            return "OVER_REJECT"

    # Пропущен тип причины отказа
    if not correct_reason:
        expected_r = expected.get("reject_reason_type", "")
        if expected_r == "CDD_FAILURE":
            # Аналитик не зафиксировал конкретный CDD-блокер
            expected_df = expected.get("decisive_factor", "").lower()
            if "ubo" in expected_df or "бенефициар" in expected_df or "владел" in expected_df:
                return "MISSED_UBO_BLOCKER"
            if "sof" in expected_df or "источник" in expected_df:
                return "MISSED_SOF_GAP"
        if expected_r == "RISK_UNACCEPTABLE":
            return "MISSED_ADVERSE_MEDIA"

    # Слабый decisive_factor при правильном режиме
    if correct_mode and not correct_decisive:
        return "WEAK_DECISIVE_FACTOR"

    # Слабый signal_trace при правильном режиме
    if correct_mode and correct_decisive and not correct_trace:
        return "WEAK_SIGNAL_TRACE"

    # Всё верно или незначительные расхождения
    return "NONE"


# ---------------------------------------------------------------------------
# 3.5 Coach message — человеческий фидбэк от наставника
# ---------------------------------------------------------------------------

def _build_coach_message(
    score: int,
    root_cause: str,
    correct_mode: bool,
    correct_decisive: bool,
    correct_cdd: bool,
) -> str:
    if score >= 85:
        return "Хороший разбор: решение и аргументация в целом согласованы."
    if root_cause == "OVER_REJECT":
        return "Ты выбрала слишком жёсткое решение — в этом кейсе пробелы ещё можно закрыть через EDD."
    if root_cause == "UNDER_REJECT":
        return "Решение мягче эталона: данные кейса требовали более жёсткого вывода."
    if root_cause == "MISREAD_CDD_STATUS":
        return "Ключевая ошибка — в статусе CDD: важно различать «незавершён» и «невозможно завершить»."
    if root_cause in ("MISSED_SOF_GAP", "MISSED_UBO_BLOCKER"):
        return "Ты пропустила критический блокер — обрати внимание на элементы CDD, которых не хватает."
    if root_cause == "MISSED_ADVERSE_MEDIA":
        return "Adverse media не отражён как решающий риск-сигнал — а именно он делает риск неприемлемым."
    if root_cause in ("WEAK_DECISIVE_FACTOR",) or not correct_decisive:
        return "Ты приняла правильное решение, но обоснование слишком общее — не выделен ключевой фактор."
    if root_cause == "WEAK_SIGNAL_TRACE":
        return "Логика решения верная, но signal trace не отражает основные сигналы кейса."
    if not correct_mode:
        return "Режим решения не совпадает с эталоном — пересмотри логику CDD для этого кейса."
    if not correct_cdd:
        return "Статус CDD определён неверно — это влияет на обоснование всего решения."
    if score >= 60:
        return "Решение в целом верное, но есть пробелы в обосновании — посмотри на детали."
    return "Разбор требует доработки — рекомендую повторить теорию по теме этого кейса."


# ---------------------------------------------------------------------------
# 4. Подсчёт score
# ---------------------------------------------------------------------------

def _calculate_score(
    correct_mode: bool,
    correct_cdd: bool,
    correct_reason: bool,
    correct_self_review: bool,
) -> int:
    """
    Deterministic score: только логика решения. Max = 70.
    decisive_factor и signal_trace убраны — их судит semantic layer.
    """
    score = 0
    if correct_mode:        score += SCORE_WEIGHTS["decision_mode"]
    if correct_cdd:         score += SCORE_WEIGHTS["cdd_status"]
    if correct_reason:      score += SCORE_WEIGHTS["reject_reason_type"]
    if correct_self_review: score += SCORE_WEIGHTS["self_review_quality"]
    return score   # max 70


def _apply_semantic_score(base_score: int, semantic_result: dict | None) -> int:
    """
    Добавляет semantic очки к deterministic base. Итого max = 100.

    Вызывается в services.py после run_semantic_review().
    Если semantic_result = None (нет semantic_hints или нет API):
      даём conservative default = 15 из 30 (половину).
      Это честнее чем 0: аналитик не наказывается за отсутствие pilot-metadata.

    Принцип: правильная логика + тот же смысл другими словами = засчитано.
    """
    if not semantic_result:
        # Нет semantic review для кейса — conservative middle ground
        return min(100, base_score + 15)

    df_match  = semantic_result.get("decisive_factor_semantic_match", "partial")
    trace_cov = semantic_result.get("signal_trace_semantic_coverage", "partial")

    df_score = {
        "match":   SEMANTIC_WEIGHTS["decisive_factor"],        # 20
        "partial": SEMANTIC_WEIGHTS["decisive_factor"] // 2,  # 10
        "miss":    0,
    }.get(df_match, 10)

    trace_score = {
        "covered":    SEMANTIC_WEIGHTS["signal_trace"],        # 10
        "partial":    SEMANTIC_WEIGHTS["signal_trace"] // 2,  # 5
        "missed_key": 0,
    }.get(trace_cov, 5)

    return min(100, base_score + df_score + trace_score)


# ---------------------------------------------------------------------------
# 4. Формирование текстового review
# ---------------------------------------------------------------------------

def _build_what_was_good(
    correct_mode: bool, correct_cdd: bool, correct_reason: bool,
    correct_decisive: bool, correct_trace: bool, user: dict, expected: dict,
) -> list[str]:
    good = []
    if correct_mode:
        mode_labels = {"approve": "Approve", "edd": "EDD/Escalation", "reject": "Reject"}
        good.append(f"Верно определён режим решения: {mode_labels.get(expected.get('decision_mode', ''), '?')}")
    if correct_cdd:
        good.append("Верно определён статус CDD")
    if correct_reason and expected.get("reject_reason_type") != "NONE":
        good.append(f"Верно определена причина отказа: {expected.get('reject_reason_type')}")
    if correct_decisive:
        good.append("Decisive factor сформулирован корректно")
    if correct_trace:
        good.append("Signal trace отражает ключевые сигналы кейса")
    return good or ["—"]


def _build_what_was_missed(
    correct_mode: bool, correct_cdd: bool, correct_reason: bool,
    correct_decisive: bool, correct_trace: bool,
    user: dict, expected: dict,
) -> list[str]:
    missed = []
    if not correct_mode:
        missed.append(
            f"Режим решения: ожидался {expected.get('decision_mode')}, "
            f"получен {user.get('decision_mode')}"
        )
    if not correct_cdd:
        missed.append(
            f"Статус CDD: ожидался «{expected.get('cdd_status')}», "
            f"получен «{user.get('cdd_status')}»"
        )
    if not correct_reason and expected.get("reject_reason_type") != "NONE":
        missed.append(
            f"Причина отказа: ожидалась {expected.get('reject_reason_type')}, "
            f"получена {user.get('reject_reason_type')}"
        )
    if not correct_decisive:
        missed.append(
            f"Decisive factor не совпадает с эталоном. "
            f"Эталон: «{expected.get('decisive_factor', '?')}»"
        )
    if not correct_trace:
        missed.append("Signal trace не охватывает ключевые сигналы кейса")
    return missed or ["—"]


# ---------------------------------------------------------------------------
# 5. Главная функция: evaluate_trainer_answer
# ---------------------------------------------------------------------------

def evaluate_trainer_answer(user_output: dict, expected_output: dict) -> dict:
    """
    Сравнивает ответ аналитика с эталоном и возвращает структурированный review.

    Бизнес-назначение: это не просто проверка правильности —
    это диагностика типа ошибки и конкретной точки, где reasoning сломался.

    Args:
        user_output:     structured_output, сформированный аналитиком.
        expected_output: эталонный structured_output из trainer_cases.py.

    Returns:
        review dict с полями: score, is_correct_*, root_cause, review_summary,
        what_was_good, what_was_missed, what_to_recheck, error_type.
    """
    correct_mode        = _compare_decision_mode(user_output, expected_output)
    correct_cdd         = _compare_cdd_status(user_output, expected_output)
    correct_reason      = _compare_reject_reason_type(user_output, expected_output)
    correct_decisive    = _compare_decisive_factor(user_output, expected_output)
    correct_trace       = _compare_signal_trace(user_output, expected_output)
    correct_self_review = _compare_self_review_quality(user_output, expected_output)

    root_cause = _detect_root_cause(
        user_output, expected_output,
        correct_mode, correct_cdd, correct_reason,
        correct_decisive, correct_trace,
    )
    # Deterministic score (max 70): только логика решения.
    # Semantic score (max 30) применяется позже в services.py через _apply_semantic_score().
    # correct_decisive и correct_trace остаются — нужны для root_cause и UI diagnosis.
    score = _calculate_score(
        correct_mode, correct_cdd, correct_reason, correct_self_review,
    )

    # Определяем error_type для learning loop
    error_type_map = {
        "OVER_REJECT":          "OVER_REJECT",
        "UNDER_REJECT":         "UNDER_REJECT",
        "MISREAD_CDD_STATUS":   "CDD_LOGIC_GAP",
        "MISSED_SOF_GAP":       "MISSED_SIGNAL",
        "MISSED_UBO_BLOCKER":   "MISSED_SIGNAL",
        "MISSED_ADVERSE_MEDIA": "MISSED_SIGNAL",
        "WEAK_DECISIVE_FACTOR": "WEAK_RATIONALE",
        "WEAK_SIGNAL_TRACE":    "WEAK_RATIONALE",
        "WEAK_RATIONALE":       "WEAK_RATIONALE",
        "NONE":                 "NONE",
    }
    error_type = error_type_map.get(root_cause, "NONE")

    # Строим review_summary
    if score >= 85:
        summary = "Решение верное и хорошо обосновано. Незначительные расхождения не влияют на защищаемость."
    elif score >= 60:
        summary = "Режим решения выбран верно, но есть пробелы в обосновании или трассировке сигналов."
    elif score >= 40:
        summary = "Частичное совпадение с эталоном. Требуется пересмотр логики CDD и decisive factor."
    else:
        summary = "Существенное расхождение с эталоном. Рекомендуется повторить теорию по данной теме."

    # Что перепроверить
    what_to_recheck = []
    if not correct_cdd:
        what_to_recheck.append("Разница между CDD incomplete и CDD cannot be completed")
    if not correct_decisive:
        what_to_recheck.append("decisive_factor — одна конкретная формулировка, не общий вывод")
    if not correct_trace:
        what_to_recheck.append("signal_trace — конкретные наблюдения, а не выводы")
    if root_cause in ("MISSED_SOF_GAP", "MISSED_UBO_BLOCKER", "MISSED_ADVERSE_MEDIA"):
        what_to_recheck.append(f"root cause: {ROOT_CAUSE_LABELS.get(root_cause, root_cause)}")
    if not what_to_recheck:
        what_to_recheck.append("Повторить тему: " + expected_output.get("reject_reason_type", "CDD"))

    coach_message = _build_coach_message(
        score, root_cause, correct_mode, correct_decisive, correct_cdd,
    )

    return {
        "is_correct_decision":        correct_mode,
        "is_correct_cdd_logic":       correct_cdd,
        "is_correct_decisive_factor": correct_decisive,
        "is_correct_signal_trace":    correct_trace,
        "error_type":                 error_type,
        "root_cause":                 root_cause,
        "root_cause_label":           ROOT_CAUSE_LABELS.get(root_cause, root_cause),
        "review_summary":             summary,
        "coach_message":              coach_message,
        "combined_summary":           None,   # заполняется в services после note_review
        "what_was_good":             _build_what_was_good(
            correct_mode, correct_cdd, correct_reason, correct_decisive, correct_trace,
            user_output, expected_output,
        ),
        "what_was_missed":           _build_what_was_missed(
            correct_mode, correct_cdd, correct_reason, correct_decisive, correct_trace,
            user_output, expected_output,
        ),
        "what_to_recheck":           what_to_recheck,
        "score":                     score,
        "note_score":                None,
        "note_review":               None,
    }


# ---------------------------------------------------------------------------
# 6. Хранение trainer runs
# ---------------------------------------------------------------------------

def _ensure_trainer_data_dir() -> None:
    os.makedirs(os.path.dirname(TRAINER_RUNS_FILE), exist_ok=True)


def load_trainer_runs() -> list:
    """Загружает историю тренировочных прогонов. Не смешивать с cases.json."""
    _ensure_trainer_data_dir()
    if not os.path.exists(TRAINER_RUNS_FILE):
        return []
    try:
        with open(TRAINER_RUNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_trainer_run(
    trainer_case_id: str,
    user_output: dict,
    expected_output: dict,
    review: dict,
    decision_note: str = "",
) -> str:
    """
    Сохраняет результат тренировочного прогона в trainer_runs.json.
    Возвращает run_id.
    """
    _ensure_trainer_data_dir()
    runs = load_trainer_runs()

    run_id = f"RUN-{str(uuid.uuid4())[:8].upper()}"
    record = {
        "run_id":            run_id,
        "trainer_case_id":   trainer_case_id,
        "saved_at":          datetime.now().strftime("%Y-%m-%d %H:%M"),
        "score":             review["score"],
        "note_score":        review.get("note_score"),
        "error_type":        review["error_type"],
        "root_cause":        review["root_cause"],
        "is_correct_decision": review["is_correct_decision"],
        "review":            review,
        "user_output":       user_output,
        "expected_output":   expected_output,
        "decision_note":     decision_note,
    }

    runs.append(record)
    with open(TRAINER_RUNS_FILE, "w", encoding="utf-8") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)

    return run_id
