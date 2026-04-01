"""Localized API messages for RBAC management (Accept-Language)."""

from __future__ import annotations

import re

from src.application.rbac_matrix import SYSTEM_ROLE_CODES


def locale_from_accept_language(accept_language: str | None) -> str:
    """Return ``\"ru\"`` or ``\"en\"`` from RFC 7231 Accept-Language."""
    if not accept_language or not accept_language.strip():
        return "en"
    first = accept_language.split(",")[0].strip().lower()
    if first.startswith("ru"):
        return "ru"
    return "en"


def msg_role_code_format(locale: str) -> str:
    return {
        "ru": "Код роли: латиница в нижнем регистре, цифры и подчёркивания, начинается с буквы.",
        "en": "Role code must be lowercase latin letters, digits, and underscores; must start with a letter.",
    }[locale]


def msg_role_code_reserved(locale: str, code: str) -> str:
    return {
        "ru": f"Зарезервировано для системных ролей: {code}",
        "en": f"Reserved for system roles: {code}",
    }[locale]


def msg_role_duplicate(locale: str, code: str) -> str:
    return {
        "ru": f"Роль с кодом «{code}» уже существует в этой клинике",
        "en": f"A role with code '{code}' already exists in this clinic",
    }[locale]


def msg_unknown_permissions(locale: str, codes: list[str]) -> str:
    joined = ", ".join(sorted(codes))
    return {
        "ru": f"Неизвестные коды прав: {joined}",
        "en": f"Unknown permission codes: {joined}",
    }[locale]


def msg_delete_global_forbidden(locale: str) -> str:
    return {
        "ru": "Системные глобальные роли нельзя удалить",
        "en": "Global system roles cannot be deleted",
    }[locale]


def msg_delete_owner_forbidden(locale: str) -> str:
    return {
        "ru": "Роль owner нельзя удалить",
        "en": "The owner role cannot be deleted",
    }[locale]


def msg_delete_role_in_use(locale: str) -> str:
    return {
        "ru": "Нельзя удалить роль: к ней привязаны сотрудники. Снимите роль у сотрудников в разделе «Сотрудники».",
        "en": "Cannot delete role: staff members are still assigned. Remove the role from users first.",
    }[locale]


def validate_clinic_role_code(normalized_code: str, locale: str) -> None:
    """Raise ValueError with a localized message if invalid."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", normalized_code):
        raise ValueError(msg_role_code_format(locale))
    if normalized_code in SYSTEM_ROLE_CODES:
        raise ValueError(msg_role_code_reserved(locale, normalized_code))
