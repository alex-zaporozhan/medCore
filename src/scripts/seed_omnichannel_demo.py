"""Seed demo omnichannel chats/messages for screenshots and local testing.

Creates several omnichannel contacts/chats and inbound messages that will appear
in /admin/omni-chat, emulating different providers (TELEGRAM, WHATSAPP, VK,
WEBCHAT, EMAIL).

Run:
  poetry run python -m src.scripts.seed_omnichannel_demo

Assumptions:
- There is at least one clinic in DB (seed_demo_data already creates it).
- Omnichannel entities and IntegrationGatewayService are migrated.
"""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic  # noqa: F401 - ensure 'clinics' table is in metadata
from src.domain.entities.omnichannel_message import Message
from src.application.dto.omnichannel_dto import NormalizedMessageDTO
from src.application.services.integration_gateway_service import IntegrationGatewayService
from src.infrastructure.database.base import AsyncSessionLocal


async def seed_omni_demo() -> None:
  async with AsyncSessionLocal() as session:  # type: AsyncSession
    # Prefer clinic of demo admin so chats are visible under admin@example.com in UI
    result = await session.execute(
      select(AdminUser).where(
        AdminUser.email == "admin@example.com",
        AdminUser.deleted_at.is_(None),
      ).limit(1)
    )
    admin = result.scalar_one_or_none()
    if admin is None:
      raise RuntimeError("Demo admin (admin@example.com) not found; run seed_demo_data first.")

    business_account_id = admin.clinic_id

    gateway = IntegrationGatewayService(
      session=session,
      business_account_id=business_account_id,
    )

    now = datetime.utcnow()

    demos: list[tuple[NormalizedMessageDTO, str, str | None]] = [
      (
        NormalizedMessageDTO(
          provider="TELEGRAM",
          external_message_id="tg-demo-1",
          from_id="10001",
          chat_external_id="10001",
          text=(
            "Добрый день, у меня не работает WhatsApp, подскажите, пожалуйста, "
            "можем ли мы перенести сегодняшнюю запись на 19:00?"
          ),
          timestamp=now - timedelta(minutes=15),
        ),
        "telegram_user_id",
        "Елена Вавилова",
      ),
      (
        NormalizedMessageDTO(
          provider="WHATSAPP",
          external_message_id="wa-demo-1",
          from_id="+79990001111",
          chat_external_id="+79990001111",
          text=(
            "Добрый день, можете перенести запись на сегодня на 19:00? Не успеваю!"
          ),
          timestamp=now - timedelta(minutes=12),
        ),
        "whatsapp_user_id",
        "Максим Соколов",
      ),
      (
        NormalizedMessageDTO(
          provider="VK",
          external_message_id="vk-demo-1",
          from_id="vk_demo_user_1",
          chat_external_id="vk_chat_1",
          text="Здравствуйте! Делаете ли вы лечение под наркозом?",
          timestamp=now - timedelta(minutes=9),
        ),
        "vk_user_id",
        "Валерий Павлов",
      ),
      (
        NormalizedMessageDTO(
          provider="WEBCHAT",
          external_message_id="web-demo-1",
          from_id="web_anonymous_1",
          chat_external_id="web_anonymous_1",
          text="Привет! Хочу записаться на консультацию сегодня вечером.",
          timestamp=now - timedelta(minutes=6),
        ),
        "webchat_user_id",
        "Гость с сайта",
      ),
      (
        NormalizedMessageDTO(
          provider="EMAIL",
          external_message_id="email-demo-1",
          from_id="client.demo@example.test",
          chat_external_id="thread-demo-1",
          text="Здравствуйте! Подскажите, можно ли перенести запись с завтра на послезавтра?",
          timestamp=now - timedelta(minutes=3),
        ),
        "email_user_id",
        "Мария Кузнецова",
      ),
    ]

    for dto, external_key, full_name in demos:
      await gateway.handle_inbound_normalized_message(dto)
      # Обновляем ФИО/контактные данные для красоты в UI
      contact = await gateway.chat_service.contacts.find_by_external_id(
        business_account_id=business_account_id,
        external_key=external_key,
        external_value=dto.from_id,
      )
      if contact is not None:
        if full_name:
          contact.full_name = full_name
        if dto.provider.upper() == "WHATSAPP":
          contact.primary_phone = dto.from_id
        if dto.provider.upper() == "EMAIL":
          # простой случай: from_id — это email
          contact.emails = [dto.from_id]

    # Специально для демо: объединим Telegram и WhatsApp в один чат,
    # чтобы показать омниканальность (сообщения из разных каналов в одном диалоге).
    telegram_contact = await gateway.chat_service.contacts.find_by_external_id(
      business_account_id=business_account_id,
      external_key="telegram_user_id",
      external_value="10001",
    )
    whatsapp_contact = await gateway.chat_service.contacts.find_by_external_id(
      business_account_id=business_account_id,
      external_key="whatsapp_user_id",
      external_value="+79990001111",
    )
    if telegram_contact and whatsapp_contact:
      chats_repo = gateway.chat_service.chats
      primary_chat = await chats_repo.find_open_by_contact(
        business_account_id=business_account_id,
        contact_id=telegram_contact.id,
      )
      secondary_chat = await chats_repo.find_open_by_contact(
        business_account_id=business_account_id,
        contact_id=whatsapp_contact.id,
      )
      if primary_chat and secondary_chat:
        # Переносим сообщения WhatsApp-чата в Telegram-чат
        msgs_result = await session.execute(
          select(Message).where(Message.chat_id == secondary_chat.id)
        )
        messages_to_move = list(msgs_result.scalars().all())
        for m in messages_to_move:
          m.chat_id = primary_chat.id
        # Обновляем last_message_at у основного чата
        if messages_to_move:
          latest_created = max(m.created_at for m in messages_to_move if m.created_at)
          primary_chat.last_message_at = latest_created.replace(tzinfo=None)
        # Удаляем лишний чат и контакт (чтобы в UI был один диалог)
        #await session.delete(secondary_chat)
        #await session.delete(whatsapp_contact)


    await session.commit()


def main() -> None:
  asyncio.run(seed_omni_demo())


if __name__ == "__main__":
  main()

