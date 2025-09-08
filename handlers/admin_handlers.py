from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from database import Database, TicketStatus
from blocked_database import BlockedDatabase
from keyboards import get_ticket_action_keyboard, get_block_user_keyboard, get_unblock_user_keyboard, \
    get_in_progress_ticket_keyboard, get_rating_keyboard
from config import Config
from utils import format_ticket_message, notify_user, safe_get_user_info, ask_for_rating


class CloseTicketForm(StatesGroup):
    waiting_for_closer_name = State()
    waiting_for_response = State()


class CloseTicketCommandForm(StatesGroup):
    waiting_for_ticket_id = State()
    waiting_for_closer_name = State()
    waiting_for_response = State()


class BlockUserForm(StatesGroup):
    waiting_for_reason = State()


class TakeToWorkForm(StatesGroup):
    waiting_for_ticket_id = State()


admin_router = Router()


# Перевод заявки в работу
@admin_router.callback_query(F.data.startswith("take_to_work_"))
async def take_ticket_to_work(callback: CallbackQuery, db: Database, bot: Bot):
    ticket_id = int(callback.data.split("_")[3])

    # Обновляем статус заявки
    db.update_ticket_status(
        ticket_id=ticket_id,
        status=TicketStatus.IN_PROGRESS
    )

    ticket = db.get_ticket(ticket_id)

    # Уведомляем пользователя
    if ticket and ticket.user_id:
        user_message = (
            f"🟡 Ваша заявка #{ticket.id} взята в работу\n\n"
            f"Технический специалист начал работу над вашей проблемой.\n"
            f"Мы свяжемся с вами по мере решения вопроса."
        )
        await notify_user(bot, ticket.user_id, user_message)

    # Обновляем сообщение с заявки
    ticket_info = (
        f"🟡 Заявка #{ticket.id} взята в работу\n\n"
        f"👤 ФИО: {ticket.full_name}\n"
        f"🚪 Кабинет: {ticket.room}\n"
        f"📝 Проблема:\n{ticket.problem}"
    )

    await callback.message.edit_text(
        ticket_info,
        reply_markup=get_in_progress_ticket_keyboard(ticket_id, ticket.user_id)
    )
    await callback.answer("✅ Заявка взята в работу!")


# Команда для перевода заявки в работу
@admin_router.message(Command("take_to_work"))
async def take_to_work_command(message: Message, state: FSMContext, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    await state.set_state(TakeToWorkForm.waiting_for_ticket_id)
    await message.answer(
        "🟡 Взять заявку в работу\n\n"
        "Введите номер заявки, которую хотите взять в работу:",
        reply_markup=ReplyKeyboardRemove()
    )


@admin_router.message(TakeToWorkForm.waiting_for_ticket_id)
async def process_take_to_work_ticket_id(message: Message, state: FSMContext, db: Database, bot: Bot):
    try:
        ticket_id = int(message.text.strip())
        ticket = db.get_ticket(ticket_id)

        if not ticket:
            await message.answer("❌ Заявка с таким номером не найдена!")
            await state.clear()
            return

        if ticket.status == TicketStatus.CLOSED:
            await message.answer("❌ Эта заявка уже закрыта!")
            await state.clear()
            return

        # Обновляем статус заявки
        db.update_ticket_status(
            ticket_id=ticket_id,
            status=TicketStatus.IN_PROGRESS
        )

        # Уведомляем пользователя
        if ticket.user_id:
            user_message = (
                f"🟡 Ваша заявка #{ticket.id} взята в работу\n\n"
                f"Технический специалист начал работу над вашей проблемой.\n"
                f"Мы свяжемся с вами по мере решения вопроса."
            )
            await notify_user(bot, ticket.user_id, user_message)

        await message.answer(f"✅ Заявка #{ticket_id} взята в работу!")
        await state.clear()

    except ValueError:
        await message.answer("❌ Некорректный номер заявки! Введите число.")
        await state.clear()
    except Exception as e:
        await message.answer("❌ Ошибка при обработке заявки!")
        await state.clear()


# Обработчик закрытия заявки
@admin_router.callback_query(F.data.startswith("close_"))
async def close_ticket_start(callback: CallbackQuery, state: FSMContext, db: Database):
    ticket_id = int(callback.data.split("_")[1])

    # Проверяем статус заявки
    ticket = db.get_ticket(ticket_id)
    if ticket.status == TicketStatus.OPEN:
        await callback.answer("❌ Сначала возьмите заявку в работу!", show_alert=True)
        return

    await state.update_data(ticket_id=ticket_id)
    await state.set_state(CloseTicketForm.waiting_for_closer_name)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Введите ваше ФИО для закрытия заявки:",
        reply_markup=ReplyKeyboardRemove()
    )


@admin_router.message(CloseTicketForm.waiting_for_closer_name)
async def process_closer_name(message: Message, state: FSMContext, db: Database):
    await state.update_data(closer_name=message.text)
    data = await state.get_data()

    ticket = db.get_ticket(data['ticket_id'])

    await state.set_state(CloseTicketForm.waiting_for_response)
    await message.answer(
        f"Заявка #{data['ticket_id']} от {ticket.full_name}\n"
        "Введите ответ для пользователя (или 'нет' если ответ не требуется):"
    )


@admin_router.message(CloseTicketForm.waiting_for_response)
async def process_response(message: Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    response = message.text if message.text.lower() != 'нет' else None

    db.update_ticket_status(
        ticket_id=data['ticket_id'],
        status=TicketStatus.CLOSED,
        closed_by=data['closer_name'],
        response=response
    )

    ticket = db.get_ticket(data['ticket_id'])

    # Уведомляем пользователя
    if ticket.user_id:
        user_message = (
            f"✅ Ваша заявка #{ticket.id} закрыта\n\n"
            f"👨‍💼 Закрыл: {data['closer_name']}\n"
        )
        if response:
            user_message += f"💬 Ответ:\n{response}"

        await notify_user(bot, ticket.user_id, user_message)

        # Сразу отправляем запрос на оценку
        await ask_for_rating(bot, ticket.user_id, ticket.id)

    await message.answer(f"✅ Заявка #{ticket.id} успешно закрыта! Пользователю отправлен запрос на оценку.")
    await state.clear()


# Команда для вывода открытых заявок
@admin_router.message(Command("open_tickets"))
@admin_router.message(F.text == "📋 Открытые заявки")
async def show_open_tickets(message: Message, db: Database, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    open_tickets = db.get_open_tickets()

    if not open_tickets:
        await message.answer("🎉 Нет новых открытых заявок!")
        return

    await message.answer(f"🟢 Новые заявки: {len(open_tickets)}")

    for ticket in open_tickets:
        ticket_info = (
            f"🟢 Новая заявка #{ticket['id']}\n\n"
            f"👤 ФИО: {ticket['full_name']}\n"
            f"🚪 Кабинет: {ticket['room']}\n"
            f"📅 Создана: {ticket['created_at']}\n\n"
            f"📝 Проблема:\n{ticket['problem'][:100]}{'...' if len(ticket['problem']) > 100 else ''}"
        )

        keyboard = get_ticket_action_keyboard(ticket['id'], ticket['user_id'])

        await message.answer(
            ticket_info,
            reply_markup=keyboard
        )


# Команда для вывода заявок в работе
@admin_router.message(Command("in_progress"))
@admin_router.message(F.text == "🟡 В работе")
async def show_in_progress_tickets(message: Message, db: Database, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    in_progress_tickets = db.get_in_progress_tickets()

    if not in_progress_tickets:
        await message.answer("📊 Нет заявок в работе.")
        return

    await message.answer(f"🟡 Заявки в работе: {len(in_progress_tickets)}")

    for ticket in in_progress_tickets:
        ticket_info = (
            f"🟡 В работе ##{ticket['id']}\n\n"
            f"👤 ФИО: {ticket['full_name']}\n"
            f"🚪 Кабинет: {ticket['room']}\n"
            f"📅 Создана: {ticket['created_at']}\n\n"
            f"📝 Проблема:\n{ticket['problem'][:100]}{'...' if len(ticket['problem']) > 100 else ''}"
        )

        keyboard = get_in_progress_ticket_keyboard(ticket['id'], ticket['user_id'])

        await message.answer(
            ticket_info,
            reply_markup=keyboard
        )


# Блокировка пользователя
@admin_router.callback_query(F.data.startswith("block_"))
async def block_user_start(callback: CallbackQuery, state: FSMContext, blocked_db: BlockedDatabase):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    ticket_id = int(parts[2])

    # Проверяем, не заблокирован ли уже пользователь
    if blocked_db.is_user_blocked(user_id):
        await callback.answer("❌ Пользователь уже заблокирован!")
        return

    await state.update_data(user_id=user_id, ticket_id=ticket_id)
    await state.set_state(BlockUserForm.waiting_for_reason)

    user_info = await safe_get_user_info(callback.bot, user_id)
    user_name = f"@{user_info['username']}" if user_info and user_info.get('username') else f"ID: {user_id}"

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🚫 Блокировка пользователя\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: {user_id}\n\n"
        f"Введите причина блокировки:",
        reply_markup=ReplyKeyboardRemove()
    )


@admin_router.message(BlockUserForm.waiting_for_reason)
async def process_block_reason(message: Message, state: FSMContext, blocked_db: BlockedDatabase, bot: Bot):
    data = await state.get_data()
    user_id = data['user_id']
    reason = message.text

    # Получаем информацию о пользователе
    user_info = await safe_get_user_info(bot, user_id)

    # Блокируем пользователя
    success = blocked_db.block_user(
        user_id=user_id,
        blocked_by=message.from_user.id,
        username=user_info.get('username') if user_info else None,
        first_name=user_info.get('first_name') if user_info else None,
        last_name=user_info.get('last_name') if user_info else None,
        reason=reason
    )

    if success:
        # Отправляем уведомление пользователю
        try:
            await bot.send_message(
                user_id,
                f"🚫 Вы были заблокированы в системе технической поддержки\n\n"
                f"📋 Причина: {reason}\n\n"
                f"❌ Вы больше не можете создавать новые заявки."
            )
        except:
            pass

        await message.answer(
            f"✅ Пользователь ID: {user_id} успешно заблокирован!\n"
            f"📋 Причина: {reason}"
        )
    else:
        await message.answer("❌ Ошибка при блокировке пользователя!")

    await state.clear()


# Разблокировка пользователя
@admin_router.callback_query(F.data.startswith("unblock_"))
async def unblock_user(callback: CallbackQuery, blocked_db: BlockedDatabase):
    user_id = int(callback.data.split("_")[1])

    success = blocked_db.unblock_user(user_id)

    if success:
        await callback.message.edit_text(
            f"🔓 Пользователь ID: {user_id} разблокирован!",
            reply_markup=None
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при разблокировке пользователя!",
            reply_markup=None
        )

    await callback.answer()


# Команда для статистики
@admin_router.message(Command("stats"))
@admin_router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, db: Database, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    stats = db.get_tickets_stats()

    stats_text = (
        "📊 Статистика заявок\n\n"
        f"📈 Всего заявок: {stats['total']}\n"
        f"🟢 Новых: {stats['open']}\n"
        f"🟡 В работе: {stats['in_progress']}\n"
        f"🔴 Закрытых: {stats['closed']}\n"
        f"📅 Сегодня: {stats['today']}"
    )

    await message.answer(stats_text)


# Команда для просмотра оценок
@admin_router.message(Command("ratings"))
@admin_router.message(F.text == "⭐ Оценки")
async def show_ratings(message: Message, db: Database, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    # Получаем статистику оценок
    rating_stats = db.get_rating_stats()
    rated_tickets = db.get_rated_tickets(10)

    if not rated_tickets:
        await message.answer("⭐ Пока нет оценок от пользователей.")
        return

    # Формируем текст статистики
    avg_rating = rating_stats.get('avg_rating', 0) or 0
    total_ratings = rating_stats.get('total_ratings', 0)

    stats_text = (
        f"⭐ Статистика оценок\n\n"
        f"📊 Средняя оценка: {avg_rating:.1f}/5\n"
        f"📈 Всего оценок: {total_ratings}\n"
        f"⭐⭐⭐⭐⭐: {rating_stats.get('five_stars', 0)}\n"
        f"⭐⭐⭐⭐: {rating_stats.get('four_stars', 0)}\n"
        f"⭐⭐⭐: {rating_stats.get('three_stars', 0)}\n"
        f"⭐⭐: {rating_stats.get('two_stars', 0)}\n"
        f"⭐: {rating_stats.get('one_stars', 0)}\n\n"
        f"Последние 10 оценок:"
    )

    await message.answer(stats_text)

    for ticket in rated_tickets:
        rating_stars = "⭐" * ticket['rating']
        rating_text = (
            f"⭐ Заявка #{ticket['id']}\n"
            f"👤 {ticket['full_name']} | 🚪 {ticket['room']}\n"
            f"🎯 Оценка: {rating_stars} ({ticket['rating']}/5)\n"
            f"👨‍💼 Исполнитель: {ticket['closed_by'] or 'Не указан'}\n"
        )

        if ticket['feedback']:
            rating_text += f"💬 Отзыв:\n{ticket['feedback'][:100]}...\n"

        await message.answer(rating_text)


# Показать заблокированных пользователей
@admin_router.message(Command("blocked"))
@admin_router.message(F.text == "🚫 Заблокированные")
async def show_blocked_users_command(message: Message, blocked_db: BlockedDatabase, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    blocked_users = blocked_db.get_blocked_users()

    if not blocked_users:
        await message.answer("🚫 Нет заблокированных пользователей.")
        return

    for user in blocked_users:
        user_text = (
            f"🚫 Заблокированный пользователь\n\n"
            f"🆔 ID: {user['user_id']}\n"
        )

        if user['username']:
            user_text += f"👤 @{user['username']}\n"
        if user['first_name'] or user['last_name']:
            user_text += f"👥 Имя: {user['first_name'] or ''} {user['last_name'] or ''}\n"

        user_text += (
            f"⏰ Заблокирован: {user['blocked_at']}\n"
            f"👨‍💼 Заблокировал: {user['blocked_by']}\n"
        )

        if user['reason']:
            user_text += f"📋 Причина: {user['reason']}\n"

        await message.answer(
            user_text,
            reply_markup=get_unblock_user_keyboard(user['user_id'])
        )


# Команда для разблокировки пользователя
@admin_router.message(Command("unblock"))
async def unblock_user_command(message: Message, blocked_db: BlockedDatabase, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    # Парсим команду: /unblock 123456789
    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /unblock <ID_пользователя>")
        return

    # Проверяем, заблокирован ли пользователь
    if not blocked_db.is_user_blocked(user_id):
        await message.answer(f"❌ Пользователь {user_id} не заблокирован!")
        return

    # Разблокируем
    success = blocked_db.unblock_user(user_id)

    if success:
        await message.answer(f"✅ Пользователь {user_id} успешно разблокирован!")

        # Пытаемся уведомить пользователя
        try:
            await message.bot.send_message(
                user_id,
                "✅ Ваша блокировка снята\n\n"
                "Вы снова можете создавать заявки в системе технической поддержки."
            )
        except:
            pass
    else:
        await message.answer("❌ Ошибка при разблокировке пользователя!")


# Обновляем справку администратора
@admin_router.message(Command("admin_help"))
@admin_router.message(F.text == "📋 Помощь админа")
async def admin_help(message: Message, config: Config):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("❌ Эта команда только для администраторов!")
        return

    help_text = (
        "🛠️ Команды для администраторов:\n\n"
        "📋 /admin_help - эта справка\n"
        "🟢 /open_tickets - новые заявки\n"
        "🟡 /in_progress - заявки в работе\n"
        "🟡 /take_to_work <номер> - взять заявку в работу\n"
        "🚫 /blocked - список заблокированных\n"
        "🔓 /unblock <ID> - разблокировать пользователя\n"
        "📊 /stats - статистика заявок\n"
        "⭐ /ratings - оценки пользователей\n\n"
        "Процесс работы:\n"
        "1. 🟢 Новая заявка → /take_to_work\n"
        "2. 🟡 В работе → Закрыть через кнопку\n"
        "3. 🔴 Закрыта → Автоматический запрос оценки\n\n"
    )
    await message.answer(help_text)