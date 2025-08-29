import logging
from telegram.ext import Application, CommandHandler, ChatMemberHandler, filters
from telegram import BotCommand, BotCommandScopeChat

# Импортируем все необходимые компоненты
from config import TOKEN, SUPER_ADMIN_ID
from services.database import init_db, get_all_admins
from filters.custom_filters import is_admin  # <-- Импортируем наш новый динамический фильтр
from handlers.start import start
from handlers.admin import admin_handler
from handlers.errors import error_handler
from handlers.members import track_channel_members
from handlers.admin_management import manage_admins_handler

async def post_init(application: Application):
    """Устанавливает команды для всех админов и супер-админа при запуске бота."""
    logger = logging.getLogger(__name__)
    logger.info("Установка команд для администраторов...")
    
    admin_commands = [BotCommand("admin", "Открыть панель администратора")]
    # Предполагаем, что команда для управления админами - /manage_admins
    super_admin_commands = admin_commands + [
        BotCommand("manage_admins", "Управление администраторами"),
    ]

    # Установка команд для супер-админа
    if SUPER_ADMIN_ID:
        try:
            await application.bot.set_my_commands(super_admin_commands, scope=BotCommandScopeChat(chat_id=SUPER_ADMIN_ID))
            logger.info(f"Команды для супер-админа {SUPER_ADMIN_ID} установлены.")
        except Exception as e:
            logger.warning(f"Не удалось установить команды для супер-админа {SUPER_ADMIN_ID}: {e}")

    # Установка команд для обычных админов из БД
    for admin_id in get_all_admins():
        if admin_id == SUPER_ADMIN_ID: continue # Не перезаписываем команды для супер-админа
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Не удалось установить команды для админа {admin_id}: {e}")

def main() -> None:
    """Запускает бота."""
    # Настройка логирования для вывода информации в консоль
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    # Инициализация базы данных
    init_db()

    # Создание экземпляра бота
    # Добавляем post_init для установки команд при старте
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # --- Регистрация обработчиков ---
    
    # Обработчик ошибок (важно регистрировать первым)
    application.add_error_handler(error_handler)

    # Обработчик админ-панели с динамическим фильтром
    # Применяем наш кастомный фильтр is_admin к каждой точке входа в ConversationHandler
    for entry_point in admin_handler.entry_points:
        # Совмещаем наш фильтр is_admin с уже существующими фильтрами (например, filters.COMMAND)
        entry_point.filters = is_admin & entry_point.filters if entry_point.filters else is_admin
    application.add_handler(admin_handler)

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчик для отслеживания вступления/выхода участников
    application.add_handler(ChatMemberHandler(track_channel_members, ChatMemberHandler.CHAT_MEMBER))

    # Обработчик для управления администраторами (только для супер-админа)
    application.add_handler(manage_admins_handler)
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
