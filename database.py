import sqlite3

def get_connection():
    conn = sqlite3.connect("bot_database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Таблицы для пользователей, групп, XP, модерации
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT);
        CREATE TABLE IF NOT EXISTS group_members (
            user_id INTEGER, chat_id INTEGER, xp INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
            wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, games_played INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        );
        CREATE TABLE IF NOT EXISTS anti_sticker (user_id INTEGER, chat_id INTEGER, PRIMARY KEY (user_id, chat_id));
        CREATE TABLE IF NOT EXISTS moderation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, moderator_id INTEGER, 
            user_id INTEGER, action TEXT, reason TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

def update_xp(user_id, chat_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE group_members SET xp = xp + ?, games_played = games_played + 1 WHERE user_id = ? AND chat_id = ?", (amount, user_id, chat_id))
    conn.commit()
    conn.close()
