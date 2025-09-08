from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from keyboards import get_rating_keyboard, get_feedback_keyboard, get_main_keyboard
from config import Config
from utils import notify_user


class RatingForm(StatesGroup):
    waiting_for_feedback = State()


rating_router = Router()


@rating_router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config):
    parts = callback.data.split("_")
    ticket_id = int(parts[1])
    rating_action = parts[2]

    # Удаляем кнопки оценки сразу после нажатия
    await callback.message.edit_reply_markup(reply_markup=None)

    if rating_action == "skip":
        await callback.message.edit_text("✅ Спасибо! Оценка не требуется.")
        await callback.answer()
        return

    rating = int(rating_action)

    # Сохраняем оценку
    db.update_ticket_rating(ticket_id, rating)

    # Получаем информацию о заявке
    ticket = db.get_ticket(ticket_id)

    if ticket:
        # Отправляем уведомление в чат администрации
        rating_stars = "⭐" * rating
        rating_info = (
            f"⭐ Новая оценка заявки #{ticket_id}\n\n"
            f"👤 Пользователь: {ticket.full_name}\n"
            f"🚪 Кабинет: {ticket.room}\n"
            f"🎯 Оценка: {rating_stars} ({rating}/5)\n"
            f"👨‍💼 Исполнитель: {ticket.closed_by or 'Не указан'}\n"
            f"📝 Проблема:\n{ticket.problem[:100]}..."
        )

        await bot.send_message(
            chat_id=config.SUPPORT_CHAT_ID,
            text=rating_info
        )

    # Переходим к сбору отзыва
    await state.update_data(ticket_id=ticket_id, rating=rating)
    await state.set_state(RatingForm.waiting_for_feedback)

    await callback.message.answer(
        "📝 Оставьте отзыв о работе технического специалиста:\n\n"
        "Напишите ваше мнение о качестве обслуживания или нажмите '🚫 Без отзыва'",
        reply_markup=get_feedback_keyboard()
    )
    await callback.answer()


@rating_router.message(F.text == "🚫 Без отзыва")
async def skip_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data['ticket_id']
    rating = data['rating']

    # Удаляем клавиатуру отзыва
    await message.answer(
        "✅ Спасибо за оценку! Ваш отзыв учтен.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Восстанавливаем основную клавиатуру
    await message.answer(
        "Вы можете создать новую заявку или посмотреть существующие:",
        reply_markup=get_main_keyboard()
    )

    await state.clear()


@rating_router.message(F.text == "❌ Отмена")
async def cancel_feedback(message: Message, state: FSMContext):
    # Удаляем клавиатуру отзыва
    await message.answer(
        "Оценка отменена.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Восстанавливаем основную клавиатуру
    await message.answer(
        "Вы можете создать новую заявку или посмотреть существующие:",
        reply_markup=get_main_keyboard()
    )

    await state.clear()


@rating_router.message(RatingForm.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config):
    data = await state.get_data()
    ticket_id = data['ticket_id']
    rating = data['rating']
    feedback = message.text

    # Сохраняем отзыв
    db.update_ticket_rating(ticket_id, rating, feedback)

    # Получаем информацию о заявке
    ticket = db.get_ticket(ticket_id)

    if ticket:
        # Отправляем полный отзыв в чат администрации
        rating_stars = "⭐" * rating
        rating_info = (
            f"⭐ Полный отзыв по заявке #{ticket_id}\n\n"
            f"👤 Пользователь: {ticket.full_name}\n"
            f"🚪 Кабинет: {ticket.room}\n"
            f"🎯 Оценка: {rating_stars} ({rating}/5)\n"
            f"👨‍💼 Исполнитель: {ticket.closed_by or 'Не указан'}\n\n"
            f"💬 Отзыв:\n{feedback}\n\n"
            f"📝 Проблема была:\n{ticket.problem[:100]}..."
        )

        await bot.send_message(
            chat_id=config.SUPPORT_CHAT_ID,
            text=rating_info
        )

    # Удаляем клавиатуру отзыва
    await message.answer(
        "✅ Спасибо за ваш отзыв! Он поможет нам стать лучше.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Восстанавливаем основную клавиатуру
    await message.answer(
        "Вы можете создать новую заявку или посмотреть существующие:",
        reply_markup=get_main_keyboard()
    )

    await state.clear()