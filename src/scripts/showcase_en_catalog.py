"""English showcase copy for video / OSS demos (not Alembic).

Imported by ``seed_multi_tenant_showcase`` and ``showcase_en_video_layer``.
Emails and slugs stay stable so existing logins keep working.
"""

from __future__ import annotations

from decimal import Decimal

SHOWCASE_PASSWORD = "ShowcaseMT2026!"

# Login emails / slugs stay stable. Display names and clinic copy are US-primary
# (Austin, Boston, Chicago) plus one French and one Italian site.
ORG_SPECS: list[dict[str, object]] = [
    {
        "key": "kazan",
        "org_name": "Brightside Dental Group",
        "clinic_name": "Brightside Dental — Austin",
        "slug": "showcase-kazan",
        "plan_slug": "start",
        "owner_email": "owner.kazan@showcase-mt.demo",
        "owner_name": "Daniel Hayes",
        "address": "410 Congress Ave, Austin, TX",
        "admins": [
            ("admin1.kazan@showcase-mt.demo", "Sarah Walsh"),
            ("admin2.kazan@showcase-mt.demo", "James Whitaker"),
        ],
        "marketers": [
            ("marketing1.kazan@showcase-mt.demo", "Emily Foster"),
            ("marketing2.kazan@showcase-mt.demo", "Ben Hale"),
        ],
        "clinicians": [
            ("doctor1.kazan@showcase-mt.demo", "Hannah Cole, DDS"),
        ],
    },
    {
        "key": "nizhny",
        "org_name": "Harbor Smile Partners",
        "clinic_name": "Harbor Smile — Boston",
        "slug": "showcase-nizhny",
        "plan_slug": "growth",
        "owner_email": "owner.nizhny@showcase-mt.demo",
        "owner_name": "Rachel Donovan",
        "address": "18 Newbury St, Boston, MA",
        "admins": [
            ("admin1.nizhny@showcase-mt.demo", "Michael Grant"),
            ("admin2.nizhny@showcase-mt.demo", "Laura Bennett"),
        ],
        "marketers": [
            ("marketing1.nizhny@showcase-mt.demo", "Chris Nolan"),
            ("marketing2.nizhny@showcase-mt.demo", "Sophie Miller"),
        ],
        "clinicians": [
            ("doctor1.nizhny@showcase-mt.demo", "Hannah Cole, DDS"),
        ],
    },
    {
        "key": "samara",
        "org_name": "Lumière Dental",
        "clinic_name": "Clinique Dentaire Lumière — Lyon",
        "slug": "showcase-samara",
        "plan_slug": "business_os",
        "owner_email": "owner.samara@showcase-mt.demo",
        "owner_name": "Julien Marchand",
        "address": "22 Rue de la République, Lyon",
        "admins": [
            ("admin1.samara@showcase-mt.demo", "Claire Dubois"),
            ("admin2.samara@showcase-mt.demo", "Antoine Moreau"),
        ],
        "marketers": [
            ("marketing1.samara@showcase-mt.demo", "Camille Laurent"),
            ("marketing2.samara@showcase-mt.demo", "Pauline Moreau"),
        ],
        "clinicians": [
            ("doctor1.samara@showcase-mt.demo", "Hannah Cole, DDS"),
        ],
    },
    {
        "key": "krasnodar",
        "org_name": "Aurora Studio Dentale",
        "clinic_name": "Studio Dentale Aurora — Milan",
        "slug": "showcase-krasnodar",
        "plan_slug": "growth",
        "owner_email": "owner.krasnodar@showcase-mt.demo",
        "owner_name": "Giulia Rossi",
        "address": "8 Via Montenapoleone, Milan",
        "admins": [
            ("admin1.krasnodar@showcase-mt.demo", "Marco Bianchi"),
            ("admin2.krasnodar@showcase-mt.demo", "Chiara Conti"),
        ],
        "marketers": [
            ("marketing1.krasnodar@showcase-mt.demo", "Luca Ferrari"),
            ("marketing2.krasnodar@showcase-mt.demo", "Elena Ricci"),
        ],
        "clinicians": [
            ("doctor1.krasnodar@showcase-mt.demo", "Hannah Cole, DDS"),
        ],
    },
    {
        "key": "rostov",
        "org_name": "Lakeshore Family Dental",
        "clinic_name": "Lakeshore Family Dental — Chicago",
        "slug": "showcase-rostov",
        "plan_slug": "start",
        "owner_email": "owner.rostov@showcase-mt.demo",
        "owner_name": "Andrew Keller",
        "address": "233 N Michigan Ave, Chicago, IL",
        "admins": [
            ("admin1.rostov@showcase-mt.demo", "Megan Brooks"),
            ("admin2.rostov@showcase-mt.demo", "Ryan Cooper"),
        ],
        "marketers": [
            ("marketing1.rostov@showcase-mt.demo", "Natalie Quinn"),
            ("marketing2.rostov@showcase-mt.demo", "David Price"),
        ],
        "clinicians": [
            ("doctor1.rostov@showcase-mt.demo", "Hannah Cole, DDS"),
        ],
    },
]

DOCTORS_TEMPLATE: list[dict[str, object]] = [
    {"full_name": "Paul Brennan, DDS", "specialization": "General dentist", "experience_years": 12},
    {"full_name": "Mary Ellis, DDS", "specialization": "Oral surgeon / implants", "experience_years": 10},
    {"full_name": "Ben Carter, DDS", "specialization": "Orthodontist", "experience_years": 8},
]

SERVICES_TEMPLATE: list[tuple[str, str, str, Decimal, int]] = [
    ("New patient exam", "therapy", "Exam and treatment plan", Decimal("1800"), 30),
    ("Professional hygiene", "hygiene", "Scaling and polish", Decimal("7200"), 60),
    ("Filling (one surface)", "therapy", "Composite restoration", Decimal("6500"), 60),
    ("Simple extraction", "surgery", "In-office extraction", Decimal("4200"), 45),
]

PATIENT_NAMES: list[str] = [
    "Noah Bennett",
    "Olivia Chen",
    "Liam Brooks",
    "Sophie Harper",
    "Ethan Baker",
    "Ava Thompson",
    "Jack Turner",
    "Mary Collins",
    "Chloe Martin",
    "Hugo Petit",
    "Sofia Greco",
    "Elise Bernard",
]

# Stable lookup markers for the ±14-day ops layer (new rows have no "Demo" prefix).
WINDOW_TASK_PREFIX_LEGACY = "Demo window:"
WINDOW_CAL_PREFIX_LEGACY = "Demo window cal:"
HUDDLE_TITLE_LEGACY = "Demo huddle: Two-week ops"
HUDDLE_TITLE = "Two-week ops"

_US_NANP_AREA = {"kazan": "512", "nizhny": "617", "rostov": "312"}


def patient_phone(org_key: str, index: int) -> str:
    """Clinic-local showcase phone (unique per clinic). US NANP 555; FR/IT national."""
    if org_key in _US_NANP_AREA:
        return f"+1{_US_NANP_AREA[org_key]}555{1000 + index:04d}"
    if org_key == "samara":
        return f"+3347201{1000 + index:04d}"
    return f"+3902801{1000 + index:04d}"

# Legacy RU / Slavic-English display names → US-primary contour (existing DBs).
DOCTOR_NAME_RU_EN: dict[str, str] = {
    "Волкова Марина Евгеньевна": "Paul Brennan, DDS",
    "Семёнов Виктор Павлович": "Mary Ellis, DDS",
    "Ларина Ольга Сергеевна": "Ben Carter, DDS",
    "Marina Volkova, DDS": "Paul Brennan, DDS",
    "Victor Semenov, DDS": "Mary Ellis, DDS",
    "Olga Larina, DDS": "Ben Carter, DDS",
    "Elena Kravtsova, DDS": "Hannah Cole, DDS",
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
    "Врач-стоматолог-терапевт": "General dentist",
    "Хирург-имплантолог": "Oral surgeon / implants",
    "Ортодонт": "Orthodontist",
}

# Overlay Alembic catalog copy (do not rewrite historical migrations).
CATALOG_PLAN_EN: dict[str, tuple[str, str]] = {
    "start": (
        "Start",
        "Single-location base: 1 clinic, up to 5 staff.",
    ),
    "growth": (
        "Growth",
        "Up to 3 clinics, up to 20 staff. AI in chats, finance, loyalty.",
    ),
    "business_os": (
        "Business OS",
        "Network up to 10 clinics: RAG, tasks, inventory, ROI, payroll.",
    ),
    "starter_rf": (
        "Start (RU region)",
        "Base + tasks — landing preset.",
    ),
}

CATALOG_OPTION_EN: dict[str, tuple[str, str | None]] = {
    "core.base": (
        "Product base",
        "Org, clinic, RBAC, schedule, basic payments",
    ),
    "tasks.kanban": ("Tasks / Kanban", None),
    "crm.pipeline": ("CRM / pipeline", None),
    "marketing.attribution": ("Marketing / attribution", None),
    "retention.bundle": ("Retention / patient return", None),
    "omni.embed.bundle": (
        "Embed widget + public perimeter",
        "Embedding bundle; API keys and webhook inbox",
    ),
    "ai.assistant.chat": ("AI assistant in chat", None),
    "ai.rag.org_kb": ("Org knowledge base (RAG)", None),
    "import.crm_v1": (
        "CRM v1 import",
        "Contacts/deals, staging per organization",
    ),
    "commerce.store_network": (
        "Store / multi-location sales",
        "Catalog option; implementation gated separately",
    ),
}
