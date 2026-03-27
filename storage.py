import os
import json
from datetime import datetime

DATA_DIR = "data"
CASES_FILE = os.path.join(DATA_DIR, "cases.json")


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_cases() -> list:
    ensure_data_dir()

    if not os.path.exists(CASES_FILE):
        return []

    try:
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_cases(cases: list) -> None:
    ensure_data_dir()

    with open(CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


def get_case(case_id: str) -> dict | None:
    """Возвращает запись по case_id или None если не найдена."""
    for record in load_cases():
        if record.get("case_data", {}).get("case_id", "") == case_id:
            return record
    return None


def save_case_record(
    case_data: dict,
    structured_output: dict,
    note: str,
    rejection_reasons: list,
    required_actions: list,
    timeline: list,
) -> None:
    cases = load_cases()

    so = structured_output or {}

    record = {
        "saved_at":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        # --- быстрые поля верхнего уровня для списка и аналитики ---
        "case_id":         case_data.get("case_id", ""),
        "decision":        so.get("decision") or case_data.get("recommendation", "—"),
        "risk_level":      so.get("risk_level") or case_data.get("selected_risk_level", "—"),
        "decisive_factor": so.get("decisive_factor", "—"),
        "error_type":      so.get("error_type", "—"),
        "confidence_score": so.get("confidence_score", 0),
        # --- полные данные ---
        "case_data":         case_data,
        "structured_output": structured_output,
        "decision_note":     note,
        "rejection_reasons": rejection_reasons,
        "required_actions":  required_actions,
        "timeline":          timeline,
    }

    case_id = case_data.get("case_id", "").strip()

    replaced = False
    if case_id:
        for i, existing in enumerate(cases):
            existing_id = existing.get("case_data", {}).get("case_id", "")
            if existing_id == case_id:
                cases[i] = record
                replaced = True
                break

    if not replaced:
        cases.append(record)

    save_cases(cases)