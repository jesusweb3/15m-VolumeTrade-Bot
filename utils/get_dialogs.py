# utils/get_dialogs.py
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User


def get_chat_type(entity) -> str:
    """Определение типа чата"""
    if isinstance(entity, User):
        return "private" if not entity.bot else "bot"
    elif isinstance(entity, Channel):
        return "channel" if entity.broadcast else "supergroup"
    elif isinstance(entity, Chat):
        return "group"
    return "unknown"


async def main():
    """Получение списка всех диалогов с их chat ID"""
    load_dotenv()

    project_root = Path(__file__).resolve().parent.parent

    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    session_name = os.getenv('SESSION_NAME', 'trading_bot_session')

    if not api_id or not api_hash:
        print("\nОшибка: API_ID и API_HASH должны быть указаны в .env\n")
        return

    sessions_dir = project_root / 'signals' / 'auth' / 'sessions'
    session_path = sessions_dir / f"{session_name}.session"

    if not session_path.exists():
        print("\n" + "=" * 80)
        print("СЕССИЯ НЕ НАЙДЕНА")
        print("=" * 80)
        print(f"\nФайл сессии не найден: {session_path}")
        print("\nСначала запустите основной проект для создания сессии:")
        print("  python main.py")
        print("\nПосле успешной авторизации запустите эту утилиту снова.\n")
        return

    client = None

    try:
        print("Подключение к Telegram для получения списка диалогов...")

        client = TelegramClient(
            str(session_path),
            int(api_id),
            api_hash
        )

        await client.connect()

        if not await client.is_user_authorized():
            print("\n" + "=" * 80)
            print("СЕССИЯ УСТАРЕЛА")
            print("=" * 80)
            print("\nСессия больше не авторизована.")
            print("Запустите основной проект для повторной авторизации:")
            print("  python main.py\n")
            return

        print("\n" + "=" * 80)
        print("СПИСОК ВАШИХ ДИАЛОГОВ (КАНАЛЫ, ГРУППЫ, ЧАТЫ)")
        print("=" * 80 + "\n")

        dialog_count = 0

        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            chat_type = get_chat_type(entity)
            chat_title = dialog.name
            chat_id = dialog.id

            username = f"@{entity.username}" if hasattr(entity, 'username') and entity.username else "Нет username"

            print(f"Тип: {chat_type:12} | ID: {chat_id:15} | Username: {username:25} | Название: {chat_title}")
            dialog_count += 1

        print("\n" + "=" * 80)
        print(f"Всего диалогов: {dialog_count}")
        print("=" * 80)
        print("\nСкопируйте chat ID нужного канала и вставьте в .env как CHANNEL_NAME\n")

    except Exception as e:
        print(f"\nОшибка: {e}\n")
    finally:
        if client:
            await client.disconnect()
        print("Готово!")


if __name__ == "__main__":
    asyncio.run(main())