# trainer_cases.py
#
# Curated библиотека тренировочных кейсов для Trainer Mode.
# Каждый кейс содержит описание ситуации и эталонный structured_output,
# с которым сравнивается ответ аналитика.
#
# Покрытие: 2 approve, 2 edd, 2 reject/CDD_FAILURE, 2 reject/RISK_UNACCEPTABLE,
#           1 borderline (EDD vs Reject), 1 сложный approve с PEP-контекстом.

TRAINER_CASES = [

    # ──────────────────────────────────────────────────────────────────────
    # APPROVE (2 кейса)
    # ──────────────────────────────────────────────────────────────────────

    {
        "case_id": "TR-001",
        "difficulty": "beginner",
        "theme": "CDD Complete",
        "description": (
            "Норвежская производственная компания, onboarding. "
            "UBO установлен, SoF подтверждён документально, "
            "screening чистый. Операция соответствует профилю."
        ),
        "case_data": {
            "case_id": "TR-001",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "Nordic Timber AS",
            "registration_country": "Норвегия",
            "business_activity": "Лесозаготовка и экспорт пиломатериалов",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Физическое лицо, резидент Норвегии, доля 100%",
            "ultimate_controller_description": "Ларс Эрикссон, CEO и единственный акционер",
            "client_country": "Норвегия",
            "counterparty_countries": ["Германия", "Швеция"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Выручка от экспорта пиломатериалов, подтверждена контрактами",
            "transaction_amount": "EUR 450,000",
            "transaction_description": "Оплата за поставку пиломатериалов покупателю в Германии",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Расчёты по экспортным контрактам",
            "product_or_service_description": "Торговый счёт для экспортных расчётов",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": [],
            "mitigating_factors_selected": ["Прозрачная структура владения", "Подтверждённый SoF"],
            "key_risk_driver": "",
            "risk_manageable": "Да",
            "selected_risk_level": "Низкий",
            "recommendation": "Одобрить",
            "edd_required": "Нет",
            "decision_rationale": "CDD завершён в полном объёме. Риск приемлем.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "approve",
            "decision": "Одобрить",
            "edd_required": "Нет",
            "cdd_status": "Complete",
            "risk_level": "Низкий",
            "reject_reason_type": "NONE",
            "decisive_factor": "Ключевые элементы CDD подтверждены, существенные блокирующие факторы не выявлены.",
            "error_type": "NONE",
            "confidence_score": 5,
            "signal_trace": [
                {"signal": "UBO установлен и документально подтверждён.", "category": "CDD", "impact": "DECISIVE", "direction": "SUPPORTS_DECISION", "comment": "Структура владения прозрачна."},
                {"signal": "SoF подтверждён экспортными контрактами.", "category": "SOF", "impact": "HIGH", "direction": "SUPPORTS_DECISION", "comment": "Источник средств соответствует деятельности."},
                {"signal": "Screening чистый: санкции, PEP, негативные публикации не выявлены.", "category": "SCREENING", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Отсутствие негативных факторов по всем базам."},
            ],
        },
    },

    {
        "case_id": "TR-002",
        "difficulty": "intermediate",
        "theme": "CDD Complete",
        "description": (
            "Немецкая IT-компания, review. UBO — гражданин Германии, "
            "PEP второй линии (родственник чиновника). "
            "Adverse media нет, SoF подтверждён, риск управляем. "
            "Задача: не переусердствовать с EDD при наличии PEP-контекста."
        ),
        "case_data": {
            "case_id": "TR-002",
            "case_type": "Review",
            "client_type": "Юридическое лицо",
            "client_name": "TechBerlin GmbH",
            "registration_country": "Германия",
            "business_activity": "Разработка программного обеспечения",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Марк Вебер, 60%, гражданин Германии",
            "ultimate_controller_description": "Марк Вебер — CEO, родственник депутата Бундестага (PEP 2-й линии)",
            "client_country": "Германия",
            "counterparty_countries": ["Австрия", "Нидерланды"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Лицензионные доходы от ПО, подтверждены договорами",
            "transaction_amount": "EUR 120,000",
            "transaction_description": "Квартальный лицензионный платёж от австрийского клиента",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Расчёты по лицензионным соглашениям",
            "product_or_service_description": "Транзакционный счёт",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Да",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": [],
            "mitigating_factors_selected": ["PEP второй линии, не прямой", "SoF прозрачен", "Adverse media отсутствует"],
            "key_risk_driver": "PEP-связь второй линии",
            "risk_manageable": "Да",
            "selected_risk_level": "Средний",
            "recommendation": "Одобрить",
            "edd_required": "Нет",
            "decision_rationale": "PEP второй линии, риск управляем. CDD завершён.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "approve",
            "decision": "Одобрить",
            "edd_required": "Нет",
            "cdd_status": "Complete",
            "risk_level": "Средний",
            "reject_reason_type": "NONE",
            "decisive_factor": "Ключевые элементы CDD подтверждены. PEP второй линии при отсутствии adverse media и прозрачном SoF не является блокирующим фактором.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "PEP второй линии выявлен, прямая связь отсутствует.", "category": "SCREENING", "impact": "DECISIVE", "direction": "SUPPORTS_DECISION", "comment": "Риск PEP-связи снижен отсутствием прямого статуса и негативных публикаций."},
                {"signal": "SoF подтверждён лицензионными договорами.", "category": "SOF", "impact": "HIGH", "direction": "SUPPORTS_DECISION", "comment": "Источник средств прозрачен и соответствует деятельности."},
                {"signal": "Adverse media и санкционные совпадения не выявлены.", "category": "SCREENING", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Негативный фон по всем базам отсутствует."},
            ],
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # EDD (2 кейса)
    # ──────────────────────────────────────────────────────────────────────

    {
        "case_id": "TR-003",
        "difficulty": "beginner",
        "theme": "SoF",
        "description": (
            "Польская агрологистическая компания, onboarding. "
            "UBO установлен, документы есть, но SoF по конкретной операции "
            "не подтверждён. Пробел закрываем — нужен EDD."
        ),
        "case_data": {
            "case_id": "TR-003",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "AgroTrans Polska",
            "registration_country": "Польша",
            "business_activity": "Агрологистика и транспортировка зерна",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Томаш Ковальски, 75%",
            "ultimate_controller_description": "Томаш Ковальски, директор и мажоритарный акционер",
            "client_country": "Польша",
            "counterparty_countries": ["Украина", "Румыния"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "",
            "transaction_amount": "EUR 280,000",
            "transaction_description": "Оплата за транспортировку зерна",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Расчёты по логистическим контрактам",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": [],
            "mitigating_factors_selected": ["UBO установлен", "Деятельность прозрачна"],
            "key_risk_driver": "SoF не подтверждён",
            "risk_manageable": "Да",
            "selected_risk_level": "Средний",
            "recommendation": "Эскалация",
            "edd_required": "Да",
            "decision_rationale": "SoF не подтверждён. Требуется запрос документов.",
            "missing_information_summary": "Подтверждение источника средств по операции",
        },
        "expected_output": {
            "decision_mode": "edd",
            "decision": "Эскалация",
            "edd_required": "Да",
            "cdd_status": "Incomplete",
            "risk_level": "Средний",
            "reject_reason_type": "NONE",
            "decisive_factor": "Источник средств по операции не подтверждён.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Источник средств по операции не подтверждён.", "category": "SOF", "impact": "DECISIVE", "direction": "SUPPORTS_ESCALATION", "comment": "SoF является обязательным элементом CDD. Пробел закрываем через запрос документов."},
                {"signal": "UBO установлен и подтверждён документально.", "category": "CDD", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Структура владения прозрачна, что снижает общий риск кейса."},
            ],
        },
    },

    {
        "case_id": "TR-004",
        "difficulty": "intermediate",
        "theme": "CDD Complete",
        "description": (
            "Эстонская IT-компания, onboarding. "
            "UBO есть, SoF подтверждён, но документы по операции "
            "предоставлены частично, экономический смысл частично понятен. "
            "Два незакрытых пробела — EDD, не Reject."
        ),
        "case_data": {
            "case_id": "TR-004",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "TechBridge Solutions OÜ",
            "registration_country": "Эстония",
            "business_activity": "IT-аутсорсинг и разработка",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Андрей Сааремяэ, 51%",
            "ultimate_controller_description": "Андрей Сааремяэ, CEO",
            "client_country": "Эстония",
            "counterparty_countries": ["Финляндия", "Великобритания"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Доходы от IT-контрактов",
            "transaction_amount": "EUR 95,000",
            "transaction_description": "Платёж за разработку системы от финского заказчика",
            "supporting_documents_provided": "Нет",
            "purpose_of_relationship": "Расчёты по IT-контрактам",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Частично",
            "matches_client_profile": "Частично",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": [],
            "mitigating_factors_selected": ["UBO установлен"],
            "key_risk_driver": "Документы не предоставлены, экономический смысл частично понятен",
            "risk_manageable": "Да",
            "selected_risk_level": "Средний",
            "recommendation": "Эскалация",
            "edd_required": "Да",
            "decision_rationale": "Документы отсутствуют, экономический смысл требует уточнения.",
            "missing_information_summary": "Договор с финским заказчиком, описание объёма работ",
        },
        "expected_output": {
            "decision_mode": "edd",
            "decision": "Эскалация",
            "edd_required": "Да",
            "cdd_status": "Incomplete",
            "risk_level": "Средний",
            "reject_reason_type": "NONE",
            "decisive_factor": "Подтверждающие документы по операции не предоставлены.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Подтверждающие документы по операции не предоставлены.", "category": "CDD", "impact": "DECISIVE", "direction": "SUPPORTS_ESCALATION", "comment": "Пробел закрываем через запрос договора с заказчиком."},
                {"signal": "Экономический смысл операции подтверждён частично.", "category": "ECONOMIC_RATIONALE", "impact": "HIGH", "direction": "SUPPORTS_ESCALATION", "comment": "Требуется уточнение объёма и роли клиента в сделке."},
                {"signal": "UBO установлен, SoF в целом понятен.", "category": "CDD", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Базовые элементы CDD подтверждены, что снижает риск отказа."},
            ],
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # REJECT / CDD_FAILURE (2 кейса)
    # ──────────────────────────────────────────────────────────────────────

    {
        "case_id": "TR-005",
        "difficulty": "beginner",
        "theme": "UBO",
        "description": (
            "Сейшельский холдинг, onboarding. UBO не установлен, "
            "документы по владению не предоставлены. "
            "Оффшорная структура без раскрытия. Обязательный отказ."
        ),
        "case_data": {
            "case_id": "TR-005",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "Pacifica Holdings Ltd",
            "registration_country": "Сейшельские острова",
            "business_activity": "Инвестиционный холдинг",
            "beneficial_owner_identified": "Нет",
            "beneficial_owner_details": "",
            "ultimate_controller_description": "",
            "client_country": "Сейшельские острова",
            "counterparty_countries": ["ОАЭ", "Гонконг"],
            "high_risk_jurisdiction_involved": "Да",
            "source_of_funds_summary": "",
            "transaction_amount": "USD 1,200,000",
            "transaction_description": "Входящий перевод от аффилированной структуры",
            "supporting_documents_provided": "Нет",
            "purpose_of_relationship": "Инвестиционная деятельность",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Не понятен",
            "matches_client_profile": "Нет",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": ["Оффшорная структура", "UBO не установлен"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "UBO не установлен, оффшорная юрисдикция",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "UBO не установлен. Завершение CDD невозможно.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Incomplete and cannot be completed",
            "risk_level": "Высокий",
            "reject_reason_type": "CDD_FAILURE",
            "decisive_factor": "Бенефициарный владелец не установлен и не может быть подтверждён.",
            "error_type": "NONE",
            "confidence_score": 5,
            "signal_trace": [
                {"signal": "Бенефициарный владелец не установлен и не может быть подтверждён.", "category": "CDD", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "EDD не устранит структурный барьер — раскрытие UBO в данной юрисдикции невозможно."},
                {"signal": "Высокорисковая оффшорная юрисдикция задействована.", "category": "GEOGRAPHY", "impact": "HIGH", "direction": "SUPPORTS_REJECT", "comment": "Сейшельские острова и контрагенты в ОАЭ/Гонконг усиливают риск непрозрачности."},
                {"signal": "SoF и подтверждающие документы отсутствуют.", "category": "SOF", "impact": "HIGH", "direction": "SUPPORTS_REJECT", "comment": "Совокупность дефицитов делает завершение CDD невозможным."},
            ],
        },
    },

    {
        "case_id": "TR-006",
        "difficulty": "intermediate",
        "theme": "CDD Failure",
        "description": (
            "Посредническая структура в ОАЭ (Фризона). "
            "UBO не раскрыт, SoF неизвестен, экономический смысл непонятен. "
            "Шаблонный отказ по невозможности завершить CDD."
        ),
        "case_data": {
            "case_id": "TR-006",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "Meridian Connect FZE",
            "registration_country": "ОАЭ (Фризона)",
            "business_activity": "Посреднические услуги",
            "beneficial_owner_identified": "Нет",
            "beneficial_owner_details": "",
            "ultimate_controller_description": "",
            "client_country": "ОАЭ",
            "counterparty_countries": ["Пакистан", "Египет"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "",
            "transaction_amount": "USD 340,000",
            "transaction_description": "Посреднический платёж",
            "supporting_documents_provided": "Нет",
            "purpose_of_relationship": "Посреднические расчёты",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Не понятен",
            "matches_client_profile": "Нет",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": ["UBO не установлен", "Посредническая структура"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "UBO неизвестен, SoF не подтверждён",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "UBO не установлен. Завершение CDD невозможно.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Incomplete and cannot be completed",
            "risk_level": "Высокий",
            "reject_reason_type": "CDD_FAILURE",
            "decisive_factor": "Бенефициарный владелец не установлен и не может быть подтверждён.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Бенефициарный владелец не установлен и не может быть подтверждён.", "category": "CDD", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "Критические дефициты по UBO не устранимы."},
                {"signal": "SoF и экономический смысл операции не установлены.", "category": "SOF", "impact": "HIGH", "direction": "SUPPORTS_REJECT", "comment": "Совокупность пробелов делает завершение CDD невозможным."},
            ],
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # REJECT / RISK_UNACCEPTABLE (2 кейса)
    # ──────────────────────────────────────────────────────────────────────

    {
        "case_id": "TR-007",
        "difficulty": "intermediate",
        "theme": "Adverse Media",
        "description": (
            "Испанская торговая компания, onboarding. "
            "CDD формально завершён, UBO и SoF подтверждены. "
            "Но есть негативные публикации о связях с торговым финансированием "
            "сомнительных схем. Риск неприемлем."
        ),
        "case_data": {
            "case_id": "TR-007",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "Eurogate Trading SL",
            "registration_country": "Испания",
            "business_activity": "Международная торговля",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Хуан Мартинес, 80%",
            "ultimate_controller_description": "Хуан Мартинес, единственный директор",
            "client_country": "Испания",
            "counterparty_countries": ["Марокко", "Турция"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Торговая выручка",
            "transaction_amount": "EUR 670,000",
            "transaction_description": "Платёж за партию товаров из Марокко",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Торговые расчёты",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Есть",
            "unresolved_screening_issues": "Негативные публикации о возможной вовлечённости в сомнительные посреднические схемы не сняты",
            "red_flags_selected": ["Негативные публикации"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "Неснятые негативные публикации",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "CDD завершён, но риск неприемлем из-за неснятых негативных публикаций.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Complete but risk not acceptable",
            "risk_level": "Высокий",
            "reject_reason_type": "RISK_UNACCEPTABLE",
            "decisive_factor": "Негативные публикации о возможной вовлечённости в сомнительные посреднические схемы не сняты.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Негативные публикации о возможной вовлечённости в сомнительные схемы не сняты.", "category": "SCREENING", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "Ключевой фактор отказа — неустранённый adverse media."},
                {"signal": "CDD формально завершён: UBO и SoF подтверждены.", "category": "CDD", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Наличие документации не устраняет риск-сигнал по adverse media."},
            ],
        },
    },

    {
        "case_id": "TR-008",
        "difficulty": "intermediate",
        "theme": "RISK_UNACCEPTABLE",
        "description": (
            "Австрийская финтех-компания, плановый пересмотр. "
            "CDD завершён, но в ходе пересмотра выявлены негативные публикации "
            "о связях с регуляторными нарушениями. "
            "Совокупный risk finding неприемлем."
        ),
        "case_data": {
            "case_id": "TR-008",
            "case_type": "Review",
            "client_type": "Юридическое лицо",
            "client_name": "AlphaStream GmbH",
            "registration_country": "Австрия",
            "business_activity": "Финансовые технологии",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Клаус Хофер, 55%",
            "ultimate_controller_description": "Клаус Хофер, CEO",
            "client_country": "Австрия",
            "counterparty_countries": ["Чехия", "Словакия"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Доходы от финтех-сервисов",
            "transaction_amount": "EUR 210,000",
            "transaction_description": "Операционные расчёты",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Операционные расчёты",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Есть",
            "unresolved_screening_issues": "Публикации о регуляторных нарушениях не сняты",
            "red_flags_selected": ["Негативные публикации при пересмотре"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "Новые adverse media при плановом пересмотре",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "Негативные публикации не сняты. Риск неприемлем.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Complete but risk not acceptable",
            "risk_level": "Высокий",
            "reject_reason_type": "RISK_UNACCEPTABLE",
            "decisive_factor": "Негативные публикации о регуляторных нарушениях, выявленные при пересмотре, не были сняты.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Негативные публикации о регуляторных нарушениях выявлены при пересмотре.", "category": "SCREENING", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "Новый adverse media при review — ключевой риск-сигнал."},
                {"signal": "CDD завершён: UBO, SoF и документы подтверждены.", "category": "CDD", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Завершённость CDD не снимает риск adverse media."},
            ],
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # ДОПОЛНИТЕЛЬНЫЕ: borderline и сложный approve
    # ──────────────────────────────────────────────────────────────────────

    {
        "case_id": "TR-009",
        "difficulty": "intermediate",
        "theme": "CDD Failure",
        "description": (
            "Borderline кейс: BVI-фонд, onboarding. "
            "UBO не раскрыт. Отказ кажется жёстким — "
            "но структура фонда в BVI делает раскрытие UBO структурно невозможным. "
            "Правильный ответ: Reject/CDD_FAILURE, а не EDD."
        ),
        "case_data": {
            "case_id": "TR-009",
            "case_type": "Onboarding",
            "client_type": "Юридическое лицо",
            "client_name": "Sunrise Capital Partners",
            "registration_country": "Британские Виргинские острова",
            "business_activity": "Частный инвестиционный фонд",
            "beneficial_owner_identified": "Нет",
            "beneficial_owner_details": "",
            "ultimate_controller_description": "",
            "client_country": "Британские Виргинские острова",
            "counterparty_countries": ["Каймановы острова"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "",
            "transaction_amount": "USD 5,000,000",
            "transaction_description": "Перевод инвестиционного капитала",
            "supporting_documents_provided": "Нет",
            "purpose_of_relationship": "Инвестиционные операции",
            "product_or_service_description": "Инвестиционный счёт",
            "economic_rationale_clear": "Не понятен",
            "matches_client_profile": "Нет",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Нет",
            "unresolved_screening_issues": "",
            "red_flags_selected": ["UBO не установлен", "Оффшорная юрисдикция"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "UBO структурно не может быть установлен в BVI",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "Структура BVI-фонда не предполагает раскрытия UBO. CDD невозможен.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Incomplete and cannot be completed",
            "risk_level": "Высокий",
            "reject_reason_type": "CDD_FAILURE",
            "decisive_factor": "Бенефициарный владелец не установлен и не может быть подтверждён в рамках структуры BVI-фонда.",
            "error_type": "NONE",
            "confidence_score": 5,
            "signal_trace": [
                {"signal": "Бенефициарный владелец не установлен. Структура BVI-фонда делает раскрытие невозможным.", "category": "CDD", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "EDD не устранит структурный барьер."},
                {"signal": "SoF и экономический смысл операции не установлены.", "category": "SOF", "impact": "HIGH", "direction": "SUPPORTS_REJECT", "comment": "Совокупность дефицитов подтверждает CDD_FAILURE."},
            ],
        },
    },

    {
        "case_id": "TR-010",
        "difficulty": "intermediate",
        "theme": "Adverse Media",
        "description": (
            "Триггерный кейс: венгерская портовая компания. "
            "CDD завершён, но появились новые публикации о санкционных схемах. "
            "Borderline: аналитик может склоняться к EDD, "
            "но правильный ответ — Reject/RISK_UNACCEPTABLE."
        ),
        "case_data": {
            "case_id": "TR-010",
            "case_type": "Trigger",
            "client_type": "Юридическое лицо",
            "client_name": "Danube Port Holdings",
            "registration_country": "Венгрия",
            "business_activity": "Портовая логистика",
            "beneficial_owner_identified": "Да",
            "beneficial_owner_details": "Золтан Варга, 70%",
            "ultimate_controller_description": "Золтан Варга, CEO",
            "client_country": "Венгрия",
            "counterparty_countries": ["Сербия", "Румыния"],
            "high_risk_jurisdiction_involved": "Нет",
            "source_of_funds_summary": "Доходы от портовых операций",
            "transaction_amount": "EUR 890,000",
            "transaction_description": "Расчёты за портовые услуги",
            "supporting_documents_provided": "Да",
            "purpose_of_relationship": "Расчёты за логистические услуги",
            "product_or_service_description": "Расчётный счёт",
            "economic_rationale_clear": "Понятен",
            "matches_client_profile": "Да",
            "sanctions_result": "Совпадений нет",
            "pep_result": "Нет",
            "adverse_media_result": "Есть",
            "unresolved_screening_issues": "Новые публикации о возможной вовлечённости в санкционные схемы не сняты",
            "red_flags_selected": ["Новые adverse media при триггерной проверке"],
            "mitigating_factors_selected": [],
            "key_risk_driver": "Новые публикации о санкционных схемах",
            "risk_manageable": "Нет",
            "selected_risk_level": "Высокий",
            "recommendation": "Отказать",
            "edd_required": "Нет",
            "decision_rationale": "Новые публикации о санкционных схемах. Риск неприемлем.",
            "missing_information_summary": "",
        },
        "expected_output": {
            "decision_mode": "reject",
            "decision": "Отказать",
            "edd_required": "Нет",
            "cdd_status": "Complete but risk not acceptable",
            "risk_level": "Высокий",
            "reject_reason_type": "RISK_UNACCEPTABLE",
            "decisive_factor": "Новые публикации о возможной вовлечённости в санкционные схемы не сняты.",
            "error_type": "NONE",
            "confidence_score": 4,
            "signal_trace": [
                {"signal": "Новые публикации о возможной вовлечённости в санкционные схемы не сняты.", "category": "SCREENING", "impact": "DECISIVE", "direction": "SUPPORTS_REJECT", "comment": "Ключевой триггер для отказа: неснятый adverse media."},
                {"signal": "CDD завершён: UBO и SoF подтверждены.", "category": "CDD", "impact": "MEDIUM", "direction": "MITIGATING", "comment": "Завершённость CDD не снимает риск adverse media."},
            ],
        },
    },

]


def get_all_trainer_cases() -> list:
    """Возвращает полный список тренировочных кейсов."""
    return TRAINER_CASES


def get_trainer_case_by_id(case_id: str) -> dict | None:
    """Возвращает тренировочный кейс по ID или None."""
    return next((c for c in TRAINER_CASES if c["case_id"] == case_id), None)
