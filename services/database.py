# c:\Users\Lenovo\Desktop\bottravel\services\database.py

import sqlite3
import logging

DB_NAME = 'bot_database.db'

def get_db_connection():
    """Устанавливает соединение с базой данных."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует таблицы в базе данных, если они не существуют."""
    conn = get_db_connection()
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
    conn.close()

# --- Функции для пользователей и подписок (остаются без изменений) ---

def add_user(user_id: int, username: str, first_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )
    conn.commit()
    conn.close()

def add_subscription(user_id: int, channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO subscriptions (user_id, channel_id) VALUES (?, ?)", (user_id, channel_id))
    conn.commit()
    conn.close()

def remove_subscription(user_id: int, channel_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE user_id = ? AND channel_id = ?", (user_id, channel_id))
    conn.commit()
    conn.close()

def get_user_ids_by_channel(channel_id: int) -> list[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM subscriptions WHERE channel_id = ?", (channel_id,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_all_users() -> list[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_channel_stats() -> dict[int, int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, COUNT(user_id) FROM subscriptions GROUP BY channel_id")
    stats = dict(cursor.fetchall())
    conn.close()
    return stats

def full_resync_channel_members(channel_id: int, member_ids: list[int]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE channel_id = ?", (channel_id,))
    if member_ids:
        cursor.executemany("INSERT OR IGNORE INTO subscriptions (user_id, channel_id) VALUES (?, ?)", [(user_id, channel_id) for user_id in member_ids])
    conn.commit()
    conn.close()

# --- Новые функции для управления администраторами ---

def add_admin(user_id: int) -> bool:
    """Добавляет нового администратора. Возвращает True, если успешно."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Такой админ уже существует
        return False
    finally:
        conn.close()

def remove_admin(user_id: int) -> bool:
    """Удаляет администратора. Возвращает True, если успешно."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    deleted_rows = cursor.rowcount
    conn.close()
    return deleted_rows > 0

def get_all_admins() -> list[int]:
    """Возвращает список ID всех администраторов."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = [row[0] for row in cursor.fetchall()]
    conn.close()
    return admins

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    admins = get_all_admins()
    return user_id in admins
