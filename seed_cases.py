# seed_cases.py
#
# Заполняет cases.json 15 демо-кейсами.
# Запуск: python3 seed_cases.py

import json, os
from datetime import datetime, timedelta

DATA_DIR   = "data"
CASES_FILE = os.path.join(DATA_DIR, "cases.json")


def _ts(days_ago: int) -> str:
    dt = datetime.now() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d %H:%M")


def _not_confirmed(ubo, sof, docs, econ_rationale) -> list:
    """Строит список незакрытых CDD-элементов из входных параметров."""
    items = []
    if ubo == "Нет":
        items.append("UBO")
    if sof == "Нет":
        items.append("SoF")
    if docs == "Нет":
        items.append("Подтверждающие документы")
    if econ_rationale not in ("Понятен",):
        items.append("Экономический смысл операции")
    return items


def _record(
    case_id, client_name, case_type, client_type,
    registration_country, business_activity,
    ubo, sof, docs, econ_rationale, high_risk_geo,
    risk_manageable, risk_level, recommendation,
    edd_required, decision_rationale,
    decision_mode, decision, cdd_status, reject_reason_type,
    decisive_factor, rationale_text,
    error_type, confidence_score,
    sr_summary, sr_main_gap, sr_recheck,
    adverse_media="Нет",
    days_ago=0,
) -> dict:
    not_confirmed = _not_confirmed(ubo, sof, docs, econ_rationale)
    confirmed = []
    if ubo == "Да":
        confirmed.append("Идентификация и UBO")
    if sof != "Нет":
        confirmed.append("Источник средств")
    if docs != "Нет":
        confirmed.append("Подтверждающие документы")
    if econ_rationale == "Понятен":
        confirmed.append("Экономический смысл операции")

    so = {
        "decision_mode":      decision_mode,
        "decision":           decision,
        "edd_required":       edd_required,
        "cdd_status":         cdd_status,
        "risk_level":         risk_level,
        "reject_reason_type": reject_reason_type,
        "decision_summary":   decision_rationale,
        "case_overview":      f"{client_name} ({registration_country}). {business_activity}",
        "key_risk_factors":   [],
        "cdd_assessment": {
            "confirmed":     confirmed,
            "not_confirmed": not_confirmed,
            "conclusion":    cdd_status,
        },
        "analysis":           rationale_text,
        "decisive_factor":    decisive_factor,
        "decision_rationale": rationale_text,
        "required_actions":   [],
        "error_type":         error_type,
        "confidence_score":   confidence_score,
        "self_review": {
            "summary":         sr_summary,
            "main_gap":        sr_main_gap,
            "what_to_recheck": sr_recheck,
        },
    }
    case_data = {
        "case_id":                         case_id,
        "case_type":                       case_type,
        "client_type":                     client_type,
        "client_name":                     client_name,
        "registration_country":            registration_country,
        "business_activity":               business_activity,
        "beneficial_owner_identified":     ubo,
        "beneficial_owner_details":        "",
        "ultimate_controller_description": "",
        "client_country":                  registration_country,
        "counterparty_countries":          [],
        "high_risk_jurisdiction_involved": high_risk_geo,
        "source_of_funds_summary":         "" if sof == "Нет" else "Подтверждён",
        "transaction_amount":              "",
        "transaction_description":         "",
        "supporting_documents_provided":   docs,
        "purpose_of_relationship":         "",
        "product_or_service_description":  "",
        "economic_rationale_clear":        econ_rationale,
        "matches_client_profile":          "Да",
        "sanctions_result":                "Совпадений нет",
        "pep_result":                      "Нет",
        "adverse_media_result":            adverse_media,
        "unresolved_screening_issues":     (
            "Негативные публикации не сняты" if adverse_media == "Есть" else ""
        ),
        "red_flags_selected":              [],
        "mitigating_factors_selected":     [],
        "key_risk_driver":                 "",
        "risk_manageable":                 risk_manageable,
        "selected_risk_level":             risk_level,
        "recommendation":                  recommendation,
        "edd_required":                    edd_required,
        "decision_rationale":              decision_rationale,
        "missing_information_summary":     "",
    }
    return {
        "saved_at":          _ts(days_ago),
        "case_id":           case_id,
        "decision":          decision,
        "risk_level":        risk_level,
        "decisive_factor":   decisive_factor,
        "error_type":        error_type,
        "confidence_score":  confidence_score,
        "case_data":         case_data,
        "structured_output": so,
        "decision_note":     f"## Decision Summary\n**Решение:** {decision}\n\n{rationale_text}",
        "rejection_reasons": [],
        "required_actions":  [],
        "timeline": [
            {"time": _ts(days_ago), "event": "Кейс создан",       "details": f"{case_type} • {client_name}"},
            {"time": _ts(days_ago), "event": "Принято решение",    "details": decision},
        ],
    }


cases = [

    # ── APPROVE ──────────────────────────────────────────────────────────────

    _record(
        case_id="APR-001", client_name="Nordic Timber AS",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Норвегия", business_activity="Лесозаготовка и экспорт",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Низкий", recommendation="Одобрить", edd_required="Нет",
        decision_rationale="CDD завершён в полном объёме. Риск находится в приемлемых пределах.",
        decision_mode="approve", decision="Одобрить",
        cdd_status="Complete", reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены, существенные блокеры не выявлены.",
        rationale_text="Структура прозрачна, UBO установлен, SoF подтверждён документально.",
        error_type="NONE", confidence_score=5,
        sr_summary="Решение логически согласовано и защищаемо.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["результаты проверки по базам"], days_ago=14,
    ),

    _record(
        case_id="APR-002", client_name="Reinholt GmbH",
        case_type="Review", client_type="Юридическое лицо",
        registration_country="Германия", business_activity="Производство промышленного оборудования",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Низкий", recommendation="Одобрить", edd_required="Нет",
        decision_rationale="Плановый пересмотр. CDD в норме. Профиль не изменился.",
        decision_mode="approve", decision="Одобрить",
        cdd_status="Complete", reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены, существенные блокеры не выявлены.",
        rationale_text="Клиент известен системе. Изменений в профиле не зафиксировано.",
        error_type="NONE", confidence_score=5,
        sr_summary="Решение стандартное, риски минимальны.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["негативные публикации"], days_ago=10,
    ),

    _record(
        case_id="APR-003", client_name="Baltic Grain Ltd",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Латвия", business_activity="Торговля зерном и агрокультурами",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Средний", recommendation="Одобрить", edd_required="Нет",
        decision_rationale="Средний риск обоснован географией, однако CDD завершён и риск управляем.",
        decision_mode="approve", decision="Одобрить",
        cdd_status="Complete", reject_reason_type="NONE",
        decisive_factor="Ключевые элементы CDD подтверждены, существенные блокеры не выявлены.",
        rationale_text="Трансграничная торговля типична для профиля. SoF и документация в норме.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение защищаемо. Средний риск обоснован.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["SoF", "негативные публикации"], days_ago=7,
    ),

    # ── REJECT / CDD_FAILURE ─────────────────────────────────────────────────

    _record(
        case_id="REJ-CDD-001", client_name="Pacifica Holdings",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Сейшельские острова", business_activity="Инвестиционный холдинг",
        ubo="Нет", sof="Нет", docs="Нет", econ_rationale="Не понятен",
        high_risk_geo="Да", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="UBO не установлен. Завершение CDD невозможно.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Incomplete and cannot be completed", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен и не может быть подтверждён.",
        rationale_text="Оффшорная структура с непрозрачным владением. UBO недоступен. EDD не устранит ключевые пробелы.",
        error_type="NONE", confidence_score=5,
        sr_summary="Отказ однозначен. Завершение CDD структурно невозможно.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["UBO"], days_ago=12,
    ),

    _record(
        case_id="REJ-CDD-002", client_name="Meridian Connect FZE",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="ОАЭ (Фризона)", business_activity="Посреднические услуги",
        ubo="Нет", sof="Нет", docs="Нет", econ_rationale="Не понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="Бенефициарный владелец не установлен. Завершение CDD невозможно.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Incomplete and cannot be completed", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен и не может быть подтверждён.",
        rationale_text="Посредническая структура без раскрытия конечного бенефициара. Критические пробелы остаются неустранёнными.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение обоснованно. CDD невозможно завершить.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["UBO"], days_ago=9,
    ),

    _record(
        case_id="REJ-CDD-003", client_name="Vostok Resources LLC",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Белиз", business_activity="Торговля природными ресурсами",
        ubo="Нет", sof="Нет", docs="Нет", econ_rationale="Не понятен",
        high_risk_geo="Да", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="Оффшор + непрозрачное UBO + отсутствие документации = невозможность завершить CDD.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Incomplete and cannot be completed", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен. CDD завершить невозможно.",
        rationale_text="Структура непрозрачна. EDD не устранит ключевые дефиции по UBO и SoF.",
        error_type="NONE", confidence_score=5,
        sr_summary="Отказ обоснован и защищаем.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["UBO", "SoF"], days_ago=6,
    ),

    _record(
        case_id="REJ-CDD-004", client_name="Sunrise Capital Partners",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Британские Виргинские острова", business_activity="Частный инвестиционный фонд",
        ubo="Нет", sof="Нет", docs="Нет", econ_rationale="Не понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="Фонд без раскрытия UBO. Завершение CDD невозможно.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Incomplete and cannot be completed", reject_reason_type="CDD_FAILURE",
        decisive_factor="Бенефициарный владелец не установлен и не может быть подтверждён.",
        rationale_text="Структура фонда не раскрывает конечных бенефициаров. Документы по владению не предоставлены.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение стандартное и защищаемо.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["UBO"], days_ago=4,
    ),

    # ── REJECT / RISK_UNACCEPTABLE ───────────────────────────────────────────
    # adverse_media="Есть" → case_data.adverse_media_result = "Есть"
    # unresolved_screening_issues заполняется автоматически в _record()

    _record(
        case_id="REJ-RISK-001", client_name="Eurogate Trading SL",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Испания", business_activity="Международная торговля",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="CDD завершён, но риск неприемлем ввиду незакрытых негативных публикаций.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Complete but risk not acceptable", reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Негативные публикации о возможной вовлечённости в схемы торгового финансирования не сняты.",
        rationale_text="Ключевым фактором отказа являются незакрытые негативные публикации. Риск не снижен до приемлемого уровня, клиент не может быть принят.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение защищаемо. Блокирующий риск-сигнал чётко идентифицирован.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["негативные публикации", "risk_level"],
        adverse_media="Есть", days_ago=11,
    ),

    _record(
        case_id="REJ-RISK-002", client_name="AlphaStream GmbH",
        case_type="Review", client_type="Юридическое лицо",
        registration_country="Австрия", business_activity="Финансовые технологии",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="Пересмотр выявил неустранимые риск-findings. CDD завершён, но риск неприемлем.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Complete but risk not acceptable", reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Негативные публикации, выявленные при пересмотре, не были сняты.",
        rationale_text="Ключевым фактором отказа являются незакрытые негативные публикации. Поскольку риск не снижен до приемлемого уровня, клиент не может быть принят.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение обоснованно. Риск-блокер чётко сформулирован.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["негативные публикации"],
        adverse_media="Есть", days_ago=8,
    ),

    _record(
        case_id="REJ-RISK-003", client_name="Danube Port Holdings",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Венгрия", business_activity="Портовая логистика",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="Новые данные по публикациям делают риск неприемлемым. Решение на грани reject/EDD.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Complete but risk not acceptable", reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Новые публикации о возможной вовлечённости в санкционные схемы не сняты.",
        rationale_text="Ключевым фактором отказа является появление новых негативных публикаций. Возможно, escalation через EDD позволил бы закрыть отдельные вопросы.",
        error_type="OVER_REJECT", confidence_score=3,
        sr_summary="Решение допустимо, однако это пограничный случай — возможно, EDD устранил бы отдельные вопросы.",
        sr_main_gap="Не исключено, что EDD позволил бы закрыть ключевые вопросы без reject.",
        sr_recheck=["негативные публикации", "decision_rationale"],
        adverse_media="Есть", days_ago=5,
    ),

    _record(
        case_id="REJ-RISK-004", client_name="Cascade Import Group",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Румыния", business_activity="Импорт потребительских товаров",
        ubo="Да", sof="Да", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Нет",
        risk_level="Высокий", recommendation="Отказать", edd_required="Нет",
        decision_rationale="CDD формально завершён, однако совокупность риск-findings делает риск неприемлемым.",
        decision_mode="reject", decision="Отказать",
        cdd_status="Complete but risk not acceptable", reject_reason_type="RISK_UNACCEPTABLE",
        decisive_factor="Публикации о связях с проблемными контрагентами не устранены.",
        rationale_text="Ключевым фактором отказа являются незакрытые негативные публикации о контрагентах. Клиент не может быть принят.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение защищаемо. Риск-сигнал конкретный.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["негативные публикации"],
        adverse_media="Есть", days_ago=2,
    ),

    # ── EDD / ESCALATION ─────────────────────────────────────────────────────

    _record(
        case_id="EDD-001", client_name="AgroTrans Polska",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Польша", business_activity="Агрологистика",
        ubo="Да", sof="Нет", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Средний", recommendation="Эскалация", edd_required="Да",
        decision_rationale="SoF не подтверждён. EDD может закрыть этот пробел.",
        decision_mode="edd", decision="Эскалация",
        cdd_status="Incomplete", reject_reason_type="NONE",
        decisive_factor="Источник средств по операции не подтверждён.",
        rationale_text="CDD не завершён по причине отсутствия подтверждения SoF. Выявленные пробелы закрываемы через EDD.",
        error_type="WEAK_RATIONALE", confidence_score=3,
        sr_summary="EDD верен, но обоснование не связывает риск-сигнал с выводом достаточно чётко.",
        sr_main_gap="Обоснование слишком общее — не объясняет, почему именно EDD, а не отказ.",
        sr_recheck=["SoF", "decision_rationale"], days_ago=13,
    ),

    _record(
        case_id="EDD-002", client_name="TechBridge Solutions",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Эстония", business_activity="IT-аутсорсинг",
        ubo="Да", sof="Да", docs="Нет", econ_rationale="Частично",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Средний", recommendation="Эскалация", edd_required="Да",
        decision_rationale="Документация неполная. Экономический смысл частично подтверждён.",
        decision_mode="edd", decision="Эскалация",
        cdd_status="Incomplete", reject_reason_type="NONE",
        decisive_factor="Подтверждающие документы по операции не предоставлены.",
        rationale_text="CDD не завершён из-за отсутствия документов. Пробелы могут быть закрыты через EDD.",
        error_type="WEAK_RATIONALE", confidence_score=3,
        sr_summary="EDD выбран верно, но обоснование расплывчатое.",
        sr_main_gap="Обоснование не указывает конкретный пробел, который EDD должен закрыть.",
        sr_recheck=["документы", "decision_rationale"], days_ago=3,
    ),

    _record(
        case_id="EDD-003", client_name="Hellas Marine Services",
        case_type="Onboarding", client_type="Юридическое лицо",
        registration_country="Греция", business_activity="Морские перевозки",
        ubo="Да", sof="Нет", docs="Да", econ_rationale="Понятен",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Средний", recommendation="Эскалация", edd_required="Да",
        decision_rationale="Источник средств по конкретной операции не подтверждён. EDD запрошен.",
        decision_mode="edd", decision="Эскалация",
        cdd_status="Incomplete", reject_reason_type="NONE",
        decisive_factor="Источник средств по операции не подтверждён.",
        rationale_text="Профиль клиента понятен. Открытый вопрос по SoF является закрываемым через EDD.",
        error_type="NONE", confidence_score=4,
        sr_summary="Решение защищаемо. Пробел по SoF чётко идентифицирован и закрываем.",
        sr_main_gap="Существенных аналитических пробелов не выявлено.",
        sr_recheck=["SoF"], days_ago=1,
    ),

    _record(
        case_id="EDD-004", client_name="Danzig Forwarding Co",
        case_type="Review", client_type="Юридическое лицо",
        registration_country="Польша", business_activity="Экспедирование грузов",
        ubo="Да", sof="Нет", docs="Да", econ_rationale="Частично",
        high_risk_geo="Нет", risk_manageable="Да",
        risk_level="Средний", recommendation="Эскалация", edd_required="Да",
        decision_rationale="Плановый пересмотр. Открытые вопросы по SoF и экономическому смыслу.",
        decision_mode="edd", decision="Эскалация",
        cdd_status="Incomplete", reject_reason_type="NONE",
        decisive_factor="Источник средств и экономическое обоснование не подтверждены в полном объёме.",
        rationale_text="CDD не завершён. Пробелы могут быть закрыты через EDD.",
        error_type="WEAK_RATIONALE", confidence_score=2,
        sr_summary="EDD верен, но обоснование не выдержит детальной проверки.",
        sr_main_gap="Неясно, почему отказ не применён при двух открытых вопросах.",
        sr_recheck=["SoF", "экономический смысл", "decision_rationale"], days_ago=0,
    ),

]

# Запись
os.makedirs(DATA_DIR, exist_ok=True)
with open(CASES_FILE, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)

print(f"Записано {len(cases)} кейсов в {CASES_FILE}")
for c in cases:
    case_data = c["case_data"]
    adv = case_data.get("adverse_media_result", "Нет")
    unres = case_data.get("unresolved_screening_issues", "")
    not_conf = c["structured_output"]["cdd_assessment"]["not_confirmed"]
    print(
        f"  {c['case_id']:20} {c['decision']:12} "
        f"риск={c['risk_level']:8} ошибка={c['error_type']:22} "
        f"adv={adv:5} not_confirmed={not_conf}"
    )