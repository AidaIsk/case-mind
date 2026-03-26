CaseMind — Case Structure v2
Общая логика

Структура кейса построена так, чтобы аналитик:

не пропускал важные факты

видел риски и пробелы

мог связать факты → анализ → решение

сформировать качественный Decision Note

1. Case Metadata

Поля:

case_id

case_date

analyst_name

case_type (Onboarding / Review / Trigger)

client_type (Individual / Legal Entity)

Зачем:
Идентификация кейса и понимание контекста проверки.

2. Client & Ownership

Поля:

client_name

registration_country

business_activity

company_age_months

digital_footprint_summary

ownership_structure_summary

beneficial_owner_identified (yes/no)

beneficial_owner_details

ultimate_controller_description

bo_gap_reason

director_details

Зачем:
Понять, кто клиент, кто им реально управляет и насколько структура прозрачна.
Выявить номинальных владельцев и скрытый контроль.

3. Geography

Поля:

client_country

counterparty_countries

intermediary_bank_countries

high_risk_jurisdiction_involved (yes/no)

geography_comments

Зачем:
Оценить географический риск, наличие оффшоров, FATF-юрисдикций и сложных маршрутов средств.

4. Funds & Transaction

Поля:

source_of_wealth_summary

source_of_funds_summary

transaction_amount

transaction_currency

transaction_description

supporting_documents_provided (yes/no)

supporting_documents_summary

funds_gaps

Зачем:
Понять происхождение средств, цель операции и наличие подтверждающих документов.
Выявить пробелы и несоответствия.

5. Economic Substance

Поля:

purpose_of_relationship

product_or_service_description

services_materiality_type (material / non-material)

services_verification_summary

economic_rationale_clear (yes/no/partly)

matches_client_profile (yes/no/partly)

unusual_structure_present (yes/no)

economic_substance_comments

Зачем:
Оценить реальный экономический смысл операции и бизнеса.
Проверить, не является ли сделка формальной или искусственной.

6. Screening

Поля:

sanctions_result

pep_result

adverse_media_result

screening_summary

unresolved_screening_issues

Зачем:
Зафиксировать результаты проверок и выявить нерешённые совпадения или риски.

7. Risk Assessment (Red Flags & Mitigants)

Поля:

red_flags_selected

suspicion_codes_suggested

mitigating_factors_selected

key_risk_driver

risk_manageable (yes/no/unclear)

alternative_explanation

Зачем:
Собрать ключевые факторы риска и смягчающие обстоятельства.
Оценить, управляем ли риск, и рассмотреть альтернативные объяснения.

8. Analyst Decision

Поля:

selected_risk_level (Low / Medium / High)

recommendation (Approve / Reject / Escalate / Insufficient Info)

edd_required (yes/no)

monitoring_actions

decision_rationale

missing_information_summary

limitations_note

Зачем:
Зафиксировать итоговое решение аналитика и обоснование.
Отразить ограничения и недостающую информацию.