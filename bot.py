import logging
from telegram.ext import Application, CommandHandler, ChatMemberHandler, filters

# Импортируем все необходимые компоненты
from config import TOKEN, SUPER_ADMIN_ID
from services.database import init_db, get_all_admins
from handlers.start import start
from handlers.admin import admin_handler
from handlers.errors import error_handler
from handlers.members import track_channel_members
from handlers.admin_management import manage_admins_handler

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
    application = Application.builder().token(TOKEN).build()

    # --- Регистрация обработчиков ---
    
    # Обработчик ошибок (важно регистрировать первым)
    application.add_error_handler(error_handler)

    # Обработчик админ-панели
    # Теперь он доступен и супер-админу, и админам из БД
    all_admin_ids = get_all_admins()
    if SUPER_ADMIN_ID:
        all_admin_ids.append(SUPER_ADMIN_ID)
    
    # Создаем фильтр для всех администраторов
    admin_user_filter = filters.User(user_id=set(all_admin_ids))

    # Применяем фильтр к каждой точке входа в ConversationHandler
    for entry_point in admin_handler.entry_points:
        entry_point.filters = admin_user_filter & entry_point.filters if entry_point.filters else admin_user_filter
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
