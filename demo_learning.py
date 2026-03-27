# demo_learning.py
#
# Демо-сценарий: 15 кейсов → learning summary → weak_zone → вывод
#
# Нарратив: аналитик системно слабо обосновывает EDD-кейсы.
# Approve-кейсы — уверенные и чистые.
# Reject-кейсы — в целом верные, но один с over-reject.
# EDD-кейсы — решение правильное, но rationale расплывчатый.

from learning import summarize

# ---------------------------------------------------------------------------
# История кейсов
# ---------------------------------------------------------------------------

history = []

# --- Approve (3 кейса) — чистые, уверенные ---

history.append({
    "decision_mode":    "approve",
    "decision":         "Одобрить",
    "cdd_status":       "Complete",
    "risk_level":       "Низкий",
    "reject_reason_type": "NONE",
    "error_type":       "NONE",
    "confidence_score": 5,
    "self_review": {
        "summary": "Решение логически согласовано. CDD завершён в полном объёме.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["screening findings"],
    },
})

history.append({
    "decision_mode":    "approve",
    "decision":         "Одобрить",
    "cdd_status":       "Complete",
    "risk_level":       "Низкий",
    "reject_reason_type": "NONE",
    "error_type":       "NONE",
    "confidence_score": 4,
    "self_review": {
        "summary": "CDD завершён. Риск в приемлемых пределах.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["SoF"],
    },
})

history.append({
    "decision_mode":    "approve",
    "decision":         "Одобрить",
    "cdd_status":       "Complete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "NONE",
    "confidence_score": 4,
    "self_review": {
        "summary": "Решение защищаемо. Ключевые элементы CDD подтверждены.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["adverse media"],
    },
})

# --- Reject (4 кейса) — 3 чистых, 1 over-reject ---

history.append({
    "decision_mode":    "reject",
    "decision":         "Отказать",
    "cdd_status":       "Incomplete and cannot be completed",
    "risk_level":       "Высокий",
    "reject_reason_type": "CDD_FAILURE",
    "error_type":       "NONE",
    "confidence_score": 5,
    "self_review": {
        "summary": "UBO не установлен и не может быть подтверждён. Отказ обоснован.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["UBO"],
    },
})

history.append({
    "decision_mode":    "reject",
    "decision":         "Отказать",
    "cdd_status":       "Complete but risk not acceptable",
    "risk_level":       "Высокий",
    "reject_reason_type": "RISK_UNACCEPTABLE",
    "error_type":       "NONE",
    "confidence_score": 4,
    "self_review": {
        "summary": "Adverse media не снят. Риск неприемлем. Решение защищаемо.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["adverse media", "risk_level"],
    },
})

history.append({
    "decision_mode":    "reject",
    "decision":         "Отказать",
    "cdd_status":       "Incomplete and cannot be completed",
    "risk_level":       "Высокий",
    "reject_reason_type": "CDD_FAILURE",
    "error_type":       "NONE",
    "confidence_score": 4,
    "self_review": {
        "summary": "SoF не подтверждён и не может быть подтверждён. Отказ правомерен.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["SoF"],
    },
})

history.append({
    "decision_mode":    "reject",
    "decision":         "Отказать",
    "cdd_status":       "Complete but risk not acceptable",
    "risk_level":       "Высокий",
    "reject_reason_type": "RISK_UNACCEPTABLE",
    "error_type":       "OVER_REJECT",   # ← borderline: скорее EDD
    "confidence_score": 3,
    "self_review": {
        "summary": "Решение возможно избыточно жёсткое — gaps выглядят закрываемыми через EDD.",
        "main_gap": "Не исключено, что EDD позволил бы закрыть ключевые вопросы без reject.",
        "what_to_recheck": ["SoF", "decision_rationale"],
    },
})

# --- EDD (8 кейсов) — решения верные, rationale слабые ---

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 3,
    "self_review": {
        "summary": "Решение рабочее, но rationale не связывает finding с выводом достаточно чётко.",
        "main_gap": "Decision rationale слишком общий — не объясняет, почему именно EDD, а не reject.",
        "what_to_recheck": ["decision_rationale", "decisive_factor"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 3,
    "self_review": {
        "summary": "EDD обоснован, но формулировка незащищаемая.",
        "main_gap": "Rationale не указывает конкретный gap, который EDD должен закрыть.",
        "what_to_recheck": ["SoF", "decision_rationale"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Высокий",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 2,
    "self_review": {
        "summary": "Решение допустимо, но обоснование слабое и шаблонное.",
        "main_gap": "Decisive factor не сформулирован достаточно конкретно.",
        "what_to_recheck": ["decisive_factor", "UBO"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 3,
    "self_review": {
        "summary": "EDD выбран верно, но logic chain оборван на середине.",
        "main_gap": "Отсутствует явная связь между risk finding и выбором EDD.",
        "what_to_recheck": ["analysis", "decision_rationale"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "NONE",   # ← один хороший EDD
    "confidence_score": 4,
    "self_review": {
        "summary": "Решение защищаемо. SoF-gap чётко идентифицирован и закрываем через EDD.",
        "main_gap": "Существенных аналитических gaps не выявлено.",
        "what_to_recheck": ["SoF"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Высокий",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 2,
    "self_review": {
        "summary": "EDD формально верен, но rationale не выдержит scrutiny.",
        "main_gap": "Неясно, почему reject не применён при high risk.",
        "what_to_recheck": ["risk_level", "decision_rationale", "decisive_factor"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 3,
    "self_review": {
        "summary": "Решение рабочее, но decisive factor сформулирован слишком широко.",
        "main_gap": "Decisive factor не указывает конкретный незакрытый CDD-элемент.",
        "what_to_recheck": ["decisive_factor", "SoF"],
    },
})

history.append({
    "decision_mode":    "edd",
    "decision":         "Эскалация",
    "cdd_status":       "Incomplete",
    "risk_level":       "Средний",
    "reject_reason_type": "NONE",
    "error_type":       "WEAK_RATIONALE",
    "confidence_score": 3,
    "self_review": {
        "summary": "EDD верен. Однако анализ не объясняет, почему gap закрываем.",
        "main_gap": "Analysis не обосновывает, что именно EDD устранит выявленный gap.",
        "what_to_recheck": ["analysis", "decisive_factor"],
    },
})

# ---------------------------------------------------------------------------
# Learning summary
# ---------------------------------------------------------------------------

summary = summarize(history)

# ---------------------------------------------------------------------------
# Вывод
# ---------------------------------------------------------------------------

print("=" * 42)
print("  CASEMIND LEARNING SUMMARY")
print("=" * 42)
print()

print(f"Cases analysed : {summary['total_cases']}")
print(f"Error rate     : {summary['error_rate'] * 100:.0f}%")
print(f"Avg confidence : {summary['avg_confidence']}/5")
print()

print("Error breakdown (errors only):")
for error_type, count in sorted(
    summary["error_distribution_errors"].items(),
    key=lambda x: x[1],
    reverse=True,
):
    bar = "█" * count
    print(f"  {error_type:<22} {bar} {count}")

print()
print("By decision mode:")
for mode, stats in summary["by_mode"].items():
    errors_only = stats.get("error_distribution_errors", {})
    error_count = sum(errors_only.values())
    mode_label  = {"edd": "EDD/Escalation", "reject": "Reject", "approve": "Approve"}.get(mode, mode)
    print(f"  {mode_label:<18} {stats['count']} cases  "
          f"avg confidence {stats['avg_confidence']}/5  "
          f"errors {error_count}")

print()
print("Weak zone detected:")
print(f"→ {summary['weak_zone']}")
print()
print("Insight:")
print("→ Решения в EDD-кейсах в целом верны, но систематически")
print("  плохо обоснованы — decisive factor и rationale")
print("  не связывают finding с выводом достаточно чётко,")
print("  чтобы выдержать compliance-scrutiny.")