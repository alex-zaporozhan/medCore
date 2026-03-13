"""Business lexicon utilities for clinics (labels and role display)."""

from __future__ import annotations

from typing import Final

from src.application.dto.clinic_dto import BusinessLexiconRead
from src.domain.entities.clinic import Clinic


DEFAULT_BUSINESS_LEXICON: Final[dict[str, dict]] = {
    "stomatology": {
        "person_label_singular": "Пациент",
        "person_label_plural": "Пациенты",
        "staff_label_plural": "Врачи",
        "role_display": {
            "doctor": "Врач",
            "nurse": "Медсестра",
            "therapist": "Терапевт",
            "master": "Мастер",
            "barber": "Барбер",
            "stylist": "Стилист",
            "nail_master": "Мастер маникюра",
            "pedicure_master": "Мастер педикюра",
            "massage_therapist": "Массажист",
            "other": "Специалист",
        },
    },
    "clinic": {
        "person_label_singular": "Пациент",
        "person_label_plural": "Пациенты",
        "staff_label_plural": "Врачи",
        "role_display": {},
    },
    "beauty_salon": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Мастера",
        "role_display": {
            "master": "Мастер",
            "barber": "Барбер",
            "stylist": "Стилист",
            "tattoo_master": "Тату‑мастер",
            "nail_master": "Мастер маникюра",
            "pedicure_master": "Мастер педикюра",
            "massage_therapist": "Массажист",
            "therapist": "Массажист",
            "other": "Специалист",
        },
    },
    "barbershop": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Мастера",
        "role_display": {
            "barber": "Барбер",
            "master": "Мастер",
            "stylist": "Стилист",
            "tattoo_master": "Тату‑мастер",
            "massage_therapist": "Массажист",
            "therapist": "Массажист",
            "other": "Специалист",
        },
    },
    "nail_salon": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Мастера",
        "role_display": {
            "nail_master": "Мастер маникюра",
            "pedicure_master": "Мастер педикюра",
            "master": "Мастер ногтевого сервиса",
            "stylist": "Стилист",
            "other": "Специалист",
        },
    },
    "massage_salon": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Специалисты",
        "role_display": {
            "massage_therapist": "Массажист",
            "therapist": "Массажист",
            "master": "Мастер",
            "other": "Специалист",
        },
    },
    "other": {
        "person_label_singular": "Клиент",
        "person_label_plural": "Клиенты",
        "staff_label_plural": "Специалисты",
        "role_display": {
            "doctor": "Специалист",
            "nurse": "Ассистент",
            "master": "Специалист",
            "stylist": "Стилист",
            "barber": "Барбер",
            "nail_master": "Мастер маникюра",
            "pedicure_master": "Мастер педикюра",
            "massage_therapist": "Массажист",
            "therapist": "Специалист",
            "other": "Специалист",
        },
    },
}


def build_business_lexicon(clinic: Clinic) -> BusinessLexiconRead:
    """Build BusinessLexiconRead for given clinic using defaults and clinic overrides."""
    business_type = (clinic.business_type or "stomatology").lower()
    base = DEFAULT_BUSINESS_LEXICON.get(business_type, DEFAULT_BUSINESS_LEXICON["other"])

    person_label_singular = (
        clinic.person_label_singular.strip()
        if getattr(clinic, "person_label_singular", None)
        else base["person_label_singular"]
    )
    person_label_plural = (
        clinic.person_label_plural.strip()
        if getattr(clinic, "person_label_plural", None)
        else base["person_label_plural"]
    )
    staff_label_plural = (
        clinic.staff_label_plural.strip()
        if getattr(clinic, "staff_label_plural", None)
        else base["staff_label_plural"]
    )

    role_display: dict[str, str] = dict(base.get("role_display", {}))

    return BusinessLexiconRead(
        business_type=business_type,
        business_type_custom_name=getattr(clinic, "business_type_custom_name", None),
        person_label_singular=person_label_singular,
        person_label_plural=person_label_plural,
        staff_label_plural=staff_label_plural,
        role_display=role_display,
    )

