import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Импортируем токен из нашего нового файла конфигурации
from config import TOKEN

# Включаем логирование, чтобы видеть ошибки
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение, когда пользователь вводит команду /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! Я простой эхо-бот. Отправь мне любое сообщение, и я его повторю.",
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Повторяет сообщение пользователя."""
    await update.message.reply_text(update.message.text)


def main() -> None:
    """Запуск бота."""
    # Проверяем, что токен доступен
    if not TOKEN:
        logger.error("Токен не найден! Проверьте .env файл.")
        return

    # Создаем объект Application и передаем ему токен
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Регистрируем обработчик для всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем бота (он будет работать, пока ты его не остановишь)
    print("Бот запущен...")
    application.run_polling()
    print("Бот остановлен.")


if __name__ == "__main__":
    main()