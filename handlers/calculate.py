import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
)

# --- Предполагается, что эти переменные определены в другом месте проекта ---
# Если у вас нет настроенного логгера, можно использовать logging.basicConfig()
logger = logging.getLogger(__name__)

# Заглушки для примера
CHOOSING_ACTION = 1
async def get_main_admin_menu_keyboard(user_id: int):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Кнопка меню", callback_data="stub")]])


# --- Константы состояний диалога для калькулятора ---
# Определяют, на каком шаге диалога с калькулятором находится пользователь
COMMISSION_CALCULATOR_INPUT = 501

CB_ADMIN_COMMISSION_CALCULATOR = "admin_commission_calculator"
CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR = "admin_back_to_main_from_calculator"


def _calculate_commission(price: float) -> tuple[float, float]:
    """
    Рассчитывает процент и сумму комиссии на основе цены.
    Изолированная бизнес-логика для простоты тестирования и поддержки.

    Args:
        price: Цена для расчета.

    Returns:
        Кортеж (процент_комиссии, сумма_комиссии).

    Raises:
        ValueError: Если цена не является положительным числом.
    """
    if not isinstance(price, (int, float)) or price <= 0:
        raise ValueError("Сумма должна быть положительным числом.")

    # Правила расчета: (верхняя_граница_цены, процент_или_формула)
    commission_rules = [
        (100000, 10.0),
        (1700000, lambda p: max(10 - ((p - 100000) / 50000) * 0.15, 0)),
        (1800000, 5.2),
        (1900000, 5.1),
        (3050000, 5.0),
        (6000000, lambda p: max(5 - ((p - 3050000) / 50000) * 0.02, 0)),
        (float('inf'), 2.8)  # Для всех цен выше 6 000 000
    ]

    commission_percent = 0.0
    for max_price, rule in commission_rules:
        if price <= max_price:
            if callable(rule):
                commission_percent = rule(price)
            else:
                commission_percent = float(rule)
            break

    commission_amount = price * commission_percent / 100
    return commission_percent, commission_amount


async def commission_calculator_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с калькулятором комиссий. Запрашивает ввод."""
    query = update.callback_query
    await query.answer()

    message_to_send = "Введите сумму для расчета комиссии:"
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Назад в меню админа", callback_data=CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR)]
    ])
    await query.edit_message_text(text=message_to_send, reply_markup=reply_markup)

    # Сохраняем ID основного сообщения калькулятора для последующего редактирования
    context.user_data['calculator_main_message_id'] = query.message.message_id
    # Очищаем старые данные на всякий случай
    context.user_data.pop('calculator_message_ids', None)

    return COMMISSION_CALCULATOR_INPUT


async def commission_calculator_receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает цену от пользователя, обновляет основное сообщение и удаляет ввод."""
    if not update.message or not update.message.text:
        return COMMISSION_CALCULATOR_INPUT  # Ждем корректного ввода
    user = update.effective_user

    user_message_id = update.message.message_id
    main_message_id = context.user_data.get('calculator_main_message_id')

    # Если по какой-то причине ID основного сообщения потерян, выходим, чтобы избежать ошибок
    if not main_message_id:
        logger.error("Не найден ID основного сообщения калькулятора в user_data.")
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_message_id)
        except Exception:
            pass
        return COMMISSION_CALCULATOR_INPUT

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Назад в меню админа", callback_data=CB_ADMIN_BACK_TO_MAIN_FROM_CALCULATOR)]
    ])


    try:
        # Заменяем запятую на точку и убираем пробелы для корректного преобразования
        price_str = update.message.text.replace(',', '.').strip()
        price = float(price_str)

        # Логика расчета вынесена в отдельную функцию
        commission_percent, commission = _calculate_commission(price)
        # --- ЛОГИРОВАНИЕ УСПЕШНОГО РАСЧЕТА ---
        # Возвращаем на уровень INFO, так как ваш bot.py уже настроен на его отображение.
        logger.info(
            f"Admin [ID: {user.id}, @{user.username}] calculated commission for price {price}. "
            f"Result: {commission_percent:.2f}% ({commission:,.2f} RUB)."
        )

        result_text = (
            f"✅ *Результат расчета:*\n"
            f"Цена: <code>{price:,.2f} руб.</code>\n"
            f"Процент комиссии: <code>{commission_percent:.2f}%</code>\n"
            f"Комиссия: <code>{commission:,.2f} руб.</code>\n\n"
            f"Введите следующую сумму для расчета."
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=result_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    except ValueError as e:
        # Обрабатываем ошибки преобразования в float и ошибки из _calculate_commission
        # --- ЛОГИРОВАНИЕ ОШИБКИ ВВОДА ---
        logger.warning(
            f"Admin [ID: {user.id}, @{user.username}] entered invalid data for calculator: '{update.message.text}'. "
            f"Error: {e}"
        )
        
        error_text = str(e) if str(e) else 'Пожалуйста, отправьте числовое значение.'
        error_message_text = (
            f"❌ *Ошибка:*\n{error_text}\n\n"
            f"Пожалуйста, введите корректную сумму."
        )
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=main_message_id,
            text=error_message_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception as e:
        # Ловим другие возможные ошибки, например, если сообщение не изменилось
        logger.error(f"Ошибка при обновлении сообщения калькулятора: {e}")

    finally:
        # В любом случае удаляем сообщение пользователя
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение пользователя {user_message_id}: {e}")

    return COMMISSION_CALCULATOR_INPUT

async def back_to_main_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возвращает в главное меню администратора, вызывая его стартовую функцию."""
    # Локальный импорт для избежания циклических зависимостей
    from .admin import admin_start

    # Очищаем ID сохраненного сообщения
    context.user_data.pop('calculator_main_message_id', None)

    # Вызываем функцию, которая отрисовывает главное меню админа
    return await admin_start(update, context)
