from telegram import Update
from telegram.ext import filters

# Импортируем зависимости из вашего проекта
from services.database import get_all_admins
from config import SUPER_ADMIN_ID

class AdminFilter(filters.BaseFilter):
    """
    Кастомный фильтр для динамической проверки прав администратора.
    """
    def filter(self, update: Update) -> bool:
        """
        Проверяет, является ли пользователь администратором (супер-админ или админ из БД).
        Фильтр запрашивает актуальный список админов из БД при каждой проверке.
        """
        # Если в обновлении нет информации о пользователе, доступ запрещен
        if not update.effective_user:
            return False

        user_id = update.effective_user.id

        # Супер-админ всегда имеет доступ
        if SUPER_ADMIN_ID and user_id == SUPER_ADMIN_ID:
            return True

        # Получаем АКТУАЛЬНЫЙ список ID администраторов из базы данных
        return user_id in get_all_admins()

# Создаем один экземпляр фильтра для удобного импорта и использования в проекте
is_admin = AdminFilter()