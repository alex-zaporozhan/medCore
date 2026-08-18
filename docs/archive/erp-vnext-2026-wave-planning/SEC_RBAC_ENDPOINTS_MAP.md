# SEC_RBAC_ENDPOINTS_MAP — чувствительные маршруты и permissions (SR1, W7)

> **Правило:** при добавлении `require_permissions` на новый маршрут — обновить эту таблицу в том же PR.  
> **Инвентарь кодов (CI gate):** `./sec_rbac_router_permissions.txt` — полный список permission-строк из `src/api/v1/routers/*.py`. После добавления роутов: `python scripts/audit_rbac_endpoints.py --write`, затем `pytest tests/application/test_sec_rbac_router_permissions_inventory.py`.  
> **Скрипт:** `python scripts/audit_rbac_endpoints.py` (отчёт), `python scripts/audit_rbac_endpoints.py --check` (проверка без записи).

| Метод | Путь (шаблон) | Permissions / примечание |
|-------|----------------|--------------------------|
| GET | `/api/v1/admin/clinics/{clinic_id}/finance/cashboxes` | `view_finance` |
| GET | `/api/v1/admin/clinics/{clinic_id}/payroll/policies` | `view_payroll` |
| GET | `/api/v1/admin/clinics/{clinic_id}/inventory/transactions` | `view_inventory` |
| GET | `/api/v1/admin/crm/leads` | `view_crm` |
| GET | `/api/v1/admin/loyalty/policy` | `view_loyalty` |
| GET | `/api/v1/admin/forms/templates` | `view_forms` |
| GET | `/api/v1/admin/attribution/summary` | `view_marketing_analytics` |
| GET | `/api/v1/admin/attribution/drill-down` | `view_marketing_analytics` |
| GET | `/api/v1/admin/tasks` | `view_tasks` |
| PUT | `/api/v1/admin/bookings/{booking_id}/complete` | `manage_finance` |
| PUT | `/api/v1/admin/bookings/{booking_id}/complete/retry` | `manage_finance` |

Расширения: ERP reports (`erp.owner_reports.read`), attribution (`attribution.reports.read`) — см. роутеры `admin_finance`, `admin_reports`, `admin_crm` и `grep require_permissions` в `src/api/v1/routers/`.
