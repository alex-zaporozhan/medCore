from uuid import UUID, uuid4

import pytest

from src.application.ai.tokenization import (
    BOOKING_TOKEN_RE,
    LEAD_TOKEN_RE,
    PATIENT_TOKEN_RE,
    WALLET_TOKEN_RE,
    make_booking_token,
    make_lead_token,
    make_patient_token,
    make_wallet_token,
    parse_booking_token,
    parse_lead_token,
    parse_patient_token,
    parse_wallet_token,
    detect_tokens,
    extract_token_strings,
    replace_tokens,
)


def test_make_and_parse_patient_token_round_trip():
    uid = uuid4()
    token = make_patient_token(uid)
    assert token.startswith("PATIENT#")
    parsed = parse_patient_token(token)
    assert parsed == uid


def test_make_and_parse_booking_token_round_trip():
    uid = uuid4()
    token = make_booking_token(uid)
    assert token.startswith("BOOKING#")
    parsed = parse_booking_token(token)
    assert parsed == uid


def test_make_and_parse_wallet_token_round_trip():
    uid = uuid4()
    token = make_wallet_token(uid)
    assert token.startswith("WALLET#")
    parsed = parse_wallet_token(token)
    assert parsed == uid


def test_make_and_parse_lead_token_round_trip():
    uid = uuid4()
    token = make_lead_token(uid)
    assert token.startswith("LEAD#")
    parsed = parse_lead_token(token)
    assert parsed == uid


@pytest.mark.parametrize(
    "pattern_maker",
    [
        (PATIENT_TOKEN_RE, make_patient_token),
        (BOOKING_TOKEN_RE, make_booking_token),
        (WALLET_TOKEN_RE, make_wallet_token),
        (LEAD_TOKEN_RE, make_lead_token),
    ],
)
def test_specific_token_regexes_match_valid_tokens(pattern_maker):
    pattern, maker = pattern_maker
    uid = uuid4()
    token = maker(uid)
    match = pattern.search(f"text before {token} text after")
    assert match is not None
    assert UUID(match.group("uuid")) == uid


def test_token_re_detects_multiple_tokens_in_text():
    p_id = uuid4()
    b_id = uuid4()
    text = f"Пациент {make_patient_token(p_id)} имеет запись {make_booking_token(b_id)}."

    tokens = detect_tokens(text)
    raw_tokens = {t.raw for t in tokens}

    assert make_patient_token(p_id) in raw_tokens
    assert make_booking_token(b_id) in raw_tokens

    by_prefix = {t.prefix: t.id for t in tokens}
    assert by_prefix["PATIENT"] == p_id
    assert by_prefix["BOOKING"] == b_id


def test_extract_token_strings_is_order_preserving():
    p_id = uuid4()
    b_id = uuid4()
    t1 = make_patient_token(p_id)
    t2 = make_booking_token(b_id)
    text = f"{t1} and {t2}"

    extracted = extract_token_strings(text)
    assert extracted == [t1, t2]


def test_replace_tokens_performs_simple_substitution():
    p_id = uuid4()
    original = make_patient_token(p_id)
    replacement = "PATIENT#OBFUSCATED"

    text = f"hello {original}"
    new_text = replace_tokens(text, [(original, replacement)])

    assert original not in new_text
    assert replacement in new_text


def test_parse_token_with_wrong_prefix_raises():
    uid = uuid4()
    token = make_patient_token(uid)
    with pytest.raises(ValueError):
        parse_booking_token(token)


