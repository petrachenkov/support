from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from keyboards import get_main_keyboard

common_router = Router()

@common_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в систему технической поддержки!\n\n"
        "Здесь вы можете создать заявку на техническое обслуживание, "
        "отслеживать статус своих заявок и получить помощь.",
        reply_markup=get_main_keyboard()
    )

@common_router.message(Command("help"))
@common_router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    help_text = (
        "🤖 Команды бота:\n\n"
        "📋 Создать заявку - оставить новую заявку на техническое обслуживание\n"
        "📊 Мои заявки - просмотреть статус ваших заявок\n"
        "❓ Помощь - показать это сообщение\n\n"
        "Для создания заявки вам потребуется:\n"
        "• ФИО и номер телефона\n"
        "• Номер кабинета\n"
        "• Описание проблемы"
    )
    await message.answer(help_text)