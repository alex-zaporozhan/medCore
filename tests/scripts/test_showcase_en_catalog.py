"""English copy catalog for multi-tenant showcase (no DB)."""

from src.scripts.showcase_en_catalog import DOCTORS_TEMPLATE, ORG_SPECS, PATIENT_NAMES, SERVICES_TEMPLATE, patient_phone


def test_showcase_emails_unique_and_ascii() -> None:
    emails: list[str] = []
    slugs: list[str] = []
    for spec in ORG_SPECS:
        emails.append(str(spec["owner_email"]))
        slugs.append(str(spec["slug"]))
        staff = list(spec["admins"]) + list(spec["marketers"])  # type: ignore[arg-type]
        if spec.get("clinicians"):
            staff = staff + list(spec["clinicians"])  # type: ignore[arg-type]
        for email, name in staff:
            emails.append(str(email))
            assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in str(name)), name
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in str(spec["clinic_name"]))
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in str(spec["org_name"]))
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in str(spec["owner_name"]))
    assert len(emails) == len(set(emails))
    assert len(slugs) == len(set(slugs))
    for name, _cat, desc, _price, _dur in SERVICES_TEMPLATE:
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in name + desc)
    for pn in PATIENT_NAMES:
        assert not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in pn)


def test_display_names_are_international_us_primary() -> None:
    forbidden = (
        "volkova",
        "kravtsova",
        "semenov",
        "larina",
        "smirnova",
        "kozlov",
        "sokolova",
        "nesterov",
        "filippova",
        "gromov",
        "mukhametzhanov",
        "kirillova",
    )
    for spec in ORG_SPECS:
        parts = [
            str(spec["clinic_name"]),
            str(spec["org_name"]),
            str(spec["owner_name"]),
            str(spec["address"]),
        ]
        staff = list(spec["admins"]) + list(spec["marketers"])  # type: ignore[arg-type]
        if spec.get("clinicians"):
            staff = staff + list(spec["clinicians"])  # type: ignore[arg-type]
        for _email, name in staff:
            parts.append(str(name))
        hay = " ".join(parts).lower()
        for bad in forbidden:
            assert bad not in hay, f"{bad} in {spec['key']}"
    chair = {str(d["full_name"]) for d in DOCTORS_TEMPLATE}
    assert "Paul Brennan, DDS" in chair
    assert "Mary Ellis, DDS" in chair
    assert "Ben Carter, DDS" in chair
    assert "Hannah Cole, DDS" in {str(c[1]) for s in ORG_SPECS for c in (s.get("clinicians") or [])}
    assert "Noah Bennett" in PATIENT_NAMES
    us_keys = {"kazan", "nizhny", "rostov"}
    for spec in ORG_SPECS:
        if spec["key"] in us_keys:
            assert ", TX" in str(spec["address"]) or ", MA" in str(spec["address"]) or ", IL" in str(spec["address"])


def test_patient_phones_match_clinic_contour() -> None:
    seen: set[str] = set()
    for spec in ORG_SPECS:
        key = str(spec["key"])
        for i, _name in enumerate(PATIENT_NAMES):
            phone = patient_phone(key, i)
            assert phone not in seen
            seen.add(phone)
            if key in {"kazan", "nizhny", "rostov"}:
                assert phone.startswith("+1")
                assert "555" in phone
            elif key == "samara":
                assert phone.startswith("+33")
            else:
                assert phone.startswith("+39")
