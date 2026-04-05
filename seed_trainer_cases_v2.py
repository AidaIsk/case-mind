# seed_trainer_cases_v2.py
# Добавляет / обновляет 10 калиброванных тренировочных кейсов
# из Калиброванного кейс-пака v2 (ru_06_case_pack.docx).
#
# Запуск: python3 seed_trainer_cases_v2.py
# Идемпотентен: повторный запуск обновляет кейсы, не дублирует.
#
# FIELD MAPPING (поля из ТЗ → существующая структура trainer_cases):
#   case_id               → tc["case_id"]                    (уже есть)
#   title_user            → tc["title_user"]                 (уже есть)
#   description_user      → tc["description_user"]           (уже есть)
#   documents_provided    → tc["documents_provided"]         (уже есть)
#   additional_observations → tc["questions_or_conflict"]    (переиспользуем; UI показывает
#                                                             как «Дополнительные наблюдения»)
#   question_to_analyst   → встраивается в конец description_user
#                           (UI не выводит его отдельно, отдельного поля нет)
#   expected_decision     → expected_output["decision_mode"] (уже есть)
#   expected_cdd_status   → expected_output["cdd_status"]    (уже есть)
#   reject_reason_type    → expected_output["reject_reason_type"] (уже есть)
#   decisive_factor       → expected_output["decisive_factor"] (уже есть)
#   key_signals           → expected_output["signal_trace"]  (уже есть)
#   common_mistake        → tc["typical_mistake"]            (уже есть)
#   rationale_gold_std    → tc["gold_standard"]              (уже есть)
#   ideal_decision_note   → tc["sample_note"]                (уже есть)
#   difficulty            → tc["difficulty"]                 (уже есть)

import json
import os

DATA_DIR     = "data"
TRAINER_FILE = os.path.join(DATA_DIR, "trainer_cases.json")
os.makedirs(DATA_DIR, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────

def _sig(signal: str, impact: str = "HIGH", direction: str = "SUPPORTS_DECISION") -> dict:
    return {"signal": signal, "category": "OTHER",
            "impact": impact, "direction": direction, "comment": ""}


def _build(
    *, case_id, title_user, description_user, additional_obs,
    question_to_analyst, documents_provided,
    # case_data
    client_name, client_type, registration_country, business_activity, case_type,
    ubo, sof, docs, econ_rationale, high_risk_geo, pep_result, adverse_media,
    unresolved_issues,
    # expected_output
    decision_mode, cdd_status, reject_reason_type, risk_level,
    decisive_factor, signal_trace,
    # meta
    common_mistake="", rationale_gold_std="", ideal_decision_note="",
    difficulty="intermediate",
) -> dict:

    _label = {"approve": "Одобрить", "edd": "Эскалация", "reject": "Отказать"}
    edd_required = "Да" if decision_mode == "edd" else "Нет"

    return {
        "case_id":       case_id,
        "title_user":    title_user,
        # question встраивается в description; отдельного поля в схеме нет
        "description_user": f"{description_user}\n\n*Вопрос аналитику:* {question_to_analyst}",
        "questions_or_conflict": additional_obs,   # → «Дополнительные наблюдения» в UI
        "documents_provided":    documents_provided,
        "difficulty":            difficulty,
        "typical_mistake":       common_mistake,
        "gold_standard":         rationale_gold_std,
        "sample_note":           ideal_decision_note,
        "case_data": {
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
            "source_of_funds_summary":         "Подтверждён" if sof == "Да" else "",
            "transaction_amount":              "",
            "transaction_description":         "",
            "supporting_documents_provided":   docs,
            "purpose_of_relationship":         "",
            "product_or_service_description":  "",
            "economic_rationale_clear":        econ_rationale,
            "matches_client_profile":          "Да",
            "sanctions_result":                "Совпадений нет",
            "pep_result":                      pep_result,
            "adverse_media_result":            adverse_media,
            "unresolved_screening_issues":     unresolved_issues,
            "red_flags_selected":              [],
            "mitigating_factors_selected":     [],
            "key_risk_driver":                 decisive_factor,
            "risk_manageable":                 "Да" if decision_mode == "approve" else "Нет",
            "selected_risk_level":             risk_level,
            "recommendation":                  _label[decision_mode],
            "edd_required":                    edd_required,
            "decision_rationale":              decisive_factor,
            "missing_information_summary":     "",
        },
        "expected_output": {
            "decision_mode":      decision_mode,
            "decision":           _label[decision_mode],
            "edd_required":       edd_required,
            "cdd_status":         cdd_status,
            "risk_level":         risk_level,
            "reject_reason_type": reject_reason_type,
            "decisive_factor":    decisive_factor,
            "signal_trace":       signal_trace,
        },
    }


# ── 10 кейсов из ru_06_case_pack v2 ─────────────────────────────────────

NEW_CASES = [

    _build(
        case_id="KM-KZ-001",
        title_user="ИТ-стартап в МФЦА",
        description_user=(
            "В банк обратилась компания, недавно зарегистрированная в МФЦА. "
            "Основной вид деятельности — разработка ПО. "
            "Бенефициар — гражданин РК с опытом работы в крупных международных ИТ-корпорациях."
        ),
        additional_obs=(
            "Офис компании находится в коворкинге МФЦА. "
            "Профиль деятельности логичен для данной юрисдикции."
        ),
        question_to_analyst="Оцените полноту CDD и приемлемость риска для данного клиента.",
        documents_provided=[
            "Сертификат регистрации МФЦА", "Устав",
            "Паспорт UBO", "Выписка с личного счёта бенефициара за 2 года",
        ],
        client_name="МФЦА ИТ-стартап", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Разработка ПО",
        case_type="Onboarding", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет", unresolved_issues="",
        decision_mode="approve", cdd_status="Complete",
        reject_reason_type="NONE", risk_level="Низкий",
        decisive_factor=(
            "Личность бенефициара установлена, SoF подтверждён предыдущим доходом "
            "от работы в международном секторе, структура владения прозрачна."
        ),
        signal_trace=[
            _sig("Прозрачная структура владения: единственный UBO установлен и верифицирован",
                 "DECISIVE", "SUPPORTS_DECISION"),
            _sig("SoF подтверждён: личные накопления от работы в международных ИТ-компаниях",
                 "HIGH", "SUPPORTS_DECISION"),
            _sig("Экономическое обоснование регистрации в МФЦА соответствует профилю бенефициара",
                 "HIGH", "SUPPORTS_DECISION"),
        ],
        common_mistake="Излишняя осторожность из-за отсутствия у компании финансовой истории (стартап).",
        rationale_gold_std=(
            "Кейс демонстрирует принцип «приоритета сути над формой»: отсутствие истории операций "
            "перекрывается прозрачным SoF бенефициара и логикой бизнеса."
        ),
        ideal_decision_note=(
            "Клиент: стартап в МФЦА, UBO — ИТ-специалист с подтверждённым легальным доходом. "
            "CDD завершён в полном объёме. Риск приемлем: источник средств на запуск бизнеса "
            "(личные накопления) прозрачен.\n\n"
            "Challenger View: можно было бы запросить EDD из-за отсутствия финансовой истории "
            "компании. Однако прозрачность SoF бенефициара и логика регистрации в МФЦА достаточны "
            "для Approve — дополнительный запрос документов был бы избыточным комплаенсом."
        ),
        difficulty="beginner",
    ),

    _build(
        case_id="KM-KZ-002",
        title_user="Поставка оборудования для агросектора",
        description_user=(
            "ТОО занимается импортом сельскохозяйственной техники из Европы. "
            "При периодическом обзоре обнаружена транзакция на крупную сумму "
            "в пользу нового поставщика."
        ),
        additional_obs=(
            "В инвойсе указаны банковские реквизиты поставщика, отличные от указанных в контракте. "
            "Поставщик является новым контрагентом без истории операций с клиентом."
        ),
        question_to_analyst=(
            "Определите необходимые действия в связи с выявленным расхождением в реквизитах."
        ),
        documents_provided=["Контракт", "Инвойс", "Транспортные накладные"],
        client_name="АгроИмпорт ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Импорт сельхозтехники",
        case_type="Review", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="Расхождение платёжных реквизитов в контракте и инвойсе не подтверждено.",
        decision_mode="edd", cdd_status="Incomplete",
        reject_reason_type="NONE", risk_level="Средний",
        decisive_factor=(
            "Несоответствие платёжных реквизитов в контракте и инвойсе требует "
            "дополнительного подтверждения легитимности изменений до проведения платежа."
        ),
        signal_trace=[
            _sig("Платёжные реквизиты в инвойсе отличаются от реквизитов в подписанном контракте",
                 "DECISIVE", "SUPPORTS_ESCALATION"),
            _sig("Поставщик — новый контрагент без истории операций с клиентом",
                 "HIGH", "SUPPORTS_ESCALATION"),
            _sig("Сумма платежа значительна и является разовой транзакцией",
                 "HIGH", "SUPPORTS_ESCALATION"),
        ],
        common_mistake=(
            "Одобрение платежа на основании того, что техника физически прибыла в РК "
            "(игнорирование риска перевода средств ненадлежащему получателю)."
        ),
        rationale_gold_std=(
            "Ситуация требует EDD: выявлен сигнал возможного перенаправления платежа, "
            "характерного для схем легализации."
        ),
        ideal_decision_note=(
            "Клиент: действующее ТОО, регулярный клиент банка. "
            "Кейс: мониторинг транзакции по импортному контракту.\n\n"
            "Что установлено: контракт подписан, транспортные накладные предоставлены, "
            "товар поступил. Поставщик — новый контрагент.\n\n"
            "Что вызывает вопросы: реквизиты в инвойсе отличаются от реквизитов в контракте. "
            "Клиент объяснил это сменой счёта поставщиком, письменного подтверждения нет.\n\n"
            "Решение: EDD. CDD не завершён — необходимо письменное подтверждение смены реквизитов.\n\n"
            "Challenger View: можно было бы рассмотреть Approve, поскольку товар физически прибыл. "
            "Однако физическая поставка не снимает риск того, что оплата уйдёт ненадлежащему "
            "получателю. До верификации реквизитов платёж проведён быть не может."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-003",
        title_user="Логистическая цепочка с «матрёшкой»",
        description_user=(
            "Заявка на открытие счёта от логистической компании. "
            "В структуре собственности — цепочка из трёх ТОО, "
            "конечным владельцем которой является оффшорная компания."
        ),
        additional_obs=(
            "Директор — наёмный менеджер без опыта в логистике. "
            "Адрес регистрации совпадает с адресом ещё 50 компаний."
        ),
        question_to_analyst="Оцените структуру владения и прозрачность бизнеса.",
        documents_provided=[
            "Учредительные документы ТОО",
            "Сертификат инкорпорации оффшорной компании",
        ],
        client_name="Логистик-Матрёшка ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Логистика",
        case_type="Onboarding", ubo="Нет", sof="Нет", docs="Частично",
        econ_rationale="Не понятен", high_risk_geo="Да", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="UBO не установлен из-за сложной офшорной цепочки владения.",
        decision_mode="reject", cdd_status="Incomplete and cannot be completed",
        reject_reason_type="CDD_FAILURE", risk_level="Высокий",
        decisive_factor=(
            "Структурный барьер в определении UBO: многослойная цепочка юридических лиц "
            "и адрес массовой регистрации указывают на намеренное сокрытие, а не технический пробел."
        ),
        signal_trace=[
            _sig("Сложная структура владения: три ТОО + офшор без раскрытого бенефициара",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Адрес массовой регистрации: совпадает с 50+ компаниями",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Признаки номинального директора: наёмный менеджер без отраслевого опыта",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake=(
            "Попытка запустить EDD и запросить паспорт директора офшора "
            "(игнорирование структурного характера проблемы)."
        ),
        rationale_gold_std=(
            "Кейс учит отличать «устранимые пробелы» от намеренного сокрытия через сложные структуры."
        ),
        ideal_decision_note=(
            "Reject: CDD Failure. Использование цепочки ТОО и офшора в сочетании с адресом "
            "массовой регистрации указывает на оболочечную структуру для сокрытия UBO. "
            "EDD структурный барьер не устранит."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-004",
        title_user="Экспорт зерна и PEP",
        description_user=(
            "Крупный экспортёр зерна. В ходе проверки выяснилось, что один из акционеров (20%) "
            "является близким родственником бывшего высокопоставленного чиновника."
        ),
        additional_obs=(
            "Профильные СМИ связывали компанию с коррупционными скандалами "
            "по распределению госсубсидий."
        ),
        question_to_analyst="Оцените риски, связанные с репутацией и статусом акционера.",
        documents_provided=[
            "Списки акционеров", "Финансовая отчётность за 3 года", "Аудиторское заключение",
        ],
        client_name="КазЗерноЭкспорт ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Экспорт зерна",
        case_type="Review", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Нет",
        pep_result="Связан с PEP (акционер 20%)", adverse_media="Есть",
        unresolved_issues="Негативные публикации о связи с хищением госсубсидий не сняты.",
        decision_mode="reject", cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE", risk_level="Высокий",
        decisive_factor=(
            "Риск-профиль превышает риск-аппетит банка: подтверждён серьёзный негативный медиа-фон "
            "о связи компании с хищением госсубсидий при наличии PEP-связи акционера."
        ),
        signal_trace=[
            _sig("PEP-связь акционера (20%) — близкий родственник бывшего высокопоставленного чиновника",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Серьёзный негативный медиа-фон: публикации о хищениях госсубсидий",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Несоответствие масштаба бизнеса активам акционера",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake=(
            "Предложение закрыть глаза на 20% акций, поскольку это ниже порога 25% "
            "(игнорирование PEP-фактора и репутации)."
        ),
        rationale_gold_std="Кейс учит, что даже при полном CDD риск может быть неприемлем по существу.",
        ideal_decision_note=(
            "Reject: Unacceptable Risk. Связь акционера с PEP и наличие медиа-фактов о хищении "
            "госсубсидий создают критический риск вовлечения банка в легализацию доходов от коррупции."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-005",
        title_user="Оптовая торговля стройматериалами",
        description_user=(
            "Действующее ТОО. Оптовые продажи цемента и арматуры. "
            "Офис и склад проверены банком при выезде."
        ),
        additional_obs=(
            "Значительная часть расчётов с покупателями планируется в наличной форме. "
            "Выезд на склад подтвердил наличие персонала и товарных остатков."
        ),
        question_to_analyst=(
            "Оцените экономическую реальность и профиль рисков по операциям с наличностью."
        ),
        documents_provided=[
            "Бухгалтерский баланс", "Договоры аренды склада",
            "Контракты с заводами-производителями в РК",
        ],
        client_name="СтройОпт ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Оптовая торговля стройматериалами",
        case_type="Review", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет", unresolved_issues="",
        decision_mode="approve", cdd_status="Complete",
        reject_reason_type="NONE", risk_level="Средний",
        decisive_factor=(
            "Бизнес-модель подтверждена физическим наличием активов и прямыми контрактами "
            "с производителями; риск наличности управляем через мониторинг оборотов."
        ),
        signal_trace=[
            _sig("Реальное наличие склада и персонала подтверждено при физическом выезде банка",
                 "DECISIVE", "SUPPORTS_DECISION"),
            _sig("Прозрачный профиль контрагентов: прямые контракты с казахстанскими заводами",
                 "HIGH", "SUPPORTS_DECISION"),
            _sig("SoF верифицирован: выручка от продаж подтверждена накладными и балансом",
                 "HIGH", "SUPPORTS_DECISION"),
        ],
        common_mistake="Автоматический отказ из-за планируемых операций с наличностью.",
        rationale_gold_std=(
            "Наличные расчёты характерны для данного сектора в РК. "
            "При подтверждённой экономической реальности они не являются индикатором легализации."
        ),
        ideal_decision_note=(
            "Клиент: действующее ТОО, оптовая торговля стройматериалами. CDD завершён.\n\n"
            "Что установлено: склад, персонал и товары подтверждены физически при выезде банка. "
            "Контракты с казахстанскими заводами предоставлены. SoF верифицирован через баланс.\n\n"
            "Что вызывает вопросы: планируемые наличные расчёты с покупателями.\n\n"
            "Решение: Approve. Наличность в данном секторе не является индикатором легализации "
            "при подтверждённом экономическом смысле. Риск управляем через мониторинг.\n\n"
            "Challenger View: риск наличных расчётов мог бы обосновать EDD. Однако бизнес-модель "
            "верифицирована физически, контрагенты прозрачны. Запрос дополнительных документов "
            "был бы избыточным комплаенсом."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-006",
        title_user="Консалтинг без адреса",
        description_user=(
            "ТОО зарегистрировано месяц назад. Уставный капитал — 100 МРП. "
            "Единственный владелец — молодой человек (21 год)."
        ),
        additional_obs=(
            "При звонке по юридическому адресу выяснилось, что компания там не находится "
            "и сотрудники арендодателя о ней не слышали."
        ),
        question_to_analyst=(
            "Проанализируйте адрес регистрации и соответствие профиля UBO заявленному бизнесу."
        ),
        documents_provided=["Устав", "Договор аренды «виртуального офиса»"],
        client_name="КонсалтГрупп ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Консалтинг",
        case_type="Onboarding", ubo="Да", sof="Нет", docs="Частично",
        econ_rationale="Не понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="Адрес регистрации фиктивен — подтверждено при проверке.",
        decision_mode="reject", cdd_status="Incomplete and cannot be completed",
        reject_reason_type="CDD_FAILURE", risk_level="Высокий",
        decisive_factor=(
            "Отсутствие физического присутствия по адресу регистрации и признаки использования «номинала» "
            "создают структурный барьер для завершения CDD."
        ),
        signal_trace=[
            _sig("Фактическое отсутствие физического офиса: адрес регистрации недостоверен (подтверждено при звонке)",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Аномальный возраст бенефициара (21 год) для заявленного консалтинга",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Использование виртуального адреса без бизнес-обоснования",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake=(
            "Запрос диплома юриста у бенефициара (EDD) вместо признания факта отсутствия реального офиса."
        ),
        rationale_gold_std="Кейс фокусируется на индикаторах оболочечных компаний.",
        ideal_decision_note=(
            "Reject: CDD Failure. Компания имеет признаки оболочки: адрес регистрации фиктивен, "
            "профиль бенефициара не соответствует сложности заявленных услуг."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-007",
        title_user="Госзакупки и офшорная задолженность",
        description_user=(
            "Компания получает значительные средства по госзакупкам. "
            "Анализ показал, что большая часть прибыли уходит в виде "
            "возврата займа компании из Белиза."
        ),
        additional_obs="Заём выдан под 0% годовых без залога.",
        question_to_analyst="Оцените условия займа и направление движения денежных средств.",
        documents_provided=["Договор займа", "График платежей", "Акты выполненных работ"],
        client_name="СтройГосПодряд ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Строительство (госзакупки)",
        case_type="Review", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Да", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="Беспроцентный заём от офшора без залога не имеет коммерческой логики.",
        decision_mode="reject", cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE", risk_level="Высокий",
        decisive_factor=(
            "Использование фиктивных долговых инструментов (беспроцентный заём от офшора) "
            "для вывода бюджетных средств указывает на схему легализации."
        ),
        signal_trace=[
            _sig("Заём от нефинансовой офшорной организации без залога и под 0%",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Транзакции в офшорную юрисдикцию (Белиз) без экономического смысла",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Источник средств — бюджетные выплаты по госзакупкам",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake=(
            "Одобрение на основании того, что компания реально строит объекты "
            "(игнорирование схемы вывода прибыли)."
        ),
        rationale_gold_std="Кейс учит выявлять схемы «round robin» и фиктивные займы.",
        ideal_decision_note=(
            "Reject: Unacceptable Risk. Финансовая схема (вывод бюджетных средств через "
            "беспроцентные займы в Белиз) соответствует типологиям профессионального отмывания денег."
        ),
        difficulty="advanced",
    ),

    _build(
        case_id="KM-KZ-008",
        title_user="Импорт электроники (TBML)",
        description_user=(
            "ТОО закупает партию смартфонов у посредника в ОАЭ. "
            "Цена в инвойсе в два раза выше рыночной."
        ),
        additional_obs="Компания-посредник в ОАЭ зарегистрирована 3 месяца назад.",
        question_to_analyst="Сравните цену в документах с рыночными показателями и оцените риск.",
        documents_provided=["Инвойс", "Таможенная декларация", "Прайс-лист"],
        client_name="ТехноИмпорт ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Импорт электроники",
        case_type="Onboarding", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Не понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="Цена инвойса вдвое превышает рыночные котировки без объяснения.",
        decision_mode="reject", cdd_status="Complete but risk not acceptable",
        reject_reason_type="RISK_UNACCEPTABLE", risk_level="Высокий",
        decisive_factor=(
            "Явные признаки TBML через завышение стоимости товара (over-invoicing) "
            "для незаконного вывода валюты."
        ),
        signal_trace=[
            _sig("Цена инвойса вдвое выше рыночных котировок на аналогичные смартфоны",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Новый контрагент-посредник в ОАЭ без истории поставок (3 месяца)",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Высоколиквидный товар (электроника) — классический инструмент TBML",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake="Запрос технического описания смартфонов (игнорирование ценового индикатора).",
        rationale_gold_std=(
            "Кейс фокусируется на выявлении манипуляций с торговым ценообразованием (TBML)."
        ),
        ideal_decision_note=(
            "Reject: Unacceptable Risk. Двукратное завышение цены импорта указывает на использование "
            "торговых операций для скрытого вывода капитала."
        ),
        difficulty="advanced",
    ),

    _build(
        case_id="KM-KZ-009",
        title_user="Промышленное производство — смена UBO",
        description_user=(
            "Крупный завод в Карагандинской области. Клиент банка 10 лет. "
            "В этом году сменился UBO (продажа бизнеса другому холдингу)."
        ),
        additional_obs=(
            "Новый владелец — прозрачный инвестиционный фонд. "
            "Деятельность завода стабильна, персонал сохранён."
        ),
        question_to_analyst="Оцените риск смены собственника.",
        documents_provided=[
            "Договор купли-продажи долей", "Аудит нового холдинга",
            "Подтверждение SoF нового владельца",
        ],
        client_name="КарагандыМеталл АО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Промышленное производство",
        case_type="Review", ubo="Да", sof="Да", docs="Да",
        econ_rationale="Понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет", unresolved_issues="",
        decision_mode="approve", cdd_status="Complete",
        reject_reason_type="NONE", risk_level="Низкий",
        decisive_factor=(
            "Легитимность смены собственника подтверждена, SoF верифицирован, "
            "экономическая деятельность завода сохранена."
        ),
        signal_trace=[
            _sig("SoF нового владельца верифицирован: средства от инвестиционной деятельности фонда",
                 "DECISIVE", "SUPPORTS_DECISION"),
            _sig("Сохранение персонала и профиля деятельности подтверждает операционную непрерывность",
                 "HIGH", "SUPPORTS_DECISION"),
            _sig("Десятилетняя положительная история отношений с банком без признаков аномалий",
                 "HIGH", "SUPPORTS_DECISION"),
        ],
        common_mistake=(
            "Запрос данных по всем дочерним компаниям фонда без необходимости (избыточный комплаенс)."
        ),
        rationale_gold_std="Смена собственника при прозрачной сделке не является риском сама по себе.",
        ideal_decision_note=(
            "Клиент: крупный завод, Карагандинская область, клиент банка 10 лет. "
            "Кейс: пересмотр в связи со сменой UBO.\n\n"
            "Что установлено: договор купли-продажи долей предоставлен; аудит нового холдинга проведён "
            "независимым аудитором; SoF нового владельца верифицирован — средства от инвестфонда. "
            "Персонал завода сохранён, профиль деятельности не изменился.\n\n"
            "Что вызывает вопросы: смена UBO — триггер для обновлённой проверки.\n\n"
            "Решение: Approve. CDD завершён, профиль риска — низкий.\n\n"
            "Challenger View: смена UBO могла бы обосновать EDD — запрос дополнительных документов "
            "по структуре фонда. Однако все материально значимые элементы CDD подтверждены. "
            "Запрос сведений о дочерних компаниях фонда, не являющихся стороной сделки, "
            "не несёт пропорциональной аналитической ценности."
        ),
        difficulty="intermediate",
    ),

    _build(
        case_id="KM-KZ-010",
        title_user="Угольная торговля и номиналы",
        description_user=(
            "Компания подала заявку на экспорт угля. "
            "Акционер — номинальное лицо, действующее по доверенности "
            "от лица, имя которого не раскрывается."
        ),
        additional_obs=(
            "Акционер не может ответить на вопросы о деталях контрактов и логистике."
        ),
        question_to_analyst="Оцените роль акционера и прозрачность структуры управления.",
        documents_provided=["Доверенность", "Устав", "Паспорт акционера"],
        client_name="КарбонТрейд ТОО", client_type="Юридическое лицо",
        registration_country="Казахстан", business_activity="Экспорт угля",
        case_type="Onboarding", ubo="Нет", sof="Нет", docs="Частично",
        econ_rationale="Не понятен", high_risk_geo="Нет", pep_result="Нет",
        adverse_media="Нет",
        unresolved_issues="UBO прямо отказался раскрыться — намеренное сокрытие.",
        decision_mode="reject", cdd_status="Incomplete and cannot be completed",
        reject_reason_type="CDD_FAILURE", risk_level="Высокий",
        decisive_factor=(
            "Использование номинального акционера и прямой отказ раскрыть личность реального "
            "распорядителя создают непреодолимый структурный барьер для завершения CDD."
        ),
        signal_trace=[
            _sig("Номинальный акционер по доверенности от нераскрытого лица — прямое сокрытие UBO",
                 "DECISIVE", "SUPPORTS_REJECT"),
            _sig("Некомпетентность акционера в вопросах бизнеса: не может ответить на операционные вопросы",
                 "HIGH", "SUPPORTS_REJECT"),
            _sig("Прямой отказ раскрыть личность реального владельца бизнеса",
                 "HIGH", "SUPPORTS_REJECT"),
        ],
        common_mistake="Попытка оценить контракт на уголь, игнорируя факт сокрытия владельца.",
        rationale_gold_std=(
            "Закрепление понятия «скрытого бенефициара» как критического барьера для CDD."
        ),
        ideal_decision_note=(
            "Reject: CDD Failure. Установлено использование номинального владельца. "
            "Личность реального распорядителя скрыта — структурный барьер для завершения CDD. "
            "EDD его не устранит."
        ),
        difficulty="advanced",
    ),
]


# ── I/O ──────────────────────────────────────────────────────────────────

def _load() -> list:
    if not os.path.exists(TRAINER_FILE):
        return []
    try:
        with open(TRAINER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(cases: list) -> None:
    with open(TRAINER_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)


def main() -> None:
    existing = _load()
    index = {c["case_id"]: i for i, c in enumerate(existing)}

    added = updated = 0
    for nc in NEW_CASES:
        cid = nc["case_id"]
        if cid in index:
            existing[index[cid]] = nc
            updated += 1
        else:
            existing.append(nc)
            index[cid] = len(existing) - 1
            added += 1

    _save(existing)
    print(f"trainer_cases.json: добавлено {added}, обновлено {updated}. Всего: {len(existing)}")
    for c in NEW_CASES:
        eo = c["expected_output"]
        print(f"  {c['case_id']:12} | {eo['decision_mode']:7} | "
              f"rr={eo['reject_reason_type']:17} | {c['difficulty']}")


if __name__ == "__main__":
    main()
