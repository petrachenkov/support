import os
from typing import List


# Загрузка переменных окружения
def load_env():
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        print("Файл .env не найден, используются значения по умолчанию")


load_env()


# Конфигурация без dataclass
class Config:
    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")

        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]

        self.SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", "0"))
        self.DB_NAME = os.getenv("DB_NAME", "tickets.db")


def load_config() -> Config:
    return Config()