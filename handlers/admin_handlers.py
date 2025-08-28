import asyncio
import logging

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS

# Предполагается, что у вас есть функция для получения всех ID пользователей из базы данных.
# Замените ее на свою реальную функцию.
async def get_all_user_ids_from_db():
    """
    Это заглушка. Вам нужно реализовать получение ID пользователей
    из вашей базы данных (PostgreSQL, SQLite, и т.д.).
    """
    logging.info("Используется заглушка для получения ID пользователей. Замените на реальную функцию БД.")
    # Пример: return [12345, 54321, ...]
    return []


admin_router = Router()
# Этот фильтр будет проверять, является ли пользователь администратором, для всех хендлеров в этом роутере
admin_router.message.filter(F.from_user.id.in_(ADMIN_IDS))
admin_router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


class BroadcastState(StatesGroup):
    get_content = State()
    confirm = State()


@admin_router.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    """Начало процесса создания рассылки."""
    await message.answer("Пришлите сообщение, которое вы хотите разослать пользователям. Это может быть текст, фото, видео, кружок или любой другой контент.")
    await state.set_state(BroadcastState.get_content)


@admin_router.message(BroadcastState.get_content)
async def get_broadcast_content(message: types.Message, state: FSMContext):
    """Получение контента для рассылки и запрос подтверждения."""
    # Сохраняем ID и чат сообщения, чтобы потом его скопировать
    await state.update_data(
        content_message_id=message.message_id,
        content_chat_id=message.chat.id
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Начать рассылку", callback_data="start_broadcast")],
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ])
    await message.answer("Вы уверены, что хотите разослать это сообщение всем пользователям?", reply_markup=keyboard)
    await state.set_state(BroadcastState.confirm)


@admin_router.callback_query(BroadcastState.confirm, F.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")


@admin_router.callback_query(BroadcastState.confirm, F.data == "start_broadcast")
async def process_broadcast(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Запуск процесса рассылки."""
    data = await state.get_data()
    message_id = data.get("content_message_id")
    chat_id = data.get("content_chat_id")
    await state.clear()

    user_ids = await get_all_user_ids_from_db()
    if not user_ids:
        await callback.message.edit_text("Не найдено ни одного пользователя для рассылки.")
        return

    await callback.message.edit_text(f"Начинаю рассылку для {len(user_ids)} пользователей. Это может занять некоторое время...")

    success_count = 0
    error_count = 0

    for user_id in user_ids:
        try:
            # Используем copy_message для точной пересылки любого контента
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=chat_id,
                message_id=message_id,
                # Можно добавить клавиатуру, если нужно
                # reply_markup=...
            )
            success_count += 1
            # Пауза для избежания лимитов Telegram
            await asyncio.sleep(0.1)
        except Exception as e:
            error_count += 1
            logging.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    await callback.message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"👍 Отправлено успешно: {success_count}\n"
        f"👎 Ошибок (пользователь заблокировал бота): {error_count}"
    )