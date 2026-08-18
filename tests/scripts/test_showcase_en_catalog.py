"""English copy catalog for multi-tenant showcase (no DB)."""

from src.scripts.showcase_en_catalog import ORG_SPECS, PATIENT_NAMES, SERVICES_TEMPLATE


def test_showcase_emails_unique_and_ascii() -> None:
    emails: list[str] = []
    slugs: list[str] = []
    for spec in ORG_SPECS:
        emails.append(str(spec["owner_email"]))
        slugs.append(str(spec["slug"]))
        for email, name in list(spec["admins"]) + list(spec["marketers"]):  # type: ignore[arg-type]
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
