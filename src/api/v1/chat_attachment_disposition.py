"""Заголовок Content-Disposition для вложений чатов (аудио без принудительного скачивания для не-владельцев)."""


def clinic_chat_attachment_content_disposition(
    content_type: str,
    file_name: str,
    *,
    allow_audio_as_attachment: bool,
) -> str:
    name = (file_name or "file").replace('"', "'")[:200]
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct.startswith("audio/") and not allow_audio_as_attachment:
        return f'inline; filename="{name}"'
    return f'attachment; filename="{name}"'
