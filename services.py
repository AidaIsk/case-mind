# services.py

from llm import generate_structured_decision_output
from renderers import render_decision_note
from validators import validate_case
from helpers import get_rejection_reasons, get_required_actions, build_case_timeline


def process_case(case_data: dict) -> dict:
    """
    Единый сервисный поток обработки кейса:
    case_data -> validation -> structured_output -> note -> derived artifacts
    """
    validation = validate_case(case_data)

    if validation["blocking_errors"]:
        return {
            "ok": False,
            "validation": validation,
            "structured_output": None,
            "note": None,
            "rejection_reasons": [],
            "required_actions": [],
            "timeline": [],
        }

    structured_output = generate_structured_decision_output(case_data)
    note = render_decision_note(structured_output)
    rejection_reasons = get_rejection_reasons(case_data)
    required_actions = get_required_actions(case_data)
    timeline = build_case_timeline(case_data)

    return {
        "ok": True,
        "validation": validation,
        "structured_output": structured_output,
        "note": note,
        "rejection_reasons": rejection_reasons,
        "required_actions": required_actions,
        "timeline": timeline,
    }