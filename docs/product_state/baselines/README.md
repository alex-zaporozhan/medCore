# Baselines (machine-readable, не RAG-нарратив)

- **`rbac_router_permissions.txt`** — отсортированный список кодов прав из `require_permissions(...)` в админ-роутерах. Обновление: `python scripts/audit_rbac_endpoints.py --write` из корня репозитория. Проверка в CI: `tests/application/test_sec_rbac_router_permissions_inventory.py`.
