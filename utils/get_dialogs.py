# utils/get_dialogs.py
import asyncio
from pathlib import Path
from pyrogram import Client
from dotenv import load_dotenv
import os

load_dotenv()


async def main():
    """Получение списка всех диалогов с их chat ID"""
    client = None

    try:
        print("Подключение к Telegram для получения списка диалогов...")

        sessions_dir = Path(__file__).parent.parent / "signals" / "auth" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_path = sessions_dir / f"{os.getenv('SESSION_NAME', 'my_account')}.session"

        client = Client(
            name=str(session_path),
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            device_model=os.getenv("DEVICE_MODEL"),
            system_version=os.getenv("SYSTEM_VERSION"),
            app_version=os.getenv("APP_VERSION"),
            lang_code=os.getenv("LANG_CODE"),
            no_updates=True
        )

        await client.start()

        print("\n" + "=" * 80)
        print("СПИСОК ВАШИХ ДИАЛОГОВ (КАНАЛЫ, ГРУППЫ, ЧАТЫ)")
        print("=" * 80 + "\n")

        dialog_count = 0

        async for dialog in client.get_dialogs():
            chat = dialog.chat
            chat_type = chat.type.value
            chat_title = chat.title or chat.first_name or "Без названия"
            chat_id = chat.id
            username = f"@{chat.username}" if chat.username else "Нет username"

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
            await client.stop()
        print("Готово!")


if __name__ == "__main__":
    asyncio.run(main())