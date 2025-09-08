from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from blocked_database import BlockedDatabase
from keyboards import get_main_keyboard, get_cancel_keyboard, get_rating_keyboard
from config import Config
from utils import safe_send_message
import logging


class TicketForm(StatesGroup):
    full_name = State()
    room = State()
    problem = State()


user_router = Router()


@user_router.message(F.text == "❌ Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )


@user_router.message(F.text == "📋 Создать заявку")
async def create_ticket_start(message: Message, state: FSMContext, blocked_db: BlockedDatabase):
    # Проверяем, не заблокирован ли пользователь
    if blocked_db.is_user_blocked(message.from_user.id):
        await message.answer(
            "🚫 Вы заблокированы в системе технической поддержки\n\n"
            "❌ Вы не можете создавать новые заявки.\n"
            "📞 Для разблокировки обратитесь к администратору."
        )
        return

    await state.set_state(TicketForm.full_name)
    await message.answer(
        "Введите ваше ФИО и номер телефона:\n"
        "(Например: Иванов Иван Иванович 89000000000)\n",
        reply_markup=get_cancel_keyboard()
    )


@user_router.message(TicketForm.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(TicketForm.room)
    await message.answer("Введите номер кабинета:")


@user_router.message(TicketForm.room)
async def process_room(message: Message, state: FSMContext):
    await state.update_data(room=message.text)
    await state.set_state(TicketForm.problem)
    await message.answer("Опишите проблему:")


@user_router.message(TicketForm.problem)
async def process_problem(message: Message, state: FSMContext, db: Database, config: Config, bot: Bot):
    data = await state.get_data()

    # Логируем создание заявки
    logging.info(f"Создание заявки от пользователя {message.from_user.id}")

    ticket_id = db.add_ticket(
        user_id=message.from_user.id,
        full_name=data['full_name'],
        room=data['room'],
        problem=message.text
    )

    logging.info(f"Заявка #{ticket_id} создана в базе данных")

    # Отправляем уведомление в чат поддержки
    ticket_info = (
        f"🟢 Новая заявка #{ticket_id}\n\n"
        f"👤 ФИО: {data['full_name']}\n"
        f"🚪 Кабинет: {data['room']}\n\n"
        f"📝 Проблема:\n{message.text}\n\n"
        f"🆔 User ID: {message.from_user.id}"
    )

    from keyboards import get_ticket_action_keyboard
    keyboard = get_ticket_action_keyboard(ticket_id, message.from_user.id)

    success = await safe_send_message(
        bot=bot,
        chat_id=config.SUPPORT_CHAT_ID,
        text=ticket_info,
        reply_markup=keyboard
    )

    await state.clear()

    if success:
        await message.answer(
            f"🟢 Ваша заявка #{ticket_id} создана!\n\n"
            "Ожидайте, когда технический специалист возьмёт её в работу.\n"
            "Вы получите уведомление о начале работы над вашей заявкой.",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            f"✅ Ваша заявка #{ticket_id} создана!\n"
            "⚠️ Внимание: Возникли проблемы с уведомлением технических специалистов.",
            reply_markup=get_main_keyboard()
        )


@user_router.message(F.text == "📊 Мои заявки")
async def show_my_tickets(message: Message, db: Database):
    tickets = db.get_user_tickets(message.from_user.id)

    if not tickets:
        await message.answer("У вас пока нет заявок.")
        return

    for ticket in tickets:
        status_emoji = "🟢" if ticket['status'] == "open" else "🟡" if ticket['status'] == "in_progress" else "🔴"

        # Форматируем дату
        created_at = ticket['created_at']
        if isinstance(created_at, str) and 'T' in created_at:
            created_at = created_at.replace('T', ' ')

        ticket_text = (
            f"📋 Заявка #{ticket['id']}\n"
            f"📅 Создана: {created_at}\n"
            f"📊 Статус: {status_emoji} {ticket['status']}\n"
            f"🚪 Кабинет: {ticket['room']}\n"
        )

        if ticket['admin_response']:
            ticket_text += f"💬 Ответ:\n{ticket['admin_response']}\n"

        if ticket['rating']:
            rating_stars = "⭐" * ticket['rating']
            ticket_text += f"⭐ Ваша оценка: {rating_stars}\n"
            if ticket['feedback']:
                ticket_text += f"📝 Отзыв:\n{ticket['feedback']}\n"

        await message.answer(ticket_text)