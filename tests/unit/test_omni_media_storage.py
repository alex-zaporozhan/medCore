from __future__ import annotations

import pytest

from src.application.services.omni_media_storage import (
    allowed_omni_upload_mime,
    is_omni_svg_upload,
    sniff_omni_upload_mime,
)


def test_sniff_webm_octet_stream_maps_to_audio_webm() -> None:
    assert sniff_omni_upload_mime("voice-x.webm", "application/octet-stream") == "audio/webm"
    assert allowed_omni_upload_mime("audio/webm") is True


def test_sniff_preserves_explicit_mime() -> None:
    assert sniff_omni_upload_mime("photo.png", "image/png") == "image/png"
    assert allowed_omni_upload_mime("image/png") is True


@pytest.mark.parametrize(
    "filename, content_type",
    [
        ("x.svg", "image/svg+xml"),
        ("icon.svgz", "application/octet-stream"),
        ("safe.png", "image/svg+xml"),
    ],
)
def test_svg_mime_or_suffix_not_allowed(filename: str, content_type: str) -> None:
    sniffed = sniff_omni_upload_mime(filename, content_type)
    assert allowed_omni_upload_mime(sniffed) is False


def test_sniff_does_not_map_svg_extension_to_image_mime() -> None:
    assert sniff_omni_upload_mime("x.svg", "application/octet-stream") == "application/octet-stream"


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("note.ogg", "audio/ogg"),
        ("track.mp3", "audio/mpeg"),
        ("clip.m4a", "audio/mp4"),
        ("sample.wav", "audio/wav"),
    ],
)
def test_sniff_audio_suffixes(filename: str, expected: str) -> None:
    assert sniff_omni_upload_mime(filename, "") == expected
    assert allowed_omni_upload_mime(expected) is True


def test_octet_stream_without_known_suffix_stays_denied() -> None:
    assert sniff_omni_upload_mime("unknown.bin", "application/octet-stream") == "application/octet-stream"
    assert allowed_omni_upload_mime("application/octet-stream") is False


def test_explicit_video_webm_allowed() -> None:
    assert sniff_omni_upload_mime("clip.webm", "video/webm") == "video/webm"
    assert allowed_omni_upload_mime("video/webm") is True


@pytest.mark.parametrize(
    "filename, content_type",
    [
        ("x.svg", "application/octet-stream"),
        ("icon.svgz", "application/octet-stream"),
        ("safe.png", "image/svg+xml"),
    ],
)
def test_is_omni_svg_upload_matches_upload_gate(filename: str, content_type: str) -> None:
    sniffed = sniff_omni_upload_mime(filename, content_type)
    assert is_omni_svg_upload(filename, sniffed) is True


def test_is_omni_svg_upload_allows_voice_webm() -> None:
    sniffed = sniff_omni_upload_mime("voice-x.webm", "application/octet-stream")
    assert sniffed == "audio/webm"
    assert is_omni_svg_upload("voice-x.webm", sniffed) is False
    assert allowed_omni_upload_mime(sniffed) is True
