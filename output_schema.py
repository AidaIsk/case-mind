# output_schema.py

REQUIRED_OUTPUT_KEYS = [
    "decision_mode",
    "decision",
    "edd_required",
    "cdd_status",
    "risk_level",
    "decision_summary",
    "case_overview",
    "key_risk_factors",
    "cdd_assessment",
    "analysis",
    "decisive_factor",
    "decision_rationale",
    "required_actions",
    "reject_reason_type",
    "error_type",
    "confidence_score",
    "self_review",
    "signal_trace",
]

ALLOWED_DECISION_MODES = {"edd", "reject", "approve"}
ALLOWED_DECISIONS = {"Эскалация", "Отказать", "Одобрить"}
ALLOWED_EDD_VALUES = {"Да", "Нет"}
ALLOWED_CDD_STATUS = {
    "Complete",
    "Incomplete",
    "Incomplete and cannot be completed",
    "Complete but risk not acceptable",
}
ALLOWED_RISK_LEVELS = {"Низкий", "Средний", "Высокий"}
ALLOWED_REJECT_REASON_TYPES = {"CDD_FAILURE", "RISK_UNACCEPTABLE", "NONE"}

ALLOWED_ERROR_TYPES = {
    "NONE",
    "OVER_REJECT",
    "UNDER_REJECT",
    "MISSED_SIGNAL",
    "WEAK_RATIONALE",
    "CDD_LOGIC_GAP",
    "INCONSISTENT_DECISION",
}

ALLOWED_SIGNAL_CATEGORIES = {
    "CDD", "SCREENING", "GEOGRAPHY", "SOF",
    "ECONOMIC_RATIONALE", "PROFILE_MISMATCH", "OTHER",
}
ALLOWED_SIGNAL_IMPACTS = {"LOW", "MEDIUM", "HIGH", "DECISIVE"}
ALLOWED_SIGNAL_DIRECTIONS = {
    "SUPPORTS_DECISION",
    "SUPPORTS_ESCALATION",
    "SUPPORTS_REJECT",
    "MITIGATING",
}


def _fallback_decisive_factor(mode: str) -> str:
    """Возвращает осмысленный decisive_factor для fallback по режиму."""
    if mode == "edd":
        return "Недостаточно информации для завершения CDD на текущем этапе."
    if mode == "reject":
        return "Выявлен фактор, делающий риск или завершение CDD невозможным."
    if mode == "approve":
        return "Ключевые элементы CDD подтверждены, существенные blockers не выявлены."
    return "Не удалось определить решающий фактор решения."


def validate_decisive_factor_logic(output: dict) -> list[str]:
    """
    Проверяет смысловое соответствие decisive_factor режиму решения.
    MVP-эвристики: не заменяют полноценный NLU, но ловят явные противоречия.
    """
    errors = []
    mode = output.get("decision_mode")
    reason = output.get("reject_reason_type", "NONE")
    text = output.get("decisive_factor", "").lower()

    if not text.strip():
        return ["decisive_factor пуст — логическая проверка невозможна"]

    # EDD: decisive_factor не должен говорить о невозможности CDD —
    # это противоречит самой идее EDD (gaps закрываемы)
    if mode == "edd":
        forbidden = ["не может быть заверш", "невозможно завершить", "завершение невозможно"]
        if any(phrase in text for phrase in forbidden):
            errors.append(
                "decisive_factor: EDD-кейс не может содержать формулировку о невозможности завершить CDD"
            )

    # Reject / CDD_FAILURE: decisive_factor должен указывать на конкретный CDD-blocker
    if mode == "reject" and reason == "CDD_FAILURE":
        blocker_signals = [
            "не установлен", "не подтверждён", "не может быть", "невозможно",
            "отсутствует", "ubo", "cdd", "бенефициар", "владелец", "идентификац",
        ]
        if not any(signal in text for signal in blocker_signals):
            errors.append(
                "decisive_factor: CDD_FAILURE требует указания конкретного CDD-блокера "
                "(UBO, идентификация, документы)"
            )

    # Reject / RISK_UNACCEPTABLE: decisive_factor должен отражать risk finding
    if mode == "reject" and reason == "RISK_UNACCEPTABLE":
        risk_signals = [
            "негатив", "риск", "adverse", "репутац", "публикац",
            "схем", "вовлечённост", "не снят", "не устранён", "неприемлем",
        ]
        if not any(signal in text for signal in risk_signals):
            errors.append(
                "decisive_factor: RISK_UNACCEPTABLE требует отражения конкретного risk finding "
                "(adverse media, репутационный риск, неустранённые findings)"
            )

    return errors


def validate_self_review_logic(output: dict) -> list[str]:
    """
    Проверяет смысловое соответствие error_type, confidence_score и self_review
    основному решению. MVP-эвристики — ловят явные противоречия.
    """
    errors = []
    error_type = output.get("error_type", "")
    confidence_score = output.get("confidence_score")
    cdd_status = output.get("cdd_status", "")
    decision_mode = output.get("decision_mode", "")
    main_gap = output.get("self_review", {}).get("main_gap", "").lower()

    # confidence_score = 5 несовместим с error_type != NONE
    if confidence_score == 5 and error_type != "NONE":
        errors.append(
            "confidence_score = 5 недопустим при наличии error_type != NONE"
        )

    # confidence_score = 5 несовместим с незавершённым CDD
    if confidence_score == 5 and cdd_status == "Incomplete":
        errors.append(
            "confidence_score = 5 недопустим при cdd_status = Incomplete"
        )

    # OVER_REJECT имеет смысл только при decision_mode = reject
    if error_type == "OVER_REJECT" and decision_mode != "reject":
        errors.append(
            "error_type OVER_REJECT применим только при decision_mode = reject"
        )

    # UNDER_REJECT не должен ставиться при decision_mode = reject
    # (решение уже reject — under-reject здесь бессмысленен)
    if error_type == "UNDER_REJECT" and decision_mode == "reject":
        errors.append(
            "error_type UNDER_REJECT недопустим при decision_mode = reject "
            "(решение уже отказ)"
        )

    # Если error_type = NONE, main_gap не должен описывать серьёзную проблему
    if error_type == "NONE":
        serious_signals = [
            "критическ", "невозможн", "серьёзн", "grоss", "значительн",
            "blocker", "не может быть", "недопустим",
        ]
        if any(sig in main_gap for sig in serious_signals):
            errors.append(
                "error_type = NONE, но self_review.main_gap содержит признаки "
                "серьёзной аналитической проблемы"
            )

    # Если error_type != NONE, main_gap не должен быть пустым / формальным
    if error_type != "NONE":
        trivial_phrases = [
            "существенных", "gaps не выявлено", "не выявлено", "отсутствует",
        ]
        if not main_gap.strip() or any(p in main_gap for p in trivial_phrases):
            errors.append(
                "error_type != NONE, но self_review.main_gap не описывает "
                "конкретного gap"
            )

    return errors


def validate_signal_trace_logic(output: dict) -> list[str]:
    """
    Проверяет смысловое соответствие signal_trace режиму решения.
    MVP-эвристики — ловят явные противоречия между trace и decision.
    """
    errors = []
    mode = output.get("decision_mode", "")
    reason = output.get("reject_reason_type", "NONE")
    decisive_factor = output.get("decisive_factor", "").lower()
    trace = output.get("signal_trace", [])

    if not isinstance(trace, list):
        return ["signal_trace не является списком — логическая проверка невозможна"]

    # Должен быть хотя бы один DECISIVE сигнал
    decisive_signals = [s for s in trace if s.get("impact") == "DECISIVE"]
    if not decisive_signals:
        errors.append("signal_trace: нет ни одного сигнала с impact = DECISIVE")

    # decisive_factor должен совпадать по смыслу хотя бы с одним DECISIVE signal
    if decisive_signals and decisive_factor:
        decisive_texts = [s.get("signal", "").lower() for s in decisive_signals]
        # Берём ключевые слова из decisive_factor (длиннее 4 символов)
        df_words = {w for w in decisive_factor.split() if len(w) > 4}
        match_found = any(
            any(word in sig_text for word in df_words)
            for sig_text in decisive_texts
        )
        if not match_found:
            errors.append(
                "signal_trace: decisive_factor не совпадает по смыслу ни с одним "
                "сигналом уровня DECISIVE"
            )

    # EDD: нельзя писать, что CDD невозможно завершить
    if mode == "edd":
        forbidden_phrases = ["невозможно завершить", "не может быть заверш", "завершение невозможно"]
        for s in trace:
            comment = s.get("comment", "").lower()
            signal_text = s.get("signal", "").lower()
            combined = comment + " " + signal_text
            if any(phrase in combined for phrase in forbidden_phrases):
                errors.append(
                    "signal_trace: EDD-кейс содержит сигнал о невозможности завершить CDD "
                    f"(signal: '{s.get('signal', '')}')"
                )

    # RISK_UNACCEPTABLE: CDD завершён — нельзя иметь сигналы о неполноте CDD
    if reason == "RISK_UNACCEPTABLE":
        cdd_incomplete_signals = [
            "ubo не установлен", "sof не подтверждён",
            "документы отсутствуют", "cdd не завершён", "не может быть завершён",
        ]
        for s in trace:
            sig_low = s.get("signal", "").lower()
            if any(phrase in sig_low for phrase in cdd_incomplete_signals):
                errors.append(
                    "signal_trace: RISK_UNACCEPTABLE предполагает завершённый CDD, "
                    f"но сигнал указывает на неполноту CDD (signal: '{s.get('signal', '')}')"
                )

    # Approve: не должно быть сигналов с direction = SUPPORTS_REJECT
    if mode == "approve":
        reject_signals = [s for s in trace if s.get("direction") == "SUPPORTS_REJECT"]
        if reject_signals:
            errors.append(
                "signal_trace: Approve-кейс содержит сигналы с direction = SUPPORTS_REJECT"
            )

    return errors


def validate_output_structure(output: dict) -> tuple[bool, list[str]]:
    errors = []

    if not isinstance(output, dict):
        return False, ["Output is not a dict"]

    for key in REQUIRED_OUTPUT_KEYS:
        if key not in output:
            errors.append(f"Missing key: {key}")

    if errors:
        return False, errors

    if output["reject_reason_type"] not in ALLOWED_REJECT_REASON_TYPES:
        errors.append(f"Invalid reject_reason_type: {output['reject_reason_type']}")

    if output["decision_mode"] not in ALLOWED_DECISION_MODES:
        errors.append(f"Invalid decision_mode: {output['decision_mode']}")

    if output["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"Invalid decision: {output['decision']}")

    if output["edd_required"] not in ALLOWED_EDD_VALUES:
        errors.append(f"Invalid edd_required: {output['edd_required']}")

    if output["cdd_status"] not in ALLOWED_CDD_STATUS:
        errors.append(f"Invalid cdd_status: {output['cdd_status']}")

    if output["risk_level"] not in ALLOWED_RISK_LEVELS:
        errors.append(f"Invalid risk_level: {output['risk_level']}")

    if not isinstance(output["decision_summary"], str):
        errors.append("decision_summary must be a string")

    if not isinstance(output["case_overview"], str):
        errors.append("case_overview must be a string")

    if not isinstance(output["analysis"], str):
        errors.append("analysis must be a string")

    if not isinstance(output["decision_rationale"], str):
        errors.append("decision_rationale must be a string")

    if not isinstance(output["decisive_factor"], str):
        errors.append("decisive_factor must be a string")
    elif not output["decisive_factor"].strip():
        errors.append("decisive_factor must not be empty")
    else:
        # Смысловая проверка: соответствие режиму решения
        logic_errors = validate_decisive_factor_logic(output)
        errors.extend(logic_errors)

    if not isinstance(output["key_risk_factors"], list):
        errors.append("key_risk_factors must be a list")

    if not isinstance(output["required_actions"], list):
        errors.append("required_actions must be a list")

    cdd_assessment = output["cdd_assessment"]
    if not isinstance(cdd_assessment, dict):
        errors.append("cdd_assessment must be an object")
    else:
        for subkey in ["confirmed", "not_confirmed", "conclusion"]:
            if subkey not in cdd_assessment:
                errors.append(f"Missing cdd_assessment.{subkey}")

        if "confirmed" in cdd_assessment and not isinstance(cdd_assessment["confirmed"], list):
            errors.append("cdd_assessment.confirmed must be a list")

        if "not_confirmed" in cdd_assessment and not isinstance(cdd_assessment["not_confirmed"], list):
            errors.append("cdd_assessment.not_confirmed must be a list")

        if "conclusion" in cdd_assessment and not isinstance(cdd_assessment["conclusion"], str):
            errors.append("cdd_assessment.conclusion must be a string")

    if len(output["key_risk_factors"]) > 5:
        errors.append("key_risk_factors must contain at most 5 items")

    if len(output["required_actions"]) > 6:
        errors.append("required_actions must contain at most 6 items")

    # --- error_type ---
    if output["error_type"] not in ALLOWED_ERROR_TYPES:
        errors.append(f"Invalid error_type: {output['error_type']}")

    # --- confidence_score ---
    cs = output["confidence_score"]
    if not isinstance(cs, int):
        errors.append("confidence_score must be an integer")
    elif not (1 <= cs <= 5):
        errors.append(f"confidence_score must be between 1 and 5, got {cs}")

    # --- self_review ---
    sr = output["self_review"]
    if not isinstance(sr, dict):
        errors.append("self_review must be an object")
    else:
        for subkey in ["summary", "main_gap", "what_to_recheck"]:
            if subkey not in sr:
                errors.append(f"Missing self_review.{subkey}")

        if "summary" in sr and not isinstance(sr["summary"], str):
            errors.append("self_review.summary must be a string")

        if "main_gap" in sr and not isinstance(sr["main_gap"], str):
            errors.append("self_review.main_gap must be a string")

        if "what_to_recheck" in sr:
            if not isinstance(sr["what_to_recheck"], list):
                errors.append("self_review.what_to_recheck must be a list")
            elif len(sr["what_to_recheck"]) > 3:
                errors.append(
                    "self_review.what_to_recheck must contain at most 3 items"
                )

    # --- signal_trace ---
    st = output["signal_trace"]
    if not isinstance(st, list):
        errors.append("signal_trace must be a list")
    elif len(st) == 0:
        errors.append("signal_trace must contain at least 1 item")
    elif len(st) > 6:
        errors.append("signal_trace must contain at most 6 items")
    else:
        for idx, sig in enumerate(st):
            if not isinstance(sig, dict):
                errors.append(f"signal_trace[{idx}] must be an object")
                continue
            for field in ["signal", "category", "impact", "direction", "comment"]:
                if field not in sig:
                    errors.append(f"signal_trace[{idx}]: missing field '{field}'")
            if "category" in sig and sig["category"] not in ALLOWED_SIGNAL_CATEGORIES:
                errors.append(f"signal_trace[{idx}]: invalid category '{sig['category']}'")
            if "impact" in sig and sig["impact"] not in ALLOWED_SIGNAL_IMPACTS:
                errors.append(f"signal_trace[{idx}]: invalid impact '{sig['impact']}'")
            if "direction" in sig and sig["direction"] not in ALLOWED_SIGNAL_DIRECTIONS:
                errors.append(f"signal_trace[{idx}]: invalid direction '{sig['direction']}'")

    # --- Смысловая логика self_review (только если форма валидна) ---
    if not errors:
        logic_errors = validate_self_review_logic(output)
        errors.extend(logic_errors)

    # --- Смысловая логика signal_trace (только если форма валидна) ---
    if not errors:
        trace_errors = validate_signal_trace_logic(output)
        errors.extend(trace_errors)

    return len(errors) == 0, errors


def build_fallback_output(case_data: dict, error_message: str) -> dict:
    """
    Если structured output сломался, UI всё равно сможет что-то показать.
    """
    recommendation = case_data.get("recommendation", "Эскалация")
    risk_level = case_data.get("selected_risk_level", "Средний")

    if recommendation == "Отказать":
        decision_mode = "reject"
        edd_required = "Нет"
        cdd_status = "Incomplete and cannot be completed"
        reject_reason_type = "CDD_FAILURE"
    elif recommendation == "Одобрить":
        decision_mode = "approve"
        edd_required = "Нет"
        cdd_status = "Complete"
        reject_reason_type = "NONE"
    else:
        decision_mode = "edd"
        edd_required = "Да"
        cdd_status = "Incomplete"
        reject_reason_type = "NONE"

    return {
        "decision_mode": decision_mode,
        "decision": recommendation,
        "edd_required": edd_required,
        "cdd_status": cdd_status,
        "risk_level": risk_level,
        "decision_summary": "Структурированный output не был корректно сгенерирован. Использован fallback-режим.",
        "case_overview": f"Клиент: {case_data.get('client_name', '—')}. Тип кейса: {case_data.get('case_type', '—')}.",
        "key_risk_factors": ["Требуется ручная проверка output"],
        "cdd_assessment": {
            "confirmed": [],
            "not_confirmed": [],
            "conclusion": f"Требуется ручная валидация structured output. Ошибка: {error_message}",
        },
        "analysis": "LLM output не прошёл валидацию структуры, поэтому note требует ручной проверки.",
        "decisive_factor": _fallback_decisive_factor(decision_mode),
        "decision_rationale": "Использован технический fallback до исправления structured output.",
        "required_actions": ["Проверить prompt, JSON output и валидацию структуры."],
        "reject_reason_type": reject_reason_type,
        "error_type": "WEAK_RATIONALE",
        "confidence_score": 2,
        "self_review": {
            "summary": (
                "Структурированный self-review не был корректно сгенерирован. "
                "Требуется ручная проверка reasoning."
            ),
            "main_gap": (
                "Качество обоснования не может быть надёжно оценено в fallback-режиме."
            ),
            "what_to_recheck": [
                "Проверить соответствие decision статусу CDD",
                "Проверить decisive_factor и decision_rationale",
            ],
        },
        "signal_trace": [
            {
                "signal": _fallback_decisive_factor(decision_mode),
                "category": "OTHER",
                "impact": "DECISIVE",
                "direction": "SUPPORTS_ESCALATION",
                "comment": (
                    "Structured output не прошёл валидацию, "
                    "trace нужно определить вручную."
                ),
            }
        ],
    }