# c:\Users\Lenovo\Desktop\bottravel\services\database.py

import sqlite3
import logging
from contextlib import contextmanager

DB_NAME = 'bot_database.db'
logger = logging.getLogger(__name__)

@contextmanager
def db_connection():
    """Контекстный менеджер для работы с базой данных."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Инициализирует таблицы в базе данных, если они не существуют."""
    with db_connection() as conn:
        cursor = conn.cursor()
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT
            )
        ''')
        # Таблица подписок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (user_id, channel_id)
            )
        ''')
        # Новая таблица администраторов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        conn.commit()

# --- Функции для пользователей и подписок (остаются без изменений) ---

def add_user(user_id: int, username: str, first_name: str):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        conn.commit()

def add_subscription(user_id: int, channel_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO subscriptions (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
        conn.commit()

def remove_subscription(user_id: int, channel_id: int):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
        conn.commit()

def get_user_ids_by_channel(channel_id: int) -> list[int]:
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM subscriptions WHERE channel_id = ?", (channel_id,))
        return [row[0] for row in cursor.fetchall()]

def get_all_users() -> list[int]:
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

def get_channel_stats() -> dict[int, int]:
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, COUNT(user_id) FROM subscriptions GROUP BY channel_id")
        return dict(cursor.fetchall())

def full_resync_channel_members(channel_id: int, member_ids: list[int]):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE channel_id = ?", (channel_id,))
        if member_ids:
            cursor.executemany("INSERT OR IGNORE INTO subscriptions (user_id, channel_id) VALUES (?, ?)", [(user_id, channel_id) for user_id in member_ids])
        conn.commit()

# --- Новые функции для управления администраторами ---

def add_admin(user_id: int) -> bool:
    """Добавляет нового администратора. Возвращает True, если успешно."""
    with db_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (user_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Такой админ уже существует
            return False

def remove_admin(user_id: int) -> bool:
    """Удаляет администратора. Возвращает True, если успешно."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_admins() -> list[int]:
    """Возвращает список ID всех администраторов."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins")
        return [row[0] for row in cursor.fetchall()]

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None
