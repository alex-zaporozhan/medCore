-- Wave 5 (QA_ARCH A3): ориентиры для EXPLAIN после миграции w5perf1idx_fin
-- Подставьте :clinic_id, :date_from, :date_to (timestamptz) под вашу среду.

-- 1) Доход по периоду (типичный путь ErpReportsRepository.get_visit_revenue_by_period)
EXPLAIN (ANALYZE, BUFFERS)
SELECT ft.clinic_id,
       coalesce(b.appointment_date, date(ft.happened_at)) AS visit_date,
       ft.booking_id,
       coalesce(sum(ft.amount), 0) AS total_amount
FROM financial_transactions ft
LEFT OUTER JOIN bookings b ON b.id = ft.booking_id
WHERE ft.clinic_id = '00000000-0000-0000-0000-000000000000'::uuid
  AND ft.type = 'income'
  AND ft.happened_at >= '2026-01-01'::timestamptz
  AND ft.happened_at < '2026-02-01'::timestamptz
GROUP BY ft.clinic_id, visit_date, ft.booking_id
ORDER BY visit_date;

-- Ожидание: использование частичного индекса idx_fin_tx_clinic_income_happened при фильтре type=income + happened_at.

-- 2) CRM sum по lead (sum_income_revenue_for_crm_lead)
EXPLAIN (ANALYZE, BUFFERS)
SELECT coalesce(sum(amount), 0)
FROM financial_transactions
WHERE clinic_id = '00000000-0000-0000-0000-000000000000'::uuid
  AND type = 'income'
  AND (lead_id = '00000000-0000-0000-0000-000000000000'::uuid OR booking_id = ANY (ARRAY[]::uuid[]));

-- Ожидание: idx_fin_tx_clinic_income_lead при фильтре по lead_id.

-- 3) Payroll overlap (get_visit_payroll_by_period)
EXPLAIN (ANALYZE, BUFFERS)
SELECT clinic_id, doctor_id, booking_id, period_start, period_end, coalesce(sum(amount), 0)
FROM salary_transactions
WHERE clinic_id = '00000000-0000-0000-0000-000000000000'::uuid
  AND period_start <= '2026-01-31'::date
  AND period_end >= '2026-01-01'::date
GROUP BY clinic_id, doctor_id, booking_id, period_start, period_end;
