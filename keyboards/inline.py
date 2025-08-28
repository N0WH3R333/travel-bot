from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Определим названия групп и их callback_data для идентификации
# В будущем это можно будет загружать из конфига или базы данных
GROUP_CHOICES = {
    "Путешествия по Азии 🌏": "join_group_asia",
    "Походы в горы ⛰️": "join_group_mountains",
    "Пляжный отдых 🏖️": "join_group_beach"
}

def get_group_selection_keyboard() -> InlineKeyboardMarkup:
    """Создает и возвращает клавиатуру для выбора группы."""
    keyboard = [
        [InlineKeyboardButton(text, callback_data=data)] for text, data in GROUP_CHOICES.items()
    ]
    return InlineKeyboardMarkup(keyboard)
