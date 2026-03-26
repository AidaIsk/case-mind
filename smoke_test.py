from logic import get_cdd_status_and_system_decision
from validators import validate_case
from helpers import get_rejection_reasons, get_required_actions, build_case_timeline
from storage import save_case_record, load_cases


def run_smoke_test():
    print("== SMOKE TEST START ==")

    edd_case = {
        "case_id": "SMOKE-EDD-001",
        "case_type": "Onboarding",
        "client_type": "Юридическое лицо",
        "client_name": "TechSolutions KZ",
        "registration_country": "Казахстан",
        "business_activity": "Разработка ПО",
        "beneficial_owner_identified": "Да",
        "beneficial_owner_details": "Формальный UBO указан",
        "ultimate_controller_description": "Фактическое влияние со стороны партнёра из ОАЭ",
        "client_country": "Казахстан",
        "counterparty_countries": ["ОАЭ", "BVI"],
        "high_risk_jurisdiction_involved": "Да",
        "source_of_funds_summary": "",
        "transaction_amount": "12 000 000 KZT",
        "transaction_description": "Платёж от BVI-компании",
        "supporting_documents_provided": "Нет",
        "purpose_of_relationship": "IT-консалтинг",
        "product_or_service_description": "Разработка ПО",
        "economic_rationale_clear": "Не понятен",
        "matches_client_profile": "Частично",
        "sanctions_result": "Совпадений нет",
        "pep_result": "Нет",
        "adverse_media_result": "Нет",
        "unresolved_screening_issues": "",
        "red_flags_selected": ["BVI payment", "Hidden control"],
        "mitigating_factors_selected": [],
        "key_risk_driver": "Непрозрачный контроль и неподтверждённый SoF",
        "risk_manageable": "Да",
        "selected_risk_level": "Высокий",
        "recommendation": "Эскалация",
        "edd_required": "Да",
        "decision_rationale": "CDD incomplete but gaps may be resolved",
        "missing_information_summary": "SoF, contract, controller details",
    }

    reject_case = {
        **edd_case,
        "case_id": "SMOKE-REJECT-001",
        "beneficial_owner_identified": "Нет",
        "ultimate_controller_description": "",
        "recommendation": "Одобрить",
        "edd_required": "Нет",
    }

    print("\n[1] Testing logic for EDD case...")
    cdd_complete, system_decision, decision_status = get_cdd_status_and_system_decision(edd_case)
    print("Result:", cdd_complete, system_decision, decision_status)
    assert cdd_complete is False
    assert system_decision == "Эскалация"

    print("\n[2] Testing validator for EDD case...")
    validation = validate_case(edd_case)
    print(validation)
    assert len(validation["blocking_errors"]) == 0

    print("\n[3] Testing logic for reject/block case...")
    validation_reject = validate_case(reject_case)
    print(validation_reject)
    assert len(validation_reject["blocking_errors"]) > 0

    print("\n[4] Testing helper functions...")
    reasons = get_rejection_reasons(edd_case)
    actions = get_required_actions(edd_case)
    timeline = build_case_timeline(edd_case)
    print("Reasons:", reasons)
    print("Actions:", actions)
    print("Timeline:", timeline)
    assert isinstance(reasons, list)
    assert isinstance(actions, list)
    assert isinstance(timeline, list)

    print("\n[5] Testing storage...")
    save_case_record(
        case_data=edd_case,
        note="Test decision note",
        rejection_reasons=reasons,
        required_actions=actions,
        timeline=timeline,
    )
    cases = load_cases()
    print(f"Loaded cases: {len(cases)}")
    assert any(c.get("case_data", {}).get("case_id") == "SMOKE-EDD-001" for c in cases)

    print("\n== SMOKE TEST PASSED ==")


if __name__ == "__main__":
    run_smoke_test()