"""English showcase copy for video / OSS demos (not Alembic).

Imported by ``seed_multi_tenant_showcase`` and ``showcase_en_video_layer``.
Emails and slugs stay stable so existing logins keep working.
"""

from __future__ import annotations

from decimal import Decimal

SHOWCASE_PASSWORD = "ShowcaseMT2026!"

ORG_SPECS: list[dict[str, object]] = [
    {
        "key": "kazan",
        "org_name": "Smile Plus Group",
        "clinic_name": "Smile Plus Dentistry — Kazan",
        "slug": "showcase-kazan",
        "plan_slug": "start",
        "owner_email": "owner.kazan@showcase-mt.demo",
        "owner_name": "Rafael Mukhametzhanov",
        "address": "12 Bauman St, Kazan",
        "admins": [
            ("admin1.kazan@showcase-mt.demo", "Svetlana Kirillova"),
            ("admin2.kazan@showcase-mt.demo", "Dmitry Ershov"),
        ],
        "marketers": [
            ("marketing1.kazan@showcase-mt.demo", "Alina Volkova"),
            ("marketing2.kazan@showcase-mt.demo", "Kirill Nazarov"),
        ],
    },
    {
        "key": "nizhny",
        "org_name": "Dental Pro Network",
        "clinic_name": "Dental Pro Clinic — Nizhny Novgorod",
        "slug": "showcase-nizhny",
        "plan_slug": "growth",
        "owner_email": "owner.nizhny@showcase-mt.demo",
        "owner_name": "Elena Smirnova",
        "address": "8 Bolshaya Pokrovskaya St, Nizhny Novgorod",
        "admins": [
            ("admin1.nizhny@showcase-mt.demo", "Igor Zaytsev"),
            ("admin2.nizhny@showcase-mt.demo", "Marina Frolova"),
        ],
        "marketers": [
            ("marketing1.nizhny@showcase-mt.demo", "Olga Lebedeva"),
            ("marketing2.nizhny@showcase-mt.demo", "Pavel Orlov"),
        ],
    },
    {
        "key": "samara",
        "org_name": "Family Dental Samara",
        "clinic_name": "Family Dental — Samara",
        "slug": "showcase-samara",
        "plan_slug": "business_os",
        "owner_email": "owner.samara@showcase-mt.demo",
        "owner_name": "Andrey Belov",
        "address": "45 Leningradskaya St, Samara",
        "admins": [
            ("admin1.samara@showcase-mt.demo", "Natalia Pavlova"),
            ("admin2.samara@showcase-mt.demo", "Sergey Tikhonov"),
        ],
        "marketers": [
            ("marketing1.samara@showcase-mt.demo", "Yulia Egorova"),
            ("marketing2.samara@showcase-mt.demo", "Maxim Zaytsev"),
        ],
    },
    {
        "key": "krasnodar",
        "org_name": "Implant Expert South",
        "clinic_name": "Implant Expert — Krasnodar",
        "slug": "showcase-krasnodar",
        "plan_slug": "growth",
        "owner_email": "owner.krasnodar@showcase-mt.demo",
        "owner_name": "Oksana Volkova",
        "address": "110 Krasnaya St, Krasnodar",
        "admins": [
            ("admin1.krasnodar@showcase-mt.demo", "Roman Nikitin"),
            ("admin2.krasnodar@showcase-mt.demo", "Irina Lebedeva"),
        ],
        "marketers": [
            ("marketing1.krasnodar@showcase-mt.demo", "Daria Orlova"),
            ("marketing2.krasnodar@showcase-mt.demo", "Konstantin Tarasov"),
        ],
    },
    {
        "key": "rostov",
        "org_name": "Premier Dent South",
        "clinic_name": "Premier Dent — Rostov-on-Don",
        "slug": "showcase-rostov",
        "plan_slug": "start",
        "owner_email": "owner.rostov@showcase-mt.demo",
        "owner_name": "Viktor Krylov",
        "address": "31 Bolshaya Sadovaya St, Rostov-on-Don",
        "admins": [
            ("admin1.rostov@showcase-mt.demo", "Alyona Mikhailova"),
            ("admin2.rostov@showcase-mt.demo", "Vladislav Timofeev"),
        ],
        "marketers": [
            ("marketing1.rostov@showcase-mt.demo", "Polina Guseva"),
            ("marketing2.rostov@showcase-mt.demo", "Alexey Semenov"),
        ],
    },
]

DOCTORS_TEMPLATE: list[dict[str, object]] = [
    {"full_name": "Marina Volkova, DDS", "specialization": "General dentist", "experience_years": 12},
    {"full_name": "Victor Semenov, DDS", "specialization": "Oral surgeon / implants", "experience_years": 10},
    {"full_name": "Olga Larina, DDS", "specialization": "Orthodontist", "experience_years": 8},
]

SERVICES_TEMPLATE: list[tuple[str, str, str, Decimal, int]] = [
    ("New patient exam", "therapy", "Exam and treatment plan", Decimal("1800"), 30),
    ("Professional hygiene", "hygiene", "Scaling and polish", Decimal("7200"), 60),
    ("Filling (one surface)", "therapy", "Composite restoration", Decimal("6500"), 60),
    ("Simple extraction", "surgery", "In-office extraction", Decimal("4200"), 45),
]

PATIENT_NAMES: list[str] = [
    "Ivan Kozlov",
    "Maria Sokolova",
    "Pavel Nesterov",
    "Olga Filippova",
    "Artem Gromov",
    "Tatiana Vishnevskaya",
    "Denis Morozov",
    "Ekaterina Kuznetsova",
    "Ilya Romanov",
    "Anna Smirnova",
    "Svetlana Belova",
    "Konstantin Tarasov",
]

# Legacy RU display names → English (existing Docker DBs).
DOCTOR_NAME_RU_EN: dict[str, str] = {
    "Волкова Марина Евгеньевна": "Marina Volkova, DDS",
    "Семёнов Виктор Павлович": "Victor Semenov, DDS",
    "Ларина Ольга Сергеевна": "Olga Larina, DDS",
}

SERVICE_NAME_RU_EN: dict[str, str] = {
    "Первичная консультация": "New patient exam",
    "Профессиональная гигиена": "Professional hygiene",
    "Лечение кариеса (одна поверхность)": "Filling (one surface)",
    "Удаление зуба простое": "Simple extraction",
}

SERVICE_DESC_EN: dict[str, str] = {name: desc for name, _cat, desc, _p, _d in SERVICES_TEMPLATE}

SPEC_BY_SLUG: dict[str, dict[str, object]] = {str(s["slug"]): s for s in ORG_SPECS}
SPEC_BY_OWNER_EMAIL: dict[str, dict[str, object]] = {
    str(s["owner_email"]).strip().lower(): s for s in ORG_SPECS
}

DOCTOR_SPEC_RU_EN: dict[str, str] = {
    "Стоматолог-терапевт": "General dentist",
    "Хирург-имплантолог": "Oral surgeon / implants",
    "Ортодонт": "Orthodontist",
}
