# Staff directory: multitenancy, cache, RBAC scope

## Data model

- **`organizations`**: groups multiple `clinics` (enterprise / network boundary). Every clinic and admin row carries `organization_id` after migration.
- **`staff_profession_categories`**: `clinic_id` FK — categories are **never** shared across clinics. Names are free-form (independent of `business_type` / lexicon templates).
- **`admins`**: `clinic_id` remains the security boundary for JWT and data; `profession_category_id` is optional and must reference a category with the **same** `clinic_id`.

## Cross-clinic access (owner)

- JWT still encodes one `clinic_id` (home clinic).
- **Owner** may call APIs for another clinic **only** if `clinic.organization_id == admin.organization_id` and the caller has role `owner` at the home clinic (`assert_clinic_in_scope` in `src/api/v1/clinic_scope.py`).
- Non-owners cannot cross clinics; wrong org returns **404** (no tenant leakage).

## RBAC effective clinic

- RBAC endpoints accept optional query `effective_clinic_id` so an owner can manage roles/policies for a selected clinic in the UI while the JWT stays bound to the home clinic.
- Frontend passes `currentClinicId` from `AdminClinicContext` into RBAC hooks.

## PATCH сотрудника (`profession_category_id`, `employment_status`)

- Тело запроса обрабатывается по **`model_fields_set`**: в JSON должны быть только те поля, которые нужно изменить.
- Явный **`"profession_category_id": null`** снимает категорию; нельзя полагаться на «оба поля None» как на «пустой PATCH» — такой запрос отклоняется.

## Redis cache

- List GET for profession categories uses key `staff:dir:v1:pc:{clinic_id}` (see `staff_directory_cache.py`).
- Invalidation on create/update/delete of categories; toggles `staff_directory_cache_enabled` / TTL in settings.

## Tests

- `tests/api/test_admin_staff_directory.py` — CRUD, 403 for doctor, 404 for foreign clinic, session `accessible_clinic_ids`.
