# test_services.py

from services import process_case


def test_valid_case():
    case_data = {
        "client_name": "Test Company",
        "client_type": "Юридическое лицо",
        "bo_identified": "Да",
        "sanctions_result": "Совпадений нет",
        "pep_result": "Нет",
        "adverse_media_result": "Нет",
        "risk_manageable": "Да",
    }

    result = process_case(case_data)

    print("\n=== VALID CASE ===")
    print("OK:", result["ok"])
    print("Note exists:", bool(result["note"]))
    print("Structured output exists:", bool(result["structured_output"]))


def test_blocked_case():
    case_data = {
        "client_name": "Test Company",
        "client_type": "Юридическое лицо",
        "bo_identified": "Нет",  # ❗ ключевой триггер
        "sanctions_result": "Совпадений нет",
        "pep_result": "Нет",
        "adverse_media_result": "Нет",
        "risk_manageable": "Да",
    }

    result = process_case(case_data)

    print("\n=== BLOCKED CASE ===")
    print("OK:", result["ok"])
    print("Blocking errors:", result["validation"]["blocking_errors"])
    print("Note:", result["note"])


if __name__ == "__main__":
    test_valid_case()
    test_blocked_case()