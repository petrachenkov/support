from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Создать заявку")],
            [KeyboardButton(text="📊 Мои заявки"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def get_admin_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Открытые заявки"), KeyboardButton(text="🟡 В работе")],
            [KeyboardButton(text="🚫 Заблокированные"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⭐ Оценки"), KeyboardButton(text="📋 Помощь админа")]
        ],
        resize_keyboard=True
    )

def get_ticket_action_keyboard(ticket_id: int, user_id: int):
    """Клавиатура для новых заявок (статус OPEN)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟡 Взять в работу", callback_data=f"take_to_work_{ticket_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_{user_id}_{ticket_id}")
            ]
        ]
    )

def get_in_progress_ticket_keyboard(ticket_id: int, user_id: int):
    """Клавиатура для заявок в работе (статус IN_PROGRESS)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Закрыть", callback_data=f"close_{ticket_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block_{user_id}_{ticket_id}")
            ]
        ]
    )

def get_rating_keyboard(ticket_id: int):
    """Клавиатура для оценки заявки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐", callback_data=f"rate_{ticket_id}_1"),
                InlineKeyboardButton(text="⭐⭐", callback_data=f"rate_{ticket_id}_2"),
                InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rate_{ticket_id}_3"),
            ],
            [
                InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_4"),
                InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rate_{ticket_id}_5"),
            ],
            [
                InlineKeyboardButton(text="🚫 Пропустить", callback_data=f"rate_{ticket_id}_skip"),
            ]
        ]
    )

def get_feedback_keyboard():
    """Клавиатура для отзыва"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚫 Без отзыва")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_block_user_keyboard(user_id: int, ticket_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить блокировку", callback_data=f"confirm_block_{user_id}_{ticket_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_block_{user_id}_{ticket_id}")
            ]
        ]
    )

def get_unblock_user_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"unblock_{user_id}")
            ]
        ]
    )