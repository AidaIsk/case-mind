# services.py

from llm import generate_structured_decision_output, is_llm_available
from renderers import render_decision_note
from validators import validate_case
from helpers import get_rejection_reasons, get_required_actions, build_case_timeline
from schemas import build_case_data
from storage import save_case_record, load_cases, get_case
from logic import get_cdd_status_and_system_decision


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


def save_result(case_data: dict, result: dict) -> None:
    """Сохраняет результат process_case() в storage. UI вызывает только эту функцию."""
    save_case_record(
        case_data=case_data,
        structured_output=result["structured_output"],
        note=result["note"],
        rejection_reasons=result["rejection_reasons"],
        required_actions=result["required_actions"],
        timeline=result["timeline"],
    )


def get_all_cases() -> list:
    """Возвращает все сохранённые кейсы. UI-точка входа для списка."""
    return load_cases()


def get_case_by_id(case_id: str) -> dict | None:
    """Возвращает кейс по ID. UI-точка входа для просмотра."""
    return get_case(case_id)


def build_case_input(*args, **kwargs) -> dict:
    """Обёртка над schemas.build_case_data. UI не импортирует schemas напрямую."""
    return build_case_data(*args, **kwargs)


def get_case_decision_meta(case_data: dict) -> tuple:
    """Обёртка над logic. UI не импортирует logic напрямую."""
    return get_cdd_status_and_system_decision(case_data)


def check_llm() -> bool:
    """Проверяет доступность LLM. UI не импортирует llm напрямую."""
    return is_llm_available()