import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from datetime import datetime

from models import Ticket, TicketStatus
from database import Database


# Настройка логирования
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs):
    try:
        await bot.send_message(chat_id, text, **kwargs)
        logging.info(f"Сообщение отправлено в чат {chat_id}")
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки в чат {chat_id}: {e}")
        return False

# Форматирование заявки для отправки
def format_ticket_message(ticket: Ticket) -> str:
    status_emoji = {
        TicketStatus.OPEN: "🟢",
        TicketStatus.IN_PROGRESS: "🟡",
        TicketStatus.CLOSED: "🔴"
    }

    message = (
        f"📋 Заявка #{ticket.id}\n\n"
        f"👤 ФИО: {ticket.full_name}\n"
        f"🚪 Кабинет: {ticket.room}\n"
        f"📅 Создана: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Статус: {status_emoji.get(ticket.status, '⚪')} {ticket.status.value}\n\n"
        f"📝 Проблема:\n{ticket.problem}"
    )

    if ticket.closed_by:
        message += f"\n\n👨‍💼 <b>Закрыл:</b> {ticket.closed_by}"
    if ticket.closed_at:
        message += f"\n📅 <b>Закрыта:</b> {ticket.closed_at.strftime('%d.%m.%Y %H:%M')}"
    if ticket.admin_response:
        message += f"\n\n💬 <b>Ответ:</b>\n{ticket.admin_response}"

    return message


# Отправка уведомления пользователю
async def notify_user(bot: Bot, user_id: int, message: str) -> bool:
    try:
        await bot.send_message(user_id, message)
        return True
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        return False


# Валидация ввода
def validate_name(name: str) -> bool:
    return len(name.strip()) >= 3 and ' ' in name


def validate_room(room: str) -> bool:
    return len(room.strip()) > 0


def validate_problem(problem: str) -> bool:
    return len(problem.strip()) >= 10


# Получение статистики заявок
def get_tickets_stats(db: Database) -> dict:
    with db.conn:
        cursor = db.conn.cursor()

        # Общее количество заявок
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total = cursor.fetchone()[0]

        # Заявки по статусам
        cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
        status_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Заявки за сегодня
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = DATE('now')")
        today = cursor.fetchone()[0]

        return {
            'total': total,
            'open': status_stats.get('open', 0),
            'in_progress': status_stats.get('in_progress', 0),
            'closed': status_stats.get('closed', 0),
            'today': today
        }


# Безопасное получение информации о пользователе
async def safe_get_user_info(bot: Bot, user_id: int) -> Optional[dict]:
    try:
        user = await bot.get_chat(user_id)
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
    except Exception as e:
        logging.error(f"Не удалось получить информацию о пользователе {user_id}: {e}")
        return None


# Форматирование времени
def format_timedelta(dt: datetime) -> str:
    now = datetime.now()
    delta = now - dt

    if delta.days > 0:
        return f"{delta.days} дн. назад"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} ч. назад"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "только что"

# Добавляем функцию для отправки запроса на оценку с удалением кнопок после нажатия
async def ask_for_rating(bot: Bot, user_id: int, ticket_id: int):
    """Отправка запроса на оценку заявки"""
    try:
        from keyboards import get_rating_keyboard
        await bot.send_message(
            user_id,
            "⭐ Оцените работу технического специалиста:\n\n"
            "Пожалуйста, оцените качество обслуживания по вашей заявке:\n",
            reply_markup=get_rating_keyboard(ticket_id)
        )
        logging.info(f"Запрос на оценку отправлен пользователю {user_id} для заявки #{ticket_id}")
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки запроса на оценку пользователю {user_id}: {e}")
        return False